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
                      AUTO_CREATE_TABLES=False, ENABLE_RATE_LIMIT=True, ENABLE_RAG=False, ENABLE_USER_FEATURES=False, ENABLE_ASSISTANT_AI=False)
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
