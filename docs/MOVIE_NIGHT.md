# Movie Night rooms

A shared decision flow for 2–8 signed-in users: create a room, invite friends, save personal preferences, vote privately on up to eight films, reveal aggregate matches, and select a winner.

## Rules

- Rooms and invitations expire after 24 hours. An invite has 256 bits of randomness; only its SHA-256 hash is stored. Share links place the token in a URL fragment, not in server request paths or query strings. The host can replace a lost invitation while the lobby is open; this invalidates old links without removing existing members.
- Only members can read a room. Each person sees their own preferences and ballot. Others see names and ballot-completion status, but no choices before reveal.
- Preferences accept up to five known genres and five released favourites. The candidate score combines the minimum and mean Jaccard genre similarity across nonempty member profiles, with stored popularity and movie ID as deterministic tie-breakers. Favourite films are excluded. Empty profiles add no constraints. This is a transparent heuristic, not a trained recommendation model.
- Starting requires at least two members and three eligible films. It freezes preferences, membership and the shortlist. Late invitations are explicitly rejected after voting begins. Existing members can reopen their room.
- Yes counts as approval, Pass is neutral, and any Veto excludes a film. Every member must vote on every candidate before the host can reveal. Votes can change during voting only.
- Reveal exposes aggregate counts only. Highest approval among non-vetoed films wins; equal counts remain tied. The host may choose any tied top match. If every film is vetoed, there is no winner; create a new room. A selected winner is immutable.
- Saving the winner uses the existing personal watchlist control. Selection never writes to other members' watchlists.

## Implementation

Routes: `/movie-night` and `/api/movie-nights`. The header and Movie Match page link to the feature. Room updates poll every three seconds while active, stopping for expiration, selection or query errors. This is polling, not a WebSocket transport.

SQLAlchemy models and Alembic revision `20260914_0007` persist rooms, memberships and votes. Room-row writes serialize transitions against joins/votes/selection. A file-backed SQLite concurrent test verifies competing selections produce one success and one conflict. Create operations lock the account row and cap each host at ten unexpired rooms. Every mutation uses existing session/CSRF/origin protections; room responses are private/no-store.

## Verification

- 79 backend tests passed, including five room tests for membership, CSRF, rotation, expiry, late joins, private preferences/ballots, incomplete ballots, ties, vetoes, immutable winners, optional watchlists and concurrent selection.
- All 14 Playwright tests passed. The new two-context test creates an invitation, joins with a separate account, casts both complete ballots, reveals/selects a winner, checks the guest watchlist remains empty, and checks the winning screen at 390px.
- Frontend lint/typecheck passed (three existing image warnings). Migration check reports no missing schema operations.
- Evidence: `docs/verification/movie-night-*`.

Public invitations require an accessible deployed origin. A localhost link works only against the local app. The test workload does not certify large-room scale or production capacity. Rooms currently have no kick/leave/reopen operation; inactive participants can block a round until expiry, so the host should start a new room if the group changes after voting begins.
