> Latest repairs and verification: [Reliability repairs](RELIABILITY_REPAIRS.md). The counts below describe the original milestone.

# Production readiness status

Local safeguards implemented and exercised September 13, 2026. The app is still a local deployment, not a completed public production launch.

## Implemented

- **Account recovery:** `/account-security` lets a signed-in user reauthenticate and generate a 256-bit recovery code. Only its SHA-256 hash is stored. Replacing the code invalidates the previous one. Reset atomically consumes it, replaces the Argon2 password hash and revokes all sessions. CSRF/origin checks, authentication throttling, bounded inputs and private/no-store responses apply. Codes are never included in URLs or browser storage. Existing users must generate and save a code before losing access; there is no email-based recovery.
- **Safe migrations:** revision `20260914_0006` adds the nullable recovery hash. Container startup uses the backup-before-upgrade script and skips redundant migration backups when already at head. Host and container schemas were upgraded. Backups use restrictive file permissions.
- **Verified scheduled backups:** the Compose `backups` service starts after backend readiness, creates an online SQLite backup daily, restores it into a temporary file, compares complete contents, and publishes success only afterward. It retains the latest 14 worker-created backups and retries failures after five minutes. A health check detects overdue success and verifies the recorded backup file and digest. This is a local-volume backup, not offsite disaster recovery; it cannot survive loss of the whole volume.
- **Operational logs:** structured request ID, route template, method, status and duration. Bodies, cookies, query strings, path-parameter values and exception messages are omitted. Unexpected exceptions produce a generic 500 and a correlation ID. Uvicorn access logging is disabled in the container to avoid logging raw query strings. External collection and alert delivery are not connected.
- **Readiness and deployment gates:** readiness queries both catalog and account/session schema. Production startup rejects unsafe credentials, HTTP origins, wildcard hosts, disabled rate limiting, automatic schema creation, experimental flags or enabled request interpretation without a key. `python production_check.py` reports boolean checks without exposing configuration secrets.
- **Concurrent test tool:** `scripts/load_test_catalog.py` exercises a bounded mix of browse and search requests without bypassing rate limits.

## Verification

- 74 backend tests passed, including recovery rotation/reuse/revocation, backup restoration, preflight rules and redacted error logging.
- The 12 existing Playwright tests passed. The new recovery test passed after fixing a test navigation race; the trace showed it had filled the previous page's username field before navigation completed.
- Frontend lint and typecheck passed with three existing image-optimization warnings. Backend, frontend and backup Docker images built successfully.
- Alembic check found no missing schema operations after migration.
- The new recovery page was checked at 390px width: no horizontal overflow. Screenshot: `docs/screenshots/account-recovery-mobile.png`.
- Live backup health check passed; a real catalog backup and disposable restore were verified.
- Updated local Docker workload: 60 requests, five workers, all 60 returned HTTP 200; median 136.55 ms, p95 420.30 ms, 25.34 requests/second. This short read-only run does not establish production capacity, authentication throughput, soak reliability or a service-level guarantee.

Evidence: `docs/verification/production-*`.

## Launch work requiring external configuration

1. Select/connect a hosting account and public domain. Existing `render.yaml` is a starting deployment manifest, not evidence of a deployed service. Provision persistent storage and configure production HTTPS origins/hosts and matching backend/frontend proxy secrets. Run production preflight and verify secure cookies on the public URL.
2. Configure an offsite backup destination with retention and encryption; perform a restoration from that destination. The Compose backup worker does not automatically exist in the separate Render deployment.
3. Connect external health checks, error/latency log alerts and backup-overdue alerts to an owned notification destination; exercise alert delivery.
4. If live request interpretation is advertised, supply provider credentials through the hosting secret manager and verify real responses and spend controls. Request interpretation remains optional and disabled locally; no provider key was supplied or live request interpretation request made.
5. Test the actual deployment under concurrent read/write and sign-in workloads. The current SQLite deployment and process-local jobs/throttles assume a single backend process; authentication throttling sees the proxy's address, so public multi-user sign-in throughput needs explicit testing and hosting-aware client attribution.

Do not mark the public launch complete solely because local tests or preflight pass.
