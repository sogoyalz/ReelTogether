import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.movie import Movie
from app.services.mock_data import build_models
from app.services.provider_metadata import merge_metadata
from app.services.review_identity import review_key
from app.services.review_fetcher import _parse_datetime
from app.services.tmdb import TmdbSyncResult, _import_record, _upsert_movie_summary


class ImplementationRegressions(unittest.TestCase):
    def test_partial_provider_refresh_preserves_known_facts(self):
        merged = merge_metadata({'runtime':'142 min','language':'English','imdb_rating':'8.2'},
            {'runtime':None,'language':'N/A','imdb_rating':'8.3'})
        self.assertEqual(merged, {'runtime':'142 min','language':'English','imdb_rating':'8.3'})

    def test_timestamp_keys_match_across_postgres_sqlite_and_offsets(self):
        naive = datetime(2026, 10, 31, 12)
        aware = datetime(2026, 10, 31, 17, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        self.assertEqual(review_key(' ALICE ', naive, 'tmdb'), review_key('alice', aware, 'tmdb'))
        self.assertEqual(_parse_datetime('2026-10-31T17:30:00+05:30'), naive)

    def test_demo_identity_is_disjoint_and_live_import_preserves_demo(self):
        engine = create_engine('sqlite://'); Base.metadata.create_all(engine)
        with Session(engine) as db, patch('app.services.omdb.fetch_movie_metadata', return_value={}):
            demo, analytics = next((m,a) for m,a in build_models() if m.slug == 'dune-part-two')
            demo.analytics_snapshots.append(analytics); db.add(demo); db.commit(); original_id = demo.id
            self.assertLess(demo.tmdb_id, 0)
            _import_record(db, _upsert_movie_summary, {'id':872585,'title':'Oppenheimer','release_date':'2023-07-21','popularity':30}, {}, TmdbSyncResult())
            db.commit(); db.refresh(demo)
            self.assertEqual((demo.id, demo.title), (original_id, 'Dune: Part Two'))
            self.assertEqual(len(list(db.scalars(select(Movie)))), 2)
        engine.dispose()

    def test_record_failure_isolated_and_non_latin_slug_is_stable(self):
        engine = create_engine('sqlite://'); Base.metadata.create_all(engine)
        with Session(engine) as db, patch('app.services.omdb.fetch_movie_metadata', return_value={}):
            result = TmdbSyncResult()
            def ingest(payload): return _import_record(db, _upsert_movie_summary, payload, {}, result)
            base = {'release_date':date.today().isoformat(),'popularity':30}
            ingest({**base,'id':500,'title':'電影'})
            with self.assertRaises(RuntimeError): ingest({**base,'id':501,'title':'Broken','popularity':{'invalid':True}})
            ingest({**base,'id':502,'title':'Good'}); ingest({**base,'id':500,'title':'Translated title'}); db.commit()
            imported = list(db.scalars(select(Movie).order_by(Movie.tmdb_id)))
            self.assertEqual([m.tmdb_id for m in imported], [500, 502])
            self.assertEqual(imported[0].slug, 'movie-500'); self.assertEqual(imported[0].status, 'released')
            self.assertEqual(result.created_movies, 2)
        engine.dispose()

    def test_empty_review_landscape_has_no_alignment_or_drivers(self):
        from app.services.review_analysis import analyze_review_landscape
        movie, _ = build_models()[0]; result = analyze_review_landscape(movie, [], {}, {})
        self.assertIsNone(result['alignment_score']); self.assertEqual(result['critics'].negative_drivers, [])
        self.assertEqual(result['audience'].positive_drivers, [])

    def test_detail_reads_never_call_optional_network_providers(self):
        from app.api.movies import _fetch_detail_enrichment
        movie, _ = build_models()[0]; movie.provider_metadata = {'runtime':'120 min'}
        with patch('app.services.omdb.urlopen', side_effect=AssertionError('network')):
            metadata, wikipedia, wikidata = _fetch_detail_enrichment(movie)
        self.assertEqual(metadata['runtime'], '120 min'); self.assertEqual((wikipedia, wikidata), ({}, {}))

    def test_distinct_provider_reviews_from_the_same_author_are_preserved(self):
        from app.services.review_fetcher import fetch_reviews_for_movie
        from app.core.config import settings
        engine = create_engine('sqlite://'); Base.metadata.create_all(engine)
        with Session(engine) as db:
            movie, _ = build_models()[0]; movie.tmdb_id = 55; db.add(movie); db.commit()
            reviews = [{'id':identifier,'author':'Same author','content':'Great story','created_at':'2026-10-31T12:00:00Z'} for identifier in ['review-a','review-b']]
            with patch.object(settings, 'TMDB_API_KEY', 'test-only'), patch('app.services.review_fetcher._tmdb_get', side_effect=[{'results':reviews},{'results':[]}]):
                fetched = fetch_reviews_for_movie(db, movie.id)
            self.assertEqual([review['source_review_id'] for review in fetched], ['review-a','review-b'])
        engine.dispose()

    def test_persisting_same_provider_review_is_idempotent_across_timezones(self):
        from app.repositories.movies import upsert_review_sentiments, list_review_sentiments
        engine = create_engine('sqlite://'); Base.metadata.create_all(engine)
        with Session(engine) as db:
            movie, _ = build_models()[0]; db.add(movie); db.commit()
            review = {'source_review_id':'stable-id','author':'Original author','content':'Good story','created_at':datetime(2026,10,31,12,tzinfo=timezone.utc),
                'source':'tmdb','sentiment_score':0.5,'sentiment_label':'positive','confidence':0.8}
            self.assertEqual(upsert_review_sentiments(db,movie.id,[review]),1)
            self.assertEqual(upsert_review_sentiments(db,movie.id,[{**review,'author':'Renamed author'}]),0)
            self.assertEqual(len(list_review_sentiments(db,movie.id)),1)
        engine.dispose()

    def test_partly_supported_constraints_request_clarification(self):
        from app.schemas.assistant import ChatRequest
        from app.services.catalog_assistant import recommend
        engine = create_engine('sqlite://'); Base.metadata.create_all(engine)
        with Session(engine) as db:
            for message in ['comedy starring Tom Hanks', 'thriller rated at least 8', 'English movies that won an Oscar']:
                result = recommend(db, ChatRequest(message=message))
                self.assertTrue(result['needs_clarification'], message)
                self.assertEqual(result['items'], [])
            result = recommend(db, ChatRequest(message='please recommend a comedy under two hours, no horror'))
            self.assertFalse(result['needs_clarification'])
        engine.dispose()

    def test_snapshot_labels_are_unique_per_movie(self):
        from sqlalchemy.exc import IntegrityError
        from app.models.movie import MovieAnalytics
        engine = create_engine('sqlite://'); Base.metadata.create_all(engine)
        with Session(engine) as db:
            movie, analytics = build_models()[0]; movie.analytics_snapshots.append(analytics); db.add(movie); db.commit()
            db.add(MovieAnalytics(movie_id=movie.id, snapshot_label='latest'))
            with self.assertRaises(IntegrityError): db.commit()
            db.rollback()
        engine.dispose()

    def test_new_trailer_archives_observation_and_clears_old_counts(self):
        from app.services.tmdb import _populate_analytics
        engine = create_engine('sqlite://'); Base.metadata.create_all(engine)
        with Session(engine) as db:
            movie, analytics = build_models()[0]; movie.analytics_snapshots.append(analytics)
            analytics.trailer_url = 'https://www.youtube.com/watch?v=oldVideo123'
            analytics.youtube_views = 12345
            movie.provider_metadata = {'youtube_observation':{'source_url':analytics.trailer_url,'verified_at':'2026-10-31T12:00:00Z'}}
            db.add(movie); db.commit()
            _populate_analytics(movie,analytics,{'videos':{'results':[{'site':'YouTube','type':'Trailer','key':'newVideo123'}]}})
            db.commit()
            self.assertEqual(analytics.youtube_views,0)
            self.assertEqual(analytics.trailer_url,'https://www.youtube.com/watch?v=newVideo123')
            self.assertNotIn('youtube_observation',movie.provider_metadata)
            archive = next(row for row in movie.analytics_snapshots if row.snapshot_label.startswith('video:'))
            self.assertEqual(archive.youtube_views,12345)
            self.assertEqual(movie.provider_metadata['youtube_observation_archive'][archive.snapshot_label]['source_url'],archive.trailer_url)
        engine.dispose()

    def test_demo_timestamps_do_not_claim_provider_verification(self):
        from app.services.movie_data import _last_verified_at
        movie, analytics = build_models()[0]
        movie.created_at = datetime.now(timezone.utc)
        self.assertIsNone(_last_verified_at(movie, analytics))
        movie.provider_metadata = {'catalog_verified_at':'2026-10-31T12:00:00Z'}
        self.assertEqual(_last_verified_at(movie, analytics), datetime(2026,10,31,12,tzinfo=timezone.utc))

    def test_omdb_uses_canonical_identity_and_rejects_a_different_movie(self):
        import json
        from io import BytesIO
        from app.services import omdb
        from app.core.config import settings
        movie, _ = build_models()[0]; movie.tmdb_id = 123
        movie.provider_metadata = {'imdb_id':'tt15398776','imdb_rating':'8.2'}
        omdb._CACHE.clear()
        payload = {'Response':'True','imdbID':'tt99999999','Title':'Different movie','Year':'2023','imdbRating':'1.0'}
        with patch.object(settings,'OMDB_API_KEY','test-only'), patch.object(omdb,'urlopen',return_value=BytesIO(json.dumps(payload).encode())) as request:
            result = omdb.fetch_movie_metadata(movie)
        self.assertIn('i=tt15398776',request.call_args.args[0])
        self.assertNotIn('&t=',request.call_args.args[0])
        self.assertEqual(result['imdb_rating'],'8.2')
        omdb._CACHE.clear()
