# Movie Match: request interpretation and metadata enrichment

The optional request interpretation integration is implemented. Live activation and provider validation are pending credentials: the local interpretation-service and movie-data credentials were blank at verification. The running app remains in catalog mode and shows that request interpretation is unavailable. No paid API calls or live movie-data imports were made during this work.

## Enable natural-language interpretation

Configure the interpretation-service credential, compatible model, enable flag, and hourly request limit using the exact settings in `backend/.env.example`. Keep credentials in the ignored environment file or your hosting secret manager.

The model name preserves the project's existing configuration; choose a model available to your API project that supports Responses structured outputs. A live compatibility/quality check has not been performed without credentials.

From the repository root, recreate the backend to load the changed environment:

```sh
docker compose up -d --force-recreate backend
```

Open `/recommendations`, sign in, then enable **Interpret my request**. It is off by default even when the server is configured. The page discloses that the current message and filters go to an external interpretation service. Account identity, stored watchlists and saved taste are not sent to the model.

Examples to evaluate after activation:

- “I've had a long day. Something lighthearted, in English, at most 100 minutes.”
- “Actually, Hindi instead; keep the time limit.”
- “Something like Inception, but no horror.”
- “Give me a different batch.”

Metadata-constrained requests still need catalog coverage. A model does not fill missing movie facts.

## Request path and limits

The Responses API returns a strict JSON-schema preference object, which is validated again with Pydantic. The backend resolves only explicitly named, unambiguous catalog references. It retrieves movies from the database and generates explanations from matching fields. No model-generated movie lists, URLs, SQL, tools or code are executed or displayed.

Each call sends only `message` and `current_filters`, with `store=false`, a 700-output-token ceiling, a 12-second socket timeout and no automatic retries. Two extraction calls may run concurrently. A process-wide rolling hourly call ceiling counts failures too; it is a local guard, **not a durable billing cap**, and resets on process restart. Configure spending limits in the provider account before a public rollout. Existing API limits and authenticated origin/CSRF checks also apply.

Incomplete, refused, invalid, oversized and failed upstream responses preserve filters and tell the user request interpretation is unavailable. Unsupported requests ask for clarification. API error bodies and keys are never returned to the browser. Structured output guarantees a shape, not correct interpretation: the UI keeps applied filters inspectable, and representative live evaluation is still required.

The upstream response uses a strict JSON schema with required properties and no additional fields.

## Backfill runtime and language

Set `TMDB_API_KEY` in `backend/.env`, recreate the backend as above, and preview a bounded batch:

```sh
docker compose exec -T backend python enrich_recommendations.py --limit 25
```

The default is a read-only plan. Before applying a batch, take a uniquely named backup using `database_backup.py`:

```sh
docker compose exec -T backend python database_backup.py backup /data/before-enrichment.sqlite
docker compose exec -T backend python enrich_recommendations.py --limit 25 --apply
```

The backup command refuses to overwrite an existing file; choose a new filename for another backup. The enrichment command requests exact TMDB IDs, verifies the returned identity, and fills missing runtime/original language fields without overwriting known runtime, unrelated metadata, catalog identity, analytics, accounts or watchlists. It records the source URL, changed fields and verification time. Each movie commits independently so completed work survives interruption.

`--limit` accepts 1–100 and bounds provider requests. Resume after the reported `last_processed_id` with `--after-id N`. Failures are returned as movie IDs with sanitized categories; three consecutive failures stop a batch. Revisit failed IDs later rather than treating a cursor as proof of completeness. Missing provider values stay missing. Running without `--apply` never calls TMDB or writes data.

## Validation scope

Provider responses are mocked in automated tests; this verifies transport handling, limits, data validation, ownership, and retrieval behavior—not live model quality or provider account access. Browser tests verify opt-in behavior and state retention after an request interpretation outage. The pre-existing catalog remains unchanged; enrichment has only been planned locally.

Current local verification: **58 backend tests and 12 browser tests pass**. Frontend lint/type checking and the Docker production build pass; lint retains three existing image optimization warnings. Live Chromium smoke confirms catalog recommendations still work, unconfigured request interpretation cannot be enabled, and the mobile page has no horizontal overflow. Evidence is in `the historical integration verification artifacts`; enrichment plans are in `docs/verification/metadata-enrichment-*.json`. No database migration or catalog mutation was needed for this milestone.
