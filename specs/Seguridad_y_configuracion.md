# GeoViable — Seguridad y configuración

## 1. Variables de entorno

Todas las variables configurables se gestionan mediante un archivo `.env` en la raíz del proyecto (no versionado en Git).

### Variables del backend (`geoviable-api`)

| Variable | Descripción | Ejemplo | Requerida |
|---|---|---|---|
| `DATABASE_URL` | URI de conexión a PostgreSQL | `postgresql://geoviable:secret@geoviable-db:5432/geoviable` | ✅ |
| `DB_HOST` | Host de la BD (si no se usa DATABASE_URL) | `geoviable-db` | — |
| `DB_PORT` | Puerto de la BD | `5432` | — |
| `DB_NAME` | Nombre de la BD | `geoviable` | — |
| `DB_USER` | Usuario de la BD | `geoviable` | — |
| `DB_PASSWORD` | Contraseña de la BD | `(generada)` | ✅ |
| `ENVIRONMENT` | Entorno de ejecución | `production` \| `development` | ✅ |
| `LOG_LEVEL` | Nivel de logging | `INFO` \| `DEBUG` | — |
| `MAX_POLYGON_AREA_KM2` | Área máxima del polígono (km²) | `100` | — |
| `MAX_POLYGON_VERTICES` | Vértices máximos del polígono | `10000` | — |
| `MAX_UPLOAD_SIZE_MB` | Tamaño máximo de payload (MB) | `5` | — |
| `QUERY_TIMEOUT_SECONDS` | Timeout de queries PostGIS | `30` | — |
| `CORS_ORIGINS` | Orígenes permitidos (comma-separated) | `https://geoviable.movilab.es` | ✅ |

### Variables de la base de datos (`geoviable-db`)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `POSTGRES_DB` | Nombre de la BD a crear | `geoviable` |
| `POSTGRES_USER` | Usuario administrador | `geoviable` |
| `POSTGRES_PASSWORD` | Contraseña del usuario | `(generada)` |

### Archivo `.env` de ejemplo

```env
# === Base de datos ===
POSTGRES_DB=geoviable
POSTGRES_USER=geoviable
POSTGRES_PASSWORD=CAMBIAR_POR_PASSWORD_SEGURO

# === Backend ===
DATABASE_URL=postgresql://geoviable:CAMBIAR_POR_PASSWORD_SEGURO@geoviable-db:5432/geoviable
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_POLYGON_AREA_KM2=100
MAX_POLYGON_VERTICES=10000
MAX_UPLOAD_SIZE_MB=5
QUERY_TIMEOUT_SECONDS=30
CORS_ORIGINS=https://geoviable.movilab.es
```

> **Regla:** El archivo `.env` **nunca** se versiona en Git. Se incluye `.env` en `.gitignore` y se mantiene un `.env.example` (sin secretos) como referencia.

## 2. CORS (Cross-Origin Resource Sharing)

Configuración de FastAPI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ["https://geoviable.movilab.es"]
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

| Origen permitido | Entorno |
|---|---|
| `https://geoviable.movilab.es` | Producción |
| `http://localhost:3000` | Desarrollo local |

## 3. HTTPS / TLS

| Aspecto | Decisión |
|---|---|
| Certificado SSL | Let's Encrypt (gratuito, renovación automática) o Cloudflare proxy |
| Terminación SSL | En Nginx (contenedor `geoviable-web`) |
| HTTP → HTTPS redirect | Sí, automático en Nginx |
| HSTS | Activado (`Strict-Transport-Security: max-age=31536000`) |

### Configuración Nginx para SSL

```nginx
server {
    listen 80;
    server_name geoviable.movilab.es;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name geoviable.movilab.es;

    ssl_certificate     /etc/letsencrypt/live/geoviable.movilab.es/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/geoviable.movilab.es/privkey.pem;

    # Seguridad
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend (archivos estáticos)
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;  # SPA routing
    }

    # API backend
    location /api/ {
        proxy_pass http://geoviable-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout para generación de PDF
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;

        # Límite de payload
        client_max_body_size 5M;
    }
}
```

## 4. Validación y sanitización de inputs

### GeoJSON como vector de ataque

El GeoJSON que envía el usuario es el principal punto de entrada de datos. Riesgos y mitigaciones:

| Riesgo | Mitigación |
|---|---|
| Payload excesivamente grande | Límite de 5 MB en Nginx (`client_max_body_size`) y en FastAPI |
| JSON malformado o malicioso | Parseo con `json.loads()` + validación Pydantic |
| Geometría inválida (auto-intersección) | Validación con `shapely.is_valid` + intento de reparación con `make_valid` |
| Polígono fuera de Galicia | Verificación de bbox antes de enviar query a PostGIS |
| Demasiados vértices (DoS por query pesada) | Límite de 10.000 vértices |
| Área excesiva (query lenta) | Límite de 100 km² + `statement_timeout` en PostgreSQL |
| SQL injection vía GeoJSON | Uso exclusivo de queries parametrizadas (SQLAlchemy bind params) |

### Límite de tamaño en FastAPI

```python
from fastapi import Request

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        if content_length > settings.max_upload_size_bytes:
            return JSONResponse(status_code=413, content={
                "error": {"code": "PAYLOAD_TOO_LARGE", "message": "..."}
            })
    return await call_next(request)
```

## 5. Rate limiting (MVP)

En el MVP no se implementa rate limiting formal dado que:
- La API es de uso interno.
- No hay autenticación.
- El número de usuarios es muy bajo.

**Preparación para el futuro:** Si se abre al público, añadir `slowapi` (basado en `limits`):

```python
# Ejemplo futuro (no implementar en MVP)
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
# 10 informes por hora por IP
@limiter.limit("10/hour")
```

## 6. Secretos y credenciales

| Secreto | Almacenamiento | Rotación |
|---|---|---|
| Contraseña de PostgreSQL | `.env` (no versionado) | Manual, cuando sea necesario |
| Claves SSH del servidor | `~/.ssh/` en el servidor OCI | Al configurar el servidor |

> En el MVP no hay API keys, tokens JWT, ni secretos de terceros. Si se añade autenticación en el futuro, considerar HashiCorp Vault o Docker secrets.

## 7. Archivos en `.gitignore`

```gitignore
# Secretos
.env
*.pem
*.key

# Datos
data/
*.shp
*.dbf
*.shx
*.prj
*.cpg

# Python
__pycache__/
*.pyc
.venv/
venv/

# Node
node_modules/
frontend/build/

# IDE
.vscode/
.idea/

# Docker
docker-compose.override.yml
```
