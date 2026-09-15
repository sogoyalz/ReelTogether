"""Regression cases from the September reliability review."""
import hashlib
import hmac
import json
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException, Response
from starlette.requests import Request
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
import test_accounts as accounts
from app.api import accounts as routes
from app.core.config import settings
from app.db.base import Base
from app.models.account import Account, LoginSession
from app.services.authentication import _attempts, hash_password, token_digest, throttle_auth, verify_password
from app.services.client_identity import client_identity
from app.services.omdb import _normalize_str
from backup_health import backup_healthy
from backup_worker import backup_once


def request(token="", extra=None):
    headers={"origin":accounts.ORIGIN,"x-movie-client":token,**(extra or {})}
    return Request({"type":"http","method":"POST","path":"/api/auth/login","headers":[(k.encode(),v.encode('latin1')) for k,v in headers.items()],"client":("frontend-proxy",1)})


def signed_token():
    identity=str(uuid.uuid4())
    return identity+"."+hmac.new(settings.PROXY_SHARED_SECRET.encode(),identity.encode(),hashlib.sha256).hexdigest()


class AuthenticationRaceTests(unittest.TestCase):
    def test_reset_wins_against_inflight_login_including_password_rehash(self):
        for rehash in (False,True):
            with self.subTest(rehash=rehash), tempfile.TemporaryDirectory() as temporary:
                _attempts.clear()
                engine=create_engine('sqlite:///'+str(Path(temporary)/'race.sqlite'))
                Base.metadata.create_all(engine)
                code='r'*43
                with Session(engine) as db:
                    db.add(Account(username='alice',password_hash=hash_password(accounts.PASSWORD),recovery_hash=token_digest(code)))
                    db.commit()
                def finish_verification_then_reset(account,password):
                    valid=verify_password(account,password)
                    with Session(engine) as reset_db:
                        routes.recover(routes.RecoveryReset(username='alice',password='replacement-password-123',recovery_code=code),request(),Response(),reset_db)
                    return valid
                with Session(engine) as db, patch.object(routes,'verify_password',side_effect=finish_verification_then_reset), patch.object(type(routes.passwords),'check_needs_rehash',return_value=rehash):
                    response=Response()
                    with self.assertRaises(HTTPException) as caught:
                        routes.login(routes.Credentials(username='alice',password=accounts.PASSWORD),request(),response,db)
                    self.assertEqual(caught.exception.status_code,401)
                    self.assertNotIn('set-cookie',response.headers)
                with Session(engine) as db:
                    self.assertEqual(db.scalar(select(func.count()).select_from(LoginSession)),0)
                    account=db.scalar(select(Account))
                    self.assertTrue(verify_password(account,'replacement-password-123'))
                    self.assertFalse(verify_password(account,accounts.PASSWORD))
                engine.dispose()
                _attempts.clear()

    def test_proxy_users_have_independent_limits_but_account_limits_are_shared(self):
        _attempts.clear()
        try:
            with patch.object(settings,'PROXY_SHARED_SECRET','test-only-proxy-secret'):
                for i in range(100): throttle_auth(request(signed_token()),f'user{i}')
                for i in range(10): throttle_auth(request(signed_token()),'same_user')
                with self.assertRaises(HTTPException) as caught: throttle_auth(request(signed_token()),'same_user')
                self.assertEqual(caught.exception.status_code,429)
                token=signed_token()
                for i in range(60): throttle_auth(request(token),f'limited{i}')
                with self.assertRaises(HTTPException): throttle_auth(request(token),'limited60')
        finally: _attempts.clear()

    def test_forged_and_non_ascii_proxy_identifiers_fall_back_to_connection(self):
        with patch.object(settings,'PROXY_SHARED_SECRET','test-only-proxy-secret'):
            for token in ['x'*36+'.'+'0'*64,str(uuid.uuid4())+'.'+'é'*64,'untrusted']:
                self.assertEqual(client_identity(request(token,{'x-forwarded-for':'1.2.3.4'})),'ip:frontend-proxy')
            self.assertTrue(client_identity(request(signed_token())).startswith('browser:'))


