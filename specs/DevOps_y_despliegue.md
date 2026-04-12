# GeoViable — DevOps y despliegue

## 1. Docker Compose (producción)

```yaml
# docker-compose.yml
version: "3.9"

services:
  # ────────────────────────────────────────────────────
  # Base de datos PostgreSQL + PostGIS
  # ────────────────────────────────────────────────────
  geoviable-db:
    image: postgis/postgis:15-3.4
    container_name: geoviable-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/scripts/init_db.sql:/docker-entrypoint-initdb.d/01_init.sql:ro
    networks:
      - geoviable-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    # NO expone puertos al host — solo accesible desde la red interna

  # ────────────────────────────────────────────────────
  # Backend FastAPI + WeasyPrint + Cron
  # ────────────────────────────────────────────────────
  geoviable-api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: geoviable-api
    restart: unless-stopped
    depends_on:
      geoviable-db:
        condition: service_healthy
    environment:
      DATABASE_URL: ${DATABASE_URL}
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      MAX_POLYGON_AREA_KM2: ${MAX_POLYGON_AREA_KM2:-100}
      MAX_POLYGON_VERTICES: ${MAX_POLYGON_VERTICES:-10000}
      MAX_UPLOAD_SIZE_MB: ${MAX_UPLOAD_SIZE_MB:-5}
      QUERY_TIMEOUT_SECONDS: ${QUERY_TIMEOUT_SECONDS:-30}
      CORS_ORIGINS: ${CORS_ORIGINS}
    volumes:
      - ./backend/app/templates:/app/templates:ro
      - ./backend/app/static:/app/static:ro
    networks:
      - geoviable-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    # NO expone puertos al host

  # ────────────────────────────────────────────────────
  # Nginx (proxy inverso + frontend estático)
  # ────────────────────────────────────────────────────
  geoviable-web:
    image: nginx:1.25-alpine
    container_name: geoviable-web
    restart: unless-stopped
    depends_on:
      - geoviable-api
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./frontend/build:/usr/share/nginx/html:ro
      - ./certs:/etc/letsencrypt:ro
    networks:
      - geoviable-net

volumes:
  pgdata:
    driver: local

networks:
  geoviable-net:
    driver: bridge
```

## 2. Dockerfile del backend

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# Dependencias del sistema para WeasyPrint y GDAL (PostGIS/GeoPandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    # GDAL para GeoPandas
    gdal-bin \
    libgdal-dev \
    # Cron
    cron \
    # Utilidades
    curl \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY app/ ./app/
COPY scripts/ ./scripts/

# Configurar cron job para actualización mensual
COPY scripts/crontab /etc/cron.d/geoviable-cron
RUN chmod 0644 /etc/cron.d/geoviable-cron && \
    crontab /etc/cron.d/geoviable-cron

# Script de entrada
COPY scripts/entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
```

### Script de entrada (`entrypoint.sh`)

```bash
#!/bin/bash
set -e

# Arrancar cron en background
cron

# Arrancar el servidor FastAPI
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --log-level ${LOG_LEVEL:-info}
```

### Crontab (`scripts/crontab`)

```cron
# Actualización mensual de capas ambientales
# Día 1 de cada mes a las 03:00 UTC
0 3 1 * * cd /app && python -m scripts.update_layers >> /var/log/geoviable_update.log 2>&1
```

## 3. Script SQL de inicialización

El archivo `backend/scripts/init_db.sql` se ejecuta automáticamente al crear el contenedor de BD por primera vez:

```sql
-- Activar extensiones
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Crear tablas (ver Esquema_base_datos.md para el DDL completo)
-- Este script debe incluir todos los CREATE TABLE + CREATE INDEX
```

## 4. Comandos de despliegue

### Primera vez (setup inicial)

```bash
# 1. Clonar repositorio en el servidor OCI
git clone https://github.com/tu-usuario/geoviable.git
cd geoviable

# 2. Crear archivo .env desde el ejemplo
cp .env.example .env
nano .env  # Editar con valores reales

# 3. Compilar el frontend
cd frontend
npm install
npm run build
cd ..

# 4. Levantar los contenedores
docker compose up -d --build

# 5. Verificar salud de los servicios
docker compose ps
docker compose logs -f geoviable-api

# 6. Cargar datos iniciales (primera vez)
docker compose exec geoviable-api python -m scripts.load_initial_data
```

### Actualización de código

```bash
# 1. Obtener cambios
git pull origin main

# 2. Reconstruir contenedores afectados
docker compose up -d --build geoviable-api

# 3. Si hay cambios en el frontend
cd frontend && npm run build && cd ..
docker compose restart geoviable-web

