# ReelTogether — After Hours

## Repository assessment

This redesign builds on the existing Next.js App Router/React/TypeScript application with TanStack Query, Lucide icons and custom CSS. FastAPI, SQLAlchemy and Alembic provide the catalog, accounts, private preferences, room state machine and maintenance services; SQLite and PostgreSQL are supported by the backend. No backend stack change, migration, account-data alteration or replacement API was needed.

The original interface had functioning search/filtering, saved movies, account security/export/deletion, comparisons, recommendations and private group voting. Its visual weaknesses were successive conflicting global stylesheets, repeated poster-grid sections, a technical discovery dashboard, inconsistent type hierarchy, and long detail-page orchestration. These are design and composition issues rather than a reason to replace working product behavior.

## Three creative directions

| Direction | Palette and typography | Layout and motion | Product character |
|---|---|---|---|
| After Hours | Ink, ivory, restrained chartreuse; Manrope and Bodoni Moda | Framed art, editorial scale, asymmetric sections, brief opacity/transform reveals | A welcoming film club with private group planning at its center |
| Electric Repertory | Midnight, violet, silver; condensed poster typography | Screen-like compositions, sharper transitions, denser discovery | A more futuristic exploration tool |
| The Screening Room | Charcoal, parchment, burnt amber; archival serif/sans | Ticket geometry, intimate compositions, restrained cuts | A quieter repertory-cinema journal |

After Hours was selected because it supports both artwork-rich discovery and the social decision-making flow, without copying a streaming service or pretending the app streams films.

## Design architecture

A single global entry establishes explicit foundation and product cascade layers. The compatibility foundation preserves existing analytical-widget layouts while the product layer owns the design tokens and new interaction surfaces. The former three competing global imports are removed. Color, typography, borders, spacing, surfaces and timing are defined centrally. Layered legacy widget rules can be removed incrementally as those internal widgets receive isolated styles; this is not a claim that all legacy CSS was deleted.

Manrope supplies readable interface text; Bodoni Moda supplies editorial display type. Both are self-hosted WOFF2 variable fonts with their upstream SIL Open Font Licenses included. The two compressed files total about 128 KB instead of 327 KB of source TTFs. Fonts are served locally, with swap/fallback behavior and no browser requests to a font service. Upstream sources: [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope), [Bodoni Moda](https://github.com/google/fonts/tree/main/ofl/bodonimoda).

Motion uses CSS transforms/opacity and IntersectionObserver, rather than a new runtime animation dependency. Content remains visible without script; only offscreen sections become reveal candidates. Reduced-motion users receive readable static content. Hero selection is manual, with no autoplay video or automatic rotation.

## Page-by-page strategy and implementation

| Surface | Redesign | Preserved behavior |
|---|---|---|
| Home | Full-bleed spotlight; ranked posters; movie-night editorial feature; four genre paths; release timeline; wide released-film panels | Existing stored feeds, catalog provenance and errors/retries |
| Navigation | Framed brand, active routes, native modal search, keyboard shortcut and mobile dock/menu | Library, discovery, match, rooms, watchlist, upcoming and security routes |
| Discovery | Genre doorways, franchise rows and model-arranged collections | Actual dashboard API, counts and honest collection descriptions |
| Library | Editorial introduction and expandable filter workspace | Every genre/status/year/studio/director/franchise/rating/streaming filter, sorting and pagination |
| Film detail | Large backdrop, framed poster, editorial title, readable synopsis and primary save/group actions | Stored metadata, trailer, cast, source notes and all optional insights |
| Film insights | Separate dynamically loaded component | Analytics/history/insight calls and charts load only when opened |
| Movie Match | Shared typography/surfaces, clear prompt choices and readable preferences/results | Current rules, filters, favorites, feedback and optional interpretation consent |
| Movie Night | Branded room, preferences, ballots, results and invitation controls | Server-owned membership/privacy, rounds, vetoes, ties, reveal, selection and optional saving |
| Watchlist/accounts | Calm private surfaces with consistent labels, controls and destructive-action separation | Session ownership, status, cross-tab logout, recovery, export, confirmation and deletion |
| Compare | Consistent side-by-side workspace, selected states and data panels | Four-film selection, URL sharing, missing data, ties and existing charts |
| Upcoming | Clear release-focused introduction and consistent cards | Full release slate and later-page browsing |
| Search/entity pages | Shared editorial hierarchy, frames, filters, empty states and navigation | Query URLs, director/studio/genre/franchise data and pagination |
| About/footer | Consistent invitation, sources and security access | Provider credits, demo disclosures, privacy and account links |

## Roadmap and boundaries

The implementation sequence was shared tokens/navigation, homepage composition, discovery/detail surfaces, mobile/private flows, then visual and functional QA. The first concrete steps were replacing the cascade entry, self-hosting fonts, building a manual spotlight, and adding reusable headings, reveal wrappers and skeletons. These are implemented rather than proposed mock controls.

Genre pathways are real links to supported genre pages. The group feature illustrates the real invite/private-vote/reveal flow, without fake live participants, invented ratings or activity counts. Demo catalog art is labeled. Existing artwork URLs are reused; no film posters were invented or committed as new image assets. Trusted provider images can use the existing framework's responsive image optimizer; other valid image sources keep the previous direct-loading fallback.

Future concepts are intentionally separate: mood discovery needs an explicit mood taxonomy and provenance; taste comparison needs consent and a privacy contract; random discovery needs filter-preserving server selection; shared watchlists/friends/activity need their own authorization and data models. None is presented as a working control here.

## Quality targets

Verify actual desktop and mobile rendering, keyboard search/focus restoration, narrow-screen filters, reduced motion, artwork failures, loading/error states, long titles and the complete existing account/room/recommendation flows. Check the production build, lint and TypeScript. Local layout and timing observations do not certify field Core Web Vitals or full WCAG conformance. Deployment still follows the production guide and remains distinct from publishing a design branch.

## Verification results

- ESLint, TypeScript and the production build pass.
- All 34 browser tests pass, including the existing account/recovery/export/deletion, recommendation, catalog and two-user private-voting journeys. Six added redesign cases cover keyboard search and focus, manual spotlight links, narrow-screen filters, reduced motion, deferred insights and poster proportions.
- All 151 backend tests pass; no backend or database code changes are part of this redesign.
- The production preview was inspected on 16 routes at 360, 390, 768, 1440 and 1920 pixels: 80 views, no horizontal overflow, all document responses successful and no uncaught browser errors. Failed image requests render 16 catalog fallbacks instead of broken image icons. Final artwork sizing received additional targeted checks after visual review.
- Source and credential-pattern review excludes real environment files, databases, logs, local reports, installed dependencies and editor configuration from publication. The fonts are validated WOFF2 assets, with licenses included. No application dependency was added.

The review found and corrected a poster-sizing regression that intercepted room-voting buttons, restored the Upcoming footer route used by existing navigation tests, and corrected the recommendation poster fan's intrinsic proportions. These checks exercise application behavior; they do not certify all accessibility criteria or real-user performance.

Deployment, real provider credentials, live catalog artwork quality and operational monitoring remain environment-specific release work. Some existing demo artwork is illustrative or unavailable upstream; the interface labels demo content and supplies fallbacks. No unsupported streaming, friends feed, taste comparison or mood API is presented as implemented.
