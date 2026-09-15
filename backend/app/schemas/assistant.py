from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

Genre = Literal["Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western"]
Language = Literal["English", "Hindi", "Tamil", "Telugu", "Malayalam", "Kannada", "Korean", "Japanese", "French", "Spanish"]
MovieId = Annotated[int, Field(gt=0)]


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    genres: list[Genre] = Field(default_factory=list, max_length=18)
    excluded_genres: list[Genre] = Field(default_factory=list, max_length=18)
    languages: list[Language] = Field(default_factory=list, max_length=10)
    max_runtime: int | None = Field(None, ge=1, le=600)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=500)
    filters: Filters = Field(default_factory=Filters)
    favorite_ids: list[MovieId] = Field(default_factory=list, max_length=20)
    excluded_ids: list[MovieId] = Field(default_factory=list, max_length=100)
    seen_ids: list[MovieId] = Field(default_factory=list, max_length=80)
    use_ai: bool = False


class PreferenceIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["recommend", "more", "reset", "clarify"]
    filters: Filters
    reference_titles: list[Annotated[str, Field(min_length=1, max_length=255)]] = Field(max_length=3)
    reason: Literal["none", "unsupported", "ambiguous", "off_topic"]


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preference: Literal["like", "dislike"]
