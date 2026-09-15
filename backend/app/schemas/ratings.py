from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.movie import MovieSummary


class UserRatingCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=255)
    movie_id: int
    rating: float = Field(ge=1.0, le=5.0)


class UserRatingResponse(BaseModel):
    id: int
    session_id: str
    movie_id: int
    rating: float
    created_at: datetime


class RecommendationItemResponse(BaseModel):
    movie: MovieSummary
    similarity_score: float
    explanation: str


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationItemResponse]
