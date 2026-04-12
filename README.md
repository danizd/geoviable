# GeoViable

> Automated environmental feasibility assessment tool for land parcels and projects in Galicia, Spain.

**Production URL:** https://geoviable.movilab.es/

## Overview

GeoViable is an internal Micro-SaaS B2B tool that automates the evaluation of environmental feasibility for land parcels. It cross-references user-drawn polygons with official environmental layers (Red Natura 2000, flood zones, hydraulic public domain, livestock routes, protected natural spaces, water masses) and generates a technical PDF report instantly.

## Tech Stack

| Component | Technology |
|---|---|
| **Infrastructure** | Oracle Cloud Always Free (ARM, 24 GB RAM, 200 GB disk) |
| **Orchestration** | Docker Compose |
| **Database** | PostgreSQL 15+ with PostGIS 3.4+ |
| **Backend** | Python 3.11 + FastAPI |
| **PDF Generation** | WeasyPrint (Jinja2 templates → HTML → PDF) |
| **Static Map** | contextily + matplotlib + geopandas |
| **Frontend** | React.js + React Leaflet |
| **Web Server** | Nginx (reverse proxy + static files) |
| **HTTPS** | Let's Encrypt / Cloudflare |

## Project Structure

```
geoviable/
├── .env.example                  # Environment variables template (safe to commit)
├── .env                          # Local environment (NEVER commit — gitignored)
├── .gitignore
├── docker-compose.yml            # Production Docker orchestration
├── README.md                     # ← You are here
├── specs/                        # Full technical specifications
│   ├── Arquitectura_y_flujos.md
│   ├── Especificaciones_frontend.md
│   ├── Especificaciones_backend.md
│   ├── API_reference.md
│   ├── Esquema_base_datos.md
│   ├── Informe_PDF_plantilla.md
│   ├── Fuentes_de_datos.md
│   ├── Seguridad_y_configuracion.md
│   ├── DevOps_y_despliegue.md
│   └── Glosario.md
├── backend/                      # FastAPI Python backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── config.py             # Pydantic Settings (env vars)
│   │   ├── models/               # SQLAlchemy + GeoAlchemy2 models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── api/                  # API route handlers
│   │   ├── services/             # Business logic (analysis, PDF, validation)
│   │   ├── templates/report/     # Jinja2 HTML templates for PDF
│   │   └── static/               # Static assets (logo, etc.)
│   ├── scripts/
│   │   ├── update_layers.py      # Monthly environmental layer update cron
│   │   ├── init_db.sql           # DB initialization SQL (PostGIS + tables)
│   │   ├── entrypoint.sh         # Container entrypoint (cron + uvicorn)
│   │   └── crontab               # Cron schedule for layer updates
│   └── tests/                    # Pytest test suite
├── frontend/                     # React.js application
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── components/           # React components (MapViewer, ToolPanel, etc.)
│       ├── services/             # API client, file parsers
│       ├── utils/                # Validation helpers
│       ├── App.jsx
│       └── index.js
├── nginx/
│   └── conf.d/
│       └── default.conf          # Nginx config (SSL + reverse proxy)
├── certs/                        # SSL certificates (not versioned)
├── data/                         # Downloaded shapefiles (not versioned)
├── backups/                      # Database backups (not versioned)
└── tmp/                          # Temporary files (not versioned)
```

## Quick Start

### Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| **Docker** | 24.0+ | Container runtime |
| **Docker Compose** | 2.20+ | Service orchestration |
| **Node.js** | 18.x (LTS) | Frontend build (local dev) |
| **Python** | 3.11+ | Backend development (local) |
| **Git** | — | Version control |

### 1. Clone the Repository

```bash
git clone <repository-url>
cd geoviable
```

### 2. Configure Environment Variables

Copy the template and customize it:

```bash
cp .env.example .env
```

Edit `.env` with your preferred editor. Key variables:

| Variable | Description | Development Default |
|---|---|---|
| `POSTGRES_DB` | Database name | `geoviable` |
| `POSTGRES_USER` | Database user | `geoviable` |
| `POSTGRES_PASSWORD` | Database password | `geoviable_dev_2026!` |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+psycopg2://geoviable:geoviable_dev_2026!@geoviable-db:5432/geoviable` |
| `ENVIRONMENT` | Runtime mode | `development` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG` |
| `CORS_ORIGINS` | Allowed origins | `http://localhost:3000,http://localhost:5173` |

> **Production:** Generate a strong password with `openssl rand -base64 32` and set `CORS_ORIGINS=https://geoviable.movilab.es`.

### 3. First-Time Setup (Docker Compose)

```bash
# Build the frontend
cd frontend && npm install && npm run build && cd ..

# Start all services
docker compose up -d --build

# Check service health
docker compose ps

# View logs
docker compose logs -f geoviable-api
```

### 4. Verify the Installation

Once all containers are running:

| Service | URL | Description |
|---|---|---|
| **Frontend** | http://localhost:80 | React app (served by Nginx) |
| **API Docs** | http://localhost:80/api/v1/docs | FastAPI Swagger UI |
| **Health Check** | http://localhost:80/api/v1/health | Service status |

### 5. Load Initial Environmental Data

On first run, the database has no environmental layers. You must load them:

```bash
# Option A: Automated (requires internet + MITECO/CNIG availability)
docker compose exec geoviable-api python -m scripts.update_layers

# Option B: Manual (recommended for first setup)
# 1. Download shapefiles manually from MITECO/CNIG (see specs/Fuentes_de_datos.md)
# 2. Place them in the data/ directory
# 3. Run the initialization script
docker compose exec geoviable-api python -m scripts.load_initial_data
```

## Development

### Backend (FastAPI) — Local Dev

```bash
# Create virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start development server (hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs will be at: http://localhost:8000/docs

### Frontend (React) — Local Dev

```bash
cd frontend
npm install
npm start  # or npm run dev
```

App will be at: http://localhost:3000 (or 5173 if using Vite)

### Running Tests

```bash
# Backend tests
cd backend
pytest -v

# Frontend tests
cd frontend
npm test
```

## Useful Docker Commands

```bash
# View all running services
docker compose ps

# Follow all logs
docker compose logs -f

# Access the database
docker compose exec geoviable-db psql -U geoviable -d geoviable

# Execute spatial queries manually
docker compose exec geoviable-db psql -U geoviable -d geoviable -c "SELECT COUNT(*) FROM red_natura_2000;"

# Run layer update manually
docker compose exec geoviable-api python -m scripts.update_layers

# Database backup
docker compose exec geoviable-db pg_dump -U geoviable geoviable | gzip > backups/backup_$(date +%Y%m%d).sql.gz

# Database restore
gunzip -c backups/backup_20260401.sql.gz | docker compose exec -T geoviable-db psql -U geoviable -d geoviable

# Rebuild a single service
docker compose up -d --build geoviable-api

# Full reset (destroys data!)
docker compose down -v
```

## Database Connection Details

| Parameter | Value |
|---|---|
| **Host (internal)** | `geoviable-db` (Docker network) |
| **Host (external)** | Not exposed to host in production |
| **Port** | 5432 |
| **Database** | `geoviable` |
| **User** | `geoviable` |
| **Password** | As defined in `.env` |
| **PostGIS Version** | 3.4+ |
| **Storage CRS** | ETRS89 / UTM zone 30N (EPSG:25830) |

### Connecting from Host (Development Only)

If you need to connect to PostgreSQL from your host machine during development, add this to `docker-compose.yml` under the `geoviable-db` service:

```yaml
ports:
  - "5432:5432"  # Only for local development
```

Then connect with:
```bash
psql -h localhost -U geoviable -d geoviable
```

Or with a GUI client like pgAdmin / DBeaver using:
- Host: `localhost`
- Port: `5432`
- Database: `geoviable`
- User: `geoviable`
- Password: (from `.env`)

## Architecture Overview

```
Internet → Cloudflare (DNS + proxy) → Oracle Cloud VM :443
  → Nginx (SSL termination + reverse proxy)
    → /api/*  → geoviable-api:8000 (FastAPI)
    → /*      → React static files (Nginx)

FastAPI ↔ geoviable-db:5432 (PostgreSQL + PostGIS)
Cron Job → update_layers.py → monthly layer refresh
```

## Environmental Layers

| # | Layer | Source | Update Frequency |
|---|---|---|---|
| 1 | Red Natura 2000 (ZEPA + LIC/ZEC) | MITECO | Annual |
| 2 | Flood Zones (SNCZI, T100+T500) | MITECO | Irregular |
| 3 | Hydraulic Public Domain (DPH) | MITECO | Irregular |
| 4 | Livestock Routes (Vías Pecuarias) | CNIG | Annual |
| 5 | Protected Natural Spaces (ENP) | MITECO | Annual |
| 6 | Surface Water Masses | MITECO | 6-year PHC cycle |
| 7 | Groundwater Masses | MITECO | 6-year PHC cycle |

All layers are stored in EPSG:25830 (ETRS89 / UTM 30N). User polygons arrive in EPSG:4326 (WGS84) and are reprojected server-side via `ST_Transform`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/analyze` | Spatial analysis → JSON response (dev utility) |
| `POST` | `/api/v1/report/generate` | Spatial analysis → PDF report (production endpoint) |
| `GET` | `/api/v1/layers/status` | Check layer update status |
| `GET` | `/api/v1/health` | Health check |

Full API reference: [specs/API_reference.md](specs/API_reference.md)

## Operational Limits (MVP)

| Parameter | Limit |
|---|---|
| Maximum polygon area | 10,000 ha (100 km²) |
| Maximum vertices | 10,000 |
| Maximum upload size | 5 MB |
| Polygons per request | 1 (single polygon only) |
| Analysis timeout | 30 seconds |

## Deployment to Production

See [specs/DevOps_y_despliegue.md](specs/DevOps_y_despliegue.md) for full deployment instructions.

Summary:

```bash
# 1. Clone on OCI server
git clone <repo-url> && cd geoviable

# 2. Configure production .env
cp .env.example .env
nano .env  # Set production values

# 3. Build frontend
cd frontend && npm install && npm run build && cd ..

# 4. Deploy
docker compose up -d --build

# 5. Verify
docker compose ps
docker compose logs -f geoviable-api
```

## License

Internal use only — GeoViable / movilab.es
