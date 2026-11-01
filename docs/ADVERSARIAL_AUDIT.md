# ReelTogether adversarial audit

## Executive summary

This audit began on `cinematic-redesign` at `fafba6149fb4c48f90626a670572182a475ffe06`, independently confirming the reported baseline of 35 browser tests and 151 backend tests. It examined PR #2 against `production-hardening`, the runtime and deployment contracts, public and private data paths, query and navigation state, persistence, browser behavior, dependency advisories and rendered accessibility. Passing baseline tests were treated as a starting point.

Fifteen verified defects are recorded below. Repairs preserve the cinematic design, account ownership, CSRF checks, private voting and existing API response shapes. No database migration, production data change, merge, deployment, force-push or PR-base change is part of this audit.

The pass is finite and evidence-based. It does not certify that every possible defect is absent, that every provider is available, or that the product meets every accessibility criterion.

## Architecture and investigation map

| Area | Actual implementation | Investigation and boundary |
|---|---|---|
| Frontend | Next.js App Router, React, TypeScript, TanStack Query, Axios, Lucide and Recharts | Route/component state, root providers, native search dialog, filters, comparison, recommendation chat, saved movies, security forms and room UI; strict type/lint/build checks |
| Styling | Two explicit CSS cascade layers, shared tokens, local licensed variable fonts | Nine widths, image failures, long titles, keyboard interaction, reduced motion and automated accessibility scans; design retained |
| API boundary | Next.js catch-all `/api` proxy, bounded uploads, 30-second upstream timeout, signed browser/peer admission identifiers | Encoded path tests, query forwarding, private cache headers, cookie/CSRF forwarding and upload regressions |
| Backend | FastAPI, Pydantic and SQLAlchemy | Public reads, malformed requests, input bounds, private ownership, sessions, maintenance authorization and failure propagation |
| Persistence | SQLite and PostgreSQL, Alembic migrations | Disposable databases/schemas only; migration checks, foreign keys, uniqueness, query hydration, atomic recovery and room transitions |
| Authentication | Argon2id, hashed opaque session tokens, seven-day revocable sessions, same-origin and CSRF checks | Registration/login/recovery, logout, cross-tab invalidation, password rotation, export/deletion and stale-response races |
| Movie Night | Private membership/preferences/ballots; host-controlled stages, round IDs and expiring hashed invitations | Two-user voting, unauthorized access, stale rounds, ties/vetoes, restart/removal and selected-movie saving |
| Background work | Durable queue, worker leases and commit fencing | Existing lease-loss/concurrency regressions rerun on SQLite and PostgreSQL; no real provider refresh scheduled |
| Operations | Non-root containers, production preflight, Redis admission, Caddy ingress, verified backups and independent deletion receipts | Source/configuration review and disposable migration/restore tests; no production service or volume touched |
| Integrations | Stored TMDB/OMDb/YouTube data; optional request interpretation; experimental RAG/legacy ratings disabled in production | Offline provider failure/identity tests and feature guards inspected. No live credentialed request or experimental-runtime certification |
| CI | Backend, frontend and dependency-security jobs | Latest audit commits must pass hosted CI before a green remote result is reported |

The repository inventory and static checks cover the source tree. Manual tracing concentrated on reachable routes, auth/room boundaries, query state, ingestion identities and operational writes. Disabled experimental code was checked for reachability/configuration boundaries rather than represented as a tested production feature. Historical design/release documents are historical evidence, not proof of the current revision.

## Detailed confirmed defects

### AUD-01 — Stale autocomplete results and obsolete requests (Medium)

| Field | Evidence |
|---|---|
| Location | `frontend/components/shared/SearchBar.tsx`; `frontend/lib/api.ts` |
| Root cause | Clickable results were keyed to the debounced value even after the visible input changed. The query did not consume the cancellation signal. Initial search-page values could also start previews without editing. |
| Reproduction | Load a result for “Fixture Movie 00”, freeze the debounce clock, then type “Chat” or clear with the keyboard. The previous title remains selectable. Hold an older request while changing queries to exercise request lifetime. |
| Fix | Show results only when the current trimmed input matches the query key; hide previews for empty input or completed navigation; activate previews while editing; consume the query cancellation signal through Axios. Loading/empty feedback has status semantics. |
| Regression | `editing a search cannot leave clickable results for the previous query`; `obsolete slow search requests are cancelled without duplicate replacement requests`. |
| Verification | The old-state reproduction failed before repair. Corrected tests require zero old choices, cancellation of the held request, and one replacement request. |

