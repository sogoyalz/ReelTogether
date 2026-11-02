"""Adversarial public-read regressions against disposable SQLite data."""
import os
os.environ.update(ENVIRONMENT='development', DATABASE_URL='sqlite://', REDIS_URL='', ENABLE_STARTUP_SYNC='false', ENABLE_JOB_WORKER='false', ENABLE_RATE_LIMIT='false', TMDB_API_KEY='', OMDB_API_KEY='', YOUTUBE_API_KEY='', ENABLE_ASSISTANT_AI='false', OPENAI_API_KEY='')
import unittest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.session import get_db
from app.models.movie import Movie, MovieAnalytics
from main import app


class PublicReadAuditTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        for i, title in enumerate(['Été 100%_literal', 'Ordinary Film']):
            movie = Movie(tmdb_id=90001+i, slug=f'audit-{i}', title=title,
                          release_date=date(2020, 1, 1), genres=['Drama'], tmdb_popularity=10,
                          provider_metadata={}, enrichment_data={})
            movie.analytics_snapshots = [MovieAnalytics(snapshot_label='latest')]
            movie.analytics_snapshots += [MovieAnalytics(snapshot_label=f'day-{j}', snapshot_date=date(2020, 1, 1)+timedelta(days=j)) for j in range(100)]
            self.db.add(movie)
        self.db.commit()
        self.db.expunge_all()
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app, base_url='http://localhost')

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_autocomplete_uses_literal_search_characters_and_unicode(self):
        for query in ['%', '_literal', 'été']:
            with self.subTest(query=query):
                response = self.client.get('/api/search/suggest', params={'q': query})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([m['slug'] for m in response.json()], ['audit-0'])

    def test_core_movie_detail_hydrates_latest_not_history(self):
        for path in ['/api/movies/1', '/api/movies/slug/audit-0']:
            self.db.expunge_all()
            loaded = []
            def observed(row, _context): loaded.append(row.snapshot_label)
            event.listen(MovieAnalytics, 'load', observed)
            try:
                response = self.client.get(path)
            finally:
                event.remove(MovieAnalytics, 'load', observed)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(loaded, ['latest'], f'{path} hydrated {len(loaded)} analytics objects')
        history = self.client.get('/api/analytics/movie/1/history')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()['points']), 101)

    def test_discovery_never_hydrates_historical_snapshots(self):
        loaded = []
        def observed(row, _context): loaded.append(row.snapshot_label)
        event.listen(MovieAnalytics, 'load', observed)
        try:
            response = self.client.get('/api/search/dashboard')
        finally:
            event.remove(MovieAnalytics, 'load', observed)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(loaded, ['latest', 'latest'], f'Discovery hydrated {len(loaded)} analytics objects')
