# ReelTogether: internship project direction

## Product decision

Make this a dependable movie discovery and research app. A recruiter should be able to open it, search a movie, understand its sources, compare it with another title, and see a coherent result. A small finished product with credible engineering evidence is stronger than a long menu of unfinished automated analysis features.

## Build next, in order

1. **Publish and validate the core demo.** Configure provider keys, refresh the catalog, deploy, and exercise search → detail → compare on mobile and desktop. Add a short demo video and a public architecture diagram. Record deployment date and actual data coverage.
2. **Watchlists implemented.** Accounts, server-side sessions, ownership checks, database uniqueness, watched status, and API/browser tests are now implemented. Next complete account recovery and validate HTTPS deployment before a broad public launch.
3. **Make data freshness visible.** Show provider name, observation time, and missing/estimated labels alongside each metric. Add a maintenance screen with job failures, last successful refresh, and quota-aware retry. Complete a backup-and-restore drill.
4. **Measure performance.** Benchmark browse/search with 1,000 and 10,000 catalog entries. Measure p50/p95 latency and query counts before moving filters into indexed database queries. Document results, hardware, and workload; claim improvements only after measurement.
5. **Choose one advanced extension.** Either build explainable recommendations with offline ranking evaluation and cold-start handling, or build a credible forecasting dataset with pre-release features, sourced outcomes, temporal holdouts, and a simple baseline. Do not add both before the core is dependable.

## Engineering work that earns interview discussion

- Explain the cache collision between an array and a paginated response, and demonstrate the browser regression test.
- Explain why movie titles cannot identify remakes, and show stable TMDB identity handling.
- Explain why an actual box-office number does not verify an unrelated social metric.
- Explain why synchronous I/O in an async route blocked other work and how FastAPI's synchronous handlers move that work to its thread pool.
- Explain migrations, rollback/backup decisions, and the limitations of in-process jobs and SQLite deployment.
- Explain why inferred audience counts are not review samples and why training/test overlap invalidates an accuracy claim.

## Résumé wording you can substantiate after understanding the code

**ReelTogether — Movie Discovery & Research App** | Next.js, TypeScript, FastAPI, SQLAlchemy, SQLite, Docker

- Built a full-stack movie research application with paginated discovery, provider metadata ingestion, and side-by-side comparisons.
- Implemented authenticated private watchlists with Argon2id password hashing, revocable sessions, CSRF protection, and ownership tests.
- Added source-aware responses, database migrations, and automated API/browser regression checks.
- Implemented strict TypeScript validation and a CI workflow covering linting, builds, migrations, and dependency audits.

Add “deployed” only after a live deployment works. Add the catalog count only after a successful refresh and count query. Add latency or accuracy improvements only after reproducible measurement. Do not describe it as production-proven, real-time social listening, or validated forecasting in its current form.

## Before applying

Be able to explain one request end-to-end without reading a script. Run the test suite yourself, reproduce one original bug, and explain its fix. Keep the README, live demo, screenshots, and résumé consistent. Acknowledge tools or assistance honestly if asked; your ability to reason about the implementation matters more than the number of files.
