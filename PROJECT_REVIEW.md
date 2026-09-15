> **Historical review:** These findings describe the tree before the repair pass. See [current repair status](docs/REPAIR_STATUS.md) for changes, verification, and remaining limitations.

# ReelTogether — full code review

Reviewed 2026-09-13. Scope: current working tree, including staged and unstaged changes, rather than only the last commit. Review anchor: HEAD `64762ba`; the checkout already contained extensive changes.

**Assessment: not ready for a public production release.** The application has substantial catalog, analytics, and UI code, but confirmed runtime crashes, ingestion data corruption, unprotected refresh routes, and misleading data/model outputs need repair. A successful build alone does not establish readiness.

## Scope and verification

- Read all **127 authored source, configuration, documentation, test, and artifact files** in the inventory below, including empty files and the package lockfile's dependency metadata. Approximately **13,992 lines** excluding the package lockfile.
- Reviewed frontend pages/components, API contracts, database models/repositories/migrations, providers, scoring, ML/RAG paths, jobs, caching, security middleware, CSS, environment examples, and Docker/Render setup.
- Inspected the 392 generated build-backup files as generated artifacts and measured their size. Did not treat bundled dependencies or compiled duplicates as independently authored code requiring a redundant line-by-line review.
- Checked the existing database using SQLite read-only mode for counts/status consistency. No catalog data, ratings, credentials, staged changes, or application source were edited.
- Frontend dependencies were reinstalled from the unchanged lockfile during verification; no dependency upgrades were applied.
- Required code-review-graph tools were tried first after reading the parent AGENTS.md; they returned no usable node/community coverage. Source review was used as the fallback.
- Providers were stubbed or API keys disabled in isolated reproductions. No paid provider calls, live user writes, production deployment, or exploit traffic were performed.

| Check | Result |
|---|---|
| Existing backend unittest suite | **3/3 pass**, using backend/venv |
| Frontend TypeScript | **Pass** (`tsc --noEmit --incremental false`) |
| Fresh frontend install and production build | **Pass**, in a temporary copy with its own npm dependencies |
| Frontend lint command | **Not configured**; opens ESLint setup prompt and exits unsuccessfully |
| Basic HTTP smoke paths | 13 paths return 200 with isolated SQLite fixtures and providers disabled/stubbed |
| Movie analytics with sourced box office | **500**, confirmed response validation failure |
| Comparison with sourced box office | **500**, same defect |
| automated analysis-response component render | **Fails** in both critic/audience and forecast components |
| Cross-page upcoming cache | **Fails**, incompatible response shapes |
| Same-title import | **Overwrites original identity**; same-title pending batch also raises IntegrityError |
| Unauthorized refresh requests | **Accepted** despite production admin key being set |
| SQLite migrations to head | **Pass** on a new temporary database |
| Alembic schema drift check | **Fails**, five foreign-key differences |
| npm audit | **11 affected packages**, including critical/high advisories; applicability requires per-advisory assessment |

The initial temporary build used a node_modules symlink and hit a tracing-path error caused by that test arrangement. A fresh local dependency install in the temporary copy resolved it and the complete standalone build passed. This was not classified as a product defect.

Limitations: no full browser interaction/accessibility audit, real-provider end-to-end validation, load test, Docker execution, PostgreSQL execution, or full ML dependency installation. The local backend environment is missing numpy, chromadb, sentence-transformers, and vaderSentiment; the required packages are listed in requirements.txt, but the current environment cannot exercise those paths. An unconditional RAG startup step reproduces a missing-chromadb failure locally. Build, route, and component reproductions are narrower than those unperformed checks.

## Findings

P1 = fix before public release because a core path fails, data is corrupted, or deployment/security is blocked. P2 = concrete correctness, reliability, presentation, or maintenance issue. Each item explains the trigger and suggested repair. This is a review, not an implementation change.

### R01 [P1] Successful automated analysis responses crash movie pages

[backend/app/schemas/ai.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/ai.py:63>) · [backend/app/api/ai.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/ai.py:35>) · [frontend/app/movies/[slug]/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/movies/[slug]/page.tsx:306>) · [frontend/components/movies/ForecastConfidenceCard.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/ForecastConfidenceCard.tsx:15>) · [frontend/components/movies/CriticAudienceDashboard.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/CriticAudienceDashboard.tsx:4>) · [frontend/lib/api.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/lib/api.ts:211>)

The frontend requires `critic_vs_audience`, `prediction.feature_importance`, forecast ranges, and methodology. The backend response model and serializer omit those fields. Once the automated analysis request succeeds, the page dereferences `ai.critic_vs_audience.critics`; the forecast card also calls `.map()` on an absent array. TypeScript accepts the hand-written interface but does not validate HTTP data.

**Confirmed:** the real API response contains only sentiment, prediction, summary, public_opinion, and discussions. Passing it into the two actual components reproduces “Cannot read properties of undefined (reading 'critics')” and “reading 'map'”. Align the API schema and serializer with the UI, then add a contract test that renders the actual response. Optional sections also need explicit unavailable states.

### R02 [P1] Reported box-office revenue causes analytics and comparison HTTP 500s

[backend/app/services/prediction_model.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/prediction_model.py:251>) · [backend/app/schemas/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/analytics.py:33>) · [backend/app/api/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/analytics.py:116>) · [backend/app/api/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/analytics.py:186>)

When OMDb supplies `box_office`, `normalize_public_forecast()` returns `engagement_metrics_note=None`. Both response schemas require a string. Constructing the response raises Pydantic ValidationError.

**Confirmed:** mocked sourced actuals produce HTTP 500 for both `/api/analytics/movie/1` and `/api/analytics/compare?movie_ids=1,2`; the same analytics route returns 200 without actuals. Make nullability consistent. This branch also marks all engagement metrics as non-estimated simply because box-office actuals exist; provenance must be tracked independently by field.

### R03 [P1] Homepage and Upcoming page collide in the query cache

[frontend/components/home/UpcomingMovies.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/home/UpcomingMovies.tsx:12>) · [frontend/app/upcoming/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/upcoming/page.tsx:12>) · [frontend/app/providers.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/providers.tsx:13>)

