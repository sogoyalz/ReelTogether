from __future__ import annotations

from datetime import date, datetime, timedelta

from app.models.movie import Movie, MovieAnalytics
from app.services.tmdb import get_tmdb_movie_enrichment


CATALOG_ENRICHMENTS: dict[str, dict] = {
    "oppenheimer": {
        "franchise": "Awards Contenders",
        "studios": ["Universal Pictures", "Syncopy"],
        "streaming_on": ["Peacock", "Prime Video"],
        "cast": ["Cillian Murphy", "Emily Blunt", "Robert Downey Jr."],
        "directors": ["Christopher Nolan"],
        "writers": ["Christopher Nolan"],
        "trailer_embed_url": "https://www.youtube.com/embed/uYPbbksJxIg",
        "box_office_history": [
            {"label": "Opening", "value_usd": 82400000},
            {"label": "Week 2", "value_usd": 174500000},
            {"label": "Week 4", "value_usd": 264300000},
            {"label": "Domestic Final", "value_usd": 330100000},
        ],
    },
    "barbie": {
        "franchise": "Barbie",
        "studios": ["Warner Bros.", "Mattel Films"],
        "streaming_on": ["Max", "Prime Video"],
        "cast": ["Margot Robbie", "Ryan Gosling", "America Ferrera"],
        "directors": ["Greta Gerwig"],
        "writers": ["Greta Gerwig", "Noah Baumbach"],
        "trailer_embed_url": "https://www.youtube.com/embed/pBk4NYhWNMM",
        "box_office_history": [
            {"label": "Opening", "value_usd": 162000000},
            {"label": "Week 2", "value_usd": 351400000},
            {"label": "Week 4", "value_usd": 526100000},
            {"label": "Domestic Final", "value_usd": 636200000},
        ],
    },
    "spider-man-no-way-home": {
        "franchise": "Spider-Man",
        "studios": ["Sony Pictures", "Marvel Studios"],
        "streaming_on": ["Netflix", "Prime Video"],
        "cast": ["Tom Holland", "Zendaya", "Benedict Cumberbatch"],
        "directors": ["Jon Watts"],
        "writers": ["Chris McKenna", "Erik Sommers"],
        "trailer_embed_url": "https://www.youtube.com/embed/JfVOs4VSpmA",
        "box_office_history": [
            {"label": "Opening", "value_usd": 260100000},
            {"label": "Week 2", "value_usd": 470300000},
            {"label": "Week 4", "value_usd": 668800000},
            {"label": "Domestic Final", "value_usd": 804800000},
        ],
    },
    "top-gun-maverick": {
        "franchise": "Top Gun",
        "studios": ["Paramount Pictures", "Skydance"],
        "streaming_on": ["Paramount+", "Prime Video"],
        "cast": ["Tom Cruise", "Miles Teller", "Jennifer Connelly"],
        "directors": ["Joseph Kosinski"],
        "writers": ["Ehren Kruger", "Eric Warren Singer"],
        "trailer_embed_url": "https://www.youtube.com/embed/giXco2jaZ_4",
        "box_office_history": [
            {"label": "Opening", "value_usd": 126700000},
            {"label": "Week 2", "value_usd": 291000000},
            {"label": "Week 4", "value_usd": 521700000},
            {"label": "Domestic Final", "value_usd": 718700000},
        ],
    },
    "avatar-the-way-of-water": {
        "franchise": "Avatar",
        "studios": ["20th Century Studios", "Lightstorm"],
        "streaming_on": ["Disney+", "Max"],
        "cast": ["Sam Worthington", "Zoe Saldana", "Sigourney Weaver"],
        "directors": ["James Cameron"],
        "writers": ["James Cameron", "Rick Jaffa", "Amanda Silver"],
        "trailer_embed_url": "https://www.youtube.com/embed/d9MyW72ELq0",
        "box_office_history": [
            {"label": "Opening", "value_usd": 134100000},
            {"label": "Week 2", "value_usd": 420000000},
            {"label": "Week 4", "value_usd": 572200000},
            {"label": "Domestic Final", "value_usd": 684100000},
        ],
    },
    "inside-out-2": {
        "franchise": "Inside Out",
        "studios": ["Pixar", "Disney"],
        "streaming_on": ["Disney+"],
        "cast": ["Amy Poehler", "Maya Hawke", "Ayo Edebiri"],
        "directors": ["Kelsey Mann"],
        "writers": ["Meg LeFauve", "Dave Holstein"],
        "trailer_embed_url": "https://www.youtube.com/embed/LEjhY15eCx0",
        "box_office_history": [
            {"label": "Opening", "value_usd": 154200000},
            {"label": "Week 2", "value_usd": 355600000},
            {"label": "Week 4", "value_usd": 545200000},
            {"label": "Domestic Final", "value_usd": 652900000},
        ],
    },
    "dune-part-two": {
        "franchise": "Dune",
        "studios": ["Warner Bros.", "Legendary"],
        "streaming_on": ["Max", "Prime Video"],
        "cast": ["Timothee Chalamet", "Zendaya", "Rebecca Ferguson"],
        "directors": ["Denis Villeneuve"],
        "writers": ["Denis Villeneuve", "Jon Spaihts"],
        "trailer_embed_url": "https://www.youtube.com/embed/Way9Dexny3w",
        "box_office_history": [
            {"label": "Opening", "value_usd": 118000000},
            {"label": "Week 2", "value_usd": 198400000},
            {"label": "Week 4", "value_usd": 289300000},
            {"label": "Domestic Final", "value_usd": 355000000},
        ],
    },
    "the-batman-part-ii": {
        "franchise": "The Batman",
        "studios": ["Warner Bros.", "DC Studios"],
        "streaming_on": ["Max"],
        "cast": ["Robert Pattinson", "Andy Serkis", "Jeffrey Wright"],
        "directors": ["Matt Reeves"],
        "writers": ["Matt Reeves", "Mattson Tomlin"],
        "trailer_embed_url": "https://www.youtube.com/embed/mqqft2x_Aa4",
        "box_office_history": [
            {"label": "Opening", "value_usd": 132000000},
            {"label": "Week 2", "value_usd": 207000000},
            {"label": "Week 4", "value_usd": 311000000},
            {"label": "Domestic Outlook", "value_usd": 402000000},
        ],
    },
    "avengers-secret-wars": {
        "franchise": "Marvel Cinematic Universe",
        "studios": ["Marvel Studios", "Disney"],
        "streaming_on": ["Disney+"],
        "cast": ["Ensemble Cast", "Legacy Avengers", "Multiverse Guests"],
        "directors": ["TBD"],
        "writers": ["Michael Waldron"],
        "trailer_embed_url": None,
        "box_office_history": [
            {"label": "Forecast", "value_usd": 195000000},
            {"label": "Early Demand", "value_usd": 286000000},
            {"label": "Tentpole Range", "value_usd": 438000000},
            {"label": "Domestic Outlook", "value_usd": 610000000},
        ],
    },
    "guardians-of-the-galaxy-rebirth": {
        "franchise": "Guardians of the Galaxy",
        "studios": ["Marvel Studios", "Disney"],
        "streaming_on": ["Disney+"],
        "cast": ["New Team Ensemble", "Cosmic Team-Up", "Legacy Cameos"],
        "directors": ["TBD"],
        "writers": ["TBD"],
        "trailer_embed_url": None,
        "box_office_history": [
            {"label": "Forecast", "value_usd": 101000000},
            {"label": "Week 2", "value_usd": 154000000},
            {"label": "Week 4", "value_usd": 221000000},
            {"label": "Domestic Outlook", "value_usd": 284000000},
        ],
    },
    "spider-man-new-day": {
        "franchise": "Spider-Man",
        "studios": ["Sony Pictures", "Marvel Studios"],
        "streaming_on": ["Netflix", "Disney+"],
        "cast": ["Tom Holland", "Zendaya", "New Supporting Cast"],
        "directors": ["TBD"],
        "writers": ["TBD"],
        "trailer_embed_url": None,
        "box_office_history": [
            {"label": "Forecast", "value_usd": 171000000},
            {"label": "Week 2", "value_usd": 274000000},
            {"label": "Week 4", "value_usd": 398000000},
            {"label": "Domestic Outlook", "value_usd": 520000000},
        ],
    },
    "inside-out-3": {
        "franchise": "Inside Out",
        "studios": ["Pixar", "Disney"],
        "streaming_on": ["Disney+"],
        "cast": ["Returning Ensemble", "New Emotions", "Family Cast"],
        "directors": ["TBD"],
        "writers": ["TBD"],
        "trailer_embed_url": None,
        "box_office_history": [
            {"label": "Forecast", "value_usd": 94000000},
            {"label": "Week 2", "value_usd": 141000000},
            {"label": "Week 4", "value_usd": 228000000},
            {"label": "Domestic Outlook", "value_usd": 330000000},
        ],
    },
    "superman-legacy": {
        "franchise": "DC Universe",
        "studios": ["DC Studios", "Warner Bros."],
        "streaming_on": ["Max"],
        "cast": ["David Corenswet", "Rachel Brosnahan", "Nicholas Hoult"],
        "directors": ["James Gunn"],
        "writers": ["James Gunn"],
        "trailer_embed_url": None,
        "box_office_history": [
            {"label": "Forecast", "value_usd": 148000000},
            {"label": "Week 2", "value_usd": 228000000},
            {"label": "Week 4", "value_usd": 332000000},
            {"label": "Domestic Outlook", "value_usd": 438000000},
        ],
    },
    "the-fantastic-four-first-steps": {
        "franchise": "Marvel Cinematic Universe",
        "studios": ["Marvel Studios", "Disney"],
        "streaming_on": ["Disney+"],
        "cast": ["Pedro Pascal", "Vanessa Kirby", "Joseph Quinn"],
        "directors": ["Matt Shakman"],
        "writers": ["Josh Friedman", "Eric Pearson"],
        "trailer_embed_url": None,
        "box_office_history": [
            {"label": "Forecast", "value_usd": 176000000},
            {"label": "Week 2", "value_usd": 288000000},
            {"label": "Week 4", "value_usd": 401000000},
            {"label": "Domestic Outlook", "value_usd": 506000000},
        ],
    },
    "shrek-5": {
        "franchise": "Shrek",
        "studios": ["DreamWorks Animation", "Universal Pictures"],
        "streaming_on": ["Peacock"],
        "cast": ["Mike Myers", "Eddie Murphy", "Cameron Diaz"],
        "directors": ["TBD"],
        "writers": ["TBD"],
        "trailer_embed_url": None,
        "box_office_history": [
            {"label": "Forecast", "value_usd": 97000000},
            {"label": "Week 2", "value_usd": 151000000},
            {"label": "Week 4", "value_usd": 219000000},
            {"label": "Domestic Outlook", "value_usd": 302000000},
        ],
    },
    "toy-story-5": {
        "franchise": "Toy Story",
        "studios": ["Pixar", "Disney"],
        "streaming_on": ["Disney+"],
        "cast": ["Tom Hanks", "Tim Allen", "New Ensemble"],
        "directors": ["TBD"],
        "writers": ["TBD"],
        "trailer_embed_url": None,
        "box_office_history": [
            {"label": "Forecast", "value_usd": 109000000},
            {"label": "Week 2", "value_usd": 174000000},
            {"label": "Week 4", "value_usd": 245000000},
            {"label": "Domestic Outlook", "value_usd": 336000000},
        ],
    },
}


