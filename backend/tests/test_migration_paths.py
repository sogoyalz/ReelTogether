"""Exercise real upgrades and historical schema adoption using disposable files."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1]


class MigrationPaths(unittest.TestCase):
    def test_erasure_upgrade_preserves_populated_accounts_and_restore_identity(self):
        from database_backup import copy_database
        with tempfile.TemporaryDirectory() as temporary:
            original=Path(temporary)/'accounts.db';restored=Path(temporary)/'restored.db'
            self.run_command(original,'-m','alembic','upgrade','20261101_0014')
            with sqlite3.connect(original) as db:
                db.execute("INSERT INTO accounts(id,username,password_hash,created_at) VALUES(1,'retained','test-only','2026-10-31 12:00:00')")
                db.execute("INSERT INTO login_sessions(token_hash,account_id,csrf_token,expires_at) VALUES('token',1,'csrf','2030-01-01')")
            copy_database(original,restored)
            for path in (original,restored):
                self.run_command(path,'-m','alembic','upgrade','head')
                self.run_command(path,'-m','alembic','check')
            with sqlite3.connect(original) as db,sqlite3.connect(restored) as other:
                row=db.execute('SELECT id,username,erasure_key FROM accounts').fetchone()
                self.assertEqual(row,other.execute('SELECT id,username,erasure_key FROM accounts').fetchone())
                self.assertEqual(db.execute('SELECT count(*) FROM login_sessions').fetchone()[0],1)
                self.assertEqual(row[:2],(1,'retained'))

    def run_command(self, database, *args):
        env = {**os.environ, 'DATABASE_URL': f'sqlite:///{database}', 'ENABLE_STARTUP_SYNC':'false'}
        result = subprocess.run([sys.executable, *args], cwd=BACKEND, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_fresh_upgrade_and_metadata_are_in_sync(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary)/'fresh.db'
            self.run_command(database, '-m', 'alembic', 'upgrade', 'head')
            self.run_command(database, '-m', 'alembic', 'check')

    def test_historical_adoption_preserves_rows_and_repairs_only_verified_demos(self):
        from app.services.mock_data import MOVIE_CATALOG
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary)/'legacy.db'
            self.run_command(database, '-m', 'alembic', 'upgrade', '20260324_0002')
            demo = MOVIE_CATALOG[6]
            with sqlite3.connect(database) as connection:
                connection.execute('DROP TABLE alembic_version')
                fields = ['tmdb_id','slug','title','release_date','status','poster_url','backdrop_url','overview','genres','tmdb_popularity']
                values = [demo[key] for key in fields]
                values[3] = values[3].isoformat(); values[8] = json.dumps(values[8])
                connection.execute(f"INSERT INTO movies ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", values)
                connection.execute("INSERT INTO movies (tmdb_id,slug,title,release_date,status,genres,tmdb_popularity) VALUES (123,'live-movie','Live Movie','2020-01-01','released','[]',1)")
                required = {column[1]: 0 for column in connection.execute('PRAGMA table_info(movie_analytics)') if column[3] and column[4] is None and column[1] != 'id'}
                required.update(movie_id=1, snapshot_label='latest', snapshot_date='2026-10-31')
                columns = ','.join(required)
                placeholders = ','.join('?' for _ in required)
                for views in (100,200):
                    required['youtube_views'] = views
                    connection.execute(f'INSERT INTO movie_analytics ({columns}) VALUES ({placeholders})', list(required.values()))
            self.run_command(database, 'upgrade_database.py', '--adopt-existing')
            self.run_command(database, '-m', 'alembic', 'check')
            self.assertEqual(len(list(Path(temporary).glob('legacy.db.backup-*'))), 1)
            with sqlite3.connect(database) as connection:
                rows = connection.execute('SELECT id,tmdb_id,title,provider_metadata FROM movies ORDER BY id').fetchall()
                self.assertEqual(rows[0][:3], (1, -7, 'Dune: Part Two'))
                self.assertEqual(json.loads(rows[0][3])['catalog_source'], 'demo')
                self.assertEqual(rows[1][1], 123)
                snapshots = connection.execute('SELECT id,snapshot_label FROM movie_analytics ORDER BY id').fetchall()
                self.assertEqual(len(snapshots), 2)
                self.assertTrue(snapshots[0][1].startswith('archived:'))
                self.assertEqual(snapshots[1][1], 'latest')
