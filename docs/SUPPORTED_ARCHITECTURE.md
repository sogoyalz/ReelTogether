# Current architecture and supported scope

Next.js renders the discovery, watchlist, account and group-planning UI. Its same-origin API proxy forwards only allowed headers and signs browser/verified-peer identities. FastAPI owns authentication, authorization, room transitions and response contracts. SQLAlchemy/Alembic own the persisted catalog, user data and maintenance queue. Provider ingestion is performed by the fenced worker, never by public detail reads. Source labels distinguish stored observations, modeled values, demo data and missing evidence.

For the default release, retain these core capabilities: stored catalog browsing/search, Movie Match rules, account-owned feedback and watchlists, and private 2–8-person movie-night voting. Room polling checks a small private revision first and fetches full detail only on change. Catalog recommendations/shortlists stream projected rows and retain only the best six/eight candidates; they still scan eligible records, so CPU remains proportional to catalog size.

| Surface | Decision |
|---|---|
| Catalog rules, private rooms, accounts, stored public insights | Supported; covered by core regressions |
| Legacy `RatingWidget` and ratings/recommendation API | Retain as experimental compatibility code; no active UI caller; API unavailable in production |
| `semantic_search`, RAG retrieval and embedding/training utilities | Retain as experiments, dependencies isolated; `ENABLE_RAG` must remain false in the default production profile |
| Natural-language model interpretation | Optional experiment, default off; needs credential/budget and live behavior verification before activation |
| Revenue model artifacts | Research/demo material; not a validated public revenue forecast |
| Wikipedia/Wikidata context | Inactive on public reads; Wikidata requires canonical stored identity plus a matching IMDb claim |
| Historical milestone reports and earlier operations screenshots | Historical evidence, not current deployment proof |

No stored tables or user data were removed to prune experimental scope. The public README and current production guide describe the release candidate. Source files that remain large or the layered CSS cascade are maintainability follow-ups; they do not substitute for the release gates in the production guide. No new state-management or vector infrastructure was introduced.
