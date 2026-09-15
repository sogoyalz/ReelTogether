> Color and motion follow-up: violet/teal accents, colored genre shortcut buttons, short entrance animations, card hover transitions, artwork fades, and a pending-response indicator. Motion is disabled when reduced motion is requested. The styles are isolated in `frontend/app/color-motion.css`.

> Follow-up: the current visual treatment uses a restrained slate/white palette, compact page headings, consistent active navigation, and less decorative styling. Movie Match moves optional request interpretation controls below the composer, groups coverage notes in an expandable section, and confirms preference changes. Verification is recorded in `docs/verification/professional-ui-*`.

# UI/UX refresh

The refresh establishes a warm neutral/olive visual system across the existing application, with a cinematic home hero and real catalog artwork. No new UI dependencies or third-party fonts were added.

## User-facing changes

- Home page leads with movie discovery and a direct Movie Match action. A featured catalog film supplies the backdrop and detail link. Search and the catalog summary are compact; developer-facing copy is removed.
- Shared movie cards show posters, title, year, genres and rating when available. Unknown ratings are not replaced with invented scores. Failed/missing artwork has a stable, accessible decorative fallback.
- Movie Match includes poster thumbnails, clearer conversation bubbles, more distinct primary actions, readable grouped preferences and a dedicated mobile preferences toggle above the conversation.
- Mobile navigation opens and closes predictably, closes after selecting a link, and supports Escape. The header uses one row on small screens.
- Focus indicators, a skip link, reduced-motion handling and mobile touch targets are included.
- Home rendering happens at request time, avoiding a permanently empty featured state when the backend is unavailable during the image build.

The original page layouts and data behavior are preserved outside the targeted changes. The style layer is `frontend/app/ui-refresh.css`; catalog artwork is rendered by `MovieArtwork.tsx` with a graceful failure state. Images use the existing provider URLs and currently bypass Next's image optimization service.

## Verification

58 backend tests and 12 existing browser flows pass. Frontend lint/type checking and the production build pass; the three pre-existing image optimization warnings remain. Browser checks at 1440px and 390px cover Home, Movie Match, Library and Watchlist, including mobile preferences and Escape navigation. Screenshots and check outputs are under `docs/screenshots/ui-*` and `docs/verification/ui-refresh-*`.

Interpretation-service and movie-provider credentials remain unconfigured. This visual refresh does not claim to activate request interpretation or fill missing metadata.
