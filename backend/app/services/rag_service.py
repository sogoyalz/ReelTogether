from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.movie import Movie
from app.repositories import movies as movie_repository
from app.services.catalog_enrichment import get_enrichment

CHROMA_PATH = Path(__file__).resolve().parents[2] / "chroma_db"
COLLECTION_NAME = "movie_pulse_catalog"
OPENAI_CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_embedder = None
_chroma_client = None
_collection = None


def initialize_rag_catalog(db: Session) -> dict[str, int | str]:
    collection = _get_collection()
    movies = movie_repository.list_movies(db)
    movie_ids = [movie.id for movie in movies]
    refreshed = refresh_embeddings(db, movie_ids)
    return {
        "collection": COLLECTION_NAME,
        "movies_seen": len(movies),
        "movies_embedded": refreshed,
    }


def refresh_embeddings(db: Session, movie_ids: list[int]) -> int:
    if not movie_ids:
        return 0

    collection = _get_collection()
    refreshed = 0

    for movie_id in movie_ids:
        movie = movie_repository.get_movie_by_id(db, movie_id)
        if movie is None:
            continue

        payload = _movie_payload(movie)
        document = payload["document"]
        metadata = payload["metadata"]
        existing = collection.get(ids=[str(movie.id)], include=["metadatas"])
        existing_signature = None
        if existing.get("metadatas"):
            existing_signature = existing["metadatas"][0].get("signature")
        if existing_signature == metadata["signature"]:
            continue

        embedding = _embed_texts([document])[0]
        collection.upsert(
            ids=[str(movie.id)],
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        refreshed += 1

    return refreshed


def retrieve_relevant_movies(db: Session, query: str, top_k: int = 5) -> list[dict]:
    try:
        collection = _get_collection()
        query_embedding = _embed_texts([query])[0]
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
    except ModuleNotFoundError:
        return _fallback_retrieve_relevant_movies(db, query, top_k=top_k)

    matches: list[dict] = []
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for movie_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
        movie = movie_repository.get_movie_by_id(db, int(movie_id))
        if movie is None:
            continue
        matches.append(
            {
                "movie": movie,
                "document": document,
                "metadata": metadata,
                "distance": float(distance),
            }
        )
    return matches


def get_movie_embedding(movie_id: int) -> list[float] | None:
    try:
        collection = _get_collection()
    except ModuleNotFoundError:
        return None
    result = collection.get(ids=[str(movie_id)], include=["embeddings"])
    embeddings = result.get("embeddings")
    if embeddings is None or len(embeddings) == 0:
        return None
    return embeddings[0]


def query_movies_by_embedding(
    db: Session,
    embedding: list[float],
    *,
    top_k: int = 10,
    exclude_movie_ids: set[int] | None = None,
) -> list[dict]:
    try:
        collection = _get_collection()
    except ModuleNotFoundError:
        return []
    result = collection.query(
        query_embeddings=[embedding],
        n_results=max(top_k + len(exclude_movie_ids or set()), top_k),
        include=["documents", "metadatas", "distances"],
    )

    matches: list[dict] = []
    excluded = exclude_movie_ids or set()
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for movie_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
        numeric_movie_id = int(movie_id)
        if numeric_movie_id in excluded:
            continue
        movie = movie_repository.get_movie_by_id(db, numeric_movie_id)
        if movie is None:
            continue
        matches.append(
            {
                "movie": movie,
                "document": document,
                "metadata": metadata,
                "distance": float(distance),
            }
        )
        if len(matches) >= top_k:
            break

    return matches


def answer_catalog_chat(
    db: Session,
    *,
    message: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    matches = retrieve_relevant_movies(db, message, top_k=5)
    if not matches:
        return {
            "reply": "I don't know from the current movie catalog context.",
            "sources": [],
        }

    context = "\n\n".join(
        f"[{index + 1}] {item['document']}"
        for index, item in enumerate(matches)
    )
    system_prompt = (
        "You are a movie research assistant for ReelTogether. "
        "Answer only using the provided movie catalog context. "
        "If the answer is not in the context, say you don't know."
    )
    provider_reply = _call_chat_provider(
        system_prompt=system_prompt,
        context=context,
        message=message,
        history=history or [],
    )
    if provider_reply is None:
        provider_reply = _fallback_reply(message, matches)

    return {
        "reply": provider_reply,
        "sources": [item["movie"].title for item in matches],
    }


def _movie_payload(movie: Movie) -> dict[str, object]:
    enrichment = get_enrichment(movie)
    directors = ", ".join(enrichment.get("directors", []))
    genres = ", ".join(movie.genres)
    document = (
        f"Title: {movie.title}\n"
        f"Overview: {movie.overview or 'No overview available.'}\n"
        f"Genres: {genres or 'Unknown'}\n"
        f"Director: {directors or 'Unknown'}\n"
        f"Release Date: {movie.release_date.isoformat()}\n"
        f"Status: {movie.status}"
    )
    signature = "|".join(
        [
            movie.title,
            movie.overview or "",
            genres,
            directors,
            movie.release_date.isoformat(),
            movie.status,
        ]
    )
    return {
        "document": document,
        "metadata": {
            "movie_id": movie.id,
            "slug": movie.slug,
            "title": movie.title,
            "signature": signature,
        },
    }


def _fallback_retrieve_relevant_movies(db: Session, query: str, top_k: int = 5) -> list[dict]:
    matches: list[dict] = []
    for movie in movie_repository.search_movies(db, query)[:top_k]:
        payload = _movie_payload(movie)
        matches.append(
            {
                "movie": movie,
                "document": payload["document"],
                "metadata": payload["metadata"],
                "distance": 1.0,
            }
        )
    return matches


def _get_collection():
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    import chromadb

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    _collection = _chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "ReelTogether movie catalog embeddings"},
    )
    return _collection


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedder


