"""Offline regressions. Never uses the developer database or provider keys."""
import os
os.environ.update(ENABLE_ASSISTANT_AI="false", OPENAI_API_KEY="", DATABASE_URL="sqlite://", REDIS_URL="", ENABLE_STARTUP_SYNC="false", ENABLE_RATE_LIMIT="false", TRUSTED_HOSTS='["localhost"]', TMDB_API_KEY="", OMDB_API_KEY="", YOUTUBE_API_KEY="")
import unittest
from datetime import date, datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.session import get_db
from app.models import Movie, MovieAnalytics
from app.core.config import settings
from app.services import tmdb
from app.services.catalog_browser import browse_catalog, CatalogBrowseFilters
from app.services.catalog_enrichment import build_history
from app.services.hype_calculator import HypeCalculator
from app.services.cache import TTLCache
from main import app

class PublicContractTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, autoflush=False)
        self.movie = Movie(tmdb_id=42, slug="example", title="Example", release_date=date(2020, 1, 1), status="upcoming", genres=["Drama"], tmdb_popularity=10, provider_metadata={"imdb_rating": "8.1", "box_office": "$100,000,000"}, enrichment_data={"directors": ["Jane Doe"]})
        self.analytics = MovieAnalytics(snapshot_label="latest")
        tmdb._populate_analytics(self.movie, self.analytics, {"popularity": 10})
        self.movie.analytics_snapshots.append(self.analytics)
        self.db.add(self.movie)
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app, base_url="http://localhost")
        self.providers = patch("app.api.movies._fetch_detail_enrichment", return_value=(self.movie.provider_metadata, {}, {}))
        self.providers.start()
    def tearDown(self):
        self.providers.stop()
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
    def test_browse_loads_latest_without_truncating_history(self):
        from app.repositories.movies import get_movie_by_id
        from sqlalchemy import inspect
        self.movie.analytics_snapshots.append(MovieAnalytics(snapshot_label="history", snapshot_date=date(2019, 1, 1)))
        self.db.commit()
        self.db.expunge_all()
        result = browse_catalog(self.db, CatalogBrowseFilters())
        movie = result.movies[0]
        self.assertIn("analytics_snapshots", inspect(movie).unloaded)
        self.assertEqual(len(movie.latest_snapshots), 1)
        detail = get_movie_by_id(self.db, movie.id)
        self.assertEqual(len(detail.analytics_snapshots), 2)
        self.assertEqual(len(build_history(detail, detail.latest_snapshots[0])), 2)

    def test_search_keeps_movies_without_analytics_and_uses_stored_metadata(self):
        self.db.add(Movie(tmdb_id=43, slug="example-no-analytics", title="Example Two", release_date=date(2020, 1, 1), genres=["Drama"], provider_metadata={"runtime": 105, "imdb_rating": "7.2"}))
        self.db.commit()
        with patch("app.services.omdb.fetch_movie_metadata", side_effect=AssertionError("List search must not call providers")):
            response = self.client.get("/api/search?q=Example&sort=title&page_size=1&page=2")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["total_pages"], 2)
        self.assertEqual(payload["items"][0]["title"], "Example Two")
        self.assertEqual(payload["items"][0]["runtime"], "105")
        self.assertEqual(payload["items"][0]["hype_score"], 0)

    def test_invalid_stored_ratings_do_not_pass_rating_filter(self):
        for value in ["NaN", "Infinity", {}, "N/A", -1, 11]:
            with self.subTest(value=value):
                self.movie.provider_metadata = {"imdb_rating": value}
                self.db.commit()
                result = browse_catalog(self.db, CatalogBrowseFilters(min_rating=7))
                self.assertEqual(result.total, 0)

    def test_ai_response_contract_without_invented_reviews(self):
        result = self.client.get(f"/api/ai/movie/{self.movie.id}")
        self.assertEqual(result.status_code, 200, result.text)
        data = result.json()
        self.assertIn("critics", data["critic_vs_audience"])
        self.assertEqual(data["prediction"]["feature_importance"], [])
        self.assertEqual(data["sentiment"]["sample_size"], 0)
        self.assertEqual(data["discussions"], [])
        self.assertEqual(data["prediction"]["forecast_status"], "actuals_available")
        self.assertEqual(data["prediction"]["predicted_opening_weekend_usd"], 0)
    def test_detail_actuals_and_status_contract(self):
        response = self.client.get(f"/api/movies/{self.movie.id}")
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["status"], "released")
        self.assertEqual(data["forecast_status"], "actuals_available")
        self.assertIsInstance(data["engagement_metrics_note"], str)
        self.assertTrue(data["engagement_metrics_are_estimated"])
        self.assertEqual(data["box_office_history"], [])
    def test_browse_filters_use_persisted_metadata(self):
        response = self.client.get("/api/movies/browse?director=Jane%20Doe&min_rating=8&status=released")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(self.client.get("/api/movies/browse?director=SomeoneElse").json()["total"], 0)
    def test_same_title_imports_preserve_identity_and_pending_rows(self):
        for tmdb_id in [43, 44, 43]:
            tmdb._upsert_movie(self.db, {"id": tmdb_id, "title": "Example", "release_date": "2030-01-01", "genres": [], "popularity": 1}, tmdb.TmdbSyncResult())
        self.db.commit()
        movies = list(self.db.scalars(select(Movie)))
        self.assertEqual(len(movies), 3)
        self.assertEqual(self.db.get(Movie, self.movie.id).tmdb_id, 42)
        self.assertEqual(len({m.slug for m in movies}), 3)
    def test_catalog_refresh_preserves_observations(self):
        self.analytics.youtube_views = 123456789
        self.analytics.trailer_url = "https://www.youtube.com/watch?v=abc"
        tmdb._populate_analytics(self.movie, self.analytics, {"popularity": 1})
        self.assertEqual(self.analytics.youtube_views, 123456789)
        self.assertIsNotNone(self.analytics.trailer_url)
    def test_maintenance_requires_admin_on_every_path(self):
        with patch.object(settings, "ADMIN_API_KEY", "test-only-secret"):
            for path in ["movies/sync-tmdb", "analytics/refresh", f"analytics/movie/{self.movie.id}/refresh", f"analytics/movie/{self.movie.id}/sentiment/refresh", "admin/jobs/tmdb-sync"]:
                self.assertEqual(self.client.post("/api/" + path).status_code, 401, path)
    def test_compare_rejects_duplicates_and_unbounded_lists(self):
        for ids in ["1,1", "1,2,3,4,5", "1"]:
            self.assertEqual(self.client.get("/api/analytics/compare", params={"movie_ids": ids}).status_code, 422)
    def test_release_day_is_consistent_across_feeds(self):
        from app.repositories.movies import list_upcoming_movies, list_released_movies
        self.movie.release_date = date.today()
        self.db.commit()
        self.assertEqual(list_upcoming_movies(self.db, date.today()), [])
        self.assertEqual(len(list_released_movies(self.db, date.today())), 1)

    def test_youtube_observations_are_dated_and_idempotent(self):
        from app.services.youtube_analytics import _record_observation
        self.analytics.youtube_views = 12345
        _record_observation(self.db, self.analytics)
        _record_observation(self.db, self.analytics)
        self.db.commit()
        self.assertEqual(len(self.movie.analytics_snapshots), 2)
        self.assertIn("youtube_observation", self.movie.provider_metadata)
        self.assertEqual(len(build_history(self.movie, self.analytics)), 1)

    def test_history_does_not_invent_snapshots(self):
        self.assertEqual(len(build_history(self.movie, self.analytics)), 1)
    def test_empty_timeline_does_not_fetch_reviews(self):
        with patch("app.api.analytics.refresh_review_sentiments_for_movie", side_effect=AssertionError("GET wrote data")):
            response = self.client.get(f"/api/analytics/movie/{self.movie.id}/sentiment/timeline")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total_reviews"], 0)
    def test_browse_does_not_reuse_stale_orm_objects(self):
        self.assertEqual(browse_catalog(self.db, CatalogBrowseFilters(min_rating=8)).total, 1)
        self.movie.provider_metadata = {"imdb_rating": "5"}
        self.db.commit()
        self.assertEqual(browse_catalog(self.db, CatalogBrowseFilters(min_rating=8)).total, 0)

