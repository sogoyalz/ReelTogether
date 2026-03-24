# Movie Pulse

Movie Pulse is a movie analytics platform with a FastAPI backend and a Next.js frontend. The app combines TMDB catalog data, YouTube trailer metrics, OMDb metadata, and internal scoring/AI layers for movie research, comparison, and discovery.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: Next.js 14, React Query, Recharts
- Data sources: TMDB, YouTube Data API, OMDb

## Local Development

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` to the backend URL, for example:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
API_BASE_URL=http://127.0.0.1:8000
```

The frontend also includes a same-origin proxy route in [`frontend/app/api/[...path]/route.ts`](/Users/souravgoyal/Desktop/moviess/frontend/app/api/[...path]/route.ts), so production deployments can set `API_BASE_URL` server-side instead of exposing the backend URL directly in the client bundle.

## Production Notes

This repo now includes:

- Alembic migration scaffolding in [`backend/alembic.ini`](/Users/souravgoyal/Desktop/moviess/backend/alembic.ini)
- backend Docker image in [`backend/Dockerfile`](/Users/souravgoyal/Desktop/moviess/backend/Dockerfile)
- frontend Docker image in [`frontend/Dockerfile`](/Users/souravgoyal/Desktop/moviess/frontend/Dockerfile)
- compose entrypoint in [`docker-compose.yml`](/Users/souravgoyal/Desktop/moviess/docker-compose.yml)
- rate limiting, trusted hosts, gzip, request IDs, and security headers in the backend app
- async startup sync so the API can boot before long TMDB/YouTube refresh work finishes
- health endpoints:
  - `/health`
  - `/health/live`
  - `/health/ready`

### Required backend env

Use [`backend/.env.example`](/Users/souravgoyal/Desktop/moviess/backend/.env.example) as the template.

Important production values:

- `ENVIRONMENT=production`
- `AUTO_CREATE_TABLES=false`
- `ENABLE_DOCS=false`
- `TRUSTED_HOSTS=["your-domain.com","www.your-domain.com"]`
- `CORS_ORIGINS=["https://your-frontend-domain.com"]`
- `SECRET_KEY=...`
- `ADMIN_API_KEY=...`
- `API_BASE_URL=https://your-backend-domain.com` on the frontend service

### Migrations

Run schema migrations before starting the production backend:

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

For future schema changes:

```bash
alembic revision -m "describe change"
alembic upgrade head
```

## Background Jobs

The backend includes an internal background job runner for long-running refresh tasks.

Admin routes:

- `POST /api/admin/jobs/startup-sync`
- `POST /api/admin/jobs/tmdb-sync`
- `POST /api/admin/jobs/youtube-refresh`
- `POST /api/admin/jobs/ai-refresh`
- `GET /api/admin/jobs`
- `GET /api/admin/jobs/{job_id}`

In production, set `ADMIN_API_KEY` and send it as the `X-Admin-Key` header.

## Deployment

### Docker Compose

```bash
docker compose up --build
```

### Render

Use Render as a `Blueprint`, not as a single Docker service from the repo root.

This repo contains 2 separate services:

- backend in [`backend/Dockerfile`](/Users/souravgoyal/Desktop/moviess/backend/Dockerfile)
- frontend in [`frontend/Dockerfile`](/Users/souravgoyal/Desktop/moviess/frontend/Dockerfile)

The Render blueprint file is [`render.yaml`](/Users/souravgoyal/Desktop/moviess/render.yaml).

#### Recommended Render flow

1. Push the repo to GitHub.
2. In Render, choose `New +` -> `Blueprint`.
3. Select this repository.
4. Let Render create both services from [`render.yaml`](/Users/souravgoyal/Desktop/moviess/render.yaml).

#### If you create services manually

Backend service:

- Root Directory: `backend`
- Dockerfile Path: `./Dockerfile`
- Health Check Path: `/health/ready`

Frontend service:

- Root Directory: `frontend`
- Dockerfile Path: `./Dockerfile`

Do not point Render at the repo root as a single Docker service, because there is no root-level `Dockerfile`.

#### Required Render environment variables

Backend:

- `ENVIRONMENT=production`
- `ENABLE_DOCS=false`
- `AUTO_CREATE_TABLES=false`
- `DATABASE_URL=...`
- `REDIS_URL=...`
- `TMDB_API_KEY=...`
- `YOUTUBE_API_KEY=...`
- `OMDB_API_KEY=...`
- `SECRET_KEY=...`
- `ADMIN_API_KEY=...`
- `CORS_ORIGINS=["https://your-frontend-url.onrender.com"]`
- `TRUSTED_HOSTS=["your-backend-url.onrender.com"]`

Frontend:

- `API_BASE_URL=https://your-backend-url.onrender.com`

### Backend

The backend container serves FastAPI on port `8000`.

### Frontend

The frontend builds in standalone mode and serves on port `3000`.

## Current Production Gaps

The project is stronger now, but these are still future work if you want a larger production system:

- external worker/queue system instead of in-process background threads
- Sentry or similar error monitoring
- CI/CD pipeline
- persistent historical AI/analytics ingestion from Reddit and YouTube comments
- auth, watchlists, notifications
