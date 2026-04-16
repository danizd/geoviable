# GeoViable — Esquema de base de datos (PostGIS)

## 1. Configuración general

```sql
-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- CRS por defecto para todas las geometrías: ETRS89 / UTM 30N
-- SRID: 25830
```

## 2. Tabla de metadatos: `layer_update_log`

Registra cada intento de actualización de capas (éxito o fallo).

```sql
CREATE TABLE layer_update_log (
    id              SERIAL PRIMARY KEY,
    layer_name      VARCHAR(100) NOT NULL,       -- Nombre de la tabla destino
    status          VARCHAR(20) NOT NULL,        -- 'success' | 'failed'
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    records_loaded  INTEGER,                     -- nº de registros cargados (NULL si falló)
    source_url      TEXT,                        -- URL de origen de la descarga
    error_message   TEXT,                        -- Detalle del error (NULL si éxito)
    file_hash       VARCHAR(64)                  -- SHA-256 del archivo descargado (para detectar si cambió)
);

CREATE INDEX idx_lul_layer_name ON layer_update_log(layer_name);
CREATE INDEX idx_lul_started_at ON layer_update_log(started_at DESC);
```

## 3. Capas ambientales

### 3.1. Red Natura 2000 (ZEPA + LIC/ZEC)

```sql
CREATE TABLE red_natura_2000 (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(20) NOT NULL,        -- Código del espacio (ej. "ES1110001")
    nombre      VARCHAR(255) NOT NULL,       -- Nombre oficial
    tipo        VARCHAR(10) NOT NULL,        -- 'ZEPA' | 'LIC' | 'ZEC'
    superficie_ha NUMERIC(12, 2),            -- Superficie oficial en hectáreas
    geom        GEOMETRY(MultiPolygon, 25830) NOT NULL
);

CREATE INDEX idx_rn2000_geom ON red_natura_2000 USING GIST (geom);
CREATE INDEX idx_rn2000_tipo ON red_natura_2000(tipo);
```

### 3.2. Zonas inundables (SNCZI)

```sql
CREATE TABLE zonas_inundables (
    id                  SERIAL PRIMARY KEY,
    periodo_retorno     VARCHAR(10) NOT NULL,    -- 'T100' | 'T500'
    nivel_peligrosidad  VARCHAR(50),             -- Nivel de peligrosidad si está disponible
    demarcacion         VARCHAR(100),            -- Demarcación hidrográfica
    geom                GEOMETRY(MultiPolygon, 25830) NOT NULL
);

CREATE INDEX idx_zi_geom ON zonas_inundables USING GIST (geom);
CREATE INDEX idx_zi_periodo ON zonas_inundables(periodo_retorno);
```

### 3.3. Dominio Público Hidráulico (DPH)

```sql
CREATE TABLE dominio_publico_hidraulico (
    id              SERIAL PRIMARY KEY,
    tipo            VARCHAR(50) NOT NULL,        -- 'cauce' | 'ribera' | 'margen'
    nombre_cauce    VARCHAR(255),                -- Nombre del cauce/río
    categoria       VARCHAR(100),                -- Categoría del tramo
    geom            GEOMETRY(MultiPolygon, 25830) NOT NULL
);

CREATE INDEX idx_dph_geom ON dominio_publico_hidraulico USING GIST (geom);
```

### 3.4. Vías pecuarias

```sql
CREATE TABLE vias_pecuarias (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(255),                -- Nombre de la vía pecuaria
    tipo_via        VARCHAR(100),                -- 'cañada' | 'cordel' | 'vereda' | 'colada'
    anchura_legal_m NUMERIC(6, 2),               -- Anchura legal en metros
    longitud_m      NUMERIC(12, 2),              -- Longitud total en metros
    estado_deslinde VARCHAR(50),                 -- 'deslindada' | 'sin_deslindar' | 'parcial'
    municipio       VARCHAR(100),
    provincia       VARCHAR(50),
    geom            GEOMETRY(MultiLineString, 25830) NOT NULL  -- Las vías son líneas, no polígonos
);

CREATE INDEX idx_vp_geom ON vias_pecuarias USING GIST (geom);

-- Nota: Para calcular la intersección con el polígono del usuario, se usará
-- ST_Buffer(vp.geom, vp.anchura_legal_m / 2) para crear un polígono virtual
-- basado en la anchura legal de la vía.
```

