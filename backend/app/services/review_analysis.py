from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from app.models.ai import MovieDiscussion
from app.models.movie import Movie

AUDIENCE_SOURCES = {"reddit", "youtube", "audience", "social"}
CRITIC_SOURCES = {"critic", "press", "review"}

POSITIVE_TERMS = {
    "amazing", "authentic", "beautiful", "best", "bold", "brilliant", "compelling",
    "excellent", "fun", "great", "heart", "hype", "impressive", "inventive",
    "love", "memorable", "moving", "powerful", "smart", "strong", "stunning",
}
NEGATIVE_TERMS = {
    "bad", "bland", "boring", "cheap", "confusing", "disappointing", "flat", "mess",
    "mid", "predictable", "rough", "slow", "thin", "underwritten", "uneven",
    "weak", "worse", "worst",
}

THEME_KEYWORDS: dict[str, set[str]] = {
    "story": {"story", "script", "plot", "writing", "narrative", "ending"},
    "cast": {"cast", "actor", "actors", "performance", "performances", "chemistry"},
    "direction": {"director", "direction", "vision", "filmmaking"},
    "visuals": {"visuals", "vfx", "cinematography", "shot", "shots", "image", "spectacle", "cgi"},
    "soundtrack": {"music", "score", "soundtrack", "sound"},
    "franchise": {"franchise", "sequel", "universe", "brand", "legacy", "fans"},
    "pacing": {"pace", "pacing", "runtime", "slow", "long"},
    "emotion": {"emotional", "emotion", "heart", "moving", "feels"},
    "humor": {"funny", "jokes", "humor", "laughs"},
    "action": {"action", "fight", "set pieces", "battle", "sequence"},
    "trailer": {"trailer", "teaser", "promo", "marketing"},
    "awards": {"oscar", "awards", "prestige", "acclaim"},
}


@dataclass
class PerspectiveSummary:
    label: str
    item_count: int
    sentiment_score: float
    summary: str
    top_themes: list[str]
    positive_drivers: list[str]
    negative_drivers: list[str]
    highlighted_quotes: list[str]


def analyze_review_landscape(
    movie: Movie,
    discussions: list[MovieDiscussion],
    enrichment: dict,
    omdb: dict[str, str | None],
) -> dict:
    audience_items = [item for item in discussions if item.source in AUDIENCE_SOURCES]
    critic_items = [item for item in discussions if item.source in CRITIC_SOURCES]

    audience = _summarize_perspective(
        label="Audience",
        items=audience_items,
        movie=movie,
        enrichment=enrichment,
        omdb=omdb,
    )
    critics = _summarize_perspective(
        label="Critics",
        items=critic_items,
        movie=movie,
        enrichment=enrichment,
        omdb=omdb,
    )

    consensus_themes = [theme for theme in audience.top_themes if theme in critics.top_themes][:4]
    divergence_themes = [
        *[theme for theme in critics.top_themes if theme not in audience.top_themes][:2],
        *[theme for theme in audience.top_themes if theme not in critics.top_themes][:2],
    ]
    alignment_score = round(max(0.0, 1 - abs(critics.sentiment_score - audience.sentiment_score)), 2)

    theme_signals = []
    for theme in _merge_preserving_order(critics.top_themes + audience.top_themes):
        critic_score = _theme_presence(theme, critic_items)
        audience_score = _theme_presence(theme, audience_items)
        theme_signals.append(
            {
                "theme": theme,
                "critic_weight": critic_score,
                "audience_weight": audience_score,
                "gap": round(abs(critic_score - audience_score), 2),
            }
        )

    return {
        "audience": audience,
        "critics": critics,
        "consensus_themes": consensus_themes,
        "divergence_themes": divergence_themes,
        "alignment_score": alignment_score,
        "theme_signals": theme_signals[:6],
    }


def sentiment_counts_from_discussions(discussions: list[MovieDiscussion]) -> dict[str, int]:
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for discussion in discussions:
        counts[_discussion_sentiment(discussion)] += 1
    return counts


def extract_top_themes(discussions: list[MovieDiscussion], fallback: list[str], limit: int = 5) -> list[str]:
    theme_counter = Counter()
    for discussion in discussions:
        theme_counter.update(_extract_themes(f"{discussion.title} {discussion.body}"))
    if not theme_counter:
        return fallback[:limit]
    merged = [theme for theme, _ in theme_counter.most_common(limit)] + fallback
    return _merge_preserving_order(merged)[:limit]


