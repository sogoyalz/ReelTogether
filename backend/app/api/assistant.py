from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.account import LoginSession, MovieFeedback, WatchlistEntry
from app.models.movie import Movie
from app.schemas.assistant import ChatRequest, FeedbackRequest
from app.services.authentication import COOKIE, current_session
from app.services.catalog_assistant import movie_runtime, movie_languages
from app.services.assistant_ai import ai_available
from app.services.assistant_chat import answer_chat

router = APIRouter()


@router.get("/coverage")
def coverage(db: Session = Depends(get_db)):
    movies = list(db.scalars(select(Movie).where(Movie.release_date <= date.today())))
    return {"released_movies": len(movies), "with_runtime": sum(movie_runtime(m) is not None for m in movies), "with_language": sum(bool(movie_languages(m)) for m in movies), "ai_available": ai_available()}


@router.post("/chat")
def chat(payload: ChatRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    liked, disliked, watched = [], [], []
    if request.cookies.get(COOKIE) or payload.use_ai:
        session = current_session(request, db)
        feedback = list(db.scalars(select(MovieFeedback).where(MovieFeedback.account_id == session.account_id)))
        liked = [item.movie_id for item in feedback if item.preference == "like"]
        disliked = [item.movie_id for item in feedback if item.preference == "dislike"]
        watched = list(db.scalars(select(WatchlistEntry.movie_id).where(WatchlistEntry.account_id == session.account_id, WatchlistEntry.status == "watched")))
    response.headers["Cache-Control"] = "private, no-store"
    return answer_chat(db, payload, liked, disliked, watched)


@router.get("/feedback")
def feedback(session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    rows = db.execute(select(MovieFeedback, Movie).join(Movie, MovieFeedback.movie_id == Movie.id).where(MovieFeedback.account_id == session.account_id).order_by(Movie.title)).all()
    return {"items": [{"movie_id": movie.id, "title": movie.title, "release_date": movie.release_date, "preference": entry.preference} for entry, movie in rows]}


@router.put("/feedback/{movie_id}")
def set_feedback(movie_id: int, payload: FeedbackRequest, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    if db.get(Movie, movie_id) is None:
        raise HTTPException(404, "Movie not found")
    key = (session.account_id, movie_id)
    entry = db.get(MovieFeedback, key)
    if entry is None:
        entry = MovieFeedback(account_id=session.account_id, movie_id=movie_id, preference=payload.preference)
        db.add(entry)
    else:
        entry.preference = payload.preference
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        entry = db.get(MovieFeedback, key)
        if entry is None:
            raise
        entry.preference = payload.preference
        db.commit()
    return {"preference": entry.preference}


@router.delete("/feedback/{movie_id}")
def remove_feedback(movie_id: int, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    db.execute(delete(MovieFeedback).where(MovieFeedback.account_id == session.account_id, MovieFeedback.movie_id == movie_id))
    db.commit()
    return {"ok": True}
