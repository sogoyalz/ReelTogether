"""Production regressions; disposable databases, no providers or credentials."""
import unittest,threading
import test_accounts as accounts
from datetime import date
from unittest.mock import patch
from fastapi import HTTPException
from sqlalchemy import event,select
from app.core.config import settings
from app.models.movie import Movie
from app.services import authentication as auth
from app.services.catalog_assistant import recommend
from app.schemas.assistant import ChatRequest
from app.services.job_fencing import fenced_job,LeaseLost
from app.services.wikidata import fetch_movie_wikidata
import test_durable_operations as durable
import test_movie_nights as nights

class AdmissionTests(unittest.TestCase):
    setUp=accounts.AccountTests.setUp
    tearDown=accounts.AccountTests.tearDown
    register=accounts.AccountTests.register
    def test_shared_auth_outage_fails_closed(self):
        with patch.object(settings,'ENVIRONMENT','production'),patch.object(auth,'sliding_window_allow',side_effect=RuntimeError('unavailable')):
            r=self.alice.post('/api/auth/register',json={'username':'alice','password':accounts.PASSWORD})
        self.assertEqual(r.status_code,503);self.assertEqual(r.headers['retry-after'],'5')
        from app.models.account import Account
        self.assertIsNone(self.db.scalar(select(Account)))
    def test_peer_budget_survives_browser_rotation_and_spoofed_forwarded_ip(self):
        calls=[]
        def limit(key,budget,seconds,**kwargs):calls.append((key,budget,kwargs));return budget!=300,60
        with patch.object(settings,'ENVIRONMENT','production'),patch.object(auth,'sliding_window_allow',side_effect=limit):
            r=self.alice.post('/api/auth/register',json={'username':'alice','password':accounts.PASSWORD},headers={'X-Forwarded-For':'198.51.100.3','X-Movie-Peer':'198.51.100.4.invalid'})
        self.assertEqual(r.status_code,429);self.assertEqual(len(calls),3)
        self.assertTrue(all(c[2]['required'] and 'alice' not in c[0] for c in calls))
    def test_password_work_never_waits_for_a_slot(self):
        with auth.password_admission(),auth.password_admission():
            with self.assertRaises(HTTPException) as e:auth.hash_password('should-not-be-hashed')
            self.assertEqual(e.exception.status_code,503)
        with auth.password_admission():pass
    def test_peer_requires_its_own_signature(self):
        import hashlib,hmac
        from starlette.requests import Request
        from app.services.client_identity import peer_identity
        peer='2001:db8::1';secret='test-only-signing-key'
        signature=hmac.new(secret.encode(),('peer:'+peer).encode(),hashlib.sha256).hexdigest()
        def request(v):return Request({'type':'http','headers':[(b'x-movie-peer',v.encode())],'client':('127.0.0.1',1)})
        with patch.object(settings,'PROXY_SHARED_SECRET',secret):
            self.assertEqual(peer_identity(request(peer+'.'+signature)),peer)
            self.assertEqual(peer_identity(request(peer+'.'+'0'*64)),'127.0.0.1')

class FencingTests(unittest.TestCase):
    setUp=durable.QueueTests.setUp
    tearDown=durable.QueueTests.tearDown
    expire=durable.QueueTests.expire
    def test_stale_handler_catalog_commit_rolls_back(self):
        self.queue.enqueue('tmdb-sync');old=self.queue.claim();self.expire(old);new=self.queue.claim()
        with self.factory() as db:
            with self.assertRaises(LeaseLost):
                with fenced_job(old,threading.Event()):
                    db.add(Movie(tmdb_id=123,title='Stale',slug='stale',release_date=date(2020,1,1),genres=[]));db.commit()
            db.rollback();self.assertIsNone(db.scalar(select(Movie)))
        with self.factory() as db,fenced_job(new,threading.Event()):
            db.add(Movie(tmdb_id=124,title='Current',slug='current',release_date=date(2020,1,1),genres=[]));db.commit()
        with self.factory() as db:self.assertEqual(db.scalar(select(Movie.title)),'Current')
    def test_heartbeat_failure_cancels_commit(self):
        self.queue.enqueue('tmdb-sync');job=self.queue.claim();lost=threading.Event();lost.set()
        with self.factory() as db,fenced_job(job,lost):
            with self.assertRaises(LeaseLost):db.commit()