### AUD-02 — Clear search loses typing focus (Low)

| Field | Evidence |
|---|---|
| Location | `SearchBar.tsx`, Clear search handler |
| Root cause | Clearing removed the focused clear button from the DOM without returning focus to the input. |
| Reproduction | Enter text, click Clear, then type using the keyboard. |
| Fix | Retain an input ref and focus it after clearing both input and debounce state. |
| Regression | `clearing search preserves keyboard input focus`. |
| Verification | Failed focus assertion before repair; corrected scenario types the next query into the input. |

### AUD-03 — Query-only browser history leaves search open (Medium)

| Field | Evidence |
|---|---|
| Location | `SiteHeader.tsx`, search lifecycle listeners |
| Root cause | Route cleanup watched the pathname; Back/Forward can change only the query string. |
| Reproduction | Search from `?q=Fixture` to `?q=Chat`, reopen search, then go Back and Forward. |
| Fix | Dismiss on `popstate`, with listener cleanup. Explicit submit/result completion still handles same-page navigation. |
| Regression | `query-only Back and Forward dismiss an open search`; existing same-film/query-only tests retained. |
| Verification | Reproduced before repair; both history directions now close the dialog. |

### AUD-04 — Clicking modal padding dismisses it (Low)

| Field | Evidence |
|---|---|
| Location | `SiteHeader.tsx`, dialog pointer handler |
| Root cause | An event targeted at the dialog element was treated as a backdrop click even within its padding. |
| Reproduction | Click two pixels inside the dialog boundary. |
| Fix | Check pointer coordinates against the dialog rectangle before dismissing. |
| Regression | `dialog padding is inside the modal while the backdrop dismisses it`. |
| Verification | Before repair, the inside click closed search. After repair, padding preserves it and a real outside click dismisses it. |

### AUD-05 — Encoded separators escape the API namespace (Medium)

| Field | Evidence |
|---|---|
| Location | `frontend/app/api/[...path]/route.ts`, proxy path construction |
| Root cause | Decoded catch-all segments were joined directly into an upstream URL. Embedded separators allowed URL normalization outside `/api`. |
| Reproduction | Request `/api/..%2Fhealth` or a backslash equivalent; the proxy reached backend `/health`. |
| Fix | Reject decoded separators, dot segments and control characters; encode accepted segments individually. Invalid paths return a private, non-cacheable 400. |
| Regression | `encoded path separators cannot escape the API proxy namespace`, with valid query forwarding checked afterward. |
| Verification | The boundary test failed before repair and passes afterward. This was an upstream-path confinement defect, not a demonstrated arbitrary-host SSRF or backend authorization bypass. |

### AUD-06 — Old-session 401 clears a new account (Medium)

| Field | Evidence |
|---|---|
| Location | `frontend/app/providers.tsx`, Axios response interceptor |
| Root cause | Any matching 401 cleared the current account, regardless of which session initiated the request. |
| Reproduction | Hold a private read, sign out, register another account through client navigation, then deliver the old read's 401. |
| Fix | Capture the originating session marker in a request-config WeakMap and clear state only if it still matches the current session. Interceptor cleanup is preserved; no token is added to URLs or logs. |
| Regression | `a delayed failure from a previous session cannot sign out a new account`. |
| Verification | The reproduction removed the new user's watchlist before repair; the new user's account and private collection remain visible after repair. Server ownership checks remain unchanged. |

### AUD-07 — Autocomplete wildcard and Unicode mismatch (Medium)

| Field | Evidence |
|---|---|
| Location | `backend/app/repositories/movies.py`, `search_movies`; `catalog_sql.py` |
| Root cause | Raw LIKE metacharacters were interpreted as patterns; SQLite's built-in lowercase did not match the catalog's Unicode semantics. |
| Reproduction | Seed “Été 100%_literal” and an ordinary title. Search suggestions for `%`, `_literal` and `été`. |
| Fix | Use parameterized autoescaped substring matching and the same Unicode-lowercase helper used by browse, on both supported databases. |
| Regression | `PublicReadAuditTests.test_autocomplete_uses_literal_search_characters_and_unicode`, included in PostgreSQL catalog CI. |
| Verification | `%` incorrectly returned the ordinary title and `été` missed its title before repair. Exact expected results pass on SQLite and PostgreSQL. This is search correctness, not SQL injection: values were already bound parameters. |