def _embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_embedder()
    return model.encode(texts, normalize_embeddings=True).tolist()


def _call_chat_provider(
    *,
    system_prompt: str,
    context: str,
    message: str,
    history: list[dict[str, str]],
) -> str | None:
    prompt = f"{system_prompt}\n\nCatalog context:\n{context}\n\nUser question: {message}"

    if settings.AI_CHAT_PROVIDER.lower() == "anthropic" and settings.anthropic_api_configured:
        return _anthropic_chat(system_prompt, prompt, history)

    if settings.openai_api_configured:
        return _openai_chat(system_prompt, prompt, history)

    return None


def _openai_chat(system_prompt: str, prompt: str, history: list[dict[str, str]]) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": item["role"], "content": item["content"]}
        for item in history[-8:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    )
    messages.append({"role": "user", "content": prompt})
    payload = json.dumps({
        "model": settings.OPENAI_CHAT_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }).encode("utf-8")
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
        raise RuntimeError(f"External chat request failed: {exc}") from exc
    return body["choices"][0]["message"]["content"].strip()


def _anthropic_chat(system_prompt: str, prompt: str, history: list[dict[str, str]]) -> str:
    messages = [
        {"role": item["role"], "content": item["content"]}
        for item in history[-8:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]
    messages.append({"role": "user", "content": prompt})
    payload = json.dumps({
        "model": settings.ANTHROPIC_CHAT_MODEL,
        "max_tokens": 700,
        "temperature": 0.2,
        "system": system_prompt,
        "messages": messages,
    }).encode("utf-8")
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
        raise RuntimeError(f"External chat request failed: {exc}") from exc
    return "".join(block.get("text", "") for block in body.get("content", [])).strip()


def _fallback_reply(message: str, matches: list[dict]) -> str:
    lines = [f"I could not use the external interpretation service, so here are the closest catalog matches for: {message}"]
    for item in matches:
        movie = item["movie"]
        lines.append(f"- {movie.title} ({movie.release_date.year})")
    return "\n".join(lines)