class RoomVersionTests(unittest.TestCase):
    setUp=nights.MovieNightTests.setUp
    tearDown=nights.MovieNightTests.tearDown
    register=nights.MovieNightTests.register
    setup_room=nights.MovieNightTests.setup_room
    join_start=nights.MovieNightTests.join_start
    def test_private_revision_changes_with_votes(self):
        self.setup_room();self.assertEqual(self.bob.get(self.path+'/version').status_code,404)
        r=self.alice.get(self.path+'/version');self.assertEqual(set(r.json()),{'revision','state','expired'})
        self.assertIn('no-store',r.headers['cache-control']);self.assertEqual(r.json()['revision'],self.alice.get(self.path).json()['revision'])
        movies=self.join_start();before=self.bob.get(self.path+'/version').json()['revision']
        r=self.alice.put(self.path+'/vote',json={'movie_id':movies[0]['id'],'round_id':1,'choice':'yes'},headers=self.a)
        self.assertEqual(r.status_code,200,r.text)
        self.assertNotEqual(before,self.bob.get(self.path+'/version').json()['revision'])
        detail=self.bob.get(self.path).json();self.assertEqual(detail['my_votes'],{});self.assertEqual(detail['results'],[])

class RetrievalTests(unittest.TestCase):
    setUp=accounts.AccountTests.setUp
    tearDown=accounts.AccountTests.tearDown
    def test_bounded_hydration_and_exact_ranking(self):
        self.db.delete(self.db.get(Movie,self.movie_id));self.db.commit()
        self.db.execute(Movie.__table__.insert(),[{'tmdb_id':1000+i,'title':f'Film {i}','slug':f'film-{i}','release_date':date(2020,1,1),'status':'released','genres':['Drama'],'tmdb_popularity':float(i),'overview':'x'*10000,'provider_metadata':{}} for i in range(1000)])
        self.db.commit();self.db.expunge_all();peak=[0];queries=[]
        def loaded(db,obj):peak[0]=max(peak[0],len(db.identity_map))
        def query(c,cu,s,p,ctx,many):
            if s.lstrip().upper().startswith('SELECT'):queries.append(s)
        event.listen(self.db,'loaded_as_persistent',loaded);event.listen(self.engine,'before_cursor_execute',query)
        try:r=recommend(self.db,ChatRequest(message='recommend'))
        finally:event.remove(self.db,'loaded_as_persistent',loaded);event.remove(self.engine,'before_cursor_execute',query)
        self.assertEqual(r['total_matches'],1000);self.assertEqual([i['movie']['title'] for i in r['items']],[f'Film {i}' for i in range(999,993,-1)])
        self.assertLessEqual(peak[0],260);self.assertTrue(all('movies.overview' not in q for q in queries))
    def test_unverified_wikidata_never_searches_titles(self):
        m=Movie(title='Ambiguous',slug='ambiguous',release_date=date(2020,1,1),provider_metadata={})
        with patch('app.services.wikidata._search_entity',side_effect=AssertionError('search')),patch('app.services.wikidata._fetch_entity',side_effect=AssertionError('network')):self.assertIsNone(fetch_movie_wikidata(m))
        m.provider_metadata={'wikidata_id':'Q999999','imdb_id':'tt1234567'}
        with patch('app.services.wikidata._fetch_entity',return_value={'claims':{'P345':[{'mainsnak':{'datavalue':{'value':'tt7654321'}}}]}}):self.assertIsNone(fetch_movie_wikidata(m))

class ErasureRecoveryTests(unittest.TestCase):
    setUp=accounts.AccountTests.setUp
    tearDown=accounts.AccountTests.tearDown
    register=accounts.AccountTests.register
    def test_signed_receipts_replay_without_deleting_reused_account_ids(self):
        import tempfile,json
        from pathlib import Path
        from app.models.account import Account,AccountErasure
        from app.services.erasure_ledger import publish_pending,replay
        from app.services.authentication import now
        self.register(self.alice,'alice');original=self.db.scalar(select(Account));identity=original.erasure_key;original_id=original.id
        self.db.add(AccountErasure(erasure_key=identity,requested_at=now()));self.db.commit()
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'deletions.jsonl';key='test-erasure-ledger-key-that-is-long-enough'
            with patch.object(settings,'ERASURE_LEDGER_PATH',str(path)),patch.object(settings,'ERASURE_LEDGER_KEY',key):
                self.assertEqual(publish_pending(self.db),1);self.assertEqual(publish_pending(self.db),0)
            self.assertNotIn('alice',path.read_text());self.assertEqual(replay(self.db,path,key),1)
            self.db.add(Account(id=original_id,username='new_account',password_hash='test-only'));self.db.commit()
            self.assertEqual(replay(self.db,path,key),0)
            self.assertIsNotNone(self.db.scalar(select(Account)))
            record=json.loads(path.read_text());record['signature']='0'*64;path.write_text(json.dumps(record)+'\n')
            with self.assertRaises(ValueError):replay(self.db,path,key)
            self.assertIsNotNone(self.db.scalar(select(Account)))
    def test_production_catalog_write_requires_worker_context(self):
        with patch.object(settings,'ENVIRONMENT','production'):
            self.db.add(Movie(tmdb_id=54321,title='Unfenced',slug='unfenced',release_date=date(2020,1,1),genres=[]))
            with self.assertRaises(LeaseLost):self.db.commit()
        self.db.rollback()