### AUD-08 — Public detail/discovery hydrate unused history (Medium)

| Field | Evidence |
|---|---|
| Location | Movie repository getters; `api/movies.py`; `api/search.py` discovery dashboard |
| Root cause | Public core reads eagerly loaded the complete writable analytics-history relationship despite needing only the latest snapshot. |
| Reproduction | Store one latest and 100 dated snapshots per film; count actual SQLAlchemy analytics-object load events. |
| Fix | Core detail explicitly selects latest-only hydration; discovery uses the summary relationship. Existing repository history behavior remains the default for history-dependent callers. |
| Regression | `test_core_movie_detail_hydrates_latest_not_history`; `test_discovery_never_hydrates_historical_snapshots`. |
| Verification | Core detail: 101 → 1 hydrated analytics objects. Two-film discovery: 202 → 2. Explicit history still returns all 101 stored dates. Both databases pass. These are measured object counts, not a fabricated latency or field-performance score. |

### AUD-09 — Visible labels differ from accessible names (Medium)

| Field | Evidence |
|---|---|
| Location | Header brand/search control; Movie Match reset and prompt buttons |
| Root cause | Replacement labels omitted visible brand/shortcut text or named the internal prompt rather than the visible action. |
| Reproduction | Automated `label-content-name-mismatch` checks on mobile and desktop, especially Movie Match. |
| Fix | Use visible brand content as the link name, include the visible shortcut in the search name, expose keyboard shortcuts semantically, and align prompt/reset names with visible words. |
| Regression | `recommendation actions keep their visible words in their accessible names`; existing role-based tests updated to the corrected exact names; automated accessibility scans repeated. |
| Verification | Initial scans reproduced the mismatches. A parenthesized shortcut still failed the rule's label comparison, so the final name includes the shortcut without hiding it in parentheses. No accessibility rule was disabled. |

### AUD-10 — Missing movie looks like a temporary outage (Low)

| Field | Evidence |
|---|---|
| Location | `frontend/app/movies/[slug]/page.tsx` |
| Root cause | All query errors reached the unavailable/retry branch; a genuine 404 never reached the empty-data fallback and received automatic retries. |
| Reproduction | Open `/movies/unknown-audit-title`. |
| Fix | Distinguish a 404 as “Movie not found”, without automatic retries; retain retry behavior for temporary errors. |
| Regression | `missing films are distinguished from a temporary catalog outage`. |
| Verification | Missing-resource reproduction failed before repair and passes afterward. This is client UI handling; it does not claim the client-rendered film document itself changes to an HTTP 404. Unknown application routes independently return 404. |

### AUD-11 — Comparison sharing shows an obsolete receipt/link (Low)

| Field | Evidence |
|---|---|
| Location | `frontend/components/compare/ShareCompareButton.tsx` |
| Root cause | Copied/fallback state was independent of selected IDs. |
| Reproduction | Share two films, change the selection, then inspect “Link copied” or the clipboard-denied fallback field. |
| Fix | Bind the receipt and fallback to the selection that was shared. A changed selection presents Share comparison again and removes the obsolete fallback. |
| Regression | `comparison sharing never claims an obsolete selection is copied`, for clipboard success and denial. |
| Verification | The stale copied-label reproduction failed before repair; both clipboard paths now reflect the new IDs. |

### AUD-12 — Active README contradicts recovery behavior (Low)

| Field | Evidence |
|---|---|
| Location | `README.md`, account/release guidance |
| Root cause | Earlier “recovery not implemented” wording, a missing screenshot link and workstation-specific release instructions remained in the active guide. |
| Reproduction | Follow the account section and compare it with the implemented recovery-code UI; resolve the screenshot target from tracked source. |
| Fix | Describe previously saved recovery codes accurately, link the audit, and state portable Compose/volume guidance. Historical release reports remain historical. |
| Regression | Documentation/link review and source publication review. |
| Verification | The active guide now matches the tested recovery workflow and no longer points to the absent screenshot. |

### AUD-13 — WebKit pointer activation breaks keyboard dismissal/return (Medium)

