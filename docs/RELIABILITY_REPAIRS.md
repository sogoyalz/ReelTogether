# Reliability repairs — September 15, 2026

## Corrected behavior

- Login performs a conditional credential update and holds its database lock through session creation. A password reset that wins first rejects the old login; a reset that follows deletes its session. The password-rehash path uses the same check.
- Authentication uses a verified, proxy-signed browser identity plus an independent username limit. Invalid signatures and forwarding headers cannot choose that identity. This avoids putting every proxied visitor into one 60-attempt bucket. Limits remain process-local, and browser identity is not a network-level abuse control; changing cookies does not reset the username limit.
- The proxy preserves retry hints and request identifiers. Malformed identity cookies are replaced instead of crashing signature verification.
- Provider metadata is normalized across browsing, watchlists, movie insights, ingestion and enrichment. Unsupported values become missing data. Provider outages retain stored ratings and runtime.
- Watchlist pagination reconciles the displayed page with the server’s canonical page after deletion.
- Starting Movie Night saves the host’s editable preferences first. Unfinished rounds can return to the lobby, clear ballots, and remove unavailable members. Invitations rotate on restart/removal. Round identifiers reject delayed ballots. A conflict refreshes room state immediately.
- Backup health requires a fresh verification record and an existing backup matching its recorded digest. Missing, modified, stale and malformed backup records fail health checks.
- Readiness and the production preflight check the persisted feature schemas, including the newest room column. Movies released today no longer receive an incorrect future-release warning.

## Validation

- 91 backend tests passed, including deterministic file-backed password-reset/login interleavings with and without password rehash, independent proxy identities, malformed metadata, backup loss/corruption and stale round requests.
- 17 browser tests passed, including two separate movie-night participants, unsaved host preferences, a restarted round, deleting the last item on a watchlist page, retry headers and malformed proxy cookies.
- TypeScript passed. Lint has no errors and retains three existing image-optimization warnings.
- Migration upgrade preserved pre-existing lobby/voting/revealed/selected rooms. Downgrade/re-upgrade and schema comparison passed against a disposable database. Production configuration preflight passed against that fixture.
- Backend and frontend dependency audits reported no known vulnerabilities at verification time.
- The production container build passed. The local services run revision `20260915_0008`, retain 1,369 catalog movies, and pass backup health.
- A bounded local read check returned HTTP 200 for all 100 requests with five workers: p50 129.88 ms, p95 332.49 ms. This is not a production-capacity benchmark.

## Remaining deployment work

This repair pass does not establish public production readiness. Offsite backup storage and restore verification, external alert delivery, durable background jobs, and a deployed hosting configuration remain outstanding. The recommender remains a heuristic without a measured quality benchmark. Browser identities and in-process limits do not replace hosting-level abuse controls.

Local verification logs and screenshots are deliberately excluded from Git. Earlier milestone documents retain their historical test counts.
