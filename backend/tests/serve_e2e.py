"""Offline disposable integration fixture server."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import atexit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
fixture_directory = TemporaryDirectory(prefix="reeltogether-browser-")
atexit.register(fixture_directory.cleanup)
fixture_url = "sqlite:///" + str(Path(fixture_directory.name) / "catalog.sqlite")
os.environ.update(PROXY_SHARED_SECRET="test-only-browser-proxy-secret", ENABLE_ASSISTANT_AI="false", OPENAI_API_KEY="", DATABASE_URL=fixture_url, REDIS_URL="", ENABLE_STARTUP_SYNC="false", ENABLE_RATE_LIMIT="false", TRUSTED_HOSTS='["localhost","127.0.0.1"]', TMDB_API_KEY="", OMDB_API_KEY="", YOUTUBE_API_KEY="")
from app.core.config import settings
settings.CORS_ORIGINS = ["http://127.0.0.1:3011", "http://localhost:3011"]
from datetime import date
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.session import get_db
from app.models import Movie, MovieAnalytics
from app.services.tmdb import _populate_analytics
from app.api import movies
from main import app
# Each request needs its own connection: concurrent SQLite callbacks on one
# shared StaticPool connection can stall the Linux interpreter.
engine = create_engine(fixture_url, connect_args={"check_same_thread": False, "timeout": 10})
@event.listens_for(engine, "connect")
def fixture_foreign_keys(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")
Base.metadata.create_all(engine)
with Session(engine) as db:
    for i in range(60):
        movie = Movie(tmdb_id=1000+i, slug=f"fixture-{i}", title=f"Fixture Movie {i:02}", release_date=date(2030, 1, 1), status="upcoming", genres=["Drama"], tmdb_popularity=60-i, overview="A deterministic movie used for automated integration checks.", enrichment_data={"directors": ["Jane Doe"]}, provider_metadata={"imdb_rating": "8.1"})
        analytics = MovieAnalytics(snapshot_label="latest")
        _populate_analytics(movie, analytics, {"popularity": 60-i})
        movie.analytics_snapshots.append(analytics)
        db.add(movie)
    for i in range(10):
        db.add(Movie(tmdb_id=2000+i, slug=f"chat-{i}", title=f"Chat Movie {i:02}", release_date=date(2020, 1, 1), status="released", genres=["Science Fiction"] + (["Horror"] if i == 2 else []), tmdb_popularity=100-i, overview="An offline recommendation fixture.", provider_metadata={"runtime": "100 min", "original_language": "en"}))
    db.commit()
def fixture_db():
    with Session(engine) as db:
        yield db
app.dependency_overrides[get_db] = fixture_db
movies._fetch_detail_enrichment = lambda movie: (movie.provider_metadata or {}, {}, {})
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8011)
