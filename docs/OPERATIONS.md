# ReelTogether operations

Compose runs the API, a database-backed maintenance worker, verified SQLite backups, and a health monitor. Run `docker compose up -d --build` after configuring the ignored root `.env`. Existing database volumes remain in place; startup applies migrations and creates a pre-migration backup.

## Durable maintenance

Maintenance requests persist before returning their job identifier. The worker claims jobs with a two-minute lease, renews every twenty seconds, and recovers expired claims. Three attempts are allowed; execution failures retry after a short delay. Active requests for the same operation are deduplicated. The most recent 100 jobs are retained by default. Authenticated `/api/admin/jobs` endpoints expose status and sanitized errors.

Delivery is at least once: a crash after a side effect but before completion can repeat work. Catalog handlers primarily update existing records; provider calls can repeat. This is not an exactly-once processing guarantee. The database must reside on persistent storage shared by the API and worker. SQLite suits this single-host setup; it is not a distributed queue deployment.

Compose disables the embedded API worker and runs `jobs` separately. Other deployments enable the embedded worker by default with `ENABLE_JOB_WORKER=true`; keep at least one worker running. Set `ENABLE_PERIODIC_SYNC=true` to schedule configured catalog/trailer refreshes every six hours. Schedules survive restarts. Startup sync is also deduplicated across restarts for six hours.

## Connect offsite backups

Uploads are disabled while `BACKUP_S3_BUCKET` is empty. In the ignored root `.env`, configure the bucket, region, optional HTTPS S3-compatible endpoint, prefix, and credentials shown in `.env.example`. Prefer temporary credentials when available. Do not commit secrets. Recreate `backups` and `monitor` after changing configuration.

Grant access to upload and download objects only under the chosen prefix. The uploader does not delete remote objects or configure bucket policies. Set a bucket lifecycle rule for your desired retention and restrict public access. Default uploads request AES256 server-side encryption; managed-key encryption additionally requires the key identifier and appropriate key permissions. Use `bucket-default` only with a provider whose bucket encryption you have configured and verified.

Each local snapshot is integrity checked and restored into a disposable database. Upload verification downloads the object again and compares its SHA-256 digest and complete database contents before recording success in `/data/backups/offsite-status.json`. This doubles transfer traffic and should be included in your storage budget. Fourteen local snapshots are retained, including during upload outages. Remote retention is controlled by your bucket lifecycle policy.

Store the verified object key and SHA-256 digest separately from this host as part of your recovery records. To restore, run inside the configured backup container:

```sh
python offsite_backup.py OBJECT_KEY VERIFIED_SHA256 /data/recovered-new.sqlite
```

Restoration refuses an existing destination and verifies the downloaded digest. Inspect the recovered database before stopping writers and intentionally changing `CONTAINER_DATABASE_URL` to the new file. Restore does not switch the running database automatically. Test a real recovery after connecting your storage; mock transfer tests do not prove credentials or bucket policy work.

## Connect alerts

Set `ALERT_WEBHOOK_URL` to an HTTPS endpoint accepting JSON POST requests and optionally `ALERT_WEBHOOK_TOKEN` for bearer authentication. Redirects are rejected. The payload contains `service`, `component`, `status` (`failed` or `recovered`), and `text`; it contains no database contents or credentials. Adapt the endpoint to your monitoring provider's required format.

The monitor checks API readiness, local backup verification, worker heartbeat, latest maintenance outcomes, and offsite backup freshness when configured. Initial healthy checks are quiet. Failed delivery retries on the next sixty-second poll; successful notifications are deduplicated until the state changes. State persists in `/data/operations/alerts.json`. Delivery is at least once: a crash between sending and saving state can duplicate a notification.

Local reports are stored in `/data/operations/health.json`. An empty webhook URL means alerts are not connected. The monitor runs on the same host, so it cannot report a complete host/network outage: configure an independent uptime monitor against your public readiness endpoint. A recent offsite verification records a successful round trip, not continuous proof that an object has not subsequently been removed.

## Release checks

Run backend unittest discovery, migration upgrade plus `alembic check`, dependency audits, frontend lint/typecheck/build, and browser tests before deployment. Queue and storage regression tests use disposable databases and fake storage, never the live catalog or external notification services.