### 3.5. Espacios Naturales Protegidos (ENP)

```sql
CREATE TABLE espacios_naturales_protegidos (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(20),                 -- Código oficial
    nombre          VARCHAR(255) NOT NULL,       -- Nombre del espacio
    categoria       VARCHAR(100) NOT NULL,       -- 'Parque Nacional' | 'Parque Natural' | 'Reserva' | 'Monumento Natural' | etc.
    subcategoria    VARCHAR(100),                -- Subcategoría si aplica
    superficie_ha   NUMERIC(12, 2),              -- Superficie oficial
    geom            GEOMETRY(MultiPolygon, 25830) NOT NULL
);

CREATE INDEX idx_enp_geom ON espacios_naturales_protegidos USING GIST (geom);
CREATE INDEX idx_enp_categoria ON espacios_naturales_protegidos(categoria);
```

### 3.6. Masas de agua superficiales

```sql
CREATE TABLE masas_agua_superficial (
    id                  SERIAL PRIMARY KEY,
    codigo_masa         VARCHAR(100),            -- Código de la masa de agua
    nombre              VARCHAR(255),            -- Nombre
    tipo                VARCHAR(100),            -- 'río' | 'lago' | 'embalse' | 'costera' | 'transición'
    categoria           VARCHAR(100),            -- Categoría según PHC
    estado_ecologico    VARCHAR(50),             -- 'bueno' | 'moderado' | 'deficiente' | 'malo'
    estado_quimico      VARCHAR(50),             -- 'bueno' | 'no alcanza buen estado'
    demarcacion         VARCHAR(100),            -- Demarcación hidrográfica
    geom                GEOMETRY(Geometry, 25830) NOT NULL  -- Puede ser Polygon o LineString
);

CREATE INDEX idx_mas_geom ON masas_agua_superficial USING GIST (geom);
```

### 3.7. Masas de agua subterráneas

```sql
CREATE TABLE masas_agua_subterranea (
    id                  SERIAL PRIMARY KEY,
    codigo_masa         VARCHAR(30),             -- Código de la masa
    nombre              VARCHAR(255),            -- Nombre
    estado_cuantitativo VARCHAR(50),             -- 'bueno' | 'malo'
    estado_quimico      VARCHAR(50),             -- 'bueno' | 'malo'
    superficie_km2      NUMERIC(10, 2),          -- Superficie
    demarcacion         VARCHAR(100),
    geom                GEOMETRY(MultiPolygon, 25830) NOT NULL
);

CREATE INDEX idx_masub_geom ON masas_agua_subterranea USING GIST (geom);
```

## 4. Notas de diseño

### Tipo de geometría

- Se usa `MultiPolygon` para la mayoría de capas porque los Shapefiles oficiales frecuentemente contienen MultiPolygons incluso para entidades simples.
- Las **vías pecuarias** se almacenan como `MultiLineString` porque son trazados lineales. Para el cálculo de afección, se genera un buffer virtual basado en la anchura legal.
- Las **masas de agua superficiales** usan `Geometry` genérico porque pueden ser ríos (líneas) o lagos/embalses (polígonos).

### Columnas y nombres

- Los nombres de columna exactos pueden variar dependiendo de los campos disponibles en los Shapefiles descargados de MITECO/CNIG.
- El script `update_layers.py` deberá mapear los campos originales del Shapefile a los nombres definidos aquí.
- Si un campo no existe en los datos originales, se deja como `NULL`.

### Mantenimiento

```sql
-- Ejecutar después de cada actualización masiva de datos:
VACUUM ANALYZE red_natura_2000;
VACUUM ANALYZE zonas_inundables;
VACUUM ANALYZE dominio_publico_hidraulico;
VACUUM ANALYZE vias_pecuarias;
VACUUM ANALYZE espacios_naturales_protegidos;
VACUUM ANALYZE masas_agua_superficial;
VACUUM ANALYZE masas_agua_subterranea;
```
