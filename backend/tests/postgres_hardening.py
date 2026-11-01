"""Run production-control regressions in isolated local PostgreSQL schemas."""
import os,sys,uuid,unittest
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch
url=os.environ.get('POSTGRES_TEST_URL','')
parsed=urlparse(url)
if parsed.hostname not in {'127.0.0.1','localhost'} or parsed.path != '/reeltest':
    raise SystemExit('Use the disposable local reeltest database')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_production_hardening as hardening
import test_accounts as accounts
import test_durable_operations as durable
from sqlalchemy import create_engine,text
engine=create_engine(url.replace('postgresql://','postgresql+psycopg://',1))
schemas=[]
def isolated(*args,**kwargs):
    schema='hardening_'+uuid.uuid4().hex
    with engine.begin() as c:c.execute(text(f'CREATE SCHEMA {schema}'))
    schemas.append(schema)
    return engine.execution_options(schema_translate_map={None:schema})
try:
    with patch.object(accounts,'create_engine',side_effect=isolated),patch.object(durable,'create_engine',side_effect=isolated):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(hardening))
    if not result.wasSuccessful():raise SystemExit(1)
finally:
    for schema in schemas:
        with engine.begin() as c:c.execute(text(f'DROP SCHEMA {schema} CASCADE'))
    engine.dispose()
