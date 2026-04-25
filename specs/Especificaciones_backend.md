# GeoViable — Especificaciones del backend

## 1. Stack y estructura del proyecto

### Dependencias principales de Python

| Paquete | Propósito |
|---|---|
| `fastapi` | Framework API REST |
| `uvicorn` | Servidor ASGI |
| `sqlalchemy` + `geoalchemy2` | ORM con soporte PostGIS |
| `psycopg2-binary` | Driver PostgreSQL |
| `pydantic` | Validación de schemas |
| `shapely` | Validación y manipulación de geometrías Python |
| `geopandas` | Lectura de Shapefiles para `update_layers.py` |
| `weasyprint` | Renderizado HTML → PDF |
| `jinja2` | Plantillas HTML para el PDF |
| `contextily` | Descarga de tiles para mapa estático |
| `matplotlib` | Renderizado de mapa estático (imagen) |
| `requests` | Descarga HTTP de capas |
| `beautifulsoup4` | Scraping de enlaces de descarga en páginas MITECO |
| `pyproj` | Reproyección de coordenadas |

### Estructura de directorios del backend

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # Punto de entrada FastAPI
│   ├── config.py                 # Variables de entorno (Settings)
│   ├── models/
│   │   ├── __init__.py
│   │   └── layers.py             # Modelos SQLAlchemy/GeoAlchemy2
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── analysis.py           # Schemas Pydantic de request/response
│   │   └── report.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py             # Router principal (/api/v1)
│   │   ├── analyze.py            # Endpoint /analyze
│   │   ├── report.py             # Endpoint /report/generate
│   │   └── layers.py             # Endpoint /layers/status
│   ├── services/
│   │   ├── __init__.py
│   │   ├── spatial_analysis.py   # Lógica de cruce espacial con PostGIS
│   │   ├── pdf_generator.py      # Generación del PDF con WeasyPrint
│   │   ├── static_map.py         # Generación del mapa estático (contextily)
│   │   └── geojson_validator.py  # Validación y sanitización del GeoJSON
│   ├── templates/
│   │   └── report/
│   │       ├── base.html         # Plantilla base Jinja2 del PDF
│   │       ├── cover.html        # Portada
│   │       ├── results.html      # Tabla de afecciones
│   │       └── styles.css        # Estilos del PDF
│   └── static/
│       └── logo.png              # Logo para el PDF
├── scripts/
│   └── update_layers.py          # Script de actualización mensual de capas
├── tests/
│   ├── test_analysis.py
│   ├── test_validation.py
│   └── fixtures/
│       └── sample_polygon.geojson
├── Dockerfile
└── requirements.txt
```

## 2. Lógica de validación del GeoJSON

El servicio `geojson_validator.py` realiza las siguientes validaciones en orden:

| # | Validación | Código de error | HTTP |
|---|---|---|---|
| 1 | JSON válido (parseo correcto) | `INVALID_JSON` | 400 |
| 2 | Estructura GeoJSON válida (`Feature` o `FeatureCollection`) | `INVALID_GEOJSON` | 400 |
| 3 | Solo 1 Feature de tipo `Polygon` o `MultiPolygon` simple | `MULTIPLE_FEATURES` | 400 |
| 4 | Geometría de tipo `Polygon` (no Point, LineString, etc.) | `INVALID_GEOMETRY_TYPE` | 400 |
| 5 | Topología válida con Shapely (`is_valid`). Si no, intentar `make_valid()` | `INVALID_TOPOLOGY` | 400 |
| 6 | Coordenadas dentro del bbox de Galicia ampliado: `[-9.5, 41.5, -6.5, 44.0]` | `OUT_OF_BOUNDS` | 400 |
| 7 | Área del polígono ≤ 100 km² (calculada reproyectando a EPSG:25830) | `AREA_TOO_LARGE` | 400 |
| 8 | Número de vértices ≤ 10.000 | `TOO_MANY_VERTICES` | 400 |

Si la geometría tiene topología inválida pero es reparable con `shapely.make_valid()`, se repara automáticamente y se continúa. Si no es reparable, se rechaza.

## 3. Servicio de análisis espacial (`spatial_analysis.py`)

### Capas a cruzar

El servicio itera sobre las siguientes tablas en orden:

| Tabla en BD | Nombre en informe | Campos de resultado |
|---|---|---|
| `red_natura_2000` | Red Natura 2000 | nombre, tipo (ZEPA/LIC/ZEC), código, % solape |
| `zonas_inundables` | Zonas inundables (SNCZI) | periodo_retorno (T100/T500), % solape |
| `dominio_publico_hidraulico` | Dominio Público Hidráulico | tipo, nombre_cauce, % solape |
| `vias_pecuarias` | Vías pecuarias | nombre, anchura_legal_m, longitud_afectada_m |
| `espacios_naturales_protegidos` | Espacios Naturales Protegidos | nombre, categoria, % solape |
| `masas_agua_superficial` | Masas de agua superficiales | nombre, tipo, estado_ecologico |
| `masas_agua_subterranea` | Masas de agua subterráneas | nombre, estado_quimico |

### Patrón de query SQL

Para cada capa, se ejecuta una consulta que:

1. Reproyecta el polígono del usuario de EPSG:4326 a EPSG:25830 con `ST_Transform`.
2. Filtra con `ST_Intersects` usando el índice GIST.
3. Calcula el área de intersección con `ST_Area(ST_Intersection(...))`.
4. Calcula el porcentaje de solape como `(area_intersección / area_parcela) * 100`.

El polígono del usuario se transforma **una sola vez** al inicio de la función usando una CTE (Common Table Expression) para evitar repetir la reproyección:

```sql
WITH user_parcel AS (
    SELECT ST_Transform(
        ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326),
        25830
    ) AS geom
)
SELECT
    layer.nombre,
    layer.tipo,
    ROUND(
        100.0 * ST_Area(ST_Intersection(layer.geom, up.geom))
        / ST_Area(up.geom),
        2
    ) AS porcentaje_solape,
    ST_Area(ST_Intersection(layer.geom, up.geom)) AS area_interseccion_m2
