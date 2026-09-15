> Update: optional natural-language preference extraction and a bounded metadata backfill command are now implemented. See [INTERPRETATION_SETUP.md](INTERPRETATION_SETUP.md) for activation, verification boundaries and current missing credentials. The original catalog-mode milestone is described below.

# Movie Match — first recommendation milestone

Movie Match is available at `/recommendations`, linked from the main navigation. This implementation replaces the disabled recommendations page and chat placeholder with a focused, catalog-backed conversation.

## Supported experience

- Search exact catalog titles and choose favourites; five is a useful starting point, not a requirement.
- Ask for genres, supported languages, and maximum runtime: `English science fiction under two hours`.
- Refine a request: `No horror`, `Comedy instead`, `Any language`, `No runtime limit`.
- Ask `something like Inception` using an exact, unambiguous released catalog title. Use the picker for remakes or spelling differences.
- Inspect the applied filters, edit them directly, and request another shortlist.
- Ask `show more` to exclude recently shown titles. Starting over clears the conversation and filters, while retaining explicitly saved taste.
- Like or dismiss recommendations. Signed-in feedback is stored against the authenticated account; guest feedback exists only while the page is mounted.
- Save recommendations to the existing private watchlist. Signed-in recommendations exclude movies marked watched and movies dismissed by that account.

## How ranking works

The server first restricts candidates to released movies and applies hard genre, language, and runtime filters. Unknown runtime or language never satisfies an active constraint. Included genres/languages use OR semantics; excluded genres remove any matching title.

Among eligible candidates, the strongest genre Jaccard similarity to a favourite ranks first. Stored TMDB popularity breaks ties, then the movie ID makes ordering reproducible. Explanations are generated from those exact facts. A dislike excludes that movie; it does not infer that every movie in its genre is disliked. With no favourites, popularity provides a transparent cold-start baseline.

This is `catalog-rules-v1`: a deterministic, content-based recommender with a focused language parser. It makes no model calls, has no API-key requirement, and does not claim general-purpose reasoning, learned embeddings, calibrated probabilities, or measured recommendation quality. Unsupported requests ask for clarification. The UI states its scope. Conversations are not persisted on the server.

## Boundaries and security

`POST /api/assistant/chat` accepts a maximum 500-character message, validated filters, at most 20 guest/reference favourites and 100 exclusions, and returns at most six real catalog titles. Signed-in chat obtains identity from the existing opaque session and verifies origin/CSRF. Feedback read/write endpoints never accept an account ID. All assistant responses are private/no-store. Existing API rate limiting remains in effect.

Migration `20260913_0005` introduces `movie_feedback` with account/movie ownership and cascading foreign keys. The development database and local Docker catalog are backed up before migration. Core dependencies are unchanged.

The current retrieval path scans released catalog rows. It is suitable for the current catalog, but not a claim of large-scale performance. Guest favourites used for ranking are bounded to the latest 20; account feedback is persisted. Recent-result exclusion is bounded, so extremely long chats can eventually repeat older picks.

Runtime and language coverage depend on actual imported provider data. Future full TMDB imports retain runtime and original language; OMDb imports retain reported languages. Existing missing fields are not fabricated. Streaming availability is not verified.

## Next development steps

1. Collect representative recommendation queries and user judgments; measure retrieval coverage and failure cases.
2. Integrate a configured language model for structured preference extraction, validate its output, and retain deterministic catalog retrieval and grounded explanations. No model integration is included in this milestone.
3. Compare the current baseline with a hybrid recommender using a separately licensed dataset and held-out evaluation. Automated fixture tests demonstrate correctness, not recommendation quality.
4. Build Movie Night rooms once the individual discovery flow is useful.

The wider deployment/account recovery work remains tracked in RELEASE_VERIFICATION.md.

## Verification for this milestone

- 44 backend tests pass: constraints, negation, multi-turn filter retention, exact title references with runtime limits, missing metadata, account isolation, CSRF, watched/disliked exclusions and search without analytics.
- 10 browser tests pass, including four new Movie Match flows and the existing six release checks.
- Frontend lint has zero errors and three existing image-optimization warnings; type checking and the Docker production build pass.
- Fresh migration to `20260913_0005` and development/container schema checks pass. The local Docker database passes integrity/foreign-key checks; its 1,369 movie rows retain the pre-migration content hash.
- Live Chromium smoke against localhost:3020 returns six catalog recommendations with no page errors or mobile horizontal overflow. Screenshots are in `docs/screenshots/movie-match-desktop.png` and `movie-match-mobile.png`.
- The live catalog contains 1,360 released movies, with zero runtime/language coverage at this point. The UI reports coverage; those filters need real provider enrichment before they can return matches locally.

Evidence is stored in `docs/verification/assistant-*`. These are local checks; no remote CI run, hosted deployment, recommendation-quality benchmark, or external interpretation integration is claimed.
