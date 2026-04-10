FROM mcr.microsoft.com/playwright/python:v1.49.1-noble AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/app/.playwright

WORKDIR /app

# curl — healthcheck için
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/.playwright
RUN playwright install chromium

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Migrations + start in one shell command.
# Shell-form CMD expands ${PORT:-8000} at runtime so Railway's
# dynamic PORT env-var is used. No ENTRYPOINT needed.
CMD alembic upgrade head ; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
