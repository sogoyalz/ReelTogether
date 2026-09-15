from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.movie import Movie
from app.models.ratings import UserRating
from app.repositories import movies as movie_repository
from app.services.catalog_enrichment import get_enrichment
from app.services.omdb import fetch_movie_metadata
from app.services.rag_service import get_movie_embedding, query_movies_by_embedding

OPENAI_CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"


def save_user_rating(db: Session, *, session_id: str, movie_id: int, rating: float) -> UserRating:
    existing = db.scalar(
        select(UserRating).where(
            UserRating.session_id == session_id,
            UserRating.movie_id == movie_id,
        )
    )
    if existing is None:
        existing = UserRating(session_id=session_id, movie_id=movie_id, rating=rating)
        db.add(existing)
    else:
        existing.rating = rating

    db.commit()
    db.refresh(existing)
    return existing


def list_user_ratings(db: Session, session_id: str) -> list[UserRating]:
    statement = (
        select(UserRating)
        .where(UserRating.session_id == session_id)
        .order_by(UserRating.created_at.desc(), UserRating.id.desc())
    )
    return list(db.scalars(statement).all())


def delete_user_rating(db: Session, session_id: str, movie_id: int) -> bool:
    existing = db.scalar(
        select(UserRating).where(
            UserRating.session_id == session_id,
            UserRating.movie_id == movie_id,
        )
    )
    if existing is None:
        return False

    db.execute(
        delete(UserRating).where(
            UserRating.session_id == session_id,
            UserRating.movie_id == movie_id,
        )
    )
    db.commit()
    return True


def get_recommendations(session: Session, session_id: str, top_n: int = 10) -> tuple[list[dict], list[dict]]:
    ratings = list_user_ratings(session, session_id)
    if not ratings:
        return [], []

    rated_movies: list[dict] = []
    weighted_vector: list[float] | None = None
    total_weight = 0.0
    rated_movie_ids: set[int] = set()

    for entry in ratings:
        movie = movie_repository.get_movie_by_id(session, entry.movie_id)
        embedding = get_movie_embedding(entry.movie_id)
        if movie is None or embedding is None:
            continue

        weight = _rating_weight(entry.rating)
        if weight == 0:
            continue

        rated_movies.append({"movie": movie, "rating": entry.rating})
        rated_movie_ids.add(movie.id)
        magnitude = abs(weight)
        if weighted_vector is None:
            weighted_vector = [value * weight for value in embedding]
        else:
            weighted_vector = [
                current + (value * weight)
                for current, value in zip(weighted_vector, embedding, strict=False)
            ]
        total_weight += magnitude

    if weighted_vector is None or total_weight == 0:
        return [], rated_movies

    query_embedding = [value / total_weight for value in weighted_vector]
    candidates = query_movies_by_embedding(
        session,
        query_embedding,
        top_k=max(top_n * 3, top_n),
        exclude_movie_ids=rated_movie_ids,
    )

    reranked: list[dict] = []
    for candidate in candidates:
        movie = candidate["movie"]
        imdb_rating = _safe_float(_imdb_rating(movie))
        similarity_score = max(0.0, 1.0 - min(float(candidate["distance"]), 1.0))
        blended_score = (similarity_score * 0.7) + ((imdb_rating / 10.0) * 0.3)
        reranked.append(
            {
                "movie": movie,
                "similarity_score": round(blended_score, 4),
                "raw_similarity_score": round(similarity_score, 4),
            }
        )

    reranked.sort(
        key=lambda item: (
            item["similarity_score"],
            item["movie"].tmdb_popularity,
            item["movie"].title,
        ),
        reverse=True,
    )
    return reranked[:top_n], rated_movies


def explain_recommendations(
    session_id: str,
    recommended_movies: list[dict],
    rated_movies: list[dict],
) -> list[dict]:
    if not recommended_movies:
        return []

    liked = [item for item in rated_movies if item["rating"] >= 4]
    disliked = [item for item in rated_movies if item["rating"] <= 2]
    provider_output = _call_explanation_provider(session_id, recommended_movies, liked, disliked)
    if provider_output:
        return provider_output

    return [
        {
            "movie_id": item["movie"].id,
            "explanation": _fallback_explanation(item["movie"], liked, disliked),
        }
        for item in recommended_movies
    ]


