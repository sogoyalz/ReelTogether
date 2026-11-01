import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.middleware import RequestContextMiddleware
from production_check import configuration_checks

class OperationsTests(unittest.TestCase):
    def test_preflight_rejects_development_settings(self):
        with patch.object(settings, 'ENVIRONMENT', 'development'), patch.object(settings, 'SECRET_KEY', 'change-me-in-production'):
            checks = configuration_checks()
            self.assertFalse(checks['production_mode'])
            self.assertFalse(checks['secure_secret_key'])

    def test_preflight_accepts_explicit_production_configuration(self):
        from contextlib import ExitStack
        values = dict(ENVIRONMENT='production', SECRET_KEY='s'*32, PROXY_SHARED_SECRET='p'*32, ADMIN_API_KEY='a'*32,
                      CORS_ORIGINS=['https://movies.example.com'], TRUSTED_HOSTS=['movies.example.com'],
                      AUTO_CREATE_TABLES=False, ENABLE_RATE_LIMIT=True, ENABLE_RAG=False, ENABLE_USER_FEATURES=False, ENABLE_ASSISTANT_AI=False, REDIS_URL='redis://shared:6379/0', ERASURE_LEDGER_PATH='/receipts/deletions.jsonl',ERASURE_LEDGER_KEY='e'*32)
        with ExitStack() as stack:
            for key, value in values.items(): stack.enter_context(patch.object(settings, key, value))
            self.assertTrue(all(configuration_checks().values()))

    def test_errors_are_generic_and_logs_omit_sensitive_input(self):
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)
        @app.get('/failure/{identifier}')
        def fail(identifier: str):
            raise ValueError('private-error-detail')
        with self.assertLogs('requests', level='INFO') as logs:
            with TestClient(app) as client:
                response = client.get('/failure/private-path?password=private-query', headers={'X-Request-ID':'untrusted-value'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['detail'], 'An unexpected error occurred')
        self.assertNotEqual(response.headers['x-request-id'], 'untrusted-value')
        output = '\n'.join(logs.output)
        for secret in ['private-path', 'private-query', 'private-error-detail', 'untrusted-value']:
            self.assertNotIn(secret, output)
        self.assertIn('/failure/{identifier}', output)

    def test_lifespan_runs_cleanup_and_propagates_startup_failure(self):
        import main
        with patch.object(main,'startup_event') as startup, patch.object(main,'shutdown_event') as shutdown:
            for _ in range(2):
                with TestClient(main.app,base_url='http://localhost') as client:
                    self.assertEqual(client.get('/health/live').status_code,200)
            self.assertEqual(startup.call_count,2)
            self.assertEqual(shutdown.call_count,2)
        with patch.object(main,'startup_event',side_effect=RuntimeError('startup failed')):
            with self.assertRaises(RuntimeError):
                with TestClient(main.app,base_url='http://localhost'): pass

    def test_metrics_only_store_route_templates_and_allowlisted_events(self):
        import json
        from app.services.operational_metrics import record_request, record_event, snapshot
        record_request('GET','/movies/{movie_id}',503,275)
        record_event('room_created')
        data = snapshot()
        route = next(row for row in data['requests'] if row['route']=='/movies/{movie_id}')
        self.assertGreaterEqual(route['errors'],1)
        self.assertEqual(sum(route['latency_buckets']),route['count'])
        self.assertGreaterEqual(data['movie_night_events']['room_created'],1)
        self.assertIn('process-local',data['scope'])
        with self.assertRaises(ValueError): record_event('arbitrary-username')
        self.assertNotIn('arbitrary-username',json.dumps(snapshot()))
