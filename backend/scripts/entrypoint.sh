#!/bin/bash
# ==============================================================================
# GeoViable — Container Entrypoint
# ==============================================================================
# Starts the cron daemon in background, then launches Uvicorn (FastAPI).
# This script is the CMD of the backend Docker image.
# ==============================================================================
set -e

# ── Start cron service in background ──
# Required for the monthly layer update cron job (update_layers.py)
echo "[entrypoint] Starting cron daemon..."
cron

# ── Set statement timeout for PostgreSQL sessions ──
# Ensures no single query runs longer than the configured limit (default 30s).
# This is applied at the session level so every connection inherits it.
export PGSTATEMENT_TIMEOUT="${QUERY_TIMEOUT_SECONDS:-30}"

# ── Launch FastAPI with Uvicorn ──
# 2 workers for ARM instance with 24 GB RAM (sufficient for internal MVP).
# log-level is read from the environment variable.
echo "[entrypoint] Starting Uvicorn on port 8000 with ${UVICORN_WORKERS:-2} workers..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-2}" \
    --log-level "${LOG_LEVEL:-info}"
