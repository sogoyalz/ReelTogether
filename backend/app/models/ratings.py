from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRating(Base):
    __tablename__ = "user_ratings"
    __table_args__ = (
        UniqueConstraint("session_id", "movie_id", name="uq_user_ratings_session_movie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(255), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    movie = relationship("Movie", back_populates="user_ratings")

    def __repr__(self) -> str:
        return f"<UserRating id={self.id} movie_id={self.movie_id} session_id={self.session_id!r} rating={self.rating}>"
