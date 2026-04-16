# GeoViable

> Herramienta automatizada de evaluación de viabilidad ambiental para parcelas y proyectos en Galicia, España.

**URL de producción:** https://geoviable.movilab.es/

## Descripción

GeoViable es una herramienta interna (Micro-SaaS B2B) que automatiza la evaluación de viabilidad ambiental de parcelas. Cruza polígonos definidos por el usuario con capas ambientales oficiales (Red Natura 2000, zonas inundables, Dominio Público Hidráulico, vías pecuarias, Espacios Naturales Protegidos, masas de agua) y genera un informe técnico PDF al instante.

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| **Infraestructura** | Oracle Cloud Always Free (ARM, 24 GB RAM, 200 GB disco) |
| **Orquestación** | Docker Compose |
| **Base de datos** | PostgreSQL 15+ con PostGIS 3.4+ |
| **Backend** | Python 3.11 + FastAPI |
| **Generación PDF** | WeasyPrint (plantillas Jinja2 → HTML → PDF) |
| **Mapa estático** | contextily + matplotlib + geopandas |
| **Frontend** | React.js + React Leaflet + Leaflet-Geoman |
| **Servidor web** | Nginx (proxy inverso + archivos estáticos) |
| **HTTPS** | Let's Encrypt / Cloudflare |

## Estructura del Proyecto

```
geoviable/
├── .env.example                  # Plantilla de variables de entorno (seguro commitear)
├── .env                          # Entorno local (NUNCA commitear — gitignored)
├── .gitignore
├── docker-compose.yml            # Orquestación Docker de producción
├── README.md                     # ← Estás aquí
├── start.bat                     # Script de inicio local (Windows)
├── specs/                        # Especificaciones técnicas completas
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
├── backend/                      # Backend FastAPI Python
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # Punto de entrada FastAPI
│   │   ├── config.py             # Configuración Pydantic (variables de entorno)
│   │   ├── database.py           # Conexión y sesión SQLAlchemy
│   │   ├── models/               # Modelos SQLAlchemy + GeoAlchemy2
│   │   ├── schemas/              # Schemas Pydantic request/response
│   │   ├── api/                  # Handlers de rutas API
│   │   ├── services/             # Lógica de negocio (análisis, PDF, validación)
│   │   ├── templates/report/     # Plantillas HTML Jinja2 para PDF
│   │   └── static/               # Recursos estáticos (logo, etc.)
│   ├── initdb/
│   │   └── 01_init.sql           # SQL de inicialización (montado como dir en Docker)
│   ├── scripts/
│   │   ├── update_layers.py      # Cron mensual de actualización de capas
│   │   ├── load_initial_data.py  # Carga manual desde ZIPs locales
│   │   ├── init_db.sql           # SQL de inicialización de BD (referencia/uso manual)
│   │   ├── entrypoint.sh         # Entrypoint del contenedor (cron + uvicorn)
│   │   └── crontab               # Programación cron para actualización de capas
│   └── tests/                    # Suite de tests con pytest
├── frontend/                     # Aplicación React.js
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── components/           # Componentes React (MapViewer, ToolPanel, etc.)
│       ├── services/             # Cliente API, parsers de archivos
│       ├── utils/                # Validaciones
│       ├── App.jsx
│       └── index.js
├── nginx/
│   └── conf.d/
│       ├── default.conf.prod     # Config Nginx producción (SSL + proxy inverso)
│       └── local-dev.conf        # Config Nginx desarrollo local (HTTP sin SSL)
├── certs/                        # Certificados SSL (no versionado)
├── data/                         # Shapefiles descargados (no versionado)
├── backups/                      # Backups de base de datos (no versionado)
└── tmp/                          # Archivos temporales (no versionado)
```

## Inicio Rápido

### Requisitos

