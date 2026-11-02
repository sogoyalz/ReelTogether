# Production candidate and release procedure

This is the current operations guide. It replaces historical setup/verification claims for production. The candidate has local API, browser, PostgreSQL and Linux container verification; it has not been published or validated on a public host.

## Supported topology

Use Docker Compose 2.24 or newer and the **standalone** `compose.production.yaml` on one server with persistent storage. Do not merge it with the development Compose file. Caddy terminates HTTPS and is the only public listener. Frontend, API, Redis, the single catalog worker, backup worker and monitor are internal services. API and frontend run as non-root users with read-only application filesystems. API database, snapshots and independent deletion receipts have explicit writable volumes. The API has one Uvicorn process; maintenance is queued and runs in `jobs`.

The supplied topology uses SQLite on one persistent host. PostgreSQL has migration/query/control regression coverage, but a managed PostgreSQL deployment needs its own native backup/PITR and restore procedure. Do not treat the SQLite backup service as PostgreSQL recovery. This profile is not a multi-region or high-availability deployment.

## Configuration and launch

Create the ignored root `.env` with `PUBLIC_HOST` (hostname only), `PUBLIC_ORIGIN` (its HTTPS origin), and separate random values of at least 32 characters for `SECRET_KEY`, `ADMIN_API_KEY`, `PROXY_SHARED_SECRET`, and `ERASURE_LEDGER_KEY`. Generate values with a password manager or `openssl rand -hex 32`. Configure optional provider credentials in the ignored `backend/.env`; the core never needs AI or experimental dependencies. Keep `ENABLE_RAG`, `ENABLE_USER_FEATURES` and `ENABLE_ASSISTANT_AI` disabled for the default release.

Configure offsite storage and external alerts using the existing root environment template and [operations guide](OPERATIONS.md). Keep the erasure signing key and a current copy of the deletion ledger independently of the database backups and server. A database snapshot alone cannot guarantee that deleted accounts stay deleted after disaster recovery. A second volume on the same server is not an offsite copy.

Review configuration without printing secret-expanded YAML:

```sh
docker compose -f compose.production.yaml config -q
```

After DNS, firewall and durable storage are prepared, launch the reviewed candidate:

```sh
docker compose -f compose.production.yaml up --build -d
```

Only Caddy exposes ports 80/443. Do not publish frontend, backend, Redis or management ports. The gateway overwrites `X-ReelTogether-Peer` with its actual transport peer. Frontend trusts **only** that configured internal header and signs it for the API. Never set `TRUSTED_CLIENT_IP_HEADER` while exposing frontend directly to untrusted clients. If another CDN/proxy is introduced, review the trust chain before using its forwarded address. See [Caddy header behavior](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).

