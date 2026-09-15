# Database-backed catalog browsing

The SQLite deployment now runs browse/search predicates, ordering, result counts, pagination and full-catalog facets in SQL. Only movies on the requested page and their latest analytics are hydrated into ORM objects. There is no global ORM or facet cache to invalidate.

Exact JSON-array membership preserves genre, studio, director and streaming filters. Persisted enrichment falls back to the existing legacy catalog entries when missing. Literal substring search uses `instr` so `%`, `_` and backslashes remain ordinary characters. Small deterministic SQLite functions preserve Unicode lowercase and validated IMDb rating parsing. Release status uses the request's date; release/year ranges can use the existing release-date index. Latest analytics are joined through an indexed movie lookup; historical rows are not loaded.

Offline enrichment readers now consistently use persisted metadata or legacy defaults. A process-local detail cache cannot change filter membership in one worker while another worker returns different facets. Network-enabled detail enrichment retains its provider cache.

The previous Python implementation remains as a compatibility path for other database dialects and as a regression reference. SQLite is the configured deployment. No table changes or data migration were required.

## Evidence

- 66 backend tests passed, including SQL/reference parity across all sort modes, page clamping, empty catalogs, Unicode/literal search, rating validation, combined filters and current release status.
- A hydration regression verifies a four-movie page loads exactly four Movie objects and at most four latest analytics objects.
- 50 read-only comparisons on the existing 1,369-movie host catalog matched movie IDs, counts, pagination and facets.
- All 12 Playwright browser tests passed.
- The backend image was rebuilt and the existing localhost:3020 site updated. Live browse, genre/rating filtering, search, unsupported years and recommendations responded successfully.

Fresh local Docker HTTP measurements used the same catalog, frontend proxy, 3 warmups, 25 samples and concurrency 1:

| Metric | Before | After |
| --- | ---: | ---: |
| Median | 103.43 ms | 32.14 ms |
| p95 | 119.74 ms | 39.78 ms |
| Maximum | 135.80 ms | 75.64 ms |

These are local sequential measurements, not production load or capacity evidence. Files are in `docs/verification/sql-browse-*`.

## Scaling limits

Substring matching and JSON facets still require database scans; moving execution into SQL does not make every filter indexed. A future larger deployment may benefit from normalized facet tables, full-text search with explicitly agreed search semantics, and dedicated load testing. The non-SQLite compatibility path still filters in Python.
