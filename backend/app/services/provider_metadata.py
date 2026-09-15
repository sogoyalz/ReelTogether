"""Normalize optional provider fields without inventing movie facts."""
import math

TEXT_FIELDS = {"imdb_id", "rated", "runtime", "language", "original_language", "box_office", "awards", "metascore", "imdb_rating", "imdb_votes", "rotten_tomatoes", "omdb_poster_url"}


def metadata_text(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    text = str(value).strip()
    return text if text and text.casefold() not in {"n/a", "nan", "none", "null", "inf", "infinity", "-inf", "-infinity"} else None


def normalize_metadata(value):
    if not isinstance(value, dict):
        return {}
    result = dict(value)
    for key in TEXT_FIELDS & result.keys():
        result[key] = metadata_text(result[key])
    for key in {"youtube_observation", "box_office_targets"} & result.keys():
        if not isinstance(result[key], dict):
            result[key] = {}
    return result
