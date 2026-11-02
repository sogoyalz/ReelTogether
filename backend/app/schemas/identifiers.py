"""Request IDs bounded to the signed integer range supported by storage.

Movie primary keys use SQLAlchemy Integer (32-bit on PostgreSQL). Use the
portable signed range on both databases; these are internal primary keys, not
the separate TMDB/demo identifiers. Missing in-range IDs retain normal 404s.
"""
from typing import Annotated

from pydantic import Field

MIN_MOVIE_ID = -(2 ** 31)
MAX_MOVIE_ID = 2 ** 31 - 1
MovieId = Annotated[int, Field(ge=MIN_MOVIE_ID, le=MAX_MOVIE_ID)]
PositiveMovieId = Annotated[int, Field(gt=0, le=MAX_MOVIE_ID)]
