from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.movie import MovieSummary
from app.schemas.ratings import RecommendationItemResponse, RecommendationResponse
from app.services.recommendation_service import explain_recommendations, get_recommendations

from .movies import _serialize_summary_fast as _serialize_summary


router = APIRouter()


@router.get("/{session_id}", response_model=RecommendationResponse)
def get_personalized_recommendations(
    session_id: str,
    top_n: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    recommendations, rated_movies = get_recommendations(db, session_id, top_n=top_n)
    explanations = explain_recommendations(session_id, recommendations, rated_movies)
    explanation_map = {item["movie_id"]: item["explanation"] for item in explanations}

    return RecommendationResponse(
        recommendations=[
            RecommendationItemResponse(
                movie=MovieSummary(**_serialize_summary(item["movie"]).model_dump()),
                similarity_score=item["similarity_score"],
                explanation=explanation_map.get(
                    item["movie"].id,
                    "This title is close to the movies you rated most highly.",
                ),
            )
            for item in recommendations
        ]
    )
