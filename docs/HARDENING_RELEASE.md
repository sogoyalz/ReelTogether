# ReelTogether implementation release — October 31, 2026

This local branch implements a substantial stabilization and account-management release against baseline `6fea66ee564e80971e70b43fe91eae0b6c0729e0`. It is not a claim that every optional feature in the previous 18-feature catalog has been delivered, or that the application has passed a hosted production launch. Remaining work is recorded below.

Historical verification notes for the stabilization release. Current rollout and recovery instructions are in [Production candidate](PRODUCTION_CANDIDATE.md). Publishing source changes does not deploy the application or migrate a production database.

## What users gain

- Account security now supports password changes, signing out other browsers, a private JSON export and permanent account deletion after password re-entry. The UI requires a typed username confirmation for deletion. The API enforces authentication, CSRF/origin checks, throttling and password verification. Changing a password rotates the current session, revokes all prior sessions and clears the old recovery code.
- Movie-night invitations survive registration/sign-in through a same-origin, movie-night-only continuation. Invite tokens remain in fragments rather than query parameters. Signing out clears another open tab’s private watchlist immediately.
- Missing reviews no longer appear as 100% alignment or a 50% sentiment score. Comparisons show ties and missing leaders honestly. Failed clipboard access offers a copyable link.
- Movie detail reads no longer wait on optional OMDb/Wikipedia/Wikidata requests. Closed insights defer history/AI requests, rendering and chart downloads. Gallery artwork is lazy-rendered and decorative fallbacks avoid duplicate title text.
- Home feeds and quick search distinguish absence from request failure and provide retry controls. Favourites, account help text and comparison controls have targeted accessibility fixes.

## Data integrity and backend changes

Demo catalog records reserve negative provider IDs and carry explicit provenance. Migration `20261031_0011` repairs only exact legacy demo matches, preserving internal movie IDs and user references. Ambiguous modified demo rows are not guessed; imports guard against overwriting those identities.

OMDb refreshes preserve known facts when a response omits fields. Canonical IMDb IDs are preferred; title/year fallback is checked before accepting facts. Review ingestion stores external review IDs, normalizes UTC legacy keys and enforces `(movie_id, source, source_review_id)` uniqueness in migration `20261031_0012`.

A trailer change archives the previous analytics row and its observation provenance before clearing counts for the new video. Migration `20261031_0013` preserves duplicate legacy snapshots under archived labels, keeps the newest original label, adds uniqueness and a movie/date index. Provider verification timestamps are distinct from generic database update timestamps.

Catalog imports isolate records with savepoints, validate provider payloads and retain successful records when another item fails. Non-Latin titles receive stable nonempty URLs; title refreshes retain prior slugs. Release labels use the current date consistently. Compound chat requests with unsupported clauses ask for clarification.

SQLite and PostgreSQL execute browse filtering, ordering, counts, facets and pagination in SQL. A four-item page hydrates four Movie objects and at most four latest analytics objects. Homepage/dashboard aggregation happens in SQL and hydrates only selected films, without historical analytics. PostgreSQL text normalization uses the `und-x-icu` collation and stable C ordering; validate that collation on the chosen hosting database.

Public movie serialization is shared through a service module rather than imported from another route module. Home/discovery and private account payloads have executable response boundaries. Readiness checks every mapped table/column. Lifespan hooks have explicit cleanup/failure tests.

## Security and operations

The proxy and backend reject request bodies above 64 KiB, including bodies without Content-Length. Backend body reads also have a ten-second deadline. Existing schema limits, CSRF/origin enforcement and bounded password hashing still apply.

Frontend responses add `nosniff`, frame restrictions, referrer and permissions policy, and a limited CSP (`frame-ancestors`, `object-src`, `base-uri`). Production adds HSTS. This is not a nonce-based script CSP or a general security certification.

Maintenance HTTP routes enqueue durable jobs. Healthy worker leases serialize catalog mutation jobs across names. Protected `/api/admin/metrics` exposes bounded process-local request histograms and anonymous room-transition counts; it does not retain usernames, room IDs, invite tokens, chat bodies or request bodies. Counters reset on restart and do not constitute a durable SLO or billing system.