Initially the catalog can be empty. Enqueue `startup-sync` through the protected admin API once the provider/demo mode is chosen; the dedicated worker executes it. Without keys, this creates explicitly labeled demo data. Review applicable provider account terms before activation; adding a key does not establish commercial permission. TMDB attribution includes its unmodified approved logo, notice and source link; JustWatch regional caveats remain visible. See [asset provenance](TMDB_ASSET.md) and [TMDB requirements](https://developer.themoviedb.org/docs/faq).

## Admission and resource bounds

Production authentication requires Redis. Failure returns 503 with Retry-After instead of silently resetting to independent process counters. Shared auth budgets include username (10/10 minutes), signed browser (60/hour), and verified transport peer (300/hour). Account writes have a shared 120/minute budget. General requests additionally have browser and peer budgets. Hashed limiter keys do not store raw usernames or IP addresses; Redis expires the windows. Multiple users behind a NAT share its peer budget; review these limits with actual traffic before raising them.

Expensive password hashing has two nonblocking slots per API process. Saturation rejects with 503 instead of filling waiting worker threads. Proxy JSON uploads are limited to 64 KiB and five seconds, including a stream that never yields data. Backend buffering is separately bounded. Client cancellation also cancels the upstream request; ordinary upstream requests have a 30-second deadline.

## Maintenance ownership

The queue serializes catalog jobs, deduplicates active names, retries at most three times and retains at most approximately 100 job records. A worker renews its lease. Every supported worker Session commit takes the queue-control lock and verifies current ownership in that same transaction; stale writes roll back. A failed heartbeat also stops subsequent commits. Production ORM catalog writes without worker context are refused. Do not run raw-SQL, inline or uncoordinated catalog import scripts against the production database. A crash can still repeat a provider read or previously committed idempotent batch; this is not exactly-once processing.

## Backups, account deletion and recovery

The standard backup worker creates a verified SQLite snapshot daily, restores a disposable copy and compares content hashes. It also authenticates the receipt ledger and checks that every exported deletion still has its receipt before accepting a new snapshot. It retains the most recent 14 successful snapshots (a count, not a guaranteed minimum number of days). S3 retention is controlled by the independently reviewed bucket lifecycle policy. Pending deletion receipts are drained before a new snapshot. Account deletion stores an opaque erasure identity in a durable outbox in the same transaction as deletion, then appends an authenticated receipt outside database snapshots. No username, password or session token is written to the receipt. Failed publication leaves a retriable outbox and returns an explicit pending-recovery response; monitoring exposes the condition.

Keep the erasure signing key stable and recoverable. Rotate it only with a planned authenticated re-signing/version transition. Retain receipts for at least as long as every restorable snapshot, including offsite/PITR history. Copying a stale ledger alongside an old snapshot is not sufficient. Preserve immutable backups until their stated expiry.

Recover to an unused file while the service remains isolated:

```sh
python restore_recovery.py /data/downloaded-verified.sqlite /data/recovered-new.sqlite --ledger /erasure-ledger/current-deletions.jsonl
```

Provide the matching `ERASURE_LEDGER_KEY` securely via environment. The command refuses to replace an existing database, migrates the copy, authenticates the complete ledger before deleting anything, replays erasures with foreign-key cascades, and checks integrity. It never activates the copy. Stable per-account identities prevent a later account that reuses a numeric ID from being erased. Migration of pre-feature backups derives the same legacy identities deterministically.

Before switching: verify current ledger completeness independently, check readiness and schema, verify synthetic account/session/watchlist/two-person room flows, inspect retained non-erased accounts, and record measured RPO/RTO. Stop writers, retain both databases, then deliberately update the configured database path. Never restore directly over the active database.

Rollback after a migration uses a separately verified pre-upgrade snapshot and compatible previous image while writers are stopped; do not blindly downgrade populated schemas. Reapply all subsequent account erasures before reactivation. The candidate adds migrations 14 (indexes) and 15 (restore identity/outbox) after the earlier 13 migrations.

## Existing-volume ownership

Backend UID/GID is `10001:10001`; frontend is the image's `node` user. Fresh Docker volumes copy the correct directory ownership. A previous root-owned database may need a one-time migration. Before changing ownership: stop writers, make and verify an external backup, inspect exactly which database/WAL/SHM/backup directories belong to this app, and change only those reviewed paths. Do not run recursive ownership changes on an arbitrary user directory. An unreadable existing volume must fail startup, not be replaced with a new empty database. The local container check exercises non-root fresh storage and restart on the same populated volume.

## Retention and monitoring

`python retention.py` is a dry run. After reviewing its counts, `python retention.py --apply` removes at most 500 records per category per invocation: expired sessions, rooms expired over 30 days, and inactive job history finished over 30 days. Repeat to drain additional batches. It does not delete accounts, catalog records, snapshots or erasure receipts. Schedule the approved policy with the operator's scheduler; it is deliberately not silently applied to existing history.

`GET /api/admin/metrics/prometheus` requires `X-Admin-Key`. Scrape privately every 15–30 seconds into a collector with an explicit retention policy, for example 14 days. The endpoint exposes bounded route-template request/error counters, cumulative latency histograms, process restart time, durable queue age, expired leases and pending erasure receipts. Counters are process-local and reset; external collection must handle counter resets. Do not expose the admin credential or collector publicly.

Alert on readiness failure, persistent 5xx increases, p95 request latency above the chosen service budget, queue age over five minutes, expired worker leases, unexported erasures, stale backups and failed offsite verification. The existing monitor sends deduplicated failure/recovery webhooks only when configured; test actual delivery and recovery before launch. A monitor on the same VM cannot detect its own total host outage: use an external uptime check as well. Never include credentials, cookies, user identifiers or chat messages in alert/log labels.

## Public release gates

Local checks are necessary evidence, not a public-launch certification. Before real users: publish the reviewed source and run hosted CI; verify real HTTPS/cookies and security headers; exercise a two-user room on the chosen host; check restarts and storage permissions; verify an actual offsite download/restore including current deletion receipts; test external failure/recovery alerts; validate provider account activation and regional behavior; run representative concurrency/load checks and record a service budget. Licensing and any public-demo claims remain owner decisions.
