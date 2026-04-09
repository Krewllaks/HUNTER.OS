#!/bin/bash
# ═══════════════════════════════════════════════════════════
# HUNTER.OS — Production Entrypoint (Phase 11)
# ───────────────────────────────────────────────────────────
# Runs Alembic migrations, then execs into the command passed
# via Dockerfile CMD (uvicorn / celery / beat).
# ═══════════════════════════════════════════════════════════
set -e

echo "============================================"
echo " HUNTER.OS v11 - Production Entrypoint"
echo "============================================"

echo "[1/2] Running database migrations..."
if alembic upgrade head; then
    echo "[OK] Migrations completed successfully"
else
    echo "[WARN] Migration failed or no pending migrations. Continuing..."
fi

echo ""
echo "[2/2] Starting application..."
exec "$@"
