"""Read-only production configuration and database preflight; never prints secrets."""
import json
from app.services.schema_health import assert_schema_ready
from sqlalchemy import select
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.account import Account, LoginSession
from app.models.movie import Movie


def configuration_checks():
    return {
        'production_mode': settings.is_production,
        'secure_secret_key': len(settings.SECRET_KEY) >= 32 and settings.SECRET_KEY != 'change-me-in-production',
        'proxy_secret': len(settings.PROXY_SHARED_SECRET) >= 32,
        'admin_key': len(settings.ADMIN_API_KEY) >= 32,
        'https_origins': bool(settings.CORS_ORIGINS) and all(origin.startswith('https://') and '*' not in origin for origin in settings.CORS_ORIGINS),
        'restricted_hosts': bool(settings.TRUSTED_HOSTS) and all('*' not in host for host in settings.TRUSTED_HOSTS),
        'migrations_required': not settings.AUTO_CREATE_TABLES,
        'rate_limiting_enabled': settings.ENABLE_RATE_LIMIT,
        'experimental_features_off': not settings.ENABLE_RAG and not settings.ENABLE_USER_FEATURES,
        'ai_configuration': not settings.ENABLE_ASSISTANT_AI or settings.openai_api_configured,
    }


def main():
    checks = configuration_checks()
    try:
        with SessionLocal() as db:
            assert_schema_ready(db)
        checks['database_schema_accessible'] = True
    except Exception:
        checks['database_schema_accessible'] = False
    print(json.dumps({'ready': all(checks.values()), 'checks': checks,
        'scope': 'Configuration preflight only; HTTPS, offsite backups and external alerts require deployment verification.'}, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
