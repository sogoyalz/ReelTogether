from __future__ import annotations

import argparse

from sqlalchemy import func, select

from app.services.catalog_browser import clear_browse_cache
from app.db.session import SessionLocal
from app.models.movie import Movie
from app.services.tmdb import sync_tmdb_catalog


def _movie_count() -> int:
    with SessionLocal() as db:
        return int(db.scalar(select(func.count()).select_from(Movie)) or 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Expand the local TMDB-backed movie catalog.")
    parser.add_argument("--target", type=int, default=1000, help="Target number of movies to store locally.")
    parser.add_argument(
        "--pages-per-feed",
        type=int,
        default=20,
        help="Maximum TMDB pages to scan per feed during this run.",
    )
    args = parser.parse_args()

    before = _movie_count()
    with SessionLocal() as db:
        result = sync_tmdb_catalog(
            db,
            pages_per_feed=args.pages_per_feed,
            target_total_movies=args.target,
            include_watch_providers=False,
            include_full_details=False,
        )
        clear_browse_cache()

    after = _movie_count()
    print(
        {
            "before": before,
            "after": after,
            "target": args.target,
            "pages_per_feed": args.pages_per_feed,
            "synced_movies": result.synced_movies,
            "created_movies": result.created_movies,
            "updated_movies": result.updated_movies,
            "failed_movies": result.failed_movies,
            "errors": result.errors[:10],
        }
    )


if __name__ == "__main__":
    main()
