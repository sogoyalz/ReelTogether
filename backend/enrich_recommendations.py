"""Plan (default) or apply a bounded TMDB metadata backfill. Never replaces catalog/analytics."""
import argparse
import json
from app.db.session import SessionLocal
from app.services.recommendation_enrichment import enrich_metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=25, help='Maximum provider requests, 1..100')
    parser.add_argument('--after-id', type=int, default=0, help='Resume after a processed movie ID')
    parser.add_argument('--apply', action='store_true', help='Fetch TMDB details and persist missing metadata')
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            report = enrich_metadata(db, limit=args.limit, after_id=args.after_id, apply=args.apply)
        print(json.dumps(report, indent=2))
        return 1 if report['failures'] else 0
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    raise SystemExit(main())
