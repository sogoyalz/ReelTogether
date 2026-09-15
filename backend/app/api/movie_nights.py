"""Small authenticated movie-night rooms. Votes remain private until reveal."""
import secrets
import uuid
from datetime import date, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.account import Account, LoginSession
from app.models.movie import Movie
from app.models.movie_night import MovieNight, NightMember, NightVote
from app.services.authentication import current_session, now, token_digest

router = APIRouter()
GENRES = {'Action','Adventure','Animation','Comedy','Crime','Documentary','Drama','Family','Fantasy','History','Horror','Music','Mystery','Romance','Science Fiction','Thriller','War','Western'}

class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')
class CreateRoom(Payload):
    title: str = Field(min_length=1, max_length=80)
class JoinRoom(Payload):
    token: str = Field(min_length=32, max_length=100)
class Preferences(Payload):
    genres: list[str] = Field(default_factory=list, max_length=5)
    favorites: list[int] = Field(default_factory=list, max_length=5)
class Ballot(Payload):
    movie_id: int
    choice: Literal['yes','pass','veto']
class Winner(Payload):
    movie_id: int


def room_for(db, room_id, account_id, *, write=False, host=False):
    if write:
        # Serialize state transitions and votes through the room row. SQLite's
        # write lock prevents a join/vote racing a start/reveal/selection.
        db.execute(update(MovieNight).where(MovieNight.id == room_id).values(version=MovieNight.version + 1))
    room = db.get(MovieNight, room_id, populate_existing=True)
    if room is None or db.get(NightMember, (room_id, account_id)) is None:
        raise HTTPException(404, 'Room not found')
    if host and room.host_id != account_id:
        raise HTTPException(403, 'Only the host can do this')
    if write and room.expires_at <= now():
        raise HTTPException(410, 'This room expired. Create a new movie night.')
    return room


def require_state(room, state):
    if room.state != state:
        raise HTTPException(409, f'This action requires the {state} stage')


def ranked(db, room):
    votes = list(db.scalars(select(NightVote).where(NightVote.room_id == room.id)))
    movies = {m.id:m for m in db.scalars(select(Movie).where(Movie.id.in_(room.candidates)))}
    result = []
    for movie_id in room.candidates:
        if movie_id not in movies: continue
        choices = [v.choice for v in votes if v.movie_id == movie_id]
        yes, veto = choices.count('yes'), choices.count('veto')
        result.append({'movie_id':movie_id, 'yes':yes, 'vetoes':veto, 'eligible':veto == 0,
            'reason': f'{yes} yes vote(s), {veto} veto(es). ' + ('Excluded by a veto.' if veto else 'No one vetoed this film.')})
    # Ties are explicitly equal; catalog ID makes display order stable, not a hidden tiebreak vote.
    result.sort(key=lambda x:(not x['eligible'], -x['yes'], x['movie_id']))
    best = max((row['yes'] for row in result if row['eligible']), default=None)
    for row in result: row['top_match'] = row['eligible'] and row['yes'] == best
    return result


