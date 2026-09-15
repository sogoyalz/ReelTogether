import os
os.environ.update(ENABLE_JOB_WORKER="false", ENABLE_PERIODIC_SYNC="false", ENABLE_ASSISTANT_AI="false", OPENAI_API_KEY="", DATABASE_URL="sqlite://", REDIS_URL="", ENABLE_STARTUP_SYNC="false", ENABLE_RATE_LIMIT="false", TRUSTED_HOSTS='["localhost"]', TMDB_API_KEY="", OMDB_API_KEY="", YOUTUBE_API_KEY="", ENVIRONMENT="development")
import unittest
from datetime import timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.models.account import Account, LoginSession, WatchlistEntry
from app.services.authentication import COOKIE, _attempts, now, token_digest
from app.services.mock_data import build_models
from main import app

ORIGIN = "http://localhost:3000"
PASSWORD = "testing-long-password-123"


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        @event.listens_for(self.engine, 'connect')
        def enable_fk(connection, _): connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        movie, analytics = build_models()[0]
        movie.analytics_snapshots.append(analytics)
        self.db.add(movie)
        self.db.commit()
        self.movie_id = movie.id
        app.dependency_overrides[get_db] = lambda: self.db
        self.alice = TestClient(app, base_url="http://localhost", headers={"Origin": ORIGIN})
        self.bob = TestClient(app, base_url="http://localhost", headers={"Origin": ORIGIN})
        _attempts.clear()

    def tearDown(self):
        self.alice.close(); self.bob.close()
        app.dependency_overrides.clear()
        self.db.close(); self.engine.dispose()
        _attempts.clear()

    def register(self, client, username):
        response = client.post('/api/auth/register', json={"username": username, "password": PASSWORD})
        self.assertEqual(response.status_code, 201, response.text)
        return {"X-CSRF-Token": response.json()['csrf_token']}

    def test_private_watchlists_and_ownership(self):
        a = self.register(self.alice, 'alice')
        b = self.register(self.bob, 'bob')
        path = f'/api/watchlist/{self.movie_id}'
        self.assertEqual(self.alice.put(path, headers=a).status_code, 200)
        self.assertEqual(self.alice.get('/api/watchlist').json()['total'], 1)
        self.assertEqual(self.bob.get('/api/watchlist').json()['total'], 0)
        self.assertEqual(self.bob.patch(path, json={'status':'watched'}, headers=b).status_code, 404)
        self.bob.delete(path, headers=b)
        self.assertEqual(self.alice.get('/api/watchlist').json()['total'], 1)
        self.assertEqual(self.alice.patch(path, json={'status':'watched', 'account_id':2}, headers=a).status_code, 422)

    def test_watchlist_query_count_is_bounded_and_stale_page_is_clamped(self):
        self.register(self.alice, 'alice')
        account_id = self.db.scalar(select(Account.id))
        for movie, analytics in build_models()[1:9]:
            movie.analytics_snapshots.append(analytics)
            self.db.add(movie)
            self.db.flush()
            self.db.add(WatchlistEntry(account_id=account_id, movie_id=movie.id, status="planned"))
        self.db.commit()
        self.db.expunge_all()
        statements = []
        def count_sql(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)
        event.listen(self.engine, "before_cursor_execute", count_sql)
        try:
            response = self.alice.get('/api/watchlist?page_size=48')
        finally:
            event.remove(self.engine, "before_cursor_execute", count_sql)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()['items']), 8)
        # Authentication, count, joined page, latest analytics; never per-movie reads.
        self.assertLessEqual(len(statements), 5, statements)
        last_page = self.alice.get('/api/watchlist?page=99&page_size=3').json()
        self.assertEqual(last_page['page'], 3)
        self.assertEqual(len(last_page['items']), 2)

    def test_recovery_code_requires_reauthentication_and_csrf(self):
        headers = self.register(self.alice, 'alice')
        self.assertEqual(self.alice.post('/api/auth/recovery-code', json={'password': PASSWORD}).status_code, 403)
        self.assertEqual(self.alice.post('/api/auth/recovery-code', json={'password': 'incorrect-password'}, headers=headers).status_code, 401)
        response = self.alice.post('/api/auth/recovery-code', json={'password': PASSWORD}, headers=headers)
        self.assertEqual(response.status_code, 200)
        code = response.json()['recovery_code']
        account = self.db.scalar(select(Account))
        self.assertNotEqual(account.recovery_hash, code)
        self.assertEqual(account.recovery_hash, token_digest(code))
        self.assertIn('no-store', response.headers['cache-control'])

    def test_recovery_is_single_use_and_revokes_all_sessions(self):
        headers = self.register(self.alice, 'alice')
        old_cookie = self.alice.cookies.get(COOKIE)
        code = self.alice.post('/api/auth/recovery-code', json={'password': PASSWORD}, headers=headers).json()['recovery_code']
        payload = {'username': 'alice', 'password': 'replacement-password-123', 'recovery_code': code}
        self.assertEqual(self.bob.post('/api/auth/recover', json=payload).status_code, 200)
        self.bob.cookies.set(COOKIE, old_cookie)
        self.assertEqual(self.bob.get('/api/auth/me').status_code, 401)
        self.assertEqual(self.bob.post('/api/auth/recover', json=payload).status_code, 400)
        self.assertEqual(self.alice.post('/api/auth/login', json={'username':'alice','password':PASSWORD}).status_code, 401)
        self.assertEqual(self.alice.post('/api/auth/login', json={'username':'alice','password':payload['password']}).status_code, 200)

    def test_rotated_recovery_code_and_unknown_user_are_rejected(self):
        headers = self.register(self.alice, 'alice')
        first = self.alice.post('/api/auth/recovery-code', json={'password': PASSWORD}, headers=headers).json()['recovery_code']
        second = self.alice.post('/api/auth/recovery-code', json={'password': PASSWORD}, headers=headers).json()['recovery_code']
        payload = {'username':'alice', 'password':PASSWORD, 'recovery_code':first}
        rejected = self.bob.post('/api/auth/recover', json=payload)
        self.assertEqual(rejected.status_code, 400)
        unknown = self.bob.post('/api/auth/recover', json={**payload, 'username':'nobody'})
        self.assertEqual(rejected.json(), unknown.json())
        self.assertEqual(self.bob.post('/api/auth/recover', json={**payload, 'recovery_code':second}, headers={'Origin':'https://evil.example'}).status_code, 403)

    def test_duplicate_saves_are_idempotent(self):
        headers = self.register(self.alice, 'alice')
        for _ in range(2): self.alice.put(f'/api/watchlist/{self.movie_id}', headers=headers)
        self.assertEqual(len(list(self.db.scalars(select(WatchlistEntry)))), 1)

    def test_csrf_and_cross_origin_requests_are_rejected(self):
        headers = self.register(self.alice, 'alice')
        path = f'/api/watchlist/{self.movie_id}'
        self.assertEqual(self.alice.put(path).status_code, 403)
        self.assertEqual(self.alice.put(path, headers={'X-CSRF-Token':'wrong'}).status_code, 403)
        self.assertEqual(self.alice.put(path, headers={**headers, 'Origin':'https://evil.example'}).status_code, 403)
        self.assertEqual(self.bob.post('/api/auth/login', json={'username':'alice','password':PASSWORD}, headers={'Origin':'https://evil.example'}).status_code, 403)

    def test_password_hash_and_session_storage(self):
        self.register(self.alice, 'alice')
        account = self.db.scalar(select(Account))
        self.assertTrue(account.password_hash.startswith('$argon2id$'))
        session = self.db.scalar(select(LoginSession))
        token = self.alice.cookies.get(COOKIE)
        self.assertEqual(session.token_hash, token_digest(token))
        self.assertNotEqual(session.token_hash, token)

    def test_logout_revokes_replayed_cookie(self):
        headers = self.register(self.alice, 'alice')
        token = self.alice.cookies.get(COOKIE)
        self.assertEqual(self.alice.post('/api/auth/logout', headers=headers).status_code, 200)
        self.bob.cookies.set(COOKIE, token)
        self.assertEqual(self.bob.get('/api/auth/me').status_code, 401)

    def test_expired_session_is_rejected(self):
        self.register(self.alice, 'alice')
        session = self.db.scalar(select(LoginSession)); session.expires_at = now()-timedelta(seconds=1); self.db.commit()
        self.assertEqual(self.alice.get('/api/watchlist').status_code, 401)

    def test_invalid_credentials_and_username_case(self):
        self.register(self.alice, 'Alice')
        failed = self.bob.post('/api/auth/login', json={'username':'alice','password':'wrong-password-123'})
        self.assertEqual(failed.status_code, 401)
        success = self.bob.post('/api/auth/login', json={'username':'ALICE','password':PASSWORD})
        self.assertEqual(success.status_code, 200)
        self.assertEqual(success.json()['user']['username'], 'alice')

    def test_cookies_and_private_cache(self):
        with patch.object(settings, 'ENVIRONMENT', 'production'):
            response = self.alice.post('/api/auth/register', json={'username':'alice','password':PASSWORD})
        cookie = response.headers['set-cookie'].lower()
        for value in ['httponly', 'secure', 'samesite=strict', 'path=/api']: self.assertIn(value, cookie)
        self.assertIn('no-store', response.headers['cache-control'])
        self.assertNotIn('password', response.text)

    def test_auth_is_required_and_user_id_cannot_be_supplied(self):
        self.assertEqual(self.alice.get('/api/watchlist?account_id=1').status_code, 401)
        self.assertEqual(self.alice.put(f'/api/watchlist/{self.movie_id}').status_code, 401)

    def test_throttling_cannot_be_bypassed_with_cookie_identity(self):
        self.register(self.alice, 'alice')
        statuses = [self.bob.post('/api/auth/login', json={'username':'alice','password':'wrong-password-123'}, headers={'X-Movie-Client':str(i)}).status_code for i in range(10)]
        self.assertEqual(statuses[-1], 429)