FROM red_natura_2000 layer, user_parcel up
WHERE ST_Intersects(layer.geom, up.geom);
```

### Timeout

- La query SQL se ejecuta con un timeout de **30 segundos** (`statement_timeout` de PostgreSQL).
- Si se excede, se devuelve HTTP 504 con mensaje descriptivo.

## 4. Servicio de generación de mapa estático (`static_map.py`)

Genera una imagen PNG del polígono del usuario superpuesto a un mapa base.

| Aspecto | Detalle |
|---|---|
| Librería | `contextily` (descargar tiles) + `matplotlib` + `geopandas` |
| Mapa base | `PNOA` (WMTS IGN) u `OpenStreetMap` (fallback automático también a CartoDB Positron) |
| Formato de salida | PNG, 300 DPI, ~1200×800 px |
| Contenido | Polígono del usuario (borde `#334155`, relleno semitransparente) + afecciones superpuestas con colores diferenciados |
| Margen | Bbox del polígono con un 20% de padding |

### Flujo

1. Crear un `GeoDataFrame` con el polígono del usuario en EPSG:25830.
2. Reproyectar a EPSG:3857 (Web Mercator) para alinear con los tiles.
3. Seleccionar proveedores según `project.basemap` recibido en `/report/generate`:
    - Si `basemap == "PNOA"`, intentar primero WMTS IGN (`OI.OrthoimageCoverage`).
    - En cualquier caso, fallback secuencial a OpenStreetMap y CartoDB Positron.
4. Añadir tiles de fondo con `contextily.add_basemap()`.
5. Superponer las geometrías de las afecciones detectadas (con leyenda por color).
6. Guardar como PNG en buffer de memoria.
7. Devolver bytes de la imagen para inyectar en la plantilla HTML del PDF.

## 5. Servicio de generación de PDF (`pdf_generator.py`)

### Flujo

1. Recibir resultados del análisis espacial + imagen del mapa estático.
2. Renderizar la plantilla Jinja2 (`report/base.html`) inyectando los datos.
3. Convertir el HTML renderizado a PDF con `WeasyPrint`.
4. Devolver el PDF como bytes (sin guardar en disco).

> Ver [Informe_PDF_plantilla.md](Informe_PDF_plantilla.md) para la estructura completa del PDF.

## 6. Gestión de errores

### Códigos HTTP de respuesta

| Código | Escenario |
|---|---|
| 200 | Análisis JSON completado con éxito |
| 200 | PDF generado con éxito (content-type: application/pdf) |
| 400 | GeoJSON inválido (topología, tipo, límites) |
| 413 | Payload demasiado grande (> 5 MB) |
| 422 | Error de validación Pydantic (campos requeridos) |
| 500 | Error interno del servidor |
| 504 | Timeout de la consulta PostGIS (> 30s) |

### Formato de error estándar

```json
{
    "error": {
        "code": "AREA_TOO_LARGE",
        "message": "El polígono excede el área máxima permitida (100 km²). Área recibida: 152.3 km².",
        "details": {
            "max_area_km2": 100,
            "received_area_km2": 152.3
        }
    }
}
```

## 7. Logging

- Formato: JSON estructurado (para fácil parseo).
- Niveles: DEBUG (dev), INFO (producción).
- Eventos a registrar:
  - Cada request recibida (método, path, IP, tamaño payload).
  - Resultado de cada análisis (nº de afecciones encontradas, tiempo de query).
  - Errores de validación (qué validación falló y por qué).
  - Errores de generación de PDF.
  - Actualizaciones de capas (éxito/fallo, nº registros).