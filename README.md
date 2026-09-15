# ReelTogether

Movie discovery, personal watchlists, and group movie-night planning.

Repository: [sogoyalz/ReelTogether](https://github.com/sogoyalz/ReelTogether)

Movie discovery and research with a Next.js / TypeScript frontend and FastAPI / SQLAlchemy backend. Browse and filter a catalog, inspect provider metadata, compare up to four films, and inspect stored audience discussions. Attention scores and revenue estimates are experimental heuristics, not validated predictions.

## Supported scope

- Paginated catalog, upcoming releases, director/studio/genre/franchise pages, and comparison links.
- Username/password accounts and private watchlists: save/remove movies, mark watched, and sign out. Argon2id password hashing, revocable server-side sessions, CSRF checks, and server-enforced ownership.
- TMDB metadata ingestion with stable provider IDs; persisted enrichment and OMDb ratings.
- YouTube observations and dated snapshots when a key and supported trailer URL are available.
- Source-aware detail responses, conservative forecast suppression, and explicit missing-review states.
- Protected maintenance endpoints, bounded background jobs and caches, health endpoints, migrations, and Docker persistence.
- Offline API regressions, browser flow tests, strict TypeScript, linting, dependency audits, and a GitHub Actions workflow.

With no provider keys, an empty database is seeded with **demo data**. Existing records are preserved. Counts inferred from TMDB popularity are **estimates**. No Google Trends, Reddit, or X feed is implemented. Search queries only read the stored catalog; importing new records is a maintenance operation.

Movie Match (`/recommendations`) now provides focused catalog chat, explainable genre-based recommendations, and account-owned taste feedback. See [Movie Match](docs/MOVIE_MATCH.md) for supported requests and limitations. Optional natural-language preference interpretation is implemented behind configuration and user opt-in; see [interpretation setup](docs/INTERPRETATION_SETUP.md). Live model validation awaits credentials. General-purpose chat and trained forecasting remain outside the supported scope. Legacy rating/recommendation APIs remain disabled by default and unavailable in production. The new authenticated account/watchlist API is separate and enabled. Optional RAG dependencies are isolated in `backend/requirements-experimental.txt`; they are not included in the core runtime or its audit claim.

Latest engineering verification: [Reliability repairs](docs/RELIABILITY_REPAIRS.md).

## Local setup

Use Python 3.12+ and Node.js 22. From the repository root:

```sh
cd backend
python3.12 -m venv venv
venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
venv/bin/python -m alembic upgrade head
venv/bin/python -m uvicorn main:app --reload
```

For an older database created without Alembic history, run `venv/bin/python upgrade_database.py --adopt-existing` **instead of** the first migration command. It verifies the legacy table/column layout, creates a timestamped SQLite backup, adopts the existing schema, and upgrades it. Do not use `alembic stamp head` as a substitute for applying migrations.

In another terminal:

```sh
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. The frontend server proxies `/api` to `API_BASE_URL` (default `http://127.0.0.1:8000`); provider keys stay on the backend. Set the same random `PROXY_SHARED_SECRET` in both environments to give anonymous browsers separate signed rate-limit identifiers. These identifiers are not user authentication and do not prevent deliberate cookie rotation; production ingress should also enforce IP-based abuse limits.

Add optional `TMDB_API_KEY`, `YOUTUBE_API_KEY`, and `OMDB_API_KEY` to the backend environment. Set `ADMIN_API_KEY` to enable maintenance; all maintenance routes reject unconfigured or invalid keys. Use the protected `/api/admin/jobs/tmdb-sync`, `/youtube-refresh`, or `/ai-refresh` routes with the `X-Admin-Key` header. Never embed that key in public frontend code. Provider coverage and quotas determine what can be populated; an absent IMDb rating does not match an IMDb filter.

## Verification

```sh
cd backend
venv/bin/python -m unittest discover -s tests -v
venv/bin/python -m alembic check
venv/bin/python -m pip_audit -r requirements.txt
cd ../frontend
npm run lint
npm run typecheck
npm run build
npm audit
npx playwright install chromium
npm test
```

Browser tests start disposable, offline servers on ports 8011 and 3011 and use an in-memory database. Set `BACKEND_PYTHON` if your Python environment is elsewhere. They must not reuse a running server. GitHub Actions runs the same checks on pushes and pull requests; the workflow must run on GitHub before claiming a green remote CI build.

## Deployment

For Docker Compose, copy root `.env.example` to `.env` and set `PROXY_SHARED_SECRET` to a random value (`openssl rand -hex 32`). Also configure `backend/.env` before starting:

```sh
docker compose up --build
```

The backend applies migrations before Uvicorn starts. Compose stores SQLite in the `movie-data` volume, permits the internal `backend` hostname, and binds the direct backend port to localhost. The frontend is exposed on port 3000. Do not remove the volume when upgrading.

`render.yaml` describes an alternative single-instance deployment with a persistent backend disk. Configure both services' identical proxy secret, allowed hosts/origins, admin key, provider keys, and the frontend API base URL. The images, local container startup, frontend proxy, persistence across restart, and restoration of a 1,369-movie database have been verified locally. Render account deployment remains pending. The backend requires persistent storage; ephemeral free-tier storage is unsuitable for this SQLite configuration.

The current design is for a **single backend instance**. Jobs are bounded but in-process and do not survive restarts. Before scaling horizontally, use a durable queue, coordinated scheduling, a supported shared database deployment, and off-host backup retention/restore procedures. `/health/live` checks process availability; `/health/ready` checks the database independently of optional provider refreshes.

## Forecast experiments

`backend/train_models.py` is an explicit offline command. It refuses fewer than 30 eligible titles, overlapping train/test partitions, and missing observed targets. Eligible features must have `feature_version="observed-v1"` and predate release. Targets must be stored under `provider_metadata.box_office_targets` with `source_url`, `verified_at`, `opening_usd`, and `domestic_usd`. No valid training dataset is bundled. The public app does not claim to serve a trained model or calibrated confidence interval.

See [engineering plan](docs/ENGINEERING_PLAN.md) for the internship roadmap and honest résumé wording, [repair status](docs/REPAIR_STATUS.md) for completed work and limitations, and [original review](PROJECT_REVIEW.md) for the pre-repair findings.


## Accounts and watchlists

Open `/watchlist` to register or sign in. Usernames contain 3–32 letters, numbers, or underscores; passwords contain 12–128 characters. Password recovery, email verification, and social login are not implemented. The UI states the recovery limitation before signup. Sessions last seven days, are stored as token hashes, and are revoked on logout. Logout/login changes clear private frontend cache state.

Write requests require an allowed `Origin` and the session's `X-CSRF-Token`. Configure `CORS_ORIGINS` with the exact frontend origin, including its port; the frontend proxy forwards the origin, CSRF header, and session cookies. Production cookies require HTTPS and `ENVIRONMENT=production`. Authentication attempts have separate limits; the deployment should enforce ingress IP limits, particularly when the backend sits behind a shared proxy.

The supported deployment is still a single backend instance. Account recovery and external hosting/TLS verification are release work before inviting a broad public user base.

## Backups and local release

```sh
cd backend
venv/bin/python database_backup.py backup /absolute/path/to/new-backup.sqlite
venv/bin/python database_backup.py verify /absolute/path/to/new-backup.sqlite
venv/bin/python database_backup.py restore-copy /absolute/path/to/new-backup.sqlite /absolute/path/to/new-restored.sqlite
```

The tool refuses existing destinations, uses SQLite's online backup API, checks integrity/foreign keys, and reports table content hashes. Restore to a separate file, stop writers, and deliberately switch the database URL only after verification. Copy backups off the deployment disk; a backup on the same disk does not protect against losing that disk.

The prepared local release runs at **http://localhost:3020** with backend port 8020 and a separate restored 1,369-movie catalog in its Docker volume. The ignored root `.env` selects project `movie-pulse-release` and these ports. `docker compose up -d` resumes it; `docker compose down` stops it without removing the volume. The original development database is preserved. Fresh installations without this local restored copy seed 16 demo titles when provider keys are absent.

See [release verification](docs/RELEASE_VERIFICATION.md) for current results and [watchlist mobile screenshot](docs/screenshots/watchlist-mobile.png).

### Account recovery and operations

Signed-in users can open **Watchlist → Account security** to generate a recovery code. Save it in a password manager; a password reset consumes the code and signs out all sessions. Recovery requires a previously saved code.

Docker Compose now runs a daily SQLite backup/restore-verification service alongside the app. Run `docker compose exec backups python backup_health.py` to check backup freshness. These backups share the local data volume; configure offsite copies before a public launch.

See [Production readiness](docs/PRODUCTION_READINESS.md) for verification, configuration checks and remaining launch dependencies. The local app is not yet publicly deployed.

### Movie Night

Open **Movie Night** to create a room for 2–8 signed-in friends. Share the invitation, save private preferences, vote Yes/Pass/Veto, and reveal the group’s matches. The host chooses among tied top results; each person can optionally save the winner. Rooms expire after 24 hours.

See [Movie Night design and verification](docs/MOVIE_NIGHT.md) for privacy rules, ranking, concurrency checks and limitations.
