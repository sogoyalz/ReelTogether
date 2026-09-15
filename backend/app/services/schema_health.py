"""Readiness covers every persisted feature, including the latest room schema."""
from sqlalchemy import select
from app.models.jobs import BackgroundJob, QueueControl, JobSchedule
from app.models.movie import Movie
from app.models.account import Account, LoginSession, WatchlistEntry, MovieFeedback
from app.models.movie_night import MovieNight, NightMember, NightVote


def assert_schema_ready(db):
    for field in (Movie.provider_metadata, Account.recovery_hash, LoginSession.token_hash,
                  WatchlistEntry.status, MovieFeedback.preference, MovieNight.round_id,
                  NightMember.genres, NightVote.choice, BackgroundJob.lease_token, QueueControl.version, JobSchedule.next_run):
        db.execute(select(field).limit(1))
