# Free portfolio deployment

The supported free layout is Vercel Hobby for the Next.js frontend, Render Free for the Python API, and Neon Free for persistent PostgreSQL. The Neon project is linked locally; web-hosting accounts must still be connected before publication. Stay within each provider's free limits; do not enable paid upgrades automatically.

## Database

The repository's `neon.ts` declares an empty policy: PostgreSQL only, with no additional services. The local `.neon` link and environment files are ignored by Git. `neon deploy` applies this policy; it does not host the website or run Alembic migrations.

Link project `winter-night-78998447`, branch `production`. Preserve existing local Compose settings when pulling credentials: use a separate ignored `.env.neon` file. Keep database credentials server-side. The Python backend accepts `postgres://`, `postgresql://`, and `postgresql+psycopg://` URLs. Use Neon's direct connection string with TLS for this deployment because startup runs schema migrations on the same URL. The API uses a small connection pool and verifies connections before reuse.

## API

Create a Render Blueprint using `render.free.yaml` instead of the paid `render.yaml`. The free file explicitly selects `plan: free` and has no disk. Supply:

- `DATABASE_URL`: the direct Neon URL with TLS enabled.
- `PROXY_SHARED_SECRET`: a randomly generated secret of at least 32 characters, shared only with the frontend server.
- `CORS_ORIGINS`: a JSON array containing the exact production frontend HTTPS origin.
- `TRUSTED_HOSTS`: a JSON array containing the assigned API hostname plus `localhost` and `127.0.0.1` for health checks.

The blueprint generates separate application/admin secrets and disables experimental features. The entrypoint runs Alembic before serving requests. On a new empty database, startup seeds the bundled demo catalog; transferring the larger local catalog is a separate step. Local accounts and private watchlists are not uploaded automatically.

Periodic refresh and continuous job polling are disabled to avoid keeping the free database awake. Submitted maintenance jobs remain queued until a worker is deliberately run; public browsing, accounts, recommendations, and movie nights do not depend on these jobs. Do not configure provider refresh keys for synchronous startup: large imports should be run separately. Offsite SQLite backup scripts are not used with PostgreSQL.

## Frontend

Import the GitHub repository on Vercel Hobby, choose the `frontend` root directory, and set the framework to Next.js. Configure server-only `API_BASE_URL` with the Render API HTTPS URL and `PROXY_SHARED_SECRET` with the identical backend value. Update the backend's allowed origin to the final Vercel production URL. Preview URLs are not automatically allowed to perform authenticated writes.

## Verification before adding the URL to a resume

Verify public HTTPS, readiness, catalog browsing, recommendation filters, account creation, watchlist persistence after a backend restart, and a two-person movie night. Confirm no credentials are exposed in browser responses or committed files. Local PostgreSQL compatibility is exercised by `tests/postgres_smoke.py` in CI, separately from the SQLite suite.

Free services have quotas and cold starts. Render may sleep after inactivity, so the first request can be slow. Do not use keep-alive pings to bypass free-tier sleeping. This is a portfolio deployment, not an always-on availability commitment.

Official references: [Render free limits](https://render.com/docs/free), [Vercel Hobby](https://vercel.com/docs/plans/hobby), [Neon plans](https://neon.com/pricing).
