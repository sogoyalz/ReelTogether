"""Parity and bounded-loading checks for SQLite catalog browsing."""
import os
os.environ.update(ENABLE_ASSISTANT_AI="false", OPENAI_API_KEY="", DATABASE_URL="sqlite://", REDIS_URL="", ENABLE_STARTUP_SYNC="false", ENABLE_RATE_LIMIT="false", TMDB_API_KEY="", OMDB_API_KEY="", YOUTUBE_API_KEY="")
import unittest
from datetime import date, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models import Movie, MovieAnalytics
from app.services.catalog_browser import CatalogBrowseFilters, _build_browse_result, browse_catalog
from app.services.mock_data import build_models


class CatalogSqlTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            for movie, analytics in build_models():
                movie.analytics_snapshots.append(analytics)
                db.add(movie)
            for i in range(36):
                movie = Movie(tmdb_id=900000+i, slug=f"parity-{i}", title=["ÉCHO 100%_", "echo", "Echo", "Straße"][i % 4],
                    overview="literal %_ query; space opera", release_date=date.today()+timedelta(days=i-18),
                    status="announced" if i % 3 else "upcoming", genres=["Drama", "Science Fiction"] if i % 2 else ["Comedy"],
                    tmdb_popularity=i % 7,
                    provider_metadata={"imdb_rating": ["8.4", "NaN", "N/A", {}, "Infinity", 7.5][i % 6]},
                    enrichment_data={"directors": ["Zoë Doe"], "studios": ["Studio A"], "franchise": "Test Saga",
                        "streaming_on": ["Stream"], "cast": ["Actor One"], "writers": ["Writer Two"]})
                if i % 3:
                    movie.analytics_snapshots.extend([MovieAnalytics(snapshot_label="latest", hype_score=i % 5, buzz_score=i % 4),
                        MovieAnalytics(snapshot_label="history", hype_score=99)])
                db.add(movie)
            db.commit()

    def tearDown(self):
        self.engine.dispose()

    def compare(self, **kwargs):
        filters = CatalogBrowseFilters(page_size=5, **kwargs)
        with Session(self.engine) as db:
            expected = _build_browse_result(db, filters)
            ids = [m.id for m in expected.movies]
        with Session(self.engine) as db:
            actual = browse_catalog(db, filters)
            self.assertEqual([m.id for m in actual.movies], ids, kwargs)
            self.assertEqual((actual.total, actual.page, actual.total_pages, actual.facets),
                             (expected.total, expected.page, expected.total_pages, expected.facets), kwargs)

    def test_all_sorts_pages_and_filters_match_reference(self):
        for sort in ["rating", "popularity", "release", "buzz", "hype", "title", "release_asc", "none", "unknown"]:
            for page in [1, 2, 999]:
                self.compare(sort=sort, page=page)
        for filters in [
            {"query": value} for value in ["%_", "ÉCHO", "straße", "zoë", "Actor One", "Writer Two", "space opera", "absent"]
        ] + [
            {"status": value} for value in ["released", "future", "announced", "upcoming", "unknown"]
        ] + [
            {"genre": "Science Fiction"}, {"genre": "Science"}, {"studio": "Studio A"},
            {"director": "Zoë Doe"}, {"franchise": "Test Saga"}, {"streaming": "Stream"},
            {"min_rating": 7}, {"min_hype": 3}, {"min_popularity": 4}, {"year": date.today().year}, {"year": -1}, {"year": 10000},
            {"query": "echo", "genre": "Drama", "min_hype": 1, "sort": "rating"},
        ]:
            with self.subTest(filters=filters):
                self.compare(**filters)

    def test_only_page_movies_are_hydrated(self):
        loaded = []
        with Session(self.engine) as db:
            event.listen(db, "loaded_as_persistent", lambda session, obj: loaded.append(obj))
            result = browse_catalog(db, CatalogBrowseFilters(page_size=4))
            self.assertGreater(result.total, 40)
            self.assertEqual(len([obj for obj in loaded if isinstance(obj, Movie)]), 4)
            self.assertLessEqual(len([obj for obj in loaded if isinstance(obj, MovieAnalytics)]), 4)
            self.assertTrue(all(obj.snapshot_label == "latest" for obj in loaded if isinstance(obj, MovieAnalytics)))

    def test_changes_are_visible_without_cache_invalidation(self):
        with Session(self.engine) as db:
            first = browse_catalog(db, CatalogBrowseFilters(genre="New Genre"))
            self.assertEqual(first.total, 0)
            movie = db.get(Movie, 1)
            movie.genres = ["New Genre"]
            db.commit()
            second = browse_catalog(db, CatalogBrowseFilters(genre="New Genre"))
            self.assertEqual(second.total, 1)
            self.assertIn("New Genre", second.facets["genres"])

    def test_empty_catalog(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            result = browse_catalog(db, CatalogBrowseFilters(page=99))
            self.assertEqual((result.total, result.page, result.total_pages, result.movies), (0, 1, 1, []))
            self.assertTrue(all(values == [] for values in result.facets.values()))