| Herramienta | Versión mínima | Propósito |
|---|---|---|
| **Docker** | 24.0+ | Ejecución de contenedores |
| **Docker Compose** | 2.20+ | Orquestación de servicios |
| **Node.js** | 18.x (LTS) | Build del frontend |
| **Python** | 3.11+ | Desarrollo backend local |
| **Git** | — | Control de versiones |

### 1. Clonar el Repositorio

```bash
git clone https://github.com/danizd/geoviable.git
cd geoviable
```

### 2. Configurar Variables de Entorno

Copiar la plantilla y personalizar:

```bash
cp .env.example .env
```

Editar `.env` con tu editor preferido. Variables clave:

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `POSTGRES_DB` | Nombre de la base de datos | `geoviable` |
| `POSTGRES_USER` | Usuario de la base de datos | `geoviable` |
| `POSTGRES_PASSWORD` | Contraseña de la base de datos | `geoviable_dev_2026!` |
| `DATABASE_URL` | Cadena de conexión SQLAlchemy | `postgresql+psycopg2://geoviable:geoviable_dev_2026!@geoviable-db:5432/geoviable` |
| `ENVIRONMENT` | Modo de ejecución | `development` |
| `LOG_LEVEL` | Nivel de logging | `debug` |
| `CORS_ORIGINS` | Orígenes permitidos | `http://localhost:3000,http://localhost:5173` |

> **Producción:** Genera una contraseña segura con `openssl rand -base64 32` y configura `CORS_ORIGINS=https://geoviable.movilab.es`.

### 3. Configuración Inicial

```bash
# Construir el frontend
cd frontend && npm install && npm run build && cd ..

# Iniciar todos los servicios
docker compose up -d --build

# Verificar estado de los servicios
docker compose ps
```

### 4. Verificar la Instalación

Cuando todos los contenedores están corriendo:

| Servicio | URL | Descripción |
|---|---|---|
| **Frontend** | http://localhost:3000 | Aplicación React (servida por Nginx) |
| **API Docs** | http://localhost:8000/docs | Swagger UI de FastAPI |
| **Health Check** | http://localhost:8000/api/v1/health | Estado del servicio |

### 5. Cargar Datos Ambientales Iniciales

Al ejecutar por primera vez, la base de datos no tiene capas ambientales. Debes cargarlas mediante una de estas opciones:

#### Opción A — Carga manual desde ZIPs (recomendada)

Los ZIPs de datos ambientales preprocesados (shapefiles oficiales de MITECO/CNIG) están disponibles bajo petición:

> **Solicita los ZIPs a:** [daniel.zas.dacosta@gmail.com](mailto:daniel.zas.dacosta@gmail.com)

Una vez recibidos, coloca los ficheros en `backend/data/` con estos nombres exactos:

| Fichero | Capa |
|---|---|
| `red_natura_2000.zip` | Red Natura 2000 (ZEPA + LIC/ZEC) |
| `zonas_inundables_t100.zip` | Zonas inundables período de retorno T100 |
| `zonas_inundables_t500.zip` | Zonas inundables período de retorno T500 |
| `dph.zip` | Dominio Público Hidráulico |
| `vias_pecuarias.zip` | Vías pecuarias |
| `enp.zip` | Espacios Naturales Protegidos |
| `masas_agua_superficial.zip` | Masas de agua superficiales |
| `masas_agua_subterranea.zip` | Masas de agua subterráneas |

Luego ejecuta el script de carga:

```bash
# (Opcional) Inspeccionar columnas y valores de demarcación antes de cargar
docker compose exec geoviable-api python -m scripts.load_initial_data --inspect

# Cargar todas las capas
docker compose exec geoviable-api python -m scripts.load_initial_data

# Cargar solo una capa (si falla o quieres recargar)
docker compose exec geoviable-api python -m scripts.load_initial_data --layer red_natura_2000
```

Capas disponibles para `--layer`: `red_natura_2000`, `zonas_inundables`, `dominio_publico_hidraulico`, `vias_pecuarias`, `espacios_naturales_protegidos`, `masas_agua_superficial`, `masas_agua_subterranea`.

