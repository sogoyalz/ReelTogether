# Contributing

Use a small branch per coherent change. Read the README and relevant documents in `docs/` before editing. Frontend framework guidance lives in the installed `next/dist/docs/` directory.

Run backend regressions with Python 3.12 and `python -m unittest discover -s tests -v` from `backend/`. Fresh migrations and historical adoption are covered by that suite. PostgreSQL integration checks require a disposable local database named `reeltest`; run both `tests/postgres_smoke.py` and `tests/postgres_catalog.py` with `POSTGRES_TEST_URL` set. Never point these tests at a development or hosted user database.

From `frontend/`, run `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build`, then `BACKEND_PYTHON=/absolute/path/to/python npm test`. Install Playwright Chromium first. Browser tests start their own disposable fixture backend and frontend servers on ports 8011 and 3011. Do not reuse a live application instance.

Preserve movie IDs and user references during migrations. Treat demo/provider identifiers as separate namespaces. Keep public reads offline and queue provider writes. Unknown facts should remain absent; do not infer authored reviews or present modeled metrics as sourced observations.

Include a reproduction and meaningful regression coverage for behavioral fixes. Explain changed API contracts and external validation limits. Never commit secrets, provider responses containing credentials, database files, generated build output or browser traces with private data. Do not use production data for tests.
