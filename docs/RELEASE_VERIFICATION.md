> Movie Match follow-up: the new recommendation milestone is documented in [MOVIE_MATCH.md](MOVIE_MATCH.md). The account/watchlist verification below describes the preceding release.

# ReelTogether release follow-up — September 13, 2026

## Implemented

Accounts use unique, case-normalized usernames and Argon2id password hashes. The backend creates random seven-day sessions, stores only session-token hashes, and revokes sessions on logout. HTTP-only session cookies use SameSite=Strict and Secure in production. Origin and CSRF checks protect writes. Password hashing concurrency is bounded, and authentication attempts are throttled independently of anonymous browser identifiers.

Private watchlists support idempotent save, remove, pagination, and planned/watched status. Ownership always comes from the authenticated session. Clients cannot select another account ID. Database foreign keys and a unique account/movie constraint protect integrity. Frontend login/logout transitions clear private cached data; the proxy preserves both its own cookie and the backend session cookie.

## Verified locally

- 30 backend tests pass, including ownership, CSRF, invalid credentials, username normalization, expiry, logout replay, password/session storage, duplicate saves, and throttling.
- Six Chromium browser tests pass, including signup → save → watched → reload → remove → logout, against a disposable offline backend.
- Strict TypeScript and lint pass (three existing nonblocking image optimization warnings).
- Both Docker images build; migrations execute before startup; the frontend proxy reaches the backend.
- A backup and restored copy have identical table content hashes and valid SQLite/foreign-key integrity.
- The restored database boots in a separate production-configured backend container and serves all 1,369 movies over HTTP inside the container.
- The local full app serves the restored 1,369-movie catalog. A real proxy login session and watched status survived a backend-container restart. The temporary verification account was removed afterwards.
- The updated core Python and frontend dependency audits report no known vulnerabilities at verification time.
- Desktop and mobile watchlist layouts were inspected; the mobile page has no horizontal overflow.

Logs and reports are in `verification/`. `catalog-benchmark.json` records a small sequential local HTTP baseline through the frontend proxy. It is not a production load test or evidence of an improvement over a previous version.

## Local review

Open **http://localhost:3020/watchlist**. Register your own account to try saving movies. The running Docker project is `movie-pulse-release`, using a separate restored catalog in its volume. The original development database and its backups remain intact. The temporary restore-check container has been stopped and removed.

## Still external or incomplete

No public hosting account was selected/connected during this run, and the TMDB, OMDb, and YouTube keys are blank. Public deployment and live provider verification therefore remain pending. Render configuration is present, but no cloud service was created and no hosted URL is claimed.

Account recovery, email verification/social login, HTTPS deployment checks, off-host backup retention, and ingress abuse controls remain work before a broad public release. The new account system does not enable the older session-ID rating/recommendation experiments. Forecasts remain unvalidated heuristics. The architecture still assumes one backend instance with in-process jobs.

For résumé purposes, describe the implemented full-stack app, authenticated watchlists, database migrations, and automated validation. A public deployment or measured prediction accuracy is not yet a supported claim.
