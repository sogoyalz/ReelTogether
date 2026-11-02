"""Run catalog parity and bounded hydration in an isolated PostgreSQL schema."""
import os
from pathlib import Path
import sys
import unittest
import uuid
from urllib.parse import urlparse
from unittest.mock import patch
from sqlalchemy import create_engine, text
url = os.environ.get('POSTGRES_TEST_URL', '')
parsed = urlparse(url)
if parsed.hostname not in {'localhost','127.0.0.1'} or parsed.path != '/reeltest':
    raise SystemExit('Use an explicit local disposable reeltest database')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_catalog_sql
import test_adversarial_audit
engine = create_engine(url.replace('postgresql://', 'postgresql+psycopg://', 1))
schemas = []
def isolated_engine(*args, **kwargs):
    schema = 'catalog_test_' + uuid.uuid4().hex
    with engine.begin() as connection: connection.execute(text(f'CREATE SCHEMA {schema}'))
    schemas.append(schema)
    return engine.execution_options(schema_translate_map={None:schema})
try:
    with patch.object(test_catalog_sql, 'create_engine', side_effect=isolated_engine), patch.object(test_adversarial_audit, 'create_engine', side_effect=isolated_engine):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(test_catalog_sql.CatalogSqlTests), unittest.defaultTestLoader.loadTestsFromTestCase(test_adversarial_audit.PublicReadAuditTests)]))
    if not result.wasSuccessful(): raise SystemExit(1)
finally:
    for schema in schemas:
        with engine.begin() as connection: connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
    engine.dispose()
