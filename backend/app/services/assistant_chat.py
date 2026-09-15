from datetime import date
import re
from sqlalchemy import select
from app.models.movie import Movie
from app.schemas.assistant import Filters
from app.services.assistant_ai import AssistantAIUnavailable, extract_preferences
from app.services.catalog_assistant import recommend


def clarification(payload, reply, mode="ai-preferences-v1"):
    return {"reply": reply, "filters": payload.filters, "items": [], "total_matches": 0, "mode": mode, "needs_clarification": True}


def answer_chat(db, payload, liked=(), disliked=(), watched=()):
    if not payload.use_ai:
        return recommend(db, payload, liked, disliked, watched)
    try:
        intent = extract_preferences(payload)
    except AssistantAIUnavailable as exc:
        reply = "Request interpretation is temporarily unavailable. Your filters are unchanged. Retry later or turn off request interpretation to use catalog mode."
        if str(exc) == "not_configured":
            reply = "Request interpretation has not been configured. Turn off request interpretation to continue with catalog mode."
        return clarification(payload, reply, "ai-unavailable")
    if intent.action == "clarify" or intent.reason != "none":
        replies = {
            "unsupported": "I can filter by genre, language and runtime, or use named favourites. Your request includes a constraint I cannot verify. Please simplify it; I haven't changed your filters.",
            "off_topic": "I can help you choose a movie. Tell me what you enjoy or what you're in the mood for.",
            "ambiguous": "Please name the movie or describe the genre and time limit you want so I can narrow the search.",
        }
        return clarification(payload, replies.get(intent.reason, replies["ambiguous"]))
    references = []
    if intent.reference_titles:
        movies = list(db.scalars(select(Movie).where(Movie.release_date <= date.today())))
        for title in intent.reference_titles:
            if not re.search(r"(?<!\w)" + re.escape(title.strip()) + r"(?!\w)", payload.message, re.I):
                return clarification(payload, "Please name the reference movie explicitly or choose it in Favourite movies.")
            matches = [m for m in movies if m.title.casefold() == title.strip().casefold()]
            if len(matches) != 1:
                return clarification(payload, "I couldn't resolve that title to one released catalog movie. Select it in Favourite movies, then try again.")
            references.append(matches[0].id)
    normalized = payload.model_copy(update={
        "message": "recommend",
        "filters": Filters() if intent.action == "reset" else intent.filters,
        "favorite_ids": [] if intent.action == "reset" else list(dict.fromkeys(payload.favorite_ids + references))[-20:],
        "excluded_ids": list(set(payload.excluded_ids) | (set(payload.seen_ids) if intent.action == "more" else set())),
    })
    result = recommend(db, normalized, liked, disliked, watched)
    result.update(mode="ai-preferences-v1", action=intent.action)
    result["reply"] = "I interpreted your request; review the applied filters. " + result["reply"]
    return result