Core Python dependency auditing reports no known vulnerabilities. Frontend production dependency auditing and root infrastructure auditing report no known vulnerabilities. The full frontend tree retains 16 moderate findings rooted in lint-tool dependencies. High/critical findings are zero. Compatible fixes were applied; the audit’s incompatible downgrade suggestions were not forced. These are scan results for the inspected dependency trees, not a guarantee against undisclosed vulnerabilities or experimental dependency sets.

CI now separates backend, frontend and security jobs so a unit failure cannot prevent independent security checks. The full frontend tree gates high severity; runtime dependencies and infrastructure gate all severities. Existing experimental dependencies remain outside the core runtime.

## Verification performed locally

| Check | Result |
| --- | --- |
| Backend unittest discovery | 131 tests passed |
| Chromium browser flows | 26 tests passed |
| PostgreSQL workflow smoke | Passed: migrations, schema check/readiness, catalog, accounts, watchlists, rooms and durable jobs |
| PostgreSQL catalog suite | Five tests passed, including Unicode/rating edge cases, all sorts/filters, bounded hydration, homepage aggregation and empty catalog |
| SQLite migrations | Fresh upgrade/check and historical adoption with real rows, backup creation, demo repair and duplicate-snapshot preservation passed |
| Frontend lint / strict TypeScript / production build | Passed |
| Core Python audit | No known vulnerabilities found |
| Frontend runtime audit | Zero vulnerabilities |
| Full frontend audit | 16 moderate; zero high/critical |
| Root infrastructure audit | Zero vulnerabilities |
| Patch / whitespace checks | Recorded in the delivery manifest |

Browser coverage includes signup/watchlist/recovery, cross-tab logout, invitation continuation, password/export/delete controls, room voting/restart/reveal/selection, delayed insights, response security headers, oversized requests and mobile layout. Targeted contrast checks cover enabled favourite suggestions and account help text. This is not complete WCAG certification or a public load test.

Mobile screenshots use an offline fixture and the development server; the development indicator is not a production UI element. No live provider credentials were used. Earlier failed regression attempts were corrected before the final recorded passing runs.

Docker daemon access was attempted, but the local daemon was stopped. No image build or container smoke result is claimed for this release. Hosted CI, live provider quota/identity checks, public HTTPS, ingress behavior and off-host restore/rollback remain unverified.

## Applying and reviewing

The source ZIP includes tracked source/configuration/documentation and new release files. It excludes `.git`, `node_modules`, build output, databases, credentials and generated local instructions. The patch targets the baseline commit above and includes new files. The evidence bundle contains final local validation logs and dependency audit results.

Review the data migrations before applying them to an existing installation. Create and verify a backup first. SQLite `python upgrade_database.py` creates a backup before upgrading; PostgreSQL requires an operator-provided native backup/restore point. Use `--adopt-existing` only for an inspected historical unmanaged schema. Then run backend regressions and frontend checks using the README/CONTRIBUTING instructions.

Run a maintenance worker before expecting queued refreshes to execute. An HTTP 202 acknowledgement does not mean data has refreshed. Poll `/api/admin/jobs/{job_id}` using the admin key. Do not expose that key in frontend code. API consumers of the legacy refresh-count responses must adopt the job acknowledgement described below.

For rollback, preserve the verified pre-upgrade backup and its matching application version. Demo ID repairs and archived snapshot labels intentionally do not reverse automatically; restoring unsafe identities would recreate collisions. The review/deployment plan must account for this data change.

## API changes

- New authenticated operations: `POST /api/auth/password`, `POST /api/auth/revoke-other-sessions`, `GET /api/auth/export`, `POST /api/auth/delete-account`.
- Legacy `POST /api/movies/sync-tmdb` and analytics refresh routes now return HTTP 202 `{job_id,status}` rather than synchronous counts; targeted refreshes use the same queue.
- Review alignment is nullable when either perspective lacks evidence. The TypeScript consumer accepts that null.
- Discovery collections return the shared MovieSummary contract. Homepage dashboard includes `updated_at`.
- Core detail reads return stored metadata; optional live wiki context is not fetched in HTTP reads.
- Released titles without sourced actuals no longer present an experimental estimate as a future forecast.

