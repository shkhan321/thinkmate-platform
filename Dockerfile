# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable \
    && corepack prepare pnpm@11.8.0 --activate \
    && pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime

# APP_ENV defaults to production in the deployed image so the production safety
# checks (admin password, demo seeding, same-origin CORS) are ON by default.
# Railway/host env vars still override this; local development runs uvicorn
# directly (not this image) and stays in the "development" default.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN python -m pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend-build /app/frontend/dist frontend/dist

EXPOSE 8000
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