class MetricsContractTests(unittest.TestCase):
    setUp=accounts.AccountTests.setUp
    tearDown=accounts.AccountTests.tearDown
    def test_prometheus_is_protected_and_has_cumulative_buckets(self):
        from app.services.operational_metrics import prometheus,record_request
        record_request('GET','/test/{id}',503,15)
        output=prometheus()
        self.assertIn('reeltogether_http_duration_ms_bucket{method="GET",route="/test/{id}",le="+Inf"} 1',output)
        with patch.object(settings,'ADMIN_API_KEY','test-only-admin-key'),patch('app.db.session.SessionLocal',return_value=self.db):
            self.assertEqual(self.alice.get('/api/admin/metrics/prometheus').status_code,401)
            r=self.alice.get('/api/admin/metrics/prometheus',headers={'X-Admin-Key':'test-only-admin-key'})
            self.assertEqual(r.status_code,200,r.text)
            self.assertIn('no-store',r.headers['cache-control'])
            self.assertIn('reeltogether_queue_oldest_seconds',r.text)
            self.assertNotIn('test-only-admin-key',r.text)

class RetentionTests(unittest.TestCase):
    setUp=accounts.AccountTests.setUp
    tearDown=accounts.AccountTests.tearDown
    register=accounts.AccountTests.register
    def test_dry_run_preserves_rows_and_apply_only_removes_expired_history(self):
        from datetime import timedelta
        from app.models.account import Account,LoginSession
        from app.models.movie_night import MovieNight,NightMember,NightVote
        from app.models.jobs import BackgroundJob
        from app.services.authentication import now
        from retention import purge
        self.register(self.alice,'alice');owner=self.db.scalar(select(Account.id))
        for identity,expiry in [('old',now()-timedelta(days=31)),('active',now()+timedelta(days=1))]:
            self.db.add(MovieNight(id=identity,host_id=owner,title=identity,invite_hash=identity,expires_at=expiry,state='lobby',candidates=[]))
        self.db.flush()
        self.db.add(NightMember(room_id='old',account_id=owner,genres=[],favorites=[]))
        self.db.add(NightVote(room_id='old',account_id=owner,movie_id=self.movie_id,choice='yes'))
        self.db.add(LoginSession(token_hash='expired',account_id=owner,csrf_token='unused',expires_at=now()-timedelta(days=1)))
        self.db.add(BackgroundJob(id='old-job',name='tmdb-sync',status='completed',queued_at=now()-timedelta(days=40),available_at=now(),finished_at=now()-timedelta(days=31),attempts=1))
        self.db.commit()
        report=purge(self.db)
        self.assertFalse(report['applied']);self.assertIsNotNone(self.db.get(MovieNight,'old'))
        report=purge(self.db,apply=True)
        self.db.expire_all()
        self.assertIsNone(self.db.get(MovieNight,'old'));self.assertIsNotNone(self.db.get(MovieNight,'active'))
        self.assertEqual(list(self.db.scalars(select(NightVote))),[])
        self.assertIsNotNone(self.db.get(Account,owner));self.assertIsNotNone(self.db.get(Movie,self.movie_id))
        self.assertIsNone(self.db.get(LoginSession,'expired'));self.assertIsNone(self.db.get(BackgroundJob,'old-job'))

class ErasureFailureTests(unittest.TestCase):
    setUp=accounts.AccountTests.setUp
    tearDown=accounts.AccountTests.tearDown
    register=accounts.AccountTests.register
    def test_failed_receipt_publish_preserves_the_durable_deletion_outbox(self):
        from app.models.account import Account,AccountErasure
        headers=self.register(self.alice,'alice')
        with patch('app.services.erasure_ledger.publish_pending',side_effect=OSError('test failure')):
            r=self.alice.post('/api/auth/delete-account',json={'password':accounts.PASSWORD},headers=headers)
        self.assertEqual(r.status_code,503);self.assertIn('Account deleted',r.json()['detail'])
        self.assertIsNone(self.db.scalar(select(Account)))
        self.assertIsNone(self.db.scalar(select(AccountErasure)).exported_at)