Both queries use `['upcoming-movies']`. The homepage stores `MovieSummary[]`; the Upcoming page expects `{items, total, ...}`. The shared QueryClient keeps data fresh for 30 seconds, so navigating immediately from Home to Upcoming reads an array and calls `data.items.map`, throwing. In the reverse direction the homepage treats a pagination object as an empty feed.

**Confirmed:** reproductions with the installed QueryClient demonstrate both wrong shapes. Include endpoint and parameters in distinct keys, or use one consistent response contract.

### R04 [P1] TMDB imports can overwrite a different film with the same title

[backend/app/services/tmdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/tmdb.py:178>) · [backend/app/services/tmdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/tmdb.py:245>)

Both upsert paths first search by TMDB ID, then treat the owner of the title-derived slug as the same movie. Importing a remake with a different TMDB ID replaces the original row's identity, date, and metadata, while existing ratings and discussions remain attached to that database ID. The slug-conflict helper cannot protect a row already selected as `existing`.

**Confirmed:** importing another ID with an existing title leaves one row, replaces its TMDB ID, and reports one update. Two same-title new results in an unflushed search import also fail with `UNIQUE constraint failed: movies.slug`. Match provider records by stable provider identity; allocate distinct slugs and account for pending rows in the same transaction.

### R05 [P1] Expensive mutation endpoints bypass admin authorization

[backend/app/api/movies.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/movies.py:394>) · [backend/app/api/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/analytics.py:209>) · [backend/app/api/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/analytics.py:222>) · [backend/app/api/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/analytics.py:234>) · [backend/app/api/admin.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/admin.py:18>)

Catalog sync, global YouTube refresh, individual YouTube refresh, and review sentiment refresh are public POST routes. Their only dependency is the database session. They trigger writes and external API work without invoking the admin authorization used by `/api/admin/jobs/*`.

**Confirmed:** with production mode and an admin key configured, requests without a key return 200 on catalog/analytics refresh, while the corresponding admin job route returns 401. Provider calls were disabled during the test. Share one authorization dependency and enqueue bounded background work. Do not rely on the frontend hiding controls.

### R06 [P1] Blocking work runs on the async request event loop

[backend/app/api/movies.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/movies.py:386>) · [backend/app/api/search.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/search.py:41>) · [backend/app/api/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/analytics.py:75>) · [backend/app/api/recommendations.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/recommendations.py:16>) · [backend/app/core/middleware.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/core/middleware.py:47>)

The routes are `async def` but call synchronous SQLAlchemy, urllib HTTP requests, synchronous Redis, and ThreadPoolExecutor waits directly. Parallelizing provider requests inside a context manager still blocks the caller while it waits for completion. A slow metadata call, search import, recommendation explanation, or refresh can stall unrelated requests on the worker.

**Confirmed:** a 250 ms mocked detail operation delays an independent 10 ms asyncio heartbeat to 267 ms. Use sync endpoints for blocking implementations, bounded thread offloading, or async clients and database sessions. Put catalog refresh and model work outside request handling and enforce timeouts.

### R07 [P1] Detail and automated analysis APIs bypass public forecast and provenance rules

[backend/app/api/movies.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/movies.py:140>) · [backend/app/api/ai.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/ai.py:46>) · [backend/app/schemas/movie.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/movie.py:48>) · [frontend/app/movies/[slug]/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/movies/[slug]/page.tsx:136>)

The analytics and compare APIs apply `build_movie_data_contract`, but movie details copy raw forecasts and accept default `forecast_is_public=True`, empty warnings, and uncorrected status. automated analysis responses likewise return bootstrap forecasts directly. The page displays those automated analysis forecasts even when the canonical analytics response would suppress them.

**Confirmed:** a released streaming-only fixture is suppressed by the canonical function but details return public=true and an $8 million opening forecast. Apply one contract consistently across all public payloads, including the automated analysis snapshot. Keep actual domestic revenue distinct from opening-weekend predictions: MovieHero currently substitutes total reported box office into an opening-labeled metric.

### R08 [P1] Production deployment does not initialize a fresh database

[render.yaml](</Users/souravgoyal/Desktop/Projects/moviess/render.yaml:16>) · [backend/Dockerfile](</Users/souravgoyal/Desktop/Projects/moviess/backend/Dockerfile:14>) · [backend/app/services/bootstrap.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/bootstrap.py:13>) · [backend/.env.production.example](</Users/souravgoyal/Desktop/Projects/moviess/backend/.env.production.example:21>)

The production blueprint disables AUTO_CREATE_TABLES. The container launches Uvicorn directly and the blueprint has no migration command. On a fresh database no component creates the tables, so startup sync and catalog queries fail. The production example also uses a relative SQLite database, but neither deployment definition mounts persistent database storage; recreating the container loses catalog changes and ratings when SQLite is used.

Run migrations as a deployment step and explicitly provision persistent storage or a supported database service. SQLite migrations themselves were successfully exercised in a temporary database; the defect is the missing deployment invocation. Docker/Render infrastructure was inspected statically, not deployed.

### R09 [P1] Default Docker Compose proxy requests are rejected

[docker-compose.yml](</Users/souravgoyal/Desktop/Projects/moviess/docker-compose.yml:17>) · [backend/.env.example](</Users/souravgoyal/Desktop/Projects/moviess/backend/.env.example:19>) · [backend/app/core/config.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/core/config.py:36>)

Compose sets frontend API_BASE_URL to `http://backend:8000`. Backend TrustedHostMiddleware allows only localhost and 127.0.0.1 under the documented example configuration. The forwarded Host header is `backend:8000`, so frontend API requests receive 400 Invalid host header.

**Confirmed:** the actual TrustedHostMiddleware rejects this hostname with the supplied defaults. Configure the internal service hostname deliberately, or provide an appropriate host-routing arrangement. CORS settings do not solve Host validation.

### R10 [P1] The dependency audit flags the deployed Next.js version

[frontend/package.json](</Users/souravgoyal/Desktop/Projects/moviess/frontend/package.json:17>) · [frontend/package-lock.json](</Users/souravgoyal/Desktop/Projects/moviess/frontend/package-lock.json:1>)