class MetadataRepairTests(unittest.TestCase):
    setUp=accounts.AccountTests.setUp
    tearDown=accounts.AccountTests.tearDown
    register=accounts.AccountTests.register

    def test_malformed_metadata_does_not_break_browse_or_watchlist(self):
        from app.models.movie import Movie
        headers=self.register(self.alice,'alice')
        self.alice.put(f'/api/watchlist/{self.movie_id}',headers=headers)
        for metadata in [{'imdb_rating':{},'runtime':[],'rated':True,'rotten_tomatoes':False},['unexpected'],'unexpected']:
            self.db.get(Movie,self.movie_id).provider_metadata=metadata
            self.db.commit()
            overview=self.alice.get(f'/api/ai/movie/{self.movie_id}')
            self.assertEqual(overview.status_code,200,overview.text)
            for path in ['/api/movies/browse','/api/watchlist']:
                response=self.alice.get(path)
                self.assertEqual(response.status_code,200,response.text)
                items=response.json()['items']
                item=items[0]['movie'] if path.endswith('watchlist') else items[0]
                for field in ('imdb_rating','runtime','rated','rotten_tomatoes'):self.assertIsNone(item[field])
                self.assertEqual(item['field_sources']['imdb_rating'],'missing')

    def test_provider_outage_keeps_stored_metadata(self):
        from urllib.error import URLError
        from app.models.movie import Movie
        from app.services import omdb
        movie=self.db.get(Movie,self.movie_id)
        movie.provider_metadata={'imdb_rating':'8.3','runtime':'120 min'}
        omdb._CACHE.clear()
        with patch.object(settings,'OMDB_API_KEY','test-only-key'), patch.object(omdb,'urlopen',side_effect=URLError('offline')):
            self.assertEqual(omdb.fetch_movie_metadata(movie)['imdb_rating'],'8.3')
            self.assertEqual(omdb.fetch_movie_metadata(movie)['runtime'],'120 min')
        omdb._CACHE.clear()

    def test_valid_numeric_metadata_is_normalized_without_serializing_objects(self):
        for value in [{},[],True,float('nan'),float('inf'),'Infinity','N/A']:
            self.assertIsNone(_normalize_str(value))
        self.assertEqual(_normalize_str(8.2),'8.2')
        self.assertEqual(_normalize_str(' 120 min '),'120 min')


class BackupHealthRepairTests(unittest.TestCase):
    def test_deleted_or_changed_backup_is_unhealthy(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source.sqlite';directory=root/'backups'
            with sqlite3.connect(source) as db:db.execute('CREATE TABLE sample (id INTEGER)')
            status=backup_once(source,directory)
            self.assertTrue(backup_healthy(directory))
            backup=directory/status['backup'];original=backup.read_bytes()
            backup.write_bytes(original+b'corruption')
            self.assertFalse(backup_healthy(directory))
            backup.write_bytes(original);backup.unlink()
            self.assertFalse(backup_healthy(directory))

    def test_malformed_or_stale_status_is_unhealthy(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            for status in [[],{}, {'ok':True,'verified_at':time.time(),'backup':'../outside.sqlite'}, {'ok':True,'verified_at':0,'backup':'missing.sqlite'}]:
                (directory/'status.json').write_text(json.dumps(status))
                self.assertFalse(backup_healthy(directory))


class SchemaAndDateTests(unittest.TestCase):
    def test_readiness_rejects_an_unmigrated_room_schema(self):
        from app.models.movie_night import MovieNight
        from app.services.schema_health import assert_schema_ready
        from sqlalchemy.exc import OperationalError
        engine=create_engine('sqlite://')
        Base.metadata.create_all(engine)
        with Session(engine) as db:assert_schema_ready(db)
        MovieNight.__table__.drop(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql('CREATE TABLE movie_nights (id TEXT PRIMARY KEY)')
        with Session(engine) as db:
            with self.assertRaises(OperationalError):assert_schema_ready(db)
        engine.dispose()

    def test_release_today_is_not_marked_as_future(self):
        from datetime import date
        from app.models.movie import Movie
        from app.services.movie_data import build_movie_data_contract
        movie=Movie(id=999,tmdb_id=999,title='Today',slug='today',release_date=date.today(),status='released',genres=[])
        result=build_movie_data_contract(movie)
        self.assertEqual(result['status'],'released')
        self.assertFalse(any('future' in warning for warning in result['warnings']))
