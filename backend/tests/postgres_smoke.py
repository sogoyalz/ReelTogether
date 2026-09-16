"""Integration smoke test against the disposable CI PostgreSQL database."""
import os
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.parse import urlparse

url = os.environ.get('POSTGRES_TEST_URL', '')
parsed = urlparse(url)
if parsed.hostname not in {'localhost', '127.0.0.1'} or parsed.path != '/reeltest':
    raise SystemExit('Use an explicit local disposable reeltest database')
os.environ.update(DATABASE_URL=url, ENABLE_JOB_WORKER='false', ENABLE_PERIODIC_SYNC='false',
                  ENABLE_STARTUP_SYNC='false', AUTO_CREATE_TABLES='false', ENABLE_RATE_LIMIT='false',
                  ENABLE_ASSISTANT_AI='false', ENABLE_RAG='false', ENABLE_USER_FEATURES='false',
                  ENVIRONMENT='development', TRUSTED_HOSTS='["localhost"]',
                  CORS_ORIGINS='["http://localhost:3000"]', REDIS_URL='', TMDB_API_KEY='',
                  OMDB_API_KEY='', YOUTUBE_API_KEY='')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for args in [('upgrade', 'head'), ('check',)]:
    subprocess.run([sys.executable, '-m', 'alembic', *args], check=True)
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.db.session import SessionLocal
from app.services.bootstrap import seed_database_if_empty
from app.services.background_jobs import JobRegistry
from app.models.movie import Movie
from main import app

with SessionLocal() as db:
    seed_database_if_empty(db)
    movie_id = db.scalar(select(Movie.id).limit(1))
with TestClient(app, base_url='http://localhost', headers={'Origin':'http://localhost:3000'}) as client:
    def checked(response, status=200):
        assert response.status_code == status, (response.status_code, response.text)
        return response.json()
    checked(client.get('/health/ready'))
    assert checked(client.get('/api/movies/browse'))['total'] > 0
    account = checked(client.post('/api/auth/register', json={'username':'pg_'+uuid.uuid4().hex[:12],
                                                            'password':'disposable-test-password-123'}), 201)
    headers = {'X-CSRF-Token':account['csrf_token']}
    checked(client.put(f'/api/watchlist/{movie_id}', headers=headers))
    assert checked(client.get('/api/watchlist'))['total'] == 1
    room = checked(client.post('/api/movie-nights', json={'title':'PostgreSQL smoke'}, headers=headers), 201)
    assert checked(client.get('/api/movie-nights/'+room['id']))['title'] == 'PostgreSQL smoke'
queue = JobRegistry()
job = queue.enqueue('tmdb-sync')
claim = queue.claim()
assert claim.id == job.id
assert queue.finish(claim.id, claim.lease_token, result={'verified':True})
assert JobRegistry().get(job.id).status == 'completed'
print('PostgreSQL: migrations, readiness, catalog, accounts, watchlists, rooms, and durable jobs passed')
