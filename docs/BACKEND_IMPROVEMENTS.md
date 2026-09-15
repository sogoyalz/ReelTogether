# Backend reliability and query improvements

Implemented September 13, 2026.

- Watchlist pages join movies in the page query and load latest analytics in one batch. A regression checks eight entries require at most five SELECTs including authentication. Ownership filtering remains part of the query. Requests beyond the last page now return the last available page, useful after deleting saved movies.
- Browse and the homepage dashboard use a separate read-only latest-analytics relationship. They do not load historical snapshots for every catalog movie or truncate the writable history collection. A regression checks detail history remains complete after browsing in the same session.
- The basic catalog endpoint applies its limit in SQL. Autocomplete also limits its database result instead of loading all matching movies and repeating the search.
- Search serializes stored catalog metadata, including runtime and ratings, without per-result provider requests or worker threads sharing ORM objects. Movies without analytics stay visible and pagination totals correspond to the returned catalog. Provider enrichment remains a separate concern.
- Rating filters treat malformed, non-finite, negative, and out-of-range stored IMDb ratings as unavailable. Browse builds combined search text only when a query is supplied.

## Verification

- 62 backend tests passed, including four new regressions covering query counts, pagination, history preservation, search completeness, and malformed ratings.
- 12 Playwright browser tests passed, covering browsing, movie details, account/watchlist flows and recommendations.
- Alembic check: no schema migration required. The new relationship changes ORM loading only.
- Backend Docker image built and the existing local container was updated. Home, catalog, search, suggestions and the recommendations page returned HTTP 200 through localhost:3020.
- Fresh sequential HTTP benchmark against the same 1,369-movie Docker catalog, 3 warmups and 25 samples each: median 101.87 → 97.01 ms; p95 117.24 → 116.32 ms. This small change is not evidence of production capacity or a statistically established speedup. Reduced history loading matters more as snapshot volume grows.

Evidence is in `docs/verification/backend-performance-*`.

## Follow-up

The SQLite database filtering follow-up is now implemented; see [SQL catalog browsing](SQL_CATALOG_BROWSING.md) for verification and measurements.

Original scaling assessment: browse prepared and filtered the full catalog in Python. Moving filtering, sorting and facets into indexed database queries is the next larger performance project and needs parity checks for enrichment fields and canonical release status. This update does not activate external request interpretation providers, deploy publicly, add password recovery, or replace process-local jobs with a durable queue.