@router.post('', status_code=201)
def create(payload: CreateRoom, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    # Account-row lock bounds concurrent room creation for one account.
    db.execute(update(Account).where(Account.id == session.account_id).values(username=Account.username))
    count = db.scalar(select(func.count()).select_from(MovieNight).where(MovieNight.host_id == session.account_id, MovieNight.expires_at > now()))
    if count >= 10: raise HTTPException(429, 'You already have ten active rooms')
    token = secrets.token_urlsafe(32)
    room = MovieNight(id=str(uuid.uuid4()), host_id=session.account_id, title=payload.title.strip() or 'Movie night', invite_hash=token_digest(token), expires_at=now()+timedelta(hours=24), state='lobby', candidates=[])
    db.add(room); db.flush()
    db.add(NightMember(room_id=room.id, account_id=session.account_id, genres=[], favorites=[]))
    db.commit()
    return {'id':room.id, 'invite_token':token}


@router.get('')
def rooms(session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    rows = db.scalars(select(MovieNight).join(NightMember, NightMember.room_id == MovieNight.id).where(NightMember.account_id == session.account_id).order_by(MovieNight.expires_at.desc()).limit(50))
    return {'items':[{'id':r.id,'title':r.title,'state':r.state,'expired':r.expires_at <= now()} for r in rows]}


@router.post('/join')
def join(payload: JoinRoom, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    room = db.scalar(select(MovieNight).where(MovieNight.invite_hash == token_digest(payload.token)))
    if room is None: raise HTTPException(404, 'Invite not found or no longer valid')
    db.execute(update(MovieNight).where(MovieNight.id == room.id).values(version=MovieNight.version+1))
    db.refresh(room)
    if room.invite_hash != token_digest(payload.token):
        raise HTTPException(404, 'Invite not found or no longer valid')
    if room.expires_at <= now(): raise HTTPException(410, 'This invitation expired')
    if db.get(NightMember,(room.id,session.account_id)):
        db.commit(); return {'id':room.id}
    if room.state != 'lobby': raise HTTPException(409, 'Voting has started; new members cannot join this round')
    if db.scalar(select(func.count()).select_from(NightMember).where(NightMember.room_id == room.id)) >= 8:
        raise HTTPException(409, 'This room is full (eight people maximum)')
    db.add(NightMember(room_id=room.id, account_id=session.account_id, genres=[], favorites=[])); db.commit()
    return {'id':room.id}


@router.get('/{room_id}')
def detail(room_id: str, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    room = room_for(db, room_id, session.account_id)
    members = db.execute(select(NightMember, Account.username).join(Account,Account.id == NightMember.account_id).where(NightMember.room_id == room_id).order_by(Account.id)).all()
    votes = list(db.scalars(select(NightVote).where(NightVote.room_id == room_id)))
    me = db.get(NightMember,(room_id,session.account_id))
    movies = {m.id:m for m in db.scalars(select(Movie).where(Movie.id.in_(list(set(room.candidates + me.favorites)))))}
    return {'id':room.id,'title':room.title,'state':room.state,'is_host':room.host_id == session.account_id,
        'expired':room.expires_at <= now(),'expires_at':room.expires_at.isoformat()+'Z', 'winner_id':room.winner_id,
        'members':[{'username':name,'is_host':member.account_id == room.host_id,'complete':bool(room.candidates) and sum(v.account_id == member.account_id for v in votes) == len(room.candidates)} for member,name in members],
        'preferences':{'genres':me.genres,'favorites':me.favorites},
        'favorite_movies':[{'id':mid,'title':movies[mid].title} for mid in me.favorites if mid in movies],
        'my_votes':{str(v.movie_id):v.choice for v in votes if v.account_id == session.account_id},
        'movies':[{'id':m.id,'slug':m.slug,'title':m.title,'poster_url':m.poster_url,'genres':m.genres,'year':m.release_date.year} for mid in room.candidates if (m:=movies.get(mid))],
        'results':ranked(db,room) if room.state in {'revealed','selected'} else []}


@router.put('/{room_id}/preferences')
def preferences(room_id: str, payload: Preferences, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    room = room_for(db,room_id,session.account_id,write=True); require_state(room,'lobby')
    if any(g not in GENRES for g in payload.genres): raise HTTPException(422,'Unknown genre')
    ids = set(payload.favorites)
    found = set(db.scalars(select(Movie.id).where(Movie.id.in_(ids), Movie.release_date <= date.today())))
    if ids != found: raise HTTPException(422,'Choose favourites from released catalog movies')
    member = db.get(NightMember,(room_id,session.account_id)); member.genres=sorted(set(payload.genres)); member.favorites=sorted(ids)
    db.commit(); return {'ok':True}


@router.post('/{room_id}/start')
def start(room_id: str, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    room = room_for(db,room_id,session.account_id,write=True,host=True); require_state(room,'lobby')
    members = list(db.scalars(select(NightMember).where(NightMember.room_id == room_id)))
    if len(members) < 2: raise HTTPException(409,'Invite at least one friend before starting')
    movies = list(db.scalars(select(Movie).where(Movie.release_date <= date.today())))
    by_id = {m.id:m for m in movies}
    profiles = [set(member.genres) | {genre for mid in member.favorites if mid in by_id for genre in by_id[mid].genres} for member in members]
    profiles = [p for p in profiles if p]
    favorites = {mid for member in members for mid in member.favorites}
    def score(movie):
        genres = set(movie.genres)
        similarities = [len(genres & p)/max(1,len(genres | p)) for p in profiles]
        group = (min(similarities)+sum(similarities)/len(similarities))/2 if similarities else 0
        return (-group,-movie.tmdb_popularity,movie.id)
    candidates = sorted((m for m in movies if m.id not in favorites),key=score)[:8]
    if len(candidates) < 3: raise HTTPException(409,'Not enough released movies for a shortlist')
    room.candidates=[m.id for m in candidates]; room.state='voting'; db.commit()
    return {'ok':True}


@router.put('/{room_id}/vote')
def vote(room_id: str, payload: Ballot, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    room = room_for(db,room_id,session.account_id,write=True); require_state(room,'voting')
    if payload.movie_id not in room.candidates: raise HTTPException(422,'Movie is not in this shortlist')
    row = db.get(NightVote,(room_id,session.account_id,payload.movie_id))
    if row: row.choice=payload.choice
    else: db.add(NightVote(room_id=room_id,account_id=session.account_id,movie_id=payload.movie_id,choice=payload.choice))
    db.commit(); return {'ok':True}


@router.post('/{room_id}/reveal')
def reveal(room_id: str, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    room=room_for(db,room_id,session.account_id,write=True,host=True); require_state(room,'voting')
    members=db.scalar(select(func.count()).select_from(NightMember).where(NightMember.room_id == room_id))
    votes=db.scalar(select(func.count()).select_from(NightVote).where(NightVote.room_id == room_id))
    if votes != members*len(room.candidates): raise HTTPException(409,'Everyone must vote on every film before the reveal')
    room.state='revealed'; db.commit(); return {'ok':True}


@router.post('/{room_id}/select')
def choose(room_id: str, payload: Winner, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    room=room_for(db,room_id,session.account_id,write=True,host=True); require_state(room,'revealed')
    if not any(r['movie_id'] == payload.movie_id and r['top_match'] for r in ranked(db,room)):
        raise HTTPException(422,'Choose one of the top matches without a veto')
    room.winner_id=payload.movie_id; room.state='selected'; db.commit(); return {'ok':True}


@router.post('/{room_id}/invite')
def refresh_invite(room_id: str, session: LoginSession = Depends(current_session), db: Session = Depends(get_db)):
    room=room_for(db,room_id,session.account_id,write=True,host=True); require_state(room,'lobby')
    token=secrets.token_urlsafe(32);room.invite_hash=token_digest(token);db.commit()
    return {'invite_token':token}