def get_enrichment(movie: Movie, allow_network: bool = False) -> dict:
    base = CATALOG_ENRICHMENTS.get(movie.slug, {})
    tmdb = get_tmdb_movie_enrichment(movie, allow_network=allow_network) or {}

    franchise = tmdb.get("franchise") or base.get("franchise")
    studios = tmdb.get("studios") or base.get("studios", [])
    streaming_on = tmdb.get("streaming_on") or base.get("streaming_on", [])
    cast = tmdb.get("cast") or base.get("cast", [])
    directors = tmdb.get("directors") or base.get("directors", [])
    writers = tmdb.get("writers") or base.get("writers", [])
    trailer_embed_url = tmdb.get("trailer_embed_url") or base.get("trailer_embed_url")

    return {
        "franchise": franchise,
        "studios": studios,
        "streaming_on": streaming_on,
        "cast": cast,
        "directors": directors,
        "writers": writers,
        "trailer_embed_url": trailer_embed_url,
        "logo_url": tmdb.get("logo_url"),
        "backdrops": tmdb.get("backdrops", []),
        "box_office_history": base.get("box_office_history", []),
    }


def build_history(movie: Movie, analytics: MovieAnalytics) -> list[dict]:
    seed = (sum(ord(char) for char in movie.slug) % 7) + 3
    history = []
    multipliers = [0.34, 0.49, 0.63, 0.77, 0.91, 1.0]

    for index, multiplier in enumerate(multipliers):
        history.append(
            {
                "snapshot_date": analytics.snapshot_date - timedelta(days=(len(multipliers) - index - 1) * 7),
                "buzz_score": round(max(0.0, analytics.buzz_score * multiplier - seed), 2),
                "hype_score": round(max(0.0, analytics.hype_score * multiplier - seed / 2), 2),
                "youtube_views": int(analytics.youtube_views * multiplier),
                "social_mentions": int((analytics.x_mentions + analytics.reddit_mentions) * multiplier),
                "google_trends_score": round(max(0.0, analytics.google_trends_score * multiplier), 2),
            }
        )

    return history


def build_score_breakdown(movie: Movie, analytics: MovieAnalytics) -> dict:
    days_until_release = (datetime.combine(movie.release_date, datetime.min.time()) - datetime.now()).days
    release_proximity = max(0, min(1, 1 - abs(days_until_release) / 365))
    youtube_interest = min(
        1.0,
        (analytics.youtube_views + analytics.youtube_likes * 8 + analytics.youtube_comments * 12) / 75_000_000,
    )
    search_interest = min(1.0, analytics.google_trends_score / 100)
    social_buzz = min(1.0, (analytics.x_mentions + analytics.reddit_mentions) / 450_000)
    sentiment = min(1.0, max(0.0, analytics.sentiment_score))
    momentum = min(1.0, max(0.0, analytics.momentum_score))

    return {
        "youtube_interest": round(youtube_interest, 2),
        "search_interest": round(search_interest, 2),
        "social_buzz": round(social_buzz, 2),
        "sentiment": round(sentiment, 2),
        "momentum": round(momentum, 2),
        "release_proximity": round(release_proximity, 2),
    }
