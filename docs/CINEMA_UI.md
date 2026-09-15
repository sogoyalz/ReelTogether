# Cinema UI refresh — September 14, 2026

Movie Match now leads with real catalog posters, a charcoal/warm-orange palette, an editorial headline and direct mood shortcuts. The empty chat placeholder was removed. Desktop preferences sit beside the main flow; mobile preferences remain expandable. Recommendation cards give posters more space, retain explanations and preserve feedback/watchlist actions.

Shared navigation, homepage statistics, library forms and account surfaces use the same palette. The library heading is smaller. Chat updates scroll inside the conversation rather than moving the entire page, and respect reduced-motion preferences. Film links and requests remain connected to real catalog data; optional request interpretation availability is still disclosed.

The existing color/motion stylesheet was replaced, rather than adding another global stylesheet. Backend behavior and account/session data were not changed.

Verification:
- Frontend lint and typecheck passed; three existing image warnings remain.
- All 13 Playwright tests passed, including recommendation refinements, account recovery and mobile flows.
- Production frontend image built and the existing local container was updated.
- Live desktop/mobile checks: recommendations returned a shortlist, mobile preferences and navigation opened, no horizontal overflow at 390px, and no page errors in the checked flows.
- Screenshots: `docs/screenshots/cinema-*`; logs: `docs/verification/cinema-ui-*`.

Artwork availability depends on the catalog's image URLs; unavailable images retain the existing title fallback.
