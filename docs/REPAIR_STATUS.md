> **Latest follow-up:** Authenticated watchlists, Docker execution, restart persistence, and backup restoration are now verified. See [release verification](RELEASE_VERIFICATION.md). The remainder of this document records the earlier repair pass.

# Repair status — September 13, 2026

The original `PROJECT_REVIEW.md` describes the pre-repair tree. This repair improves the supported catalog/research app; it does not certify that every possible defect is eliminated or that the product is production-proven.

## Disposition of the original findings

| Review ID | Change / disposition |
| --- | --- |
| R01 | Analytics response now includes the frontend's full analysis shape. Browser detail rendering is covered. |
| R02 | Actual box-office data no longer produces a null required note or claims to verify unrelated attention estimates. |
| R03 | Home and paginated upcoming feeds have distinct React Query keys. Navigation regression covered. |
| R04 | Imports match by TMDB ID, never by title; pending imports are flushed before slug resolution. Already-corrupted historical identities require provider reconciliation. |
| R05 | All maintenance routes require a configured admin key, including development. Disabled user-specific experiments are not exposed in production. |
| R06 | Blocking database/provider API handlers use synchronous FastAPI handlers; Redis checks are offloaded from async middleware. |
| R07 | Detail/list/analytics serialization applies the canonical status/provenance/forecast contract. |
| R08 | Container startup runs migrations; Compose and Render define persistent SQLite storage. Legacy upgrade tooling validates layout and backs up first. Container runtime/cloud deployment remain unverified. |
| R09 | Compose explicitly permits its internal backend hostname. Configuration validation passes. |
| R10 | Next.js/React and core Python dependencies upgraded. Both core dependency audits report no known vulnerabilities at verification time. Optional ML dependencies are excluded from that claim. |
| R11 | Rating filtering reads persisted provider metadata. Missing ratings correctly fail a positive threshold. Existing catalogs need an OMDb-enabled refresh to populate ratings. |
| R12 | Browse forwards the director filter to catalog filtering. |
| R13 | TMDB enrichment and OMDb metadata are persisted in JSON columns and survive process restart. |
| R14 | Catalog refresh preserves existing analytics. YouTube refresh records verification metadata and dated observations. |
| R15 | History returns stored snapshots; fabricated growth curves and static box-office outlook histories are removed from public output. Earlier history cannot be reconstructed. |
| R16 | Synthetic discussions are not created or counted publicly; sample sizes reflect stored sourced discussions. Aggregate critic scores are not ingested as authored review sentences. |
| R17 | Public analysis reads current observations; legacy snapshots refresh when their input data changes. |
| R18 | Training CLI now runs explicitly and fails clearly without suitable data. Public forecasts are identified as experimental heuristics. A trained production model remains future work. |
| R19 | Training requires observed pre-release features and sourced outcomes; insufficient data and empty evaluation sets fail. Temporal partitions are disjoint. Statistical/model quality is not claimed. |
| R20 | Proxy requests and responses use no-store, with an upstream timeout. Mutation/private failures cannot receive a public cache policy. |
| R21 | Matching proxy secrets support signed anonymous browser identifiers rather than one shared proxy quota. These are not authentication or robust anti-abuse identity; ingress IP limits remain deployment work. |
| R22 | Catalog filters/facets/output derive status from release dates; release-day handling is consistent across feeds. |
| R23 | Date-only release values format in UTC, preserving calendar dates in Chicago. |
| R24 | Secondary-button contrast, keyboard focus, disabled states, and table scrolling corrected. |
| R25 | Upcoming and entity pages expose pagination; upcoming ordering is nearest release first. |
| R26 | Migration aligns cascade constraints, including legacy review tables. Schema checks pass; runtime SQLite connections enforce foreign keys. |
| R27 | Sentiment normalization is monotonic, and score breakdown normalization matches the scoring formula. |
| R28 | Caches are bounded; browse no longer caches ORM instances across sessions. Jobs use two workers, bounded retention, and active-job deduplication. |
| R29 | Provider negative caches expire quickly, successful entries expire, Redis connection attempts back off and retry, and network timeouts are bounded. |
| R30 | 392 generated build-backup files removed from the index; local copies preserved. Ignore rules exclude them from Git, TypeScript, and Docker contexts. |

Additional changes: strict TypeScript; noninteractive lint configuration; CI workflow; comparison IDs deduplicated/bounded with URL state as the source of truth; debounced search suggestions; mixed-unit bar chart replaced with separate values; unvalidated confidence/feature importance claims removed; default RAG startup disabled; recommendation/chat/rating experiments excluded from the supported product navigation/scope.

## Verification and evidence

See `verification/` for the final local test/build/audit logs. Browser tests use an offline fixture backend and real Chromium. Database migration was exercised on a fresh database and on a copy of the existing legacy database before applying locally. The local upgrade retained all 1,369 movies and row counts in all nine existing tables, with zero foreign-key violations. A timestamped SQLite backup is stored beside the database and ignored by Git.

Strict TypeScript and the production frontend build pass. Lint has no errors and three nonblocking Next.js image-optimization warnings. Compose configuration validates; Docker execution was unavailable because the local Docker daemon was stopped. The GitHub Actions workflow is added but has not yet run remotely. Provider-backed ingestion, cloud secrets/hosting, and restored-backup operation have not been verified against a live deployment.

## Remaining release work

1. Restart local servers to load the upgraded dependencies and matching proxy secrets. Run the documented setup on a clean machine or container.
2. Configure provider keys and refresh metadata. Validate identity/source correctness against providers, especially any records imported before the identity fix.
3. Bring up Docker, verify persistent data across restart, exercise a backup restore, then deploy and smoke-test the real provider-backed application.
4. Keep forecasts experimental until a suitable historical dataset, baseline, held-out evaluation, and calibration exist. Keep personal features disabled until authentication and ownership checks exist.
5. Benchmark full-catalog filtering before claiming scale. Adopt durable jobs/shared infrastructure before multiple backend instances.
