# GeoViable — Referencia de API

**Base URL:** `https://geoviable.movilab.es/api/v1`

## Autenticación

Sin autenticación en el MVP. La API es de acceso libre.

---

## Endpoints

### 1. `POST /analyze`

Recibe la geometría del usuario y devuelve los resultados del análisis espacial en JSON.

> **Uso en implementación actual:** además de depuración, el frontend lo usa para previsualizar afecciones en el mapa antes de generar el PDF.

#### Request

**Content-Type:** `application/json`  
**Tamaño máximo del body:** 5 MB

```json
{
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-8.5449, 42.8782],
                [-8.5400, 42.8782],
                [-8.5400, 42.8750],
                [-8.5449, 42.8750],
                [-8.5449, 42.8782]
            ]
        ]
    },
    "properties": {}
}
```

#### Validaciones

| Regla | Código de error | HTTP |
|---|---|---|
| JSON válido | `INVALID_JSON` | 400 |
| GeoJSON válido (Feature o FeatureCollection con 1 Feature) | `INVALID_GEOJSON` | 400 |
| Solo tipo Polygon o MultiPolygon simple | `INVALID_GEOMETRY_TYPE` | 400 |
| Solo 1 polígono | `MULTIPLE_FEATURES` | 400 |
| Topología válida (no se auto-intersecta) | `INVALID_TOPOLOGY` | 400 |
| Dentro del bbox de Galicia `[-9.5, 41.5, -6.5, 44.0]` | `OUT_OF_BOUNDS` | 400 |
| Área ≤ 100 km² | `AREA_TOO_LARGE` | 400 |
| Vértices ≤ 10.000 | `TOO_MANY_VERTICES` | 400 |

#### Response — 200 OK

```json
{
    "analysis": {
        "parcel": {
            "area_m2": 25430.5,
            "area_ha": 2.54,
            "centroid": [-8.5424, 42.8766],
            "crs_used": "EPSG:25830"
        },
        "layers": [
            {
                "layer_name": "Red Natura 2000",
                "affected": true,
                "features": [
                    {
                        "nombre": "Complexo húmido de Corrubedo",
                        "tipo": "ZEC",
                        "codigo": "ES1110006",
                        "area_interseccion_m2": 12500.3,
                        "porcentaje_solape": 49.15
                    }
                ]
            },
            {
                "layer_name": "Zonas inundables (SNCZI)",
                "affected": false,
                "features": []
            },
            {
                "layer_name": "Dominio Público Hidráulico",
                "affected": false,
                "features": []
            },
            {
                "layer_name": "Vías pecuarias",
                "affected": false,
                "features": []
            },
            {
                "layer_name": "Espacios Naturales Protegidos",
                "affected": true,
                "features": [
                    {
                        "nombre": "Parque Natural Corrubedo",
                        "categoria": "Parque Natural",
                        "area_interseccion_m2": 25430.5,
                        "porcentaje_solape": 100.0
                    }
                ]
            },
            {
                "layer_name": "Masas de agua superficiales",
                "affected": false,
                "features": []
            },
            {
                "layer_name": "Masas de agua subterráneas",
                "affected": false,
                "features": []
            }
        ],
        "summary": {
            "total_layers_checked": 7,
            "layers_affected": 2,
            "overall_risk": "alto"
        },
        "metadata": {
            "data_updated_at": "2026-04-01T03:00:00Z",
            "analysis_duration_ms": 342
        }
    }
}
```

#### Campo `overall_risk` (derivado)

| Condición | Valor |
|---|---|
| 0 capas afectadas | `"ninguno"` |
| 1-2 capas afectadas, todas con < 10% solape | `"bajo"` |
| 1-2 capas afectadas, alguna con ≥ 10% solape | `"medio"` |
| 3+ capas afectadas, o Red Natura / ENP con ≥ 50% solape | `"alto"` |
| Afección total a DPH o zona inundable T100 | `"muy alto"` |

> **Nota:** Este indicador es orientativo y no sustituye un estudio ambiental formal.

#### Response — Error (ejemplo)

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

---

### 2. `POST /report/generate`

Realiza el análisis espacial y genera un informe PDF completo.