The current lockfile audit reports **11 affected packages: 1 critical, 7 high, 2 moderate, 1 low**. Next.js is pinned to 14.2.35 and is included in the affected ranges. Other affected packages include axios, lodash, postcss, and transitive tools.

This is a dependency finding, not a claim that every advisory is exploitable in this application. For example, some critical entries have platform or feature prerequisites. The [Next.js maintainer advisory for Server Components denial of service](https://github.com/vercel/next.js/security/advisories/GHSA-8h8q-6873-q5fj) explicitly includes Next.js 14 App Router versions in its affected range. Update supported dependencies and rerun the application checks; do not blindly apply a force upgrade. Full audit JSON is included in the evidence directory. Backend dependencies were not comprehensively vulnerability-scanned.

### R11 [P2] IMDb filtering and sorting operate on empty metadata

[backend/app/services/catalog_browser.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_browser.py:94>) · [backend/app/services/catalog_browser.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_browser.py:146>) · [frontend/app/movies/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/movies/page.tsx:222>) · [frontend/app/search/search-results.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/search/search-results.tsx:166>)

`_prepare_movie()` always sets metadata to `{}`. `_matches()` interprets missing IMDb ratings as zero. Any positive minimum removes every movie, even if OMDb has its rating. Rating sort also ranks all IMDb values as zero and falls back to hype/title.

**Confirmed:** a nonempty catalog returns zero results for minimum rating 1. Store/cache ratings in a queryable field before filtering; do not restore one network call per movie on every browse request.

### R12 [P2] The library director filter is silently ignored

[frontend/app/movies/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/movies/page.tsx:67>) · [backend/app/api/movies.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/movies.py:339>)

The UI sends `director`, and CatalogBrowseFilters supports it, but `/api/movies/browse` never declares or forwards it. FastAPI ignores the extra query parameter, so selecting a director leaves the catalog unfiltered. The search endpoint does accept it. Add the parameter to the browse route and test that other directors are excluded.

### R13 [P2] Enriched catalog metadata disappears after restart

[backend/app/services/tmdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/tmdb.py:22>) · [backend/app/services/tmdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/tmdb.py:146>) · [backend/app/services/catalog_enrichment.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_enrichment.py:253>) · [backend/app/models/movie.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/models/movie.py:11>)

Studios, cast, directors, providers, franchise, images, and embedded trailer URLs live in the process-only `_DETAIL_CACHE`; the Movie model does not persist them. Ordinary API calls use allow_network=false, including detail serialization. Restarting loses enrichment for imported titles that are not in the small static fallback table. Startup refresh only revisits selected feed pages, not the entire expanded catalog.

**Confirmed:** a non-seeded movie returns a cached actor before the cache is cleared and an empty cast afterward. Persist enrichment with refresh timestamps, and make catalog/discovery endpoints read it. Avoid live network work during every browse request.

### R14 [P2] TMDB sync overwrites measured YouTube statistics with estimates

[backend/app/services/tmdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/tmdb.py:292>) · [backend/app/services/tmdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/tmdb.py:328>) · [backend/app/services/youtube_analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/youtube_analytics.py:135>) · [backend/app/services/startup_jobs.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/startup_jobs.py:59>)

Every TMDB upsert calls `_populate_analytics`, replacing stored views, likes, comments, sentiment, and forecast values with estimates. Previously fetched YouTube measurements are discarded. Scheduled TMDB and YouTube refreshes are independently enqueued, so completion order can leave estimates as the final values; manual sync and search imports do the same.

**Confirmed:** a stored measured view count of 123,456,789 becomes 1,922,571 during TMDB population. Keep source-specific fields and observation timestamps, and only fill missing measurements with explicitly identified estimates.

### R15 [P2] The historical momentum chart is manufactured from one snapshot

[backend/app/services/catalog_enrichment.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_enrichment.py:279>) · [backend/app/api/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/analytics.py:129>) · [frontend/components/movies/TrendChart.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/TrendChart.tsx:16>)

`build_history()` derives six prior weeks by multiplying the current snapshot by fixed increasing coefficients. It never reads historical observations. The API and chart present the result as Momentum Over Time, and loading-state copy calls it historical snapshots. Even falling real metrics produce an upward-looking curve.

**Confirmed by source and returned history:** one current snapshot generates six past points. Store actual dated observations, or explicitly label the visualization as a simulated illustration and exclude it from factual trend analysis.

### R16 [P2] Synthetic discussion and sample counts are presented as public opinion

[backend/app/services/ai_foundation.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/ai_foundation.py:147>) · [backend/app/services/ai_foundation.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/ai_foundation.py:180>) · [backend/app/services/ai_foundation.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/ai_foundation.py:76>) · [frontend/app/movies/[slug]/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/movies/[slug]/page.tsx:127>)

The bootstrap creates Reddit/YouTube-labeled discussion templates with example.com URLs and marks them seeded only inside raw_payload. Public opinion aggregates those templates and emits viewer-highlight quotations without carrying the seeded flag to the frontend. Sentiment sample_size is invented from estimated mentions with a minimum of 80 rather than counted from analyzed reviews. The UI calls these scored discussion samples.

The review refresh path stores real review sentiments in a different table, so it does not automatically replace this synthetic evidence. Carry explicit provenance, exclude seeded items from real counts/summaries, and show insufficient-data states until sourced reviews are available.

### R17 [P2] automated analysis refresh leaves existing snapshots unchanged

[backend/app/services/ai_foundation.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/ai_foundation.py:180>) · [backend/app/services/ai_foundation.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/ai_foundation.py:206>) · [backend/app/services/ai_foundation.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/ai_foundation.py:234>) · [backend/app/services/startup_jobs.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/startup_jobs.py:133>)

Each `_ensure_*` helper returns immediately if any snapshot exists for the movie. The automated analysis refresh job calls those helpers, so changed metrics and newly ingested discussion do not recompute features, sentiment, predictions, or summaries. The UI can keep showing old values indefinitely.

**Confirmed:** increasing the underlying opening forecast tenfold leaves the automated analysis prediction unchanged at 92,288,000 after another foundation refresh. Separate initialization from recomputation, version snapshots by inputs, and test a changed-input refresh.

### R18 [P2] The advertised training command and runtime ML integration are incomplete

[backend/train_models.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/train_models.py>) · [backend/model_artifacts/box_office_forecaster.json](</Users/souravgoyal/Desktop/Projects/moviess/backend/model_artifacts/box_office_forecaster.json>) · [backend/app/services/prediction_model.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/prediction_model.py:12>) · [backend/app/services/ai_foundation.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/ai_foundation.py:234>) · [README.md](</Users/souravgoyal/Desktop/Projects/moviess/README.md:249>)

`train_models.py` is empty, and the saved forecaster JSON is also empty. The loader returns None. The richer `build_prediction_payload` and `apply_prediction_snapshot` functions have no callers in the application; the public automated analysis API uses the separate bootstrap heuristic. Thus the README claim that the training command updates an integrated artifact is not true for this checkout.

Implement an executable training entry point and connect validated inference to the serving path, or revise the product and resume claims to describe the current heuristic implementation. Do not claim trained model accuracy from this state.

### R19 [P2] Forecast evaluation uses forecast targets and overlapping splits

[backend/app/services/model_training.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/model_training.py:139>) · [backend/app/services/model_training.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/model_training.py:282>) · [backend/app/services/model_training.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/model_training.py:108>) · [backend/app/services/catalog_enrichment.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_enrichment.py:113>)

Training accepts static Opening and Domestic Outlook entries as ground truth, without requiring a released film or sourced actual revenue. With fewer than six rows, validation and test are subsets of the training set. It also selects the latest feature snapshots rather than snapshots available before the forecast date, introducing temporal leakage if used to evaluate pre-release prediction.

**Confirmed:** The Batman Part II, dated after the review date, contributes $132 million / $402 million targets. With five synthetic rows, train IDs are 0–4 and test IDs are 3–4. Require sourced actuals, point-in-time features, and disjoint splits; report insufficient evaluation data instead of an apparently successful score.

### R20 [P2] The proxy applies public caching to private and mutable responses

[frontend/app/api/[...path]/route.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/api/[...path]/route.ts:18>) · [frontend/app/api/[...path]/route.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/api/[...path]/route.ts:36>) · [backend/app/api/ratings.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/ratings.py:12>)

Every GET is revalidated for 60 seconds and every response without an upstream cache header gets `public, max-age=60`, including ratings, recommendations, admin job responses, mutations, and failures. There is no invalidation after a rating write/delete. Private user data should not be declared publicly cacheable, and a fresh read may show old ratings or recommendations for a minute.

Use an allowlist of cacheable public catalog GETs; use no-store/private behavior for user/admin routes and mutations. Forward relevant error headers such as Retry-After. Cache-policy behavior was verified in source; a shared-CDN disclosure was not attempted.

### R21 [P2] Rate limiting groups all proxied visitors under one backend client

[frontend/app/api/[...path]/route.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/api/[...path]/route.ts:47>) · [backend/app/core/middleware.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/core/middleware.py:42>)

The Next proxy does not convey a verified original client identity. Backend rate limits use `request.client.host` plus path, so visitors routed through one frontend server share the same limit for common endpoints. Meanwhile, distinct movie paths create distinct limit buckets, which weakens an intended overall cap.

Define one trusted proxy strategy and rate-limit by verified client identity or authenticated principal. Do not blindly trust arbitrary client-supplied forwarded headers. The actual deployed reverse-proxy topology was not exercised.

### R22 [P2] Stored release statuses become inconsistent with dates

[backend/app/services/mock_data.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/mock_data.py:398>) · [backend/app/services/catalog_browser.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_browser.py:127>) · [backend/app/api/movies.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/movies.py:78>) · [backend/app/services/movie_data.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/movie_data.py:120>)

Canonical date-based status exists but most browse/list routes still use stored movie.status. Seed refresh retains hard-coded statuses, and normal provider sync does not revisit every catalog row. An already-released title can therefore remain in the future filter while the released feed includes it by date.

**Read-only local evidence:** 157 of 1,369 movie rows have release dates before the current date but are not marked released. Derive public status consistently at query/serialization time or update the full catalog when dates cross, while preserving a clear release-day convention.

### R23 [P2] Date-only release dates display one day early in US time zones

[frontend/lib/formatters.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/lib/formatters.ts:17>)

`new Date('YYYY-MM-DD')` represents UTC midnight, then `toLocaleDateString` converts it to the browser's local time zone. Release dates are calendar dates, not timestamps.

**Confirmed with TZ=America/Chicago:** 2026-10-02 renders as Oct 1, 2026. Parse date components without UTC conversion or format explicitly as a date-only value. This affects cards, movie details, comparisons, and search previews.

### R24 [P2] Secondary buttons have identical foreground and background colors

[frontend/app/globals.css](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/globals.css:1385>) · [frontend/app/globals.css](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/globals.css:1391>)

The final light-theme cascade sets `.cta-button` background to #111111, then `.secondary-button` text to #111111 without restoring its background. Elements carrying both classes have nearly invisible labels, including Library/Search/Compare links and pagination buttons.

**Confirmed by parsing the actual stylesheet cascade:** background=#111111, color=#111111. Give secondary buttons an explicit background in their final rule and verify focus, hover, and disabled states in both desktop and mobile layouts.

### R25 [P2] Entity and upcoming pages truncate results with no pagination controls

[frontend/components/discovery/EntityMovieGrid.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/discovery/EntityMovieGrid.tsx:23>) · [frontend/app/upcoming/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/upcoming/page.tsx:14>)

These pages request only page 1 with 48 items and display the total count, but offer no way to reach remaining pages. A studio/genre with more than 48 films advertises a larger catalog than the user can browse. Add page controls or incremental loading. The upcoming page also uses descending release order, so distant announced titles can occupy the first page ahead of nearer releases.

### R26 [P2] Fresh migrations do not match model foreign-key definitions

[backend/alembic/versions/20260321_0001_initial_schema.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/alembic/versions/20260321_0001_initial_schema.py:82>) · [backend/app/models/ai.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/models/ai.py:14>) · [backend/app/db/session.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/db/session.py:15>)

The initial migration omits ondelete=CASCADE on five automated analysis/discussion movie foreign keys, while the ORM declares it. **Confirmed:** upgrading a fresh SQLite database to head succeeds, then `alembic check` exits 255 and requests five remove/add foreign-key pairs. Databases created with create_all and migrations therefore differ. SQLite connections also do not enable foreign-key enforcement, so raw deletes do not realize the declared database behavior there.

Add a forward migration, establish an explicit SQLite foreign-key policy, and gate schema drift. ORM relationship cascades may mask the mismatch in ordinary ORM deletes; this was not observed as a current public deletion endpoint failure.

### R27 [P2] A negative sentiment can score higher than a positive sentiment

[backend/app/services/hype_calculator.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/hype_calculator.py:42>) · [backend/app/services/catalog_enrichment.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_enrichment.py:299>)

Hype sentiment normalization uses `(x+1)/2` only when x is negative, and uses x directly otherwise. That creates a discontinuity at zero: a slightly negative score becomes about 0.5 while a slightly positive score remains about 0.01. The component breakdown uses a different normalization again.

**Confirmed with other inputs held constant:** sentiment -0.01 yields hype 22.40, while +0.01 yields 15.12. Define one input scale and one shared normalization for scoring and explanations.

### R28 [P2] Search caches and rate-limit maps have no bound or eviction

[backend/app/services/cache.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/cache.py:23>) · [backend/app/services/cache.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/cache.py:40>) · [backend/app/services/catalog_browser.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_browser.py:50>) · [backend/app/core/middleware.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/core/middleware.py:42>)

TTLCache stops serving expired entries but never removes them unless the same key is overwritten or clear() is called. Arbitrary search/filter combinations retain entire result objects and ORM graphs. Rate-limit dictionaries likewise retain every unique client/path key permanently. Over time, distinct searches and movie paths grow worker memory even after their TTLs expire.

Implement size bounds and actual eviction. Cache immutable response data rather than request-session ORM objects. Also clarify Redis invalidation: TTLCache.clear() clears only the in-process store, so JSON-backed entries remain until Redis expiry.

### R29 [P2] Transient provider failures are cached until process restart

[backend/app/services/omdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/omdb.py:21>) · [backend/app/services/omdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/omdb.py:37>) · [backend/app/services/wikidata.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/wikidata.py:17>) · [backend/app/services/wikipedia.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/wikipedia.py:18>)

Provider caches have no TTL. An OMDb HTTP error or temporary unavailable response stores None and every future request returns it immediately. Wikipedia/Wikidata misses are similarly permanent. This can turn a temporary outage or pre-release absence into missing ratings and metadata for the worker's lifetime.

Use bounded positive and short-lived negative caching with retries/backoff and source timestamps. Ensure network exceptions, including direct TimeoutError where relevant, lead to a controlled unavailable state rather than dropping search rows.

### R30 [P2] Hundreds of generated build backups are staged for commit

[.gitignore](</Users/souravgoyal/Desktop/Projects/moviess/.gitignore:1>) · [frontend/.dockerignore](</Users/souravgoyal/Desktop/Projects/moviess/frontend/.dockerignore:1>) · [frontend/tsconfig.json](</Users/souravgoyal/Desktop/Projects/moviess/frontend/tsconfig.json:36>)

The Git index contains **392 `.next_backup*` files totaling 441,125,687 bytes** (about 441 MB decimal). These include bundles, caches, build traces, and generated types. Ignore rules only exclude `.next/`, so the backups are included in commits and Docker build context. The broad TypeScript include patterns also pick up backup .ts files.

Remove generated backups from the index while preserving any intentionally retained local copies, and ignore all generated variants. No files were unstaged or deleted during this review.

## Additional gaps and conditional risks

- **ML recommendation implementation requires another runtime check.** `rag_service.get_movie_embedding` truth-tests `result.get("embeddings")`; ndarray results from a Chroma get may raise an ambiguous-truth-value error. The local environment lacks numpy/Chroma, so this is not included as a reproduced finding. Validate against the pinned Chroma version and use explicit None/length checks. The collection also does not declare a cosine metric while recommendation scoring interprets distance as 1 minus similarity.
- **Startup readiness is tied to optional enrichment.** RAG initialization and model downloads are unconditional in startup sync, and a failure leaves the job failed with readiness returning 503. STARTUP_SYNC_TIMEOUT_SECONDS is configured but unused. There is no bounded retry or separation between core database readiness and optional enrichment readiness. Conversely, readiness does not test a database query once startup is considered complete.
- **PostgreSQL is not validated.** The repository search uses SQLite-specific `json_extract`, requirements have no PostgreSQL driver, and migrations/settings are exercised only on SQLite. A generic DATABASE_URL field does not establish PostgreSQL support.
- **Background jobs are not durable.** Each enqueue creates a daemon thread. Registry eviction can remove a running job record after the history cap is exceeded, causing later update lookups to fail. There is no concurrency bound, shutdown drain, or cross-worker scheduler coordination. Bound work and use durable jobs before scaling workers.
- **Anonymous ratings identity is entirely client-supplied.** There is no authenticated ownership or server-issued signed session contract; callers who know a session ID can read/change its ratings. The frontend currently disables ratings, so assess the intended identity/privacy model before exposing it. Concurrent first ratings can also hit the session/movie uniqueness constraint without conflict handling.
- **Review provenance needs further cleanup.** A generated OMDb Metascore sentence is passed through sentiment analysis and counted as a review at the movie release date. Negative/mixed review wording is not a substitute for actual review text. YouTube comment ingestion also ignores fetched published_at when inserting discussion rows.
- **Search/discovery semantics differ from labels.** The semantic scoring module is unused by current browse matching; “None” sort falls back to hype; the Sci-Fi collection tests the literal `Sci-Fi` label while provider genres can use different names. SearchBar initialValue does not synchronize on query-only URL changes. These deserve focused UI tests after the crash fixes.
- **Disabled and disconnected surfaces:** recommendations route is a placeholder, RatingWidget and ChatWidget are disabled, catalog chat service has no public route, and SentimentTimeline has no active page/API-client integration. Do not list these as working user features.
- **Documentation drift:** README links point to an old absolute local directory; documented catalog size is 1,361 versus 1,369 observed; ML integration claims are contradicted by empty files and unused code. There is no CI configuration or frontend test suite. Correct the README after establishing the intended product scope.
- **Accessibility and charts:** several search/picker inputs rely on placeholders rather than accessible labels; large comparison tables lack horizontal-scroll containment; chart colors remain pale after the light-theme override. InterestChart compares dollars, counts, and a search score multiplied by a million on one unlabeled scale. These require browser/mobile verification and clearer units, not merely passing TypeScript.

## Suggested repair order

1. Align automated analysis and analytics response contracts; repair upcoming query keys; add integration tests for these exact failures.
2. Protect refresh routes, move blocking provider/refresh work off the async loop, and update audited dependencies with regression checks.
3. Fix stable movie identity and transaction behavior before another real import. Preserve measured metrics and persist enrichment.
4. Separate sourced facts, estimates, templates, and unavailable data across all APIs/charts. Make public forecast normalization consistent and recompute stale snapshots.
5. Fix rating/director filters, statuses, dates, pagination, and button contrast.
6. Establish a reproducible fresh deployment: migrations, persistent database, correct trusted hosts, a fully installed runtime, and core readiness independent of optional model work. Reconcile migrations with models.
7. Finish or remove inactive ML/features, validate training methodology, clean generated build backups from version control, and update docs/demo claims.
8. Run browser navigation tests and a real-provider smoke session after repairs. Add CI for backend tests, frontend typecheck/build/lint, API contracts, and migration drift.

## Evidence

Isolated reproduction code and outputs are in the sibling `review-evidence` directory. They use a temporary in-memory SQLite database and provider stubs. The synthetic output is evidence about application behavior, not measured movie data. They are review probes, not a replacement for a maintained test suite.

[review-evidence/reproduce.py](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/reproduce.py>) · [review-evidence/reproduce-output.jsonl](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/reproduce-output.jsonl>) · [review-evidence/http_checks.py](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/http_checks.py>) · [review-evidence/http-output.jsonl](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/http-output.jsonl>) · [review-evidence/frontend-reproduce.cjs](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/frontend-reproduce.cjs>) · [review-evidence/frontend-output.txt](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/frontend-output.txt>) · [review-evidence/more_checks.py](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/more_checks.py>) · [review-evidence/more-output.jsonl](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/more-output.jsonl>) · [review-evidence/build.log](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/build.log>) · [review-evidence/npm-audit.json](</Users/souravgoyal/Desktop/Projects/moviess/review-evidence/npm-audit.json>)

## File-by-file coverage

Each row was reviewed in the current checkout. “Reviewed” means static inspection of that file and its role; it does not mean the file is proven defect-free. Finding references apply to interactions spanning files. Empty/package initializer files were checked as such. Dependency lock metadata was checked through install/build/audit rather than reading vendored package implementations.

| File | Review notes |
|---|---|
| [.gitignore](</Users/souravgoyal/Desktop/Projects/moviess/.gitignore>) | Reviewed; R30. |
| [README.md](</Users/souravgoyal/Desktop/Projects/moviess/README.md>) | Reviewed; R18. |
| [backend/.dockerignore](</Users/souravgoyal/Desktop/Projects/moviess/backend/.dockerignore>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [backend/.env.example](</Users/souravgoyal/Desktop/Projects/moviess/backend/.env.example>) | Reviewed; R09. |
| [backend/.env.production.example](</Users/souravgoyal/Desktop/Projects/moviess/backend/.env.production.example>) | Reviewed; R08. |
| [backend/Dockerfile](</Users/souravgoyal/Desktop/Projects/moviess/backend/Dockerfile>) | Reviewed; R08. |
| [backend/alembic.ini](</Users/souravgoyal/Desktop/Projects/moviess/backend/alembic.ini>) | Reviewed migration/logging configuration; migration command exercised. |
| [backend/alembic/env.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/alembic/env.py>) | Reviewed and executed against temporary SQLite; drift detected in initial migration (R26). |
| [backend/alembic/script.py.mako](</Users/souravgoyal/Desktop/Projects/moviess/backend/alembic/script.py.mako>) | Reviewed revision template; no independent issue confirmed. |
| [backend/alembic/versions/20260321_0001_initial_schema.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/alembic/versions/20260321_0001_initial_schema.py>) | Reviewed; R26. |
| [backend/alembic/versions/20260324_0002_add_ratings_and_review_sentiments.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/alembic/versions/20260324_0002_add_ratings_and_review_sentiments.py>) | Reviewed; upgrade succeeded in temporary SQLite database. |
| [backend/app/__init__.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/__init__.py>) | Reviewed empty package initializer. |
| [backend/app/api/__init__.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/__init__.py>) | Reviewed package imports/exports. |
| [backend/app/api/admin.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/admin.py>) | Reviewed; R05. |
| [backend/app/api/ai.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/ai.py>) | Reviewed; R01, R07. |
| [backend/app/api/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/analytics.py>) | Reviewed; R02, R05, R06, R15. |
| [backend/app/api/movies.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/movies.py>) | Reviewed; R05, R06, R07, R12, R22. |
| [backend/app/api/ratings.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/ratings.py>) | Reviewed; R20. |
| [backend/app/api/recommendations.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/recommendations.py>) | Reviewed; R06. |
| [backend/app/api/search.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/api/search.py>) | Reviewed; R06. |
| [backend/app/core/__init__.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/core/__init__.py>) | Reviewed empty package initializer. |
| [backend/app/core/config.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/core/config.py>) | Reviewed; R09. |
| [backend/app/core/middleware.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/core/middleware.py>) | Reviewed; R06, R21, R28. |
| [backend/app/db/__init__.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/db/__init__.py>) | Reviewed empty package initializer. |
| [backend/app/db/base.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/db/base.py>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [backend/app/db/session.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/db/session.py>) | Reviewed; R26. |
| [backend/app/models/__init__.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/models/__init__.py>) | Reviewed package imports/exports. |
| [backend/app/models/ai.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/models/ai.py>) | Reviewed; R26. |
| [backend/app/models/movie.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/models/movie.py>) | Reviewed; R13. |
| [backend/app/models/ratings.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/models/ratings.py>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [backend/app/repositories/__init__.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/repositories/__init__.py>) | Reviewed package imports/exports. |
| [backend/app/repositories/movies.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/repositories/movies.py>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [backend/app/schemas/__init__.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/__init__.py>) | Reviewed validation/defaults and API usage; cross-layer contracts covered by R01/R02/R07 where applicable. |
| [backend/app/schemas/ai.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/ai.py>) | Reviewed; R01. |
| [backend/app/schemas/analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/analytics.py>) | Reviewed; R02. |
| [backend/app/schemas/discovery.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/discovery.py>) | Reviewed validation/defaults and API usage; cross-layer contracts covered by R01/R02/R07 where applicable. |
| [backend/app/schemas/movie.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/movie.py>) | Reviewed; R07. |
| [backend/app/schemas/ratings.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/schemas/ratings.py>) | Reviewed validation/defaults and API usage; cross-layer contracts covered by R01/R02/R07 where applicable. |
| [backend/app/services/__init__.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/__init__.py>) | Reviewed empty package initializer. |
| [backend/app/services/ai_foundation.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/ai_foundation.py>) | Reviewed; R16, R17, R18. |
| [backend/app/services/background_jobs.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/background_jobs.py>) | Reviewed thread/registry lifecycle; eviction and durability caveats. |
| [backend/app/services/bootstrap.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/bootstrap.py>) | Reviewed; R08. |
| [backend/app/services/cache.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/cache.py>) | Reviewed; R28. |
| [backend/app/services/catalog_browser.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_browser.py>) | Reviewed; R11, R22, R28. |
| [backend/app/services/catalog_enrichment.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/catalog_enrichment.py>) | Reviewed; R13, R15, R19, R27. |
| [backend/app/services/hype_calculator.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/hype_calculator.py>) | Reviewed; R27. |
| [backend/app/services/mock_data.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/mock_data.py>) | Reviewed; R22. |
| [backend/app/services/model_training.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/model_training.py>) | Reviewed; R19. |
| [backend/app/services/movie_data.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/movie_data.py>) | Reviewed; R22. |
| [backend/app/services/omdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/omdb.py>) | Reviewed; R29. |
| [backend/app/services/prediction_model.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/prediction_model.py>) | Reviewed; R02, R18. |
| [backend/app/services/rag_service.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/rag_service.py>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [backend/app/services/recommendation_service.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/recommendation_service.py>) | Reviewed rating persistence, vector combination/reranking, provider calls and explanations; R06 plus ML/identity caveats. |
| [backend/app/services/redis_store.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/redis_store.py>) | Reviewed JSON cache/rate limiting and failure fallback; no external Redis instance exercised. |
| [backend/app/services/review_analysis.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/review_analysis.py>) | Reviewed keyword analysis, perspective summaries and theme aggregation; mostly disconnected from serving response (R01). |
| [backend/app/services/review_fetcher.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/review_fetcher.py>) | Reviewed fetching, deduplication, analyzer paths and weekly aggregation; synthetic critic sentence caveat; actual ML execution unavailable. |
| [backend/app/services/semantic_search.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/semantic_search.py>) | Reviewed tokenization/scoring; currently unused by browse matching. |
| [backend/app/services/startup_jobs.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/startup_jobs.py>) | Reviewed; R14, R17. |
| [backend/app/services/tmdb.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/tmdb.py>) | Reviewed; R04, R13, R14. |
| [backend/app/services/wikidata.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/wikidata.py>) | Reviewed; R29. |
| [backend/app/services/wikipedia.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/wikipedia.py>) | Reviewed; R29. |
| [backend/app/services/youtube_analytics.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/app/services/youtube_analytics.py>) | Reviewed; R14. |
| [backend/expand_catalog.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/expand_catalog.py>) | Reviewed CLI argument flow and summary-only imports; importer findings R04/R13/R14. |
| [backend/main.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/main.py>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [backend/model_artifacts/box_office_forecaster.json](</Users/souravgoyal/Desktop/Projects/moviess/backend/model_artifacts/box_office_forecaster.json>) | Empty artifact; loader returns None; R18. |
| [backend/requirements.txt](</Users/souravgoyal/Desktop/Projects/moviess/backend/requirements.txt>) | Reviewed pins/import requirements; local ML packages missing; no clean Python 3.12/Docker install performed. |
| [backend/tests/test_movie_data.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/tests/test_movie_data.py>) | Reviewed and executed: 3 passing tests; coverage limited to canonical movie-data helper. |
| [backend/train_models.py](</Users/souravgoyal/Desktop/Projects/moviess/backend/train_models.py>) | Empty file; R18. |
| [create_project.sh](</Users/souravgoyal/Desktop/Projects/moviess/create_project.sh>) | Empty scaffold script. |
| [docker-compose.yml](</Users/souravgoyal/Desktop/Projects/moviess/docker-compose.yml>) | Reviewed; R09. |
| [frontend/.dockerignore](</Users/souravgoyal/Desktop/Projects/moviess/frontend/.dockerignore>) | Reviewed; R30. |
| [frontend/.env.local.example](</Users/souravgoyal/Desktop/Projects/moviess/frontend/.env.local.example>) | Reviewed example keys/configuration; no live credentials reproduced in report. |
| [frontend/.env.production.example](</Users/souravgoyal/Desktop/Projects/moviess/frontend/.env.production.example>) | Reviewed example keys/configuration; no live credentials reproduced in report. |
| [frontend/.gitignore](</Users/souravgoyal/Desktop/Projects/moviess/frontend/.gitignore>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [frontend/Dockerfile](</Users/souravgoyal/Desktop/Projects/moviess/frontend/Dockerfile>) | Reviewed multi-stage packaging; build passed locally; Docker execution not performed. |
| [frontend/app/api/[...path]/route.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/api/[...path]/route.ts>) | Reviewed; R20, R21. |
| [frontend/app/compare/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/compare/page.tsx>) | Reviewed picker/state/URL synchronization; duplicate URL IDs allowed; R02 affects API; browser history and mobile table tests pending. |
| [frontend/app/discover/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/discover/page.tsx>) | Reviewed dashboard and collection rendering; canonical genre vocabulary/provenance caveats. |
| [frontend/app/franchises/[franchise]/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/franchises/[franchise]/page.tsx>) | Reviewed route/parameter handling and entity integration; pagination covered by R25. |
| [frontend/app/genres/[genre]/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/genres/[genre]/page.tsx>) | Reviewed route/parameter handling and entity integration; pagination covered by R25. |
| [frontend/app/globals.css](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/globals.css>) | Reviewed; R24. |
| [frontend/app/layout.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/layout.tsx>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [frontend/app/movies/[slug]/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/movies/[slug]/page.tsx>) | Reviewed; R01, R07, R16. |
| [frontend/app/movies/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/movies/page.tsx>) | Reviewed; R11, R12. |
| [frontend/app/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/page.tsx>) | Reviewed route/parameter handling and entity integration; pagination covered by R25. |
| [frontend/app/people/[name]/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/people/[name]/page.tsx>) | Reviewed route/parameter handling and entity integration; pagination covered by R25. |
| [frontend/app/providers.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/providers.tsx>) | Reviewed; R03. |
| [frontend/app/recommendations/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/recommendations/page.tsx>) | Reviewed; explicitly disabled placeholder. |
| [frontend/app/search/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/search/page.tsx>) | Reviewed route/parameter handling and entity integration; pagination covered by R25. |
| [frontend/app/search/search-results.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/search/search-results.tsx>) | Reviewed filters/state/pagination; R11; page-only aggregates labeled as current result set. |
| [frontend/app/studios/[studio]/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/studios/[studio]/page.tsx>) | Reviewed route/parameter handling and entity integration; pagination covered by R25. |
| [frontend/app/upcoming/page.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/app/upcoming/page.tsx>) | Reviewed; R03, R25. |
| [frontend/components/compare/ComparisonChart.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/compare/ComparisonChart.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/compare/ComparisonSpotlight.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/compare/ComparisonSpotlight.tsx>) | Reviewed rankings/display; zero/absent forecasts can still produce arbitrary winner; R02/R07 affect inputs. |
| [frontend/components/compare/ComparisonTable.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/compare/ComparisonTable.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/compare/ShareCompareButton.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/compare/ShareCompareButton.tsx>) | Reviewed; clipboard rejection is not handled; browser verification pending. |
| [frontend/components/discovery/EntityMovieGrid.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/discovery/EntityMovieGrid.tsx>) | Reviewed; R25. |
| [frontend/components/home/BuzzRanking.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/home/BuzzRanking.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/home/HomeSignalOverview.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/home/HomeSignalOverview.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/home/ReleasedMovies.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/home/ReleasedMovies.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/home/TrendingMovies.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/home/TrendingMovies.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/home/UpcomingMovies.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/home/UpcomingMovies.tsx>) | Reviewed; R03. |
| [frontend/components/movies/BoxOfficeHistoryChart.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/BoxOfficeHistoryChart.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/movies/CriticAudienceDashboard.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/CriticAudienceDashboard.tsx>) | Reviewed; R01. |
| [frontend/components/movies/ForecastConfidenceCard.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/ForecastConfidenceCard.tsx>) | Reviewed; R01. |
| [frontend/components/movies/HypeGauge.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/HypeGauge.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/movies/InterestChart.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/InterestChart.tsx>) | Reviewed; mixed/scaled units and missing estimate labeling require correction. |
| [frontend/components/movies/MovieHero.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/MovieHero.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/movies/ScoreBreakdownCard.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/ScoreBreakdownCard.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/movies/SentimentTimeline.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/SentimentTimeline.tsx>) | Reviewed chart/date conversion; not mounted or fetched by active detail page. |
| [frontend/components/movies/TrendChart.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/movies/TrendChart.tsx>) | Reviewed; R15. |
| [frontend/components/recommendations/RatingWidget.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/recommendations/RatingWidget.tsx>) | Reviewed; ratings explicitly disabled. |
| [frontend/components/shared/ChatWidget.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/shared/ChatWidget.tsx>) | Reviewed; disabled UI and not mounted by layout. |
| [frontend/components/shared/MovieCard.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/shared/MovieCard.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/shared/QueryState.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/shared/QueryState.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/components/shared/SearchBar.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/shared/SearchBar.tsx>) | Reviewed preview/query/submit; initialValue not synchronized on URL-only navigation; accessible label missing. |
| [frontend/components/shared/SiteHeader.tsx](</Users/souravgoyal/Desktop/Projects/moviess/frontend/components/shared/SiteHeader.tsx>) | Reviewed rendering, inputs, states, and consumers; no separate confirmed blocker beyond shared findings. |
| [frontend/lib/api.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/lib/api.ts>) | Reviewed; R01. |
| [frontend/lib/catalog.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/lib/catalog.ts>) | Reviewed helper matching/parsing; no additional blocker confirmed. |
| [frontend/lib/formatters.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/lib/formatters.ts>) | Reviewed; R23. |
| [frontend/lib/server-api.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/lib/server-api.ts>) | Reviewed SSR fetch/fallback; clean build and homepage smoke check passed. |
| [frontend/next-env.d.ts](</Users/souravgoyal/Desktop/Projects/moviess/frontend/next-env.d.ts>) | Reviewed source/configuration and its integration; no additional independent finding confirmed. |
| [frontend/next.config.mjs](</Users/souravgoyal/Desktop/Projects/moviess/frontend/next.config.mjs>) | Reviewed; standalone build passed in clean temporary copy. |
| [frontend/package-lock.json](</Users/souravgoyal/Desktop/Projects/moviess/frontend/package-lock.json>) | Reviewed; R10. |
| [frontend/package.json](</Users/souravgoyal/Desktop/Projects/moviess/frontend/package.json>) | Reviewed scripts/dependencies; lint not configured; R10. |
| [frontend/tsconfig.json](</Users/souravgoyal/Desktop/Projects/moviess/frontend/tsconfig.json>) | Reviewed and typecheck passed; strict=false and includes backup types; R30. |
| [render.yaml](</Users/souravgoyal/Desktop/Projects/moviess/render.yaml>) | Reviewed; R08. |

Excluded from authored-code coverage: dependency installations/virtual environments, .git internals, OS metadata, generated caches and graph database, compiled .next outputs and their backups. Existing local .env files were checked without exposing values. Existing application databases were inspected only for read-only counts/statuses. Source review cannot guarantee discovery of every possible defect.
