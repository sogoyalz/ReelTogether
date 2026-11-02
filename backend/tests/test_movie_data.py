import unittest
from datetime import date, datetime, timedelta

from app.models.movie import Movie, MovieAnalytics
from app.services.catalog_enrichment import get_enrichment
from app.services.mock_data import build_models
from app.services.movie_data import build_movie_data_contract


class MovieDataContractTests(unittest.TestCase):
    def test_dune_part_two_is_canonically_released(self) -> None:
        movie, analytics = next(
            (movie, analytics)
            for movie, analytics in build_models()
            if movie.slug == "dune-part-two"
        )

        contract = build_movie_data_contract(
            movie,
            analytics=analytics,
            enrichment=get_enrichment(movie),
            omdb_metadata={},
            opening=analytics.predicted_opening_weekend_usd,
            domestic=analytics.predicted_domestic_total_usd,
        )

        self.assertEqual(contract["status"], "released")
        self.assertEqual(contract["field_sources"]["release_date"], "generated")
        self.assertIn("Core metadata is currently coming from local demo fallback data", " ".join(contract["warnings"]))

    def test_future_theatrical_title_keeps_public_forecast(self) -> None:
        movie, analytics = next(
            (movie, analytics)
            for movie, analytics in build_models()
            if movie.slug == "the-batman-part-ii"
        )
        movie.release_date = date.today() + timedelta(days=365)

        contract = build_movie_data_contract(
            movie,
            analytics=analytics,
            enrichment=get_enrichment(movie),
            omdb_metadata={},
            opening=analytics.predicted_opening_weekend_usd,
            domestic=analytics.predicted_domestic_total_usd,
        )

        self.assertEqual(contract["status"], "announced")
        self.assertTrue(contract["forecast_is_public"])
        self.assertEqual(contract["field_sources"]["predicted_opening_weekend_usd"], "generated")

    def test_streaming_availability_does_not_establish_release_type(self) -> None:
        movie = Movie(
            tmdb_id=1,
            slug="war-machine",
            title="War Machine",
            release_date=date(2017, 5, 26),
            status="released",
            poster_url=None,
            backdrop_url=None,
            overview="Streaming satire",
            genres=["Comedy", "War"],
            tmdb_popularity=50.0,
            created_at=datetime(2026, 1, 1),
        )
        analytics = MovieAnalytics(
            snapshot_label="latest",
            snapshot_date=date(2026, 1, 1),
            youtube_views=1_000_000,
            youtube_likes=20_000,
            youtube_comments=1_000,
            google_trends_score=55.0,
            x_mentions=5_000,
            reddit_mentions=1_200,
            sentiment_score=0.2,
            sentiment_positive=40,
            sentiment_neutral=30,
            sentiment_negative=30,
            momentum_score=0.4,
            buzz_score=42.0,
            hype_score=38.0,
            predicted_opening_weekend_usd=99_000_000,
            predicted_domestic_total_usd=210_000_000,
            trailer_url=None,
            last_updated=datetime(2026, 1, 1),
        )

        contract = build_movie_data_contract(
            movie,
            analytics=analytics,
            enrichment={"streaming_on": ["Netflix"]},
            omdb_metadata={},
            opening=analytics.predicted_opening_weekend_usd,
            domestic=analytics.predicted_domestic_total_usd,
        )

        self.assertFalse(contract["forecast_is_public"])
        self.assertEqual(contract["predicted_opening_weekend_usd"], 0.0)
        self.assertEqual(contract["distribution_type"], "unknown")
        self.assertEqual(contract["forecast_status"], "unavailable")
        self.assertNotIn('streaming-first', contract['forecast_note'])

    def test_future_streaming_availability_does_not_suppress_forecast(self):
        movie = Movie(tmdb_id=999, slug='future-fixture', title='Future fixture',
                      release_date=date.today() + timedelta(days=30), status='released', genres=[])
        for studios in ([], ['Independent Studio']):
            with self.subTest(studios=studios):
                contract = build_movie_data_contract(movie,
                    enrichment={'streaming_on': ['Netflix'], 'studios': studios}, opening=10_000_000)
                self.assertEqual(contract['distribution_type'], 'unknown')
                self.assertEqual(contract['forecast_status'], 'modeled')
                self.assertEqual(contract['predicted_opening_weekend_usd'], 10_000_000)

    def test_release_distribution_requires_explicit_provenance(self):
        movie = Movie(tmdb_id=999, slug='release-fixture', title='Release fixture',
                      release_date=date.today() + timedelta(days=30), status='upcoming', genres=[])
        evidence = {'type': 'streaming-first', 'source_url': 'https://example.org/release',
                    'verified_at': '2026-10-31T12:00:00Z'}
        for value in (None, 'streaming-first', {'type': []}, {'type': 'streaming-first'},
                      {**evidence, 'source_url': 'javascript:invalid'},
                      {**evidence, 'verified_at': 'invalid'}):
            with self.subTest(value=value):
                movie.provider_metadata = {'release_distribution': value}
                self.assertEqual(build_movie_data_contract(movie)['distribution_type'], 'unknown')
        movie.provider_metadata = {'release_distribution': evidence}
        contract = build_movie_data_contract(movie, opening=10_000_000)
        self.assertEqual(contract['distribution_type'], 'streaming-first')
        self.assertEqual(contract['forecast_status'], 'suppressed')
        self.assertFalse(contract['forecast_is_public'])
        # Stored theatrical actuals override a conflicting release label.
        contract = build_movie_data_contract(movie, omdb_metadata={'box_office': '$10,000,000'})
        self.assertEqual(contract['distribution_type'], 'theatrical')
        self.assertEqual(contract['forecast_status'], 'actuals_available')


if __name__ == "__main__":
    unittest.main()