| Field | Evidence |
|---|---|
| Location | `SiteHeader.tsx`, search opener and mobile-menu toggle |
| Root cause | The handlers assumed a pointer click would focus a button. WebKit does not make that assumption, so dialog close could restore elsewhere and menu Escape might never bubble through the header. |
| Reproduction | In WebKit, click search then Escape; click the mobile menu then Escape. |
| Fix | Explicitly focus the activating button before opening search/toggling navigation. Keyboard-shortcut opening keeps native restoration to its previously focused control. |
| Regression | Existing search-focus and mobile-menu tests plus repeated mobile/desktop search tests run in WebKit. |
| Verification | Three WebKit failures reproduced this assumption. The affected test group passes after repair. Native browser-chrome tab stops are distinguished from focus escaping into interactive page controls. |

### AUD-14 — WebKit cross-tab logout leaves stale private UI (Medium)

| Field | Evidence |
|---|---|
| Location | `frontend/lib/account.ts`; `frontend/app/providers.tsx` |
| Root cause | The only cross-tab notification was a storage event. The tested WebKit engine shared the new storage value but did not deliver the event to the other live page. |
| Reproduction | Open a private watchlist in two pages in the same context, sign out in one, and inspect the other. Instrumentation confirmed the changed marker and missing storage event. |
| Fix | Add a shared page-lifetime BroadcastChannel alongside storage events; deduplicate markers and remove listeners on cleanup. The sender uses the same channel instance, avoiding self-notification. Only random invalidation markers cross tabs. |
| Regression | `signing out clears another tab’s private watchlist immediately`, retained unchanged and exercised in WebKit/Chromium. |
| Verification | The old WebKit run failed the existing test. The affected group passes after repair. Session revocation was already enforced by the backend; this fix clears stale client UI. Browser suspension can still defer execution until a page resumes. |

### AUD-15 — Broken region labeling relationships (Low)

| Field | Evidence |
|---|---|
| Location | Homepage social section and Movie Match poster gallery |
| Root cause | The social section referenced a heading ID that did not exist. The gallery used an accessible label on a generic container without a naming role. |
| Reproduction | Inspect the scanner's incomplete ARIA checks, resolve `aria-labelledby="social-title"`, and query the named gallery as a semantic group. |
| Fix | Add the missing heading ID and give the gallery a group role. |
| Regression | The accessible-name regression also asserts the named homepage region and gallery group. |
| Verification | Incomplete checks were investigated rather than counted as passes; the source relationships are corrected and targeted browser assertions pass. |

## Testing report

Final executed counts and hosted CI evidence are recorded with the publication receipt. The initial fresh baseline was **35 Chromium browser tests, 151 backend tests**. The new suite contains **48 browser tests** and **154 backend tests**; the PostgreSQL catalog suite expands from five to eight tests. Counts describe tests, not a claim of exhaustive coverage.

Relevant commands use the repository's scripts:

```sh
# backend, using the isolated test interpreter
python -m unittest discover -s tests -v
python tests/postgres_smoke.py
python tests/postgres_catalog.py
python tests/postgres_hardening.py
python -m pip_audit -r requirements.txt
# frontend
npm run lint
npm run typecheck
npm run build
npm test -- --browser=chromium
npm test -- --browser=webkit
npm audit
npm audit --omit=dev
# root tooling
npm audit
```

`POSTGRES_TEST_URL` pointed only to a temporary local `reeltest` database; PostgreSQL test scripts additionally create unique schemas. Browser fixtures use disposable data and blank provider credentials. No destructive test uses an existing installation's data.

The rendered matrix covers 16 public routes at **320, 375, 390, 430, 768, 1024, 1280, 1440 and 1920 CSS pixels**. Accessibility checks use selected WCAG A/AA rules at mobile/desktop widths and selected private states. Image-error fallbacks, long untrusted titles, safe text rendering, query failures, keyboard operation and reduced motion receive separate checks. These are automated observations, not full accessibility or real-user performance certification.

## Executed validation results