Al finalizar, el script imprime el conteo de registros cargados en cada tabla. Todos deben ser > 0.

#### Opción B — Actualización automatizada (requiere internet)

```bash
# Descarga y carga desde MITECO/CNIG directamente (puede fallar si las URLs cambian)
docker compose exec geoviable-api python -m scripts.update_layers
```

## Desarrollo

### Backend (FastAPI) — Desarrollo Local

```bash
# Crear entorno virtual
cd backend
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor de desarrollo (hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación API en: http://localhost:8000/docs

### Frontend (React) — Desarrollo Local

```bash
cd frontend
npm install
npm start
```

La aplicación estará en: http://localhost:3000

### Ejecutar Tests

```bash
# Tests del backend
cd backend
pytest -v

# Tests del frontend
cd frontend
npm test
```

## Comandos Útiles de Docker

```bash
# Ver servicios en ejecución
docker compose ps

# Seguir logs en tiempo real
docker compose logs -f

# Acceder a la base de datos
docker compose exec geoviable-db psql -U geoviable -d geoviable

# Ejecutar consultas espaciales
docker compose exec geoviable-db psql -U geoviable -d geoviable -c "SELECT COUNT(*) FROM red_natura_2000;"

# Actualizar capas manualmente
docker compose exec geoviable-api python -m scripts.update_layers

# Backup de la base de datos
docker compose exec geoviable-db pg_dump -U geoviable geoviable | gzip > backups/backup_$(date +%Y%m%d).sql.gz

# Restaurar base de datos
gunzip -c backups/backup_20260401.sql.gz | docker compose exec -T geoviable-db psql -U geoviable -d geoviable

# Reconstruir un servicio individual
docker compose up -d --build geoviable-api

# Reset completo (¡destruye datos!)
docker compose down -v
```

## Detalles de la Base de Datos

| Parámetro | Valor |
|---|---|
| **Host (interno)** | `geoviable-db` (red Docker) |
| **Puerto** | 5432 |
| **Base de datos** | `geoviable` |
| **Usuario** | `geoviable` |
| **Contraseña** | La definida en `.env` |
| **Versión PostGIS** | 3.4+ |
| **CRS de almacenamiento** | ETRS89 / UTM zona 30N (EPSG:25830) |

### Conectar desde el Host (Solo Desarrollo)

Si necesitas conectar PostgreSQL desde tu máquina local durante el desarrollo, añade esto en `docker-compose.yml` bajo el servicio `geoviable-db`:

```yaml
ports:
  - "5432:5432"  # Solo desarrollo local
