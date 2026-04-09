# HUNTER.OS Backend — Multi-stage Docker Build
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ADDED (Phase 11): Playwright browser cache path. Pinning this
# guarantees browsers land in a predictable, persistent location
# so rebuilds don't re-download Chromium.
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ADDED (Phase 11): Ensure the Playwright browser path exists
# before installing browsers into it.
RUN mkdir -p /app/.playwright

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy application code
COPY . .

# ADDED (Phase 11): Production entrypoint — runs alembic
# migrations before handing off to the CMD below.
RUN chmod +x /app/scripts/entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint → migrations → exec CMD
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