def _rating_weight(rating: float) -> float:
    if rating >= 4:
        return rating - 3.0
    if rating <= 2:
        return -(3.0 - rating)
    return 0.25


def _imdb_rating(movie: Movie) -> str | None:
    omdb = fetch_movie_metadata(movie) or {}
    return omdb.get("imdb_rating")


def _safe_float(value: str | None) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _call_explanation_provider(
    session_id: str,
    recommended_movies: list[dict],
    liked_movies: list[dict],
    disliked_movies: list[dict],
) -> list[dict] | None:
    prompt = _build_explanation_prompt(session_id, recommended_movies, liked_movies, disliked_movies)
    try:
        if settings.AI_CHAT_PROVIDER.lower() == "anthropic" and settings.anthropic_api_configured:
            content = _anthropic_completion(prompt)
        elif settings.openai_api_configured:
            content = _openai_completion(prompt)
        else:
            return None
    except RuntimeError:
        return None

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, list):
        return None

    explanations: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        movie_id = item.get("movie_id")
        explanation = item.get("explanation")
        if isinstance(movie_id, int) and isinstance(explanation, str) and explanation.strip():
            explanations.append({"movie_id": movie_id, "explanation": explanation.strip()})
    return explanations or None


def _build_explanation_prompt(
    session_id: str,
    recommended_movies: list[dict],
    liked_movies: list[dict],
    disliked_movies: list[dict],
) -> str:
    liked_text = ", ".join(
        f"{item['movie'].title} ({item['rating']:.1f}/5)"
        for item in liked_movies
    ) or "None"
    disliked_text = ", ".join(
        f"{item['movie'].title} ({item['rating']:.1f}/5)"
        for item in disliked_movies
    ) or "None"
    recommended_text = "\n".join(
        f"- movie_id={item['movie'].id}; title={item['movie'].title}; genres={', '.join(item['movie'].genres)}; "
        f"director={', '.join(get_enrichment(item['movie']).get('directors', [])) or 'Unknown'}"
        for item in recommended_movies
    )
    return (
        "You are generating ReelTogether recommendation explanations.\n"
        f"Session: {session_id}\n"
        f"The user liked: {liked_text}\n"
        f"The user disliked: {disliked_text}\n"
        "Explain in 1 friendly sentence why each recommendation fits the user.\n"
        "Return only valid JSON as a list of objects with keys movie_id and explanation.\n"
        f"Recommendations:\n{recommended_text}"
    )


def _openai_completion(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": settings.OPENAI_CHAT_MODEL,
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        }
    ).encode("utf-8")
    request = Request(
        OPENAI_CHAT_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"External recommendation explanation request failed: {exc}") from exc
    return body["choices"][0]["message"]["content"].strip()


def _anthropic_completion(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": settings.ANTHROPIC_CHAT_MODEL,
            "max_tokens": 800,
            "temperature": 0.4,
            "system": "Return only valid JSON.",
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    request = Request(
        ANTHROPIC_MESSAGES_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"External recommendation explanation request failed: {exc}") from exc
    return "".join(block.get("text", "") for block in body.get("content", [])).strip()


def _fallback_explanation(movie: Movie, liked_movies: list[dict], disliked_movies: list[dict]) -> str:
    liked_genres = {genre for item in liked_movies for genre in item["movie"].genres}
    disliked_genres = {genre for item in disliked_movies for genre in item["movie"].genres}
    overlap = [genre for genre in movie.genres if genre in liked_genres and genre not in disliked_genres]
    if overlap:
        return f"It lines up with your higher-rated picks through {', '.join(overlap[:2])} and a similar overall tone."
    if movie.genres:
        return f"It stays close to the genres you respond to best, especially {', '.join(movie.genres[:2])}."
    return "It matches the overall embedding pattern of the movies you rated more highly."
