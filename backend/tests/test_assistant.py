import os
os.environ.update(ENABLE_ASSISTANT_AI="false", OPENAI_API_KEY="", DATABASE_URL="sqlite://", REDIS_URL="", ENABLE_STARTUP_SYNC="false", ENABLE_RATE_LIMIT="false", TRUSTED_HOSTS='["localhost"]', TMDB_API_KEY="", OMDB_API_KEY="", YOUTUBE_API_KEY="", ENVIRONMENT="development")
import unittest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.session import get_db
from app.models.movie import Movie
from app.models.account import MovieFeedback
from app.schemas.assistant import ChatRequest, Filters
from app.services.catalog_assistant import parse_filters, recommend
from app.services.authentication import _attempts
from main import app


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        @event.listens_for(self.engine, 'connect')
        def fk(connection, _): connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        specs = [
            ('Space Seed', ['Science Fiction'], 110, 'en', 5),
            ('Space Match', ['Science Fiction'], 100, 'en', 10),
            ('Popular Drama', ['Drama'], 90, 'hi', 999),
            ('Scary Space', ['Science Fiction', 'Horror'], 95, 'en', 90),
            ('Unknown Metadata', ['Science Fiction'], None, None, 70),
            ('Long Space', ['Science Fiction'], 150, 'en', 80),
            ('Exactly Two Hours', ['Science Fiction'], 120, 'en', 60),
        ]
        for i, (title, genres, runtime, language, popularity) in enumerate(specs, 1):
            self.db.add(Movie(id=i, tmdb_id=i, title=title, slug=f'movie-{i}', release_date=date(2020, 1, 1), genres=genres, tmdb_popularity=popularity, provider_metadata={'runtime': runtime, 'original_language': language}))
        self.db.add(Movie(id=8, tmdb_id=8, title='Future Space', slug='future', release_date=date(2099, 1, 1), genres=['Science Fiction'], tmdb_popularity=10000))
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app, base_url='http://localhost', headers={'Origin': 'http://localhost:3000'})
        _attempts.clear()

    def tearDown(self):
        self.client.close(); app.dependency_overrides.clear(); self.db.close(); self.engine.dispose(); _attempts.clear()

    def query(self, **kwargs):
        return recommend(self.db, ChatRequest(**kwargs))

    def test_hard_filters_exclude_unknowns_and_runtime_boundary(self):
        result = self.query(message='English sci-fi under two hours, no horror')
        self.assertEqual({item['movie']['id'] for item in result['items']}, {1, 2})
        self.assertEqual(result['filters'].max_runtime, 119)

    def test_followup_preserves_and_replaces_constraints(self):
        first = self.query(message='English sci-fi under two hours')
        second = self.query(message='No horror', filters=first['filters'])
        self.assertEqual(second['filters'].languages, ['English'])
        self.assertEqual({i['movie']['id'] for i in second['items']}, {1, 2})
        third = self.query(message='Drama instead', filters=second['filters'])
        self.assertEqual(third['filters'].genres, ['Drama'])
        self.assertEqual(third['items'], [])

    def test_negation_list_does_not_recommend_excluded_genres(self):
        filters, _, _ = parse_filters('No horror or drama, but sci-fi', Filters())
        self.assertEqual(filters.excluded_genres, ['Drama', 'Horror'])
        self.assertEqual(filters.genres, ['Science Fiction'])

    def test_personalization_beats_popularity_and_excludes_seed(self):
        result = self.query(message='recommend', favorite_ids=[1])
        self.assertEqual(result['items'][0]['movie']['id'], 6)
        self.assertIn('Space Seed', result['items'][0]['reasons'][0])
        self.assertNotIn(1, [i['movie']['id'] for i in result['items']])
        self.assertNotIn(8, [i['movie']['id'] for i in result['items']])

    def test_more_excludes_previous_results(self):
        first = self.query(message='recommend')
        seen = [i['movie']['id'] for i in first['items']]
        second = self.query(message='show more', excluded_ids=seen)
        self.assertTrue(set(seen).isdisjoint(i['movie']['id'] for i in second['items']))

    def test_unknown_requests_and_titles_ask_for_clarification(self):
        for message in ['Write me a shell script', 'something like Nonexistent Film', 'not English']:
            result = self.query(message=message)
            self.assertTrue(result['needs_clarification'], message)
            self.assertEqual(result['items'], [])

    def test_exact_reference_is_carried_to_next_turn(self):
        first = self.query(message='something like Space Seed')
        self.assertEqual(first['favorite_ids'], [1])
        second = self.query(message='recommend', favorite_ids=first['favorite_ids'])
        self.assertEqual(second['items'][0]['movie']['id'], 6)

    def test_no_matches_never_relaxes_filters(self):
        result = self.query(message='Japanese horror under 10 minutes')
        self.assertEqual(result['items'], [])
        self.assertIn('No more catalog movies', result['reply'])

    def test_movie_reference_and_runtime_are_both_applied(self):
        result = self.query(message='something like Space Seed but under two hours')
        self.assertEqual(result['favorite_ids'], [1])
        self.assertEqual(result['filters'].max_runtime, 119)
        self.assertNotIn(6, [item['movie']['id'] for item in result['items']])
        self.assertIn('Space Seed', result['items'][0]['reasons'][0])

    def test_api_validates_payload_and_keeps_results_private(self):
        response = self.client.post('/api/assistant/chat', json={'message': 'recommend'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('no-store', response.headers['cache-control'])
        for payload in [{'message': 'x'*501}, {'message': 'recommend', 'account_id': 1}, {'message': 'recommend', 'filters': {'max_runtime': -2}}]:
            self.assertEqual(self.client.post('/api/assistant/chat', json=payload).status_code, 422)

    def test_favourite_search_does_not_require_analytics(self):
        response = self.client.get('/api/search/suggest', params={'q': 'Space Seed'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['id'], 1)

    def test_streaming_constraint_is_not_silently_ignored(self):
        result = self.query(message='comedy on Netflix')
        self.assertTrue(result['needs_clarification'])
        self.assertEqual(result['items'], [])

    def test_coverage_reports_missing_metadata_honestly(self):
        result = self.client.get('/api/assistant/coverage')
        self.assertEqual(result.json(), {'released_movies': 7, 'with_runtime': 6, 'with_language': 6, 'ai_available': False})

    def test_feedback_ownership_csrf_and_personalized_exclusions(self):
        register = self.client.post('/api/auth/register', json={'username': 'tasteuser', 'password': 'long-test-password-123'})
        headers = {'X-CSRF-Token': register.json()['csrf_token']}
        self.assertEqual(self.client.put('/api/assistant/feedback/1', json={'preference': 'like'}).status_code, 403)
        self.assertEqual(self.client.put('/api/assistant/feedback/1', json={'preference': 'like'}, headers=headers).status_code, 200)
        self.client.put('/api/assistant/feedback/2', json={'preference': 'dislike'}, headers=headers)
        self.client.put('/api/watchlist/4', headers=headers)
        self.client.patch('/api/watchlist/4', json={'status': 'watched'}, headers=headers)
        result = self.client.post('/api/assistant/chat', json={'message': 'recommend'}, headers=headers)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertTrue({1, 2, 4}.isdisjoint(i['movie']['id'] for i in result.json()['items']))
        with TestClient(app, base_url='http://localhost', headers={'Origin': 'http://localhost:3000'}) as other:
            self.assertEqual(other.get('/api/assistant/feedback').status_code, 401)
            other_register = other.post('/api/auth/register', json={'username': 'otheruser', 'password': 'long-test-password-123'})
            self.assertEqual(other.get('/api/assistant/feedback').json()['items'], [])
            other.delete('/api/assistant/feedback/1', headers={'X-CSRF-Token': other_register.json()['csrf_token']})
        self.assertEqual(len(self.client.get('/api/assistant/feedback').json()['items']), 2)
        self.client.delete('/api/assistant/feedback/1', headers=headers)
        self.assertEqual(len(list(self.db.scalars(select(MovieFeedback)))), 1)