| Check | Fresh result | Fail / skip | Evidence and limits |
|---|---|---|---|
| Initial Chromium baseline | 35 passed | 0 / 0 | Fresh execution at the audit starting revision |
| Initial backend baseline | 151 passed | 0 / 0 | Fresh SQLite/offline suite |
| Expanded Chromium suite | 48 passed | 0 / 0 | Accounts, recovery, private rooms, adversarial search/session/proxy/sharing and long-title cases |
| Expanded WebKit suite | 48 passed | 0 / 0 | Initial 43/47 run exposed four failures; repaired run passed all expanded checks |
| Backend suite | 154 passed | 0 / 0 | Includes three new public-read tests with Unicode/literal-search subcases |
| PostgreSQL catalog | 8 passed | 0 / 0 | Includes all three new public-read tests |
| PostgreSQL hardening | 14 passed | 0 / 0 | Shared admission failure handling, fencing, erasure and operations |
| PostgreSQL migration/smoke | Passed | 0 / not applicable | Fresh upgrade/check, readiness, catalog, account/watchlist/room and durable queue scenarios |
| Lint / TypeScript / production build | Passed | 0 / not applicable | Real frontend package scripts |
| Dependency audit | Zero known advisories | 0 / not applicable | Frontend full/runtime, root npm tree and backend runtime requirements; point-in-time advisory result |
| Responsive matrix | 144 views, no overflow or uncaught page errors | 0 detected / not applicable | 16 routes × nine widths; repeated after the first repair batch |
| Public/private accessibility | 51 scans, zero detected violations | Incomplete checks documented | Includes search, signed-in preferences/security, lobby, voting, reveal, selected result and root text scaling; not full AA certification |
| Emulated touch | Passed | 0 / not applicable | Search opening, Clear focus and submission on a 390px touch context |
| Real Redis concurrency | Passed | 0 / not applicable | 32 simultaneous attempts: exactly 7 admitted and 25 rejected at a limit of 7; temporary service outage failed closed |
| Initial local Firefox attempt | 8 non-UI checks passed | 39 launch failures / 0 | Browser profile creation failure; no Firefox UI compatibility claim from this attempt |
| README links / diff whitespace | Passed | 0 / not applicable | No missing local README targets and clean diff whitespace |

Final hosted Chromium/Firefox/WebKit and publication results are recorded in the delivery receipt. No test is deleted or skipped to obtain a passing result. Native browser-chrome focus was correctly distinguished from application focus escape during investigation.

## Remaining risks and explicit limitations

- Firefox was downloaded and attempted. It cannot create/open its profile in this environment, including with a workspace-local temporary directory. The initial attempt passed eight non-UI checks and blocked 39 browser-dependent tests at launch; this does **not** establish Firefox UI compatibility. A new hosted Linux Firefox CI job provides separate verification; its outcome is recorded in the delivery receipt. Local Firefox/macOS UI compatibility remains unverified.
- Automated accessibility scans and keyboard tests do not replace manual VoiceOver/NVDA testing. The pre-ARIA-repair 51-scan pass had 39 scans with incomplete checks: 754 contrast node occurrences over gradients/overlaps, three missing-ID occurrences and four generic-container naming occurrences. Repeated contexts are not unique defects. The two ARIA root causes were repaired as AUD-15. The repeated final 51-scan pass contains only incomplete contrast checks (754 repeated node occurrences), with no remaining incomplete ARIA checks. Gradient/artwork contrast remains a manual-review limitation and is not counted as passing. Native browser zoom controls and every assistive-technology/browser combination are not certified.
- Live provider credentials, actual upstream catalogs/poster URLs, paid interpretation, hosting/TLS, offsite object storage and external alerts were not activated. Existing illustrative demo artwork can fail upstream and uses fallbacks. Local tests do not establish a live production SLA.
- Catalog-wide aggregate operations still scale with catalog size; the measured repair removes historical-snapshot amplification, not every possible scaling cost. Field LCP/INP/CLS, large backup memory usage and long-duration soak/load behavior remain unmeasured here.
- Core database rows must satisfy the schema's application contracts. Malformed optional-provider metadata and migration paths are tested; this audit is not a repair tool for arbitrarily corrupted database files or every possible invalid core-column value.
- Suspended/background pages cannot execute invalidation code until the browser permits them to resume. BroadcastChannel, storage notification and session revalidation complement server-side revocation rather than replacing it.
- Optional/experimental runtimes remain outside the supported production claim. A Starlette test-client deprecation warning is visible in test logs; it did not fail the executed suites.
- The production topology was reviewed, not deployed. Previously running unrelated containers/volumes are outside the audit and are not modified.

## GitHub and review status

Work stays on `cinematic-redesign`, targeting `production-hardening` in draft PR #2. Verified changes are pushed only after diff and private-file review. The final delivery records commit IDs, file count, clean-worktree status, push result and CI result. PR #2 must remain draft, open, unmerged and undeployed.