# 4. Verificar
docker compose logs -f geoviable-api --tail=50
```

### Comandos útiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Acceder a la BD
docker compose exec geoviable-db psql -U geoviable -d geoviable

# Ejecutar actualización de capas manualmente
docker compose exec geoviable-api python -m scripts.update_layers

# Backup de la BD
docker compose exec geoviable-db pg_dump -U geoviable geoviable > backup_$(date +%Y%m%d).sql

# Restaurar backup
cat backup_20260401.sql | docker compose exec -T geoviable-db psql -U geoviable -d geoviable
```

## 5. Backups

### Estrategia de backup

| Aspecto | Decisión |
|---|---|
| Qué se respalda | Solo la base de datos (el código está en Git) |
| Herramienta | `pg_dump` |
| Frecuencia | Diario a las 02:00 UTC |
| Retención | 7 días (últimos 7 backups) |
| Almacenamiento | En el disco del servidor + opcionalmente Oracle Object Storage |

### Script de backup (`scripts/backup_db.sh`)

```bash
#!/bin/bash
BACKUP_DIR="/opt/geoviable/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/geoviable_${TIMESTAMP}.sql.gz"

# Crear backup comprimido
docker compose exec -T geoviable-db pg_dump -U geoviable geoviable | gzip > "${BACKUP_FILE}"

# Eliminar backups de más de 7 días
find "${BACKUP_DIR}" -name "geoviable_*.sql.gz" -mtime +7 -delete

echo "[$(date)] Backup creado: ${BACKUP_FILE}"
```

### Crontab del host (servidor OCI)

```cron
# Backup diario a las 02:00 UTC
0 2 * * * /opt/geoviable/scripts/backup_db.sh >> /var/log/geoviable_backup.log 2>&1
```

## 6. Monitorización

### Health checks

| Servicio | Endpoint / Comando | Frecuencia |
|---|---|---|
| PostgreSQL | `pg_isready` | 10s |
| FastAPI | `GET /api/v1/health` | 30s |
| Nginx | Puerto 443 abierto | — |

### Logging centralizado

- Los logs de todos los contenedores son accesibles vía `docker compose logs`.
- El backend escribe logs JSON a stdout (capturado por Docker).
- Para monitorización avanzada en el futuro: considerar Prometheus + Grafana o un servicio SaaS como Better Stack.

### Alertas básicas (MVP)

En el MVP no se implementa un sistema de alertas formal. Se recomienda:
- Revisar periódicamente `docker compose ps` para verificar que todos los contenedores están `Up`.
- Revisar los logs del cron de actualización (`/var/log/geoviable_update.log`).
- Consultar `GET /api/v1/layers/status` para verificar que las capas están actualizadas.

## 7. Consideraciones ARM (Oracle Cloud)

| Aspecto | Nota |
|---|---|
| Imágenes Docker | Usar imágenes con soporte `linux/arm64` (la mayoría de imágenes oficiales lo soportan) |
| WeasyPrint | Funciona en ARM; las dependencias de sistema (Pango, Cairo) están disponibles en los repos de Debian/Ubuntu ARM64 |
| Playwright (fallback scraping) | Chromium tiene builds ARM64; instalar con `playwright install chromium` |
| GDAL | Disponible en repos de Debian ARM64 (`gdal-bin`, `libgdal-dev`) |
| Rendimiento | ARM Ampere A1 ofrece buen rendimiento para cargas de trabajo como PostGIS y generación de PDF |

## 8. Estructura de directorios del proyecto completo

```
geoviable/
├── CLAUDE.md                          # Contexto global del proyecto
├── .env.example                       # Variables de entorno (sin secretos)
├── .gitignore
├── docker-compose.yml
├── specs/                             # Especificaciones (documentación)
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
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── services/
│   │   ├── templates/
│   │   └── static/
│   ├── scripts/
│   │   ├── update_layers.py
│   │   ├── load_initial_data.py
│   │   ├── init_db.sql
│   │   ├── backup_db.sh
│   │   ├── entrypoint.sh
│   │   └── crontab
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── components/
│       │   ├── MapViewer.jsx
│       │   ├── ToolPanel.jsx
│       │   ├── DrawTools.jsx
│       │   ├── FileUploader.jsx
│       │   ├── ProjectForm.jsx
│       │   ├── GenerateReport.jsx
│       │   └── LayerStatus.jsx
│       ├── services/
│       │   ├── api.js
│       │   └── fileParser.js
│       ├── utils/
│       │   └── validation.js
│       ├── App.jsx
│       ├── App.css
│       └── index.js
├── nginx/
│   └── conf.d/
│       └── default.conf
└── certs/                             # Certificados SSL (no versionados)
```
