import unittest
from datetime import date, timedelta
from fastapi.testclient import TestClient
import test_accounts as accounts
from test_accounts import ORIGIN
from app.models import Movie
from app.models.movie_night import MovieNight
from app.services.authentication import now
from main import app

class MovieNightTests(unittest.TestCase):
    setUp = accounts.AccountTests.setUp
    tearDown = accounts.AccountTests.tearDown
    register = accounts.AccountTests.register

    def setup_room(self):
        for i in range(10):
            self.db.add(Movie(tmdb_id=800000+i,slug=f'night-{i}',title=f'Night Film {i}',release_date=date(2020,1,1),genres=['Comedy'] if i%2 else ['Drama'],tmdb_popularity=i))
        self.db.commit()
        self.a=self.register(self.alice,'alice');self.b=self.register(self.bob,'bob')
        result=self.alice.post('/api/movie-nights',json={'title':'Friday'},headers=self.a)
        self.assertEqual(result.status_code,201,result.text)
        self.rid=result.json()['id'];self.token=result.json()['invite_token'];self.path='/api/movie-nights/'+self.rid
        return result

    def join_start(self):
        self.assertEqual(self.bob.post('/api/movie-nights/join',json={'token':self.token},headers=self.b).status_code,200)
        self.assertEqual(self.alice.post(self.path+'/start',headers=self.a).status_code,200)
        return self.alice.get(self.path).json()['movies']

    def test_membership_csrf_invites_and_late_join(self):
        self.setup_room()
        self.assertEqual(self.bob.get(self.path).status_code,404)
        self.assertEqual(self.alice.post(self.path+'/start').status_code,403)
        self.assertEqual(self.alice.post(self.path+'/start',headers=self.a).status_code,409)
        rotated=self.alice.post(self.path+'/invite',headers=self.a).json()['invite_token']
        self.assertEqual(self.bob.post('/api/movie-nights/join',json={'token':self.token},headers=self.b).status_code,404)
        self.token=rotated;self.join_start()
        with TestClient(app,base_url='http://localhost',headers={'Origin':ORIGIN}) as guest:
            headers=self.register(guest,'charlie')
            self.assertEqual(guest.post('/api/movie-nights/join',json={'token':self.token},headers=headers).status_code,409)
        self.assertEqual(self.bob.post(self.path+'/reveal',headers=self.b).status_code,403)
        self.assertEqual(self.alice.put(self.path+'/preferences',json={'genres':['Comedy']},headers=self.a).status_code,409)

    def test_private_votes_reveal_ties_and_optional_watchlist(self):
        self.setup_room();movies=self.join_start()
        self.assertEqual(self.alice.post(self.path+'/reveal',headers=self.a).status_code,409)
        self.assertEqual(self.alice.put(self.path+'/vote',json={'movie_id':999999,'choice':'yes'},headers=self.a).status_code,422)
        for m in movies:
            self.assertEqual(self.alice.put(self.path+'/vote',json={'movie_id':m['id'],'choice':'yes'},headers=self.a).status_code,200)
        private=self.bob.get(self.path)
        self.assertIn('no-store',private.headers['cache-control'])
        self.assertEqual(private.json()['my_votes'],{});self.assertEqual(private.json()['results'],[])
        for i,m in enumerate(movies):
            self.assertEqual(self.bob.put(self.path+'/vote',json={'movie_id':m['id'],'choice':'veto' if i==0 else 'yes'},headers=self.b).status_code,200)
        self.assertEqual(self.alice.post(self.path+'/reveal',headers=self.a).status_code,200)
        result=self.alice.get(self.path).json()['results']
        self.assertEqual(sum(r['top_match'] for r in result),len(movies)-1)
        self.assertEqual(self.alice.post(self.path+'/select',json={'movie_id':movies[0]['id']},headers=self.a).status_code,422)
        self.assertEqual(self.alice.post(self.path+'/select',json={'movie_id':movies[1]['id']},headers=self.a).status_code,200)
        self.assertEqual(self.bob.put(self.path+'/vote',json={'movie_id':movies[1]['id'],'choice':'veto'},headers=self.b).status_code,409)
        self.assertEqual(self.alice.post(self.path+'/select',json={'movie_id':movies[2]['id']},headers=self.a).status_code,409)
        self.assertEqual(self.alice.get('/api/watchlist').json()['total'],0)
        self.assertEqual(self.bob.get('/api/watchlist').json()['total'],0)

    def test_preferences_are_private_and_expired_rooms_are_read_only(self):
        self.setup_room()
        self.assertEqual(self.alice.put(self.path+'/preferences',json={'genres':['Invented']},headers=self.a).status_code,422)
        self.assertEqual(self.alice.put(self.path+'/preferences',json={'favorites':[999999]},headers=self.a).status_code,422)
        self.assertEqual(self.alice.put(self.path+'/preferences',json={'genres':['Comedy']},headers=self.a).status_code,200)
        self.bob.post('/api/movie-nights/join',json={'token':self.token},headers=self.b)
        self.assertEqual(self.bob.get(self.path).json()['preferences']['genres'],[])
        room=self.db.get(MovieNight,self.rid);room.expires_at=now()-timedelta(seconds=1);self.db.commit()
        self.assertTrue(self.alice.get(self.path).json()['expired'])
        self.assertEqual(self.alice.post(self.path+'/start',headers=self.a).status_code,410)
        self.assertEqual(self.bob.post('/api/movie-nights/join',json={'token':self.token},headers=self.b).status_code,410)

    def test_all_vetoed_has_no_winner(self):
        self.setup_room();movies=self.join_start()
        for client,headers in [(self.alice,self.a),(self.bob,self.b)]:
            for m in movies: client.put(self.path+'/vote',json={'movie_id':m['id'],'choice':'veto'},headers=headers)
        self.alice.post(self.path+'/reveal',headers=self.a)
        self.assertFalse(any(r['top_match'] for r in self.bob.get(self.path).json()['results']))
        self.assertEqual(self.alice.post(self.path+'/select',json={'movie_id':movies[0]['id']},headers=self.a).status_code,422)

    def test_concurrent_winner_selection_is_atomic(self):
        import tempfile
        from pathlib import Path
        from concurrent.futures import ThreadPoolExecutor
        from types import SimpleNamespace
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from fastapi import HTTPException
        from app.db.base import Base
        from app.models.account import Account
        from app.models.movie_night import NightMember, NightVote
        from app.api.movie_nights import choose, Winner
        with tempfile.TemporaryDirectory() as temporary:
            engine=create_engine('sqlite:///'+str(Path(temporary)/'race.sqlite'),connect_args={'timeout':10})
            Base.metadata.create_all(engine)
            with Session(engine) as db:
                db.add_all([Account(id=i,username=f'user{i}',password_hash='unused') for i in [1,2]])
                db.add_all([Movie(id=i,tmdb_id=i,slug=f'film-{i}',title=f'Film {i}',release_date=date(2020,1,1),genres=[]) for i in [1,2]])
                db.flush()
                db.add(MovieNight(id='race',host_id=1,title='Race',invite_hash='x'*64,expires_at=now()+timedelta(hours=1),state='revealed',candidates=[1,2]))
                db.flush()
                for account in [1,2]:
                    db.add(NightMember(room_id='race',account_id=account,genres=[],favorites=[]))
                    for movie in [1,2]:db.add(NightVote(room_id='race',account_id=account,movie_id=movie,choice='yes'))
                db.commit()
            def select_winner(movie_id):
                with Session(engine) as db:
                    try:
                        choose('race',Winner(movie_id=movie_id),session=SimpleNamespace(account_id=1),db=db)
                        return 200
                    except HTTPException as error:return error.status_code
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(select_winner,[1,2])),[200,409])
            engine.dispose()
