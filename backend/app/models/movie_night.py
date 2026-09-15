from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class MovieNight(Base):
    __tablename__ = 'movie_nights'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey('accounts.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(80))
    invite_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    state: Mapped[str] = mapped_column(String(16), default='lobby')
    candidates: Mapped[list[int]] = mapped_column(JSON, default=list)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey('movies.id', ondelete='SET NULL'), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)

class NightMember(Base):
    __tablename__ = 'night_members'
    room_id: Mapped[str] = mapped_column(ForeignKey('movie_nights.id', ondelete='CASCADE'), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id', ondelete='CASCADE'), primary_key=True)
    genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    favorites: Mapped[list[int]] = mapped_column(JSON, default=list)

class NightVote(Base):
    __tablename__ = 'night_votes'
    room_id: Mapped[str] = mapped_column(ForeignKey('movie_nights.id', ondelete='CASCADE'), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id', ondelete='CASCADE'), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True)
    choice: Mapped[str] = mapped_column(String(8))