def _summarize_perspective(
    *,
    label: str,
    items: list[MovieDiscussion],
    movie: Movie,
    enrichment: dict,
    omdb: dict[str, str | None],
) -> PerspectiveSummary:
    fallback_themes = [
        *movie.genres[:2],
        *(enrichment.get("studios", [])[:1]),
        *( [enrichment["franchise"]] if enrichment.get("franchise") else []),
    ]
    themes = extract_top_themes(items, fallback_themes, limit=4)
    if not items:
        summary = _fallback_summary(label, movie, themes, omdb)
        return PerspectiveSummary(
            label=label,
            item_count=0,
            sentiment_score=0.0,
            summary=summary,
            top_themes=themes,
            positive_drivers=[],
            negative_drivers=[],
            highlighted_quotes=[],
        )

    counts = sentiment_counts_from_discussions(items)
    total = sum(counts.values()) or 1
    sentiment_score = round((counts["positive"] - counts["negative"]) / total, 2)
    positive_drivers = _top_reasons(items, target_sentiment="positive", fallback=themes)
    negative_drivers = _top_reasons(items, target_sentiment="negative", fallback=themes)
    summary = _build_summary(
        label=label,
        movie=movie,
        sentiment_score=sentiment_score,
        themes=themes,
        counts=counts,
        omdb=omdb,
    )
    highlighted_quotes = [item.body[:180].strip() for item in items[:3]]
    return PerspectiveSummary(
        label=label,
        item_count=len(items),
        sentiment_score=sentiment_score,
        summary=summary,
        top_themes=themes,
        positive_drivers=positive_drivers,
        negative_drivers=negative_drivers,
        highlighted_quotes=highlighted_quotes,
    )


def _build_summary(
    *,
    label: str,
    movie: Movie,
    sentiment_score: float,
    themes: list[str],
    counts: dict[str, int],
    omdb: dict[str, str | None],
) -> str:
    tone = "mixed"
    if sentiment_score >= 0.35:
        tone = "mostly positive"
    elif sentiment_score <= -0.2:
        tone = "skeptical"

    subject = "reviewers" if label == "Critics" else "audiences"
    extra = ""
    if label == "Critics" and (omdb.get("imdb_rating") or omdb.get("rotten_tomatoes")):
        extra = f" Ratings context sits around IMDb {omdb.get('imdb_rating') or 'n/a'} and Rotten Tomatoes {omdb.get('rotten_tomatoes') or 'n/a'}."

    return (
        f"{label} are currently {tone} on {movie.title}. "
        f"{subject.capitalize()} are focusing most on {', '.join(themes) if themes else 'overall movie quality'}, "
        f"with {counts['positive']} positive, {counts['neutral']} neutral, and {counts['negative']} negative takes captured.{extra}"
    )


def _fallback_summary(label: str, movie: Movie, themes: list[str], omdb: dict[str, str | None]) -> str:
    if label == "Critics":
        return (
            f"Direct critic review coverage is still thin for {movie.title}. "
            f"Until more press reactions are ingested, the best signals are {', '.join(themes) if themes else 'genre and release context'} "
            f"plus ratings like IMDb {omdb.get('imdb_rating') or 'n/a'} and Rotten Tomatoes {omdb.get('rotten_tomatoes') or 'n/a'}."
        )
    return (
        f"Audience discussion for {movie.title} is still limited. "
        f"Current signal is being inferred mostly from {', '.join(themes) if themes else 'general movie buzz'}."
    )


def _top_reasons(items: list[MovieDiscussion], target_sentiment: str, fallback: list[str]) -> list[str]:
    counter = Counter()
    for item in items:
        if _discussion_sentiment(item) != target_sentiment:
            continue
        counter.update(_extract_themes(f"{item.title} {item.body}"))
    if not counter:
        return fallback[:3]
    return [theme for theme, _ in counter.most_common(3)]


def _extract_themes(text: str) -> list[str]:
    lowered = text.lower()
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            themes.append(theme)
    return themes


def _theme_presence(theme: str, items: list[MovieDiscussion]) -> float:
    if not items:
        return 0.0
    hits = 0
    for item in items:
        if theme in _extract_themes(f"{item.title} {item.body}"):
            hits += 1
    return round(hits / len(items), 2)


def _discussion_sentiment(discussion: MovieDiscussion) -> str:
    payload = {}
    if discussion.raw_payload:
        try:
            payload = json.loads(discussion.raw_payload)
        except json.JSONDecodeError:
            payload = {}
    sentiment = payload.get("sentiment")
    if sentiment in {"positive", "neutral", "negative"}:
        return sentiment

    text = re.sub(r"[^a-z0-9\s]", " ", discussion.body.lower())
    words = [word for word in text.split() if word]
    positive_hits = sum(word in POSITIVE_TERMS for word in words)
    negative_hits = sum(word in NEGATIVE_TERMS for word in words)

    if discussion.source in CRITIC_SOURCES:
        positive_hits += sum(token in text for token in ("acclaim", "craft", "layered", "precision"))
        negative_hits += sum(token in text for token in ("derivative", "hollow", "overlong", "uneven"))

    score = positive_hits - negative_hits
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def _merge_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        merged.append(value)
    return merged
