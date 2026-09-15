import sqlite3
import tempfile
import unittest
from pathlib import Path
from backup_worker import backup_once
from database_backup import inspect_database

class BackupTests(unittest.TestCase):
    def test_backup_is_restorable_and_read_only_to_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.sqlite'
            with sqlite3.connect(source) as db:
                db.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)')
                db.execute("INSERT INTO sample VALUES (1, 'preserve me')")
            before = inspect_database(source)
            status = backup_once(source, root / 'backups')
            self.assertTrue(status['ok'])
            self.assertEqual(inspect_database(root / 'backups' / status['backup']), before)
            self.assertEqual(inspect_database(source), before)
            self.assertTrue((root / 'backups' / 'status.json').exists())

    def test_failed_backup_does_not_publish_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                backup_once(root / 'absent.sqlite', root / 'backups')
            self.assertFalse((root / 'backups' / 'status.json').exists())