## Remaining release decisions

Public deployment, live provider setup, ingress/distributed rate limits, provider spend limits, off-host retention and a verified hosted restore are still required before claiming production readiness. Account deletion removes active database data and hosted rooms, but backup retention/purge behavior must be validated in the chosen deployment.

The About route contains TMDB’s required notice and JustWatch credit. The current [TMDB FAQ](https://developer.themoviedb.org/docs/faq) also requires an approved logo and specifies attribution placement; the [movie watch-provider documentation](https://developer.themoviedb.org/reference/movie-watch-providers) requires JustWatch attribution. The official branding asset page could not be retrieved through the available web fetch. Approved branding assets and the applicable public/commercial activation decision remain outstanding. No full licensing compliance claim is made.

The broader roadmap remains explicit: regional streaming availability, group runtime/language constraints and readiness/leave/host-transfer flows, recurring groups, collections, calendar integrations and other optional proposals are not implemented by this release. CSS consolidation, additional component extraction, exhaustive response generation and durable observability also remain.

## Audit issue status

“Implemented” refers to the concrete change described, verified locally. “Partial” keeps the unresolved acceptance criteria visible; it must not be counted as a closed issue.

| Issue | Status | Implementation / remaining criteria |
| --- | --- | --- |
| RT-001 | implemented | Reserved negative demo IDs, explicit provenance, exact-match legacy repair, and a live-import guard for ambiguous legacy demo rows. Internal IDs remain stable. |
| RT-002 | partial | Patched Next/React/Axios and compatible transitives in both lockfiles. Runtime audits are clean; 16 moderate lint-tool dependency advisories remain. |
| RT-003 | implemented | Future-release test uses a date relative to today rather than a date that has already passed. |
| RT-004 | implemented | Partial OMDb results merge only known facts; missing/null fields preserve stored metadata. |
| RT-005 | implemented | Provider review IDs have a database uniqueness constraint; legacy timestamp identities normalize UTC across database dialects. |
| RT-006 | implemented | Revoked/expired cookies fall back to guest discovery. AI-enabled requests still require a valid authenticated session. |
| RT-007 | implemented | Storage-event account invalidation clears private query caches across tabs; focus and 401 responses revalidate account state. |
| RT-008 | implemented | New demo records and verified legacy demo repairs use Science Fiction, matching supported filters and TMDB naming. |
| RT-009 | implemented | Non-Latin titles get nonempty ID-based slugs; provider title changes preserve existing URLs; collisions resolve deterministically. |
| RT-010 | implemented | Core detail, analytics and comparison reads use persisted metadata and make no optional provider requests. Live wiki context is no longer fetched on that critical path. |
| RT-011 | implemented | Legacy adoption checks the historical nine-table schema, creates a backup and upgrades through the current migrations. |
| RT-012 | implemented | Per-record savepoints, payload validation and sanitized failures preserve unrelated successful imports. |
| RT-013 | implemented | Trailer replacement archives prior analytics/provenance and clears counts before observing the new video. Sourced labels require matching video URLs. |
| RT-014 | implemented | Discovery, suggestions, dashboards and public summaries use date-derived release status, including release day. |
| RT-015 | implemented | Unsupported residual clauses request clarification instead of silently applying only the recognized subset. |
| RT-016 | implemented | Missing review evidence yields null alignment, No reviews UI and no fabricated positive/negative drivers. |
| RT-017 | implemented | Favourite suggestions and account help text have readable colors; browser regressions verify at least 4.5:1 contrast for those controls. |
| RT-018 | implemented | Comparison search has an associated label and selectable films expose aria-pressed. |
| RT-019 | implemented | Frontend responses set anti-framing, MIME, referrer, permissions and a limited CSP policy. Production adds HSTS. |
| RT-020 | partial | Both proxy and backend enforce 64 KiB body ceilings, including chunked requests; backend body reads have a deadline. Shared ingress/account budgets and provider spend controls still depend on deployment. |
| RT-021 | implemented | SQLite and PostgreSQL browse in SQL with page-sized hydration. Homepage/dashboard statistics aggregate in SQL and load only selected films. |
| RT-022 | partial | Fast active collaboration polling is retained; revealed rooms poll less frequently, hidden tabs pause, transient errors back off and focus refreshes. Lightweight version polling is deferred. |
| RT-023 | implemented | Readiness selects every mapped column in every persisted table, detecting missing feature schema. |
| RT-024 | partial | Password changes, revocation of other sessions, private data export and reauthenticated account deletion are implemented. Hosted backup retention/purge behavior still needs operator validation. |
| RT-025 | pending external | No hosted rollout, HTTPS/ingress validation or off-host restore was performed. Docker daemon was unavailable for image verification. |
| RT-026 | implemented | Backend, frontend and security run as independent CI jobs. PostgreSQL parity and real migration paths are included. Hosted CI itself has not run for this local branch. |
| RT-027 | partial | Account/watchlist/export and home/discovery payloads have executable response schemas; missing homepage timestamp and discovery shape mismatch are fixed. Full generated TypeScript/OpenAPI coverage is deferred. |
| RT-028 | partial | Movie DTO serialization moved out of route modules; cached detail network orchestration and unsafe parallel ORM serialization were removed. Large page/workspace extraction remains. |
| RT-029 | partial | Removed unused reseeding, live full-summary serialization and search-import helpers. Broader experimental ML/RAG/component cleanup remains a separate decision. |
| RT-030 | pending | The three stylesheet layers are retained. Targeted contrast is fixed; full visual-token consolidation remains. |
| RT-031 | partial | Homepage feeds distinguish empty/error states and offer retry; quick search distinguishes connectivity failure from no results. Exhaustive form-field error mapping is deferred. |
| RT-032 | implemented | Forecast descriptions identify the import popularity heuristic and its limits; released titles without actuals no longer show a future revenue forecast. |
| RT-033 | implemented | Winner board identifies ties and unavailable data; clipboard failure exposes a selectable comparison URL. |
| RT-034 | partial | OMDb uses a canonical IMDb ID when available and validates title/year fallback. Wiki identity resolution remains unverified and excluded from core detail reads. |
| RT-035 | implemented | Duplicate legacy snapshots are archived, not deleted; movie/label uniqueness and a movie/date index are enforced. |
| RT-036 | partial | README, contributing guide, PR/issue templates and this release record are updated. An owner-selected license, public demo and broader portfolio assets remain. |
| RT-037 | partial | Protected process-local route latency/error histograms and anonymous room-transition counters are available. Durable SLO collection, DB wait metrics and external alert validation remain. |
| RT-038 | implemented | FastAPI lifespan replaces deprecated hooks; repeated startup/shutdown and startup-failure behavior have regression coverage. |
| RT-039 | partial | HTTP refreshes enqueue durable jobs and healthy leases serialize catalog jobs across names. This is at-least-once work; side-effect fencing under arbitrary worker failure or direct CLI concurrency is not established. |
| RT-040 | implemented | Closed insights defer API requests, rendering and chart modules. Gallery uses lazy Next Image rendering; decorative fallback artwork no longer repeats the hero title. |
| RT-041 | partial | About/data-source credits, the TMDB notice and JustWatch attribution/link are visible. Approved TMDB branding assets and commercial/public activation checks remain pending. |

## Follow-up recheck

A subsequent recheck found that the public analytics and comparison endpoints still called OMDb even though core movie-detail serialization had been made offline. Those calls are now replaced with normalized stored metadata. A regression configures an OMDb key, blocks provider network calls and verifies movie detail, analytics and comparison all return successfully while retaining the stored ratings. The regression failed against the earlier implementation and passes after this correction.

Fresh validation: 131 backend tests, 26 Chromium tests, frontend lint, TypeScript and production build passed. Frontend production dependency auditing remains clean; the full frontend tree retains 16 moderate tooling advisories. This recheck does not change the outstanding production and roadmap items listed above.
