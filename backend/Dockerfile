# ==============================================================================
# GeoViable — Backend Dockerfile
# ==============================================================================
# Target: python:3.11-slim on linux/arm64 (Oracle Cloud Ampere A1)
# ==============================================================================
FROM public.ecr.aws/docker/library/python:3.11-slim

# ── Prevent Python buffering + set UTF-8 ──
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ── System dependencies ──
#   • WeasyPrint: Pango, Cairo, GDK-Pixbuf, FFI
#   • GeoPandas: GDAL native libraries
#   • Cron: layer update scheduling
#   • curl: health checks
#   • g++: required to build GDAL Python bindings
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint rendering engine
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    # GDAL for GeoPandas / shapefile processing
    gdal-bin \
    libgdal-dev \
    # Build tools for GDAL Python bindings
    g++ \
    # Cron for monthly layer updates
    cron \
    # Health check utility
    curl \
    # Clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    # Set GDAL include path for pip compilation
    && export CPLUS_INCLUDE_PATH=/usr/include/gdal \
    && export C_INCLUDE_PATH=/usr/include/gdal

# ── Working directory ──
WORKDIR /app

# ── Install Python dependencies ──
# Copy requirements first for Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──
COPY app/ ./app/
COPY scripts/ ./scripts/

# ── Cron job configuration ──
COPY scripts/crontab /etc/cron.d/geoviable-cron
RUN chmod 0644 /etc/cron.d/geoviable-cron \
    && crontab /etc/cron.d/geoviable-cron

# ── Create log file for cron output ──
RUN touch /var/log/geoviable_update.log

# ── Entrypoint script (starts cron + uvicorn) ──
COPY scripts/entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
