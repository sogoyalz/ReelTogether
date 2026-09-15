"""Offline recovery, transfer integrity, and notification regressions."""
import os
import json
import tempfile
import unittest
from pathlib import Path
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.jobs import BackgroundJob
from app.services.background_jobs import JobRegistry, QueueFull, utcnow
from job_worker import execute_job
from offsite_backup import publish_backup, restore_offsite
from operations_monitor import notify_changes, deliver

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.engine=create_engine('sqlite:///'+self.temp.name+'/queue.sqlite',connect_args={'check_same_thread':False})
        Base.metadata.create_all(self.engine)
        self.factory=sessionmaker(self.engine)
        self.queue=JobRegistry(session_factory=self.factory)
    def tearDown(self):
        self.engine.dispose();self.temp.cleanup()
    def expire(self, job):
        with self.factory() as db:
            row=db.get(BackgroundJob,job.id)
            row.lease_until=utcnow()-timedelta(seconds=1)
            row.available_at=utcnow()-timedelta(seconds=1)
            db.commit()
    def test_restart_and_deduplication(self):
        first=self.queue.enqueue('tmdb-sync')
        other=JobRegistry(session_factory=self.factory)
        self.assertEqual(first.id,other.enqueue('tmdb-sync').id)
        claimed=other.claim()
        execute_job(other,claimed,{'tmdb-sync':lambda:{'count':2}})
        self.assertEqual(self.queue.get(first.id).result['count'],2)
        self.assertNotEqual(first.id,self.queue.enqueue('tmdb-sync').id)
    def test_competing_workers_claim_once(self):
        self.queue.enqueue('tmdb-sync')
        with ThreadPoolExecutor(2) as pool:
            claims=list(pool.map(lambda _:self.queue.claim(),range(2)))
        self.assertEqual(sum(job is not None for job in claims),1)
    def test_expired_worker_cannot_complete_reclaimed_job(self):
        self.queue.enqueue('tmdb-sync');old=self.queue.claim();self.expire(old)
        new=self.queue.claim()
        self.assertEqual(new.attempts,2)
        self.assertFalse(self.queue.finish(old.id,old.lease_token,result={'stale':True}))
        self.assertFalse(self.queue.heartbeat(old.id,old.lease_token))
        self.assertTrue(self.queue.heartbeat(new.id,new.lease_token))
        self.assertTrue(self.queue.finish(new.id,new.lease_token,result={}))
    def test_crashes_exhaust_retry_budget(self):
        job=self.queue.enqueue('tmdb-sync')
        for attempt in range(3):self.expire(self.queue.claim())
        self.assertIsNone(self.queue.claim())
        self.assertEqual(self.queue.get(job.id).status,'failed')
    def test_exception_retries_without_storing_secret(self):
        queued=self.queue.enqueue('tmdb-sync');job=self.queue.claim()
        def fail():raise ValueError('secret credential')
        execute_job(self.queue,job,{'tmdb-sync':fail})
        self.assertIsNone(self.queue.claim())
        row=self.queue.get(queued.id)
        self.assertEqual(row.error,'ValueError');self.assertEqual(row.status,'queued')
    def test_schedule_persists_and_queue_is_bounded(self):
        queue=JobRegistry(max_jobs=1,session_factory=self.factory)
        self.assertIsNotNone(queue.schedule_due('tmdb-sync'))
        self.assertIsNone(JobRegistry(session_factory=self.factory).schedule_due('tmdb-sync'))
        with self.assertRaises(QueueFull):queue.enqueue('youtube-refresh')
        with self.assertRaises(ValueError):queue.enqueue('arbitrary-code')
        job=queue.claim();queue.finish(job.id,job.lease_token,result={})
        queue.enqueue('youtube-refresh');self.assertEqual(len(queue.list()),1)

class FakeStorage:
    def __init__(self):self.objects={};self.corrupt=False;self.extra=None
    def upload_file(self,path,bucket,key,ExtraArgs):
        self.objects[key]=Path(path).read_bytes();self.extra=ExtraArgs
    def download_file(self,bucket,key,path):
        Path(path).write_bytes(b'corrupt' if self.corrupt else self.objects[key])

class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'source.sqlite'
        import sqlite3
        with sqlite3.connect(self.source) as db:
            db.execute('CREATE TABLE example (id INTEGER PRIMARY KEY)');db.execute('INSERT INTO example VALUES (1)')
        self.storage=FakeStorage()
        self.env=patch.dict(os.environ,{'BACKUP_S3_BUCKET':'test-bucket','BACKUP_S3_PREFIX':'test','BACKUP_S3_ENCRYPTION':'AES256'})
        self.env.start()
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_verified_round_trip_and_safe_restore(self):
        status=publish_backup(self.source,self.root,self.storage)
        self.assertTrue(status['ok']);self.assertEqual(self.storage.extra['ServerSideEncryption'],'AES256')
        destination=self.root/'restored.sqlite'
        restore_offsite(status['key'],status['sha256'],destination,self.storage)
        with self.assertRaises(ValueError):restore_offsite(status['key'],status['sha256'],destination,self.storage)
        self.assertTrue(destination.exists())
    def test_corruption_never_reports_success(self):
        self.storage.corrupt=True
        with self.assertRaises(ValueError):publish_backup(self.source,self.root,self.storage)
        self.assertFalse((self.root/'offsite-status.json').exists())
    def test_unconfigured_storage_is_inert(self):
        with patch.dict(os.environ,{'BACKUP_S3_BUCKET':''}):self.assertIsNone(publish_backup(self.source,self.root,self.storage))
        self.assertFalse(self.storage.objects)
    def test_local_retention_survives_upload_outage(self):
        from backup_worker import backup_once
        backups=self.root/'backups'
        with patch('backup_worker.publish_backup',side_effect=OSError('offline')):
            for _ in range(16):
                with self.assertRaises(OSError):backup_once(self.source,backups)
        self.assertEqual(len(list(backups.glob('catalog-*.sqlite'))),14)

class AlertTests(unittest.TestCase):
    def test_failure_recovery_and_deduplication(self):
        sent=[]
        def sender(component,healthy):sent.append((component,healthy));return True
        state=notify_changes({'worker':True},{},sender)
        self.assertEqual(sent,[])
        for healthy in (False,False,True,True):state=notify_changes({'worker':healthy},state,sender)
        self.assertEqual(sent,[('worker',False),('worker',True)])
    def test_failed_delivery_is_retried(self):
        state=notify_changes({'worker':False},{},lambda *_:False)
        self.assertNotIn('worker',state)
        self.assertEqual(notify_changes({'worker':False},state,lambda *_:True),{'worker':False})
    def test_endpoint_requires_https(self):
        with patch.dict(os.environ,{'ALERT_WEBHOOK_URL':'http://example.com'}):
            with self.assertRaises(ValueError):deliver('worker',False)
    def test_missing_worker_heartbeat_is_unhealthy(self):
        from job_health import worker_healthy
        self.assertFalse(worker_healthy('/nonexistent/reeltogether/heartbeat'))
