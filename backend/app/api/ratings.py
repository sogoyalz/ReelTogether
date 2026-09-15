from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import movies as movie_repository
from app.schemas.ratings import UserRatingCreate, UserRatingResponse
from app.services.recommendation_service import delete_user_rating, list_user_ratings, save_user_rating

router = APIRouter()


@router.post("", response_model=UserRatingResponse)
def create_rating(payload: UserRatingCreate, db: Session = Depends(get_db)):
    movie = movie_repository.get_movie_by_id(db, payload.movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    rating = save_user_rating(
        db,
        session_id=payload.session_id,
        movie_id=payload.movie_id,
        rating=payload.rating,
    )
    return UserRatingResponse(
        id=rating.id,
        session_id=rating.session_id,
        movie_id=rating.movie_id,
        rating=rating.rating,
        created_at=rating.created_at,
    )


@router.get("/{session_id}", response_model=list[UserRatingResponse])
def get_ratings_for_session(session_id: str, db: Session = Depends(get_db)):
    ratings = list_user_ratings(db, session_id)
    return [
        UserRatingResponse(
            id=rating.id,
            session_id=rating.session_id,
            movie_id=rating.movie_id,
            rating=rating.rating,
            created_at=rating.created_at,
        )
        for rating in ratings
    ]


@router.delete("/{session_id}/{movie_id}")
def remove_rating(session_id: str, movie_id: int, db: Session = Depends(get_db)):
    removed = delete_user_rating(db, session_id, movie_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Rating not found")
    return {"deleted": True}