```

Luego conecta con:
```bash
psql -h localhost -U geoviable -d geoviable
```

O con un cliente GUI como pgAdmin / DBeaver:
- Host: `localhost`
- Puerto: `5432`
- Base de datos: `geoviable`
- Usuario: `geoviable`
- Contraseña: (la de `.env`)

## Arquitectura

```
Internet → Cloudflare (DNS + proxy) → Oracle Cloud VM :443
  → Nginx (terminación SSL + proxy inverso)
    → /api/*  → geoviable-api:8000 (FastAPI)
    → /*      → Archivos estáticos React (Nginx)

FastAPI ↔ geoviable-db:5432 (PostgreSQL + PostGIS)
Cron Job → update_layers.py → actualización mensual de capas
```

## Capas Ambientales

| # | Capa | Fuente | Frecuencia de actualización |
|---|---|---|---|
| 1 | Red Natura 2000 (ZEPA + LIC/ZEC) | MITECO | Anual |
| 2 | Zonas inundables (SNCZI, T100+T500) | MITECO | Irregular |
| 3 | Dominio Público Hidráulico (DPH) | MITECO | Irregular |
| 4 | Vías pecuarias | CNIG | Anual |
| 5 | Espacios Naturales Protegidos (ENP) | MITECO | Anual |
| 6 | Masas de agua superficiales | MITECO | Ciclo PHC 6 años |
| 7 | Masas de agua subterráneas | MITECO | Ciclo PHC 6 años |

Todas las capas se almacenan en EPSG:25830 (ETRS89 / UTM 30N). Los polígonos del usuario llegan en EPSG:4326 (WGS84) y se reproyectan en el servidor con `ST_Transform`.

## Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/v1/analyze` | Análisis espacial → respuesta JSON (utilidad dev) |
| `POST` | `/api/v1/report/generate` | Análisis espacial → informe PDF (endpoint producción) |
| `GET` | `/api/v1/layers/status` | Estado de actualización de capas |
| `GET` | `/api/v1/health` | Health check |

Referencia completa de la API: [specs/API_reference.md](specs/API_reference.md)

## Límites Operativos (MVP)

| Parámetro | Límite |
|---|---|
| Área máxima del polígono | 10.000 ha (100 km²) |
| Vértices máximos | 10.000 |
| Tamaño máximo de subida | 5 MB |
| Polígonos por solicitud | 1 (solo un polígono) |
| Timeout de análisis | 30 segundos |

## Despliegue en Producción

Ver [specs/DevOps_y_despliegue.md](specs/DevOps_y_despliegue.md) para instrucciones completas.

Resumen:

```bash
# 1. Clonar en servidor OCI
git clone https://github.com/danizd/geoviable.git && cd geoviable

# 2. Configurar .env de producción
cp .env.example .env
nano .env  # Valores de producción

# 3. Construir frontend
cd frontend && npm install && npm run build && cd ..

# 4. Desplegar
docker compose up -d --build

# 5. Verificar
docker compose ps
docker compose logs -f geoviable-api
```

## Notas de Desarrollo Local

### Problemas de red al hacer pull de imágenes

Si Docker no puede acceder a Docker Hub (timeout de red), las imágenes se obtienen automáticamente de **AWS ECR Public** (`public.ecr.aws/docker/library/`), que es un mirror configurado en `docker-compose.yml` y `backend/Dockerfile`.

### Nginx local (sin SSL)

En desarrollo local, Nginx usa la configuración `nginx/conf.d/local-dev.conf` que **no requiere certificados SSL**. El archivo de producción (`default.conf.prod`) se ignora en local.

### Frontend

El frontend debe construirse antes de iniciar los servicios. Si modificas el código React:

```bash
cd frontend && npm run build
```

Los cambios se reflejan automáticamente porque `frontend/build/` está montado como volumen en Nginx.

## Solución de Problemas Post-Despliegue

Si después de ejecutar `docker compose up -d --build` algo no funciona, revisa esta lista en orden:

### 1. El contenedor API se reinicia continuamente (estado `Restarting`)

**Síntoma:** `docker compose ps` muestra `geoviable-api` en estado `Restarting` con exit code 255.

**Causa probable:** Los scripts de entrada tienen saltos de línea Windows (CRLF) que rompen el shebang `#!/bin/bash` en Linux.

```bash
# Verificar logs del contenedor
docker logs geoviable-api --tail 5
# Si ves: "exec ./entrypoint.sh: no such file or directory" → es CRLF
```

**Solución:**
```bash
# En Windows (PowerShell):
powershell -Command "(Get-Content -Raw backend\scripts\entrypoint.sh) -replace \"`r`n\",\"`n\" | Set-Content -NoNewline backend\scripts\entrypoint.sh"
powershell -Command "(Get-Content -Raw backend\scripts\crontab) -replace \"`r`n\",\"`n\" | Set-Content -NoNewline backend\scripts\crontab"

# Reconstruir el contenedor
docker compose up -d --build geoviable-api
```

> **Prevención:** Añade un archivo `.gitattributes` con `*.sh text eol=lf` y `*.sh text eol=lf` al repositorio para que Git normalice los saltos de línea automáticamente.

---

### 2. Nginx devuelve "403 Forbidden" al acceder a http://localhost

**Síntoma:** El navegador muestra un error 403 al abrir http://localhost.

**Causa probable:** La carpeta `frontend/build/` está vacía — nunca se compiló la aplicación React.

```bash
# Verificar si hay archivos en el build
dir frontend\build
# Si está vacío → necesita compilación
```

**Solución:**
```bash
cd frontend
npm install
npm run build
cd ..
```

> **Nota:** Este paso debe ejecutarse **antes** del primer `docker compose up -d` y cada vez que modifiques el código frontend.

---

### 3. La API devuelve error 500 — `function st_geomfromgeojson does not exist`

**Síntoma:** Al llamar a `/api/v1/report/generate` o `/api/v1/analyze`, la respuesta es 500 con el error mencionado.

**Causa probable:** La extensión PostGIS no está instalada en la base de datos. Esto ocurre cuando el archivo `init_db.sql` no se ejecutó en la creación inicial del contenedor (porque era un directorio en lugar de un archivo, o porque el contenedor ya existía).

**Solución:**
```bash
# Instalar PostGIS manualmente
docker exec geoviable-db psql -U geoviable -d geoviable -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Crear las tablas
docker exec -i geoviable-db psql -U geoviable -d geoviable < backend\initdb\01_init.sql

# Si no existe init_db.sql, créalo a partir del esquema en specs/Esquema_base_datos.md
```

**Verificación:**
```bash
docker exec geoviable-db psql -U geoviable -d geoviable -c "\dt"
# Deberías ver las 7 tablas de capas + layer_update_log
```

---

### 4. El informe PDF aparece vacío (riesgo "NINGUNO", 0 capas con afección)

**Síntoma:** El PDF se genera correctamente pero todas las capas muestran "No" en la columna de afección y "—" en solapamiento.

**Causa probable:** Las tablas de capas están vacías (0 registros). Esto es **esperable en una instalación fresca** — los datos ambientales deben cargarse explícitamente.

**Diagnóstico:**
```bash
docker exec geoviable-db psql -U geoviable -d geoviable -c "
  SELECT 'red_natura_2000' AS tbl, count(*) FROM red_natura_2000
  UNION ALL SELECT 'zonas_inundables', count(*) FROM zonas_inundables
  UNION ALL SELECT 'dominio_publico_hidraulico', count(*) FROM dominio_publico_hidraulico
  UNION ALL SELECT 'vias_pecuarias', count(*) FROM vias_pecuarias
  UNION ALL SELECT 'espacios_naturales_protegidos', count(*) FROM espacios_naturales_protegidos
  UNION ALL SELECT 'masas_agua_superficial', count(*) FROM masas_agua_superficial
  UNION ALL SELECT 'masas_agua_subterranea', count(*) FROM masas_agua_subterranea;
"
```

**Solución — Carga manual desde ZIPs (recomendado):**
```bash
# Solicita los ZIPs a daniel.zas.dacosta@gmail.com y colócalos en backend/data/
docker compose exec geoviable-api python -m scripts.load_initial_data
```

**Solución — Actualización automatizada (requiere internet):**
```bash
# Descarga desde MITECO/CNIG (puede fallar si las URLs han cambiado)
docker compose exec geoviable-api python -m scripts.update_layers
```

**Solución — Cargar datos de muestra (desarrollo/testing):**
```bash
# Verificar que init_db.sql existe como archivo (no como directorio)
dir backend\scripts\init_db.sql

# Si la tabla es un directorio, eliminarla y crear el archivo correcto:
rmdir /s /q backend\scripts\init_db.sql
# Luego crear backend\scripts\init_db.sql con el DDL de specs/Esquema_base_datos.md
```

> **Cuidado con las coordenadas:** Si usas datos de muestra propios, asegúrate de que están en **EPSG:25830 (UTM zona 30N)**. Coordenadas en UTM zona 29N (X: ~680.000-730.000) no intersectarán con polígonos proyectados a zona 30N (X: ~20.000-60.000 para Galicia occidental).

---

### 5. Diagnóstico rápido completo

Si no estás seguro de qué falla, ejecuta esta secuencia:

```bash
# 1. Estado de contenedores
docker compose ps

# 2. Logs del API (buscar errores)
docker logs geoviable-api --tail 30

# 3. Health check de la API
curl http://localhost:8000/api/v1/health

# 4. Verificar PostGIS
docker exec geoviable-db psql -U geoviable -d geoviable -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'postgis';"

# 5. Verificar datos en tablas
docker exec geoviable-db psql -U geoviable -d geoviable -c "SELECT COUNT(*) FROM red_natura_2000;"

# 6. Probar el endpoint de análisis con un polígono de prueba
curl -X POST http://localhost:8000/api/v1/analyze ^
  -H "Content-Type: application/json" ^
  -d "{\"type\":\"Feature\",\"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[-8.65,42.95],[-8.55,42.95],[-8.55,43.02],[-8.65,43.02],[-8.65,42.95]]]},\"properties\":{}}"
```

---

## Despliegue en Producción (Oracle Cloud)

El servidor de producción es una instancia Oracle Cloud Always Free (ARM, 24 GB RAM) con **Nginx Proxy Manager** como proxy inverso externo.

### Arquitectura de puertos en producción

| Servicio | Puerto externo (host) | Puerto interno (contenedor) |
|---|---|---|
| Frontend (Nginx) | 3000 | 80 |
| API (FastAPI) | 8001 | 8000 |
| Base de datos | no expuesto | 5432 |

Nginx Proxy Manager enruta el tráfico externo hacia estos puertos. Dentro de la red Docker, el frontend hace proxy de `/api/` hacia `geoviable-api:8000`.

### Primer despliegue

```bash
# 1. Clonar el repositorio
git clone https://github.com/danizd/geoviable.git
cd geoviable

# 2. Crear el fichero de configuración
cp .env.example .env
# Editar .env con los valores de producción

# 3. Subir los ZIPs de datos ambientales a backend/data/
# (solicitar a daniel.zas.dacosta@gmail.com)

# 4. Arrancar los servicios con el compose de Oracle
docker compose -f docker-compose-oracle.yml up -d --build
```

> El frontend ya está compilado en `frontend/build/` dentro del repositorio — no es necesario instalar npm en el servidor.

### Actualizar a la última versión

```bash
git pull origin master
docker compose -f docker-compose-oracle.yml up -d --build
```

Si el backend cambió (Dockerfile o dependencias Python), Docker reconstruirá la imagen automáticamente gracias a `--build`. La base de datos y sus datos **no se pierden** porque el volumen `pgdata` persiste.

### Reset completo (borra la BD)

```bash
docker compose -f docker-compose-oracle.yml down -v
docker compose -f docker-compose-oracle.yml up -d --build
# Después recargar los datos ambientales:
docker compose -f docker-compose-oracle.yml exec geoviable-api python -m scripts.load_initial_data
```

### Actualizar solo el frontend (sin rebuild)

```bash
# En local: compilar y subir
cd frontend && npm run build && cd ..
git add frontend/build/
git commit -m "build: actualizar frontend"
git push

# En el servidor:
git pull origin master
docker compose -f docker-compose-oracle.yml restart geoviable-web
```

### Comandos útiles en producción

```bash
# Estado de los servicios
docker compose -f docker-compose-oracle.yml ps

# Logs en tiempo real
docker compose -f docker-compose-oracle.yml logs -f

# Logs solo del API
docker compose -f docker-compose-oracle.yml logs -f geoviable-api

# Health check
curl http://localhost:8001/api/v1/health
```

---

## Licencia

Uso interno — GeoViable / movilab.es