class UtilityTests(unittest.TestCase):
    def test_sentiment_is_monotonic(self):
        now = datetime.now()
        scores = [HypeCalculator.calculate_hype_score({"sentiment_score": x}, now) for x in [-1, -.01, 0, .01, 1]]
        self.assertEqual(scores, sorted(scores))
    def test_cache_bounded_expired_and_clear(self):
        cache = TTLCache(ttl_seconds=10, max_entries=2)
        with patch("app.services.cache.monotonic", return_value=0):
            for i in range(3): cache.get_or_set(str(i), lambda: i)
        self.assertEqual(len(cache._entries), 2)
        with patch("app.services.cache.monotonic", return_value=11):
            self.assertEqual(cache.get_or_set("2", lambda: 9), 9)
        cache.clear()
        self.assertEqual(len(cache._entries), 0)

class TrainingAndJobsTests(unittest.TestCase):
    def test_small_training_dataset_is_rejected(self):
        from app.services.model_training import split_rows, evaluate_model
        with self.assertRaises(ValueError): split_rows([])
        with self.assertRaises(ValueError): evaluate_model({}, [], [])

    def test_temporal_splits_are_disjoint(self):
        from app.services.model_training import split_rows, DataRow
        rows = [DataRow(i, str(i), date(2020, 1, i + 1), {}, 1, 1) for i in range(30)]
        groups = split_rows(rows)
        train, validation, test = [{r.movie_id for r in groups[key]} for key in ('train', 'validation', 'test')]
        self.assertFalse(train & validation or train & test or validation & test)
        self.assertEqual(len(train | validation | test), 30)

    def test_jobs_deduplicate_active_work(self):
        from threading import Event
        from app.services.background_jobs import JobRegistry
        gate = Event()
        registry = JobRegistry(max_jobs=2)
        def job():
            gate.wait(2)
            return {}
        try:
            first = registry.enqueue('sync', job)
            second = registry.enqueue('sync', job)
            self.assertEqual(first.id, second.id)
        finally:
            gate.set()
            registry._executor.shutdown(wait=True)
        self.assertEqual(registry.get(first.id).status, 'completed')