> **Endpoint principal** para el flujo de producción.

#### Request

**Content-Type:** `application/json`  
**Tamaño máximo del body:** 5 MB

```json
{
    "geojson": {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-8.5449, 42.8782],
                    [-8.5400, 42.8782],
                    [-8.5400, 42.8750],
                    [-8.5449, 42.8750],
                    [-8.5449, 42.8782]
                ]
            ]
        },
        "properties": {}
    },
    "project": {
        "name": "Ampliación nave industrial — Parcela 234",
        "author": "Estudio Técnico López",
        "description": "Evaluación previa para licencia urbanística",
        "basemap": "PNOA"
    }
}
```

#### Campos del objeto `project`

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `name` | string | ✅ | 3-100 caracteres |
| `author` | string | ❌ | 0-100 caracteres |
| `description` | string | ❌ | 0-500 caracteres |
| `basemap` | string | ❌ | `PNOA` u `OpenStreetMap` (default backend: `OpenStreetMap`) |

#### Validaciones

Mismas validaciones del GeoJSON que en `/analyze`, más:
- `project.name` es obligatorio y debe tener 3-100 caracteres.
- Si `project.basemap` no se envía, el backend usa `OpenStreetMap` para el mapa estático del PDF.

#### Response — 200 OK

**Content-Type:** `application/pdf`  
**Content-Disposition:** `attachment; filename="GeoViable_Informe_{project_name}_{fecha}.pdf"`

El cuerpo de la respuesta es el archivo PDF binario.

#### Response — Errores

Mismos códigos que `/analyze`, más:

| Código | Escenario | HTTP |
|---|---|---|
| `MISSING_GEOJSON` | Falta el campo `geojson` en el body | 422 |
| `MISSING_PROJECT_NAME` | No se proporcionó nombre del proyecto | 422 |
| `PROJECT_NAME_TOO_LONG` | Nombre de proyecto > 100 caracteres | 422 |
| `PDF_GENERICATION_FAILED` | Error interno al generar el PDF | 500 |

---

### 3. `GET /layers/status`

Devuelve el estado de actualización de las capas ambientales.

#### Request

Sin parámetros.

#### Response — 200 OK

```json
{
    "layers": [
        {
            "name": "red_natura_2000",
            "display_name": "Red Natura 2000",
            "last_updated": "2026-04-01T03:12:45Z",
            "status": "success",
            "records_count": 1247
        },
        {
            "name": "zonas_inundables",
            "display_name": "Zonas inundables (SNCZI)",
            "last_updated": "2026-04-01T03:15:30Z",
            "status": "success",
            "records_count": 3891
        },
        {
            "name": "dominio_publico_hidraulico",
            "display_name": "Dominio Público Hidráulico",
            "last_updated": "2026-04-01T03:18:02Z",
            "status": "success",
            "records_count": 5623
        },
        {
            "name": "vias_pecuarias",
            "display_name": "Vías pecuarias",
            "last_updated": "2026-04-01T03:20:15Z",
            "status": "success",
            "records_count": 342
        },
        {
            "name": "espacios_naturales_protegidos",
            "display_name": "Espacios Naturales Protegidos",
            "last_updated": "2026-04-01T03:22:30Z",
            "status": "success",
            "records_count": 89
        },
        {
            "name": "masas_agua_superficial",
            "display_name": "Masas de agua superficiales",
            "last_updated": "2026-04-01T03:25:00Z",
            "status": "success",
            "records_count": 2156
        },
        {
            "name": "masas_agua_subterranea",
            "display_name": "Masas de agua subterráneas",
            "last_updated": "2026-04-01T03:27:00Z",
            "status": "success",
            "records_count": 45
        }
    ],
    "last_global_update": "2026-04-01T03:27:00Z"
}
```

---

### 4. `GET /health`

Health check para monitorización y Docker healthcheck.

#### Response — 200 OK

```json
{
    "status": "healthy",
    "database": "connected",
    "version": "1.0.0"
}
```

#### Response — 503 Service Unavailable

```json
{
    "status": "unhealthy",
    "database": "disconnected",
    "version": "1.0.0"
}
```
