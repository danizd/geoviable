-- ==============================================================================
-- GeoViable — Database Initialization Script
-- ==============================================================================
-- Runs automatically on first PostgreSQL container creation.
-- Creates PostGIS extensions and all environmental layer tables.
-- ==============================================================================

-- ── Extensions ──
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- ── Layer update log (metadata) ──
CREATE TABLE IF NOT EXISTS layer_update_log (
    id              SERIAL PRIMARY KEY,
    layer_name      VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    records_loaded  INTEGER,
    source_url      TEXT,
    error_message   TEXT,
    file_hash       VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_lul_layer_name ON layer_update_log(layer_name);
CREATE INDEX IF NOT EXISTS idx_lul_started_at ON layer_update_log(started_at DESC);

-- ── 1. Red Natura 2000 (ZEPA + LIC/ZEC) ──
CREATE TABLE IF NOT EXISTS red_natura_2000 (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(20) NOT NULL,
    nombre          VARCHAR(255) NOT NULL,
    tipo            VARCHAR(10) NOT NULL,
    superficie_ha   NUMERIC(12, 2),
    geom            GEOMETRY(MultiPolygon, 25830) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rn2000_geom ON red_natura_2000 USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_rn2000_tipo ON red_natura_2000(tipo);

-- ── 2. Zonas inundables (SNCZI) ──
CREATE TABLE IF NOT EXISTS zonas_inundables (
    id                  SERIAL PRIMARY KEY,
    periodo_retorno     VARCHAR(10) NOT NULL,
    nivel_peligrosidad  VARCHAR(50),
    demarcacion         VARCHAR(100),
    geom                GEOMETRY(MultiPolygon, 25830) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_zi_geom ON zonas_inundables USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_zi_periodo ON zonas_inundables(periodo_retorno);

-- ── 3. Dominio Público Hidráulico (DPH) ──
CREATE TABLE IF NOT EXISTS dominio_publico_hidraulico (
    id              SERIAL PRIMARY KEY,
    tipo            VARCHAR(50),
    nombre_cauce    VARCHAR(255),
    categoria       VARCHAR(100),
    demarcacion     VARCHAR(100),
    geom            GEOMETRY(MultiPolygon, 25830) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dph_geom ON dominio_publico_hidraulico USING GIST (geom);

-- ── 4. Vías pecuarias ──
CREATE TABLE IF NOT EXISTS vias_pecuarias (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(255),
    tipo_via        VARCHAR(100),
    anchura_legal_m NUMERIC(6, 2),
    longitud_m      NUMERIC(12, 2),
    estado_deslinde VARCHAR(50),
    municipio       VARCHAR(100),
    provincia       VARCHAR(50),
    geom            GEOMETRY(MultiLineString, 25830) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vp_geom ON vias_pecuarias USING GIST (geom);

-- ── 5. Espacios Naturales Protegidos (ENP) ──
CREATE TABLE IF NOT EXISTS espacios_naturales_protegidos (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(20),
    nombre          VARCHAR(255) NOT NULL,
    categoria       VARCHAR(100) NOT NULL,
    subcategoria    VARCHAR(100),
    superficie_ha   NUMERIC(12, 2),
    geom            GEOMETRY(MultiPolygon, 25830) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_enp_geom ON espacios_naturales_protegidos USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_enp_categoria ON espacios_naturales_protegidos(categoria);

-- ── 6. Masas de agua superficiales ──
CREATE TABLE IF NOT EXISTS masas_agua_superficial (
    id                  SERIAL PRIMARY KEY,
    codigo_masa         VARCHAR(100),
    nombre              VARCHAR(255),
    tipo                VARCHAR(100),
    categoria           VARCHAR(100),
    estado_ecologico    VARCHAR(50),
    estado_quimico      VARCHAR(50),
    demarcacion         VARCHAR(100),
    geom                GEOMETRY(Geometry, 25830) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mas_geom ON masas_agua_superficial USING GIST (geom);

-- ── 7. Masas de agua subterráneas ──
CREATE TABLE IF NOT EXISTS masas_agua_subterranea (
    id                  SERIAL PRIMARY KEY,
    codigo_masa         VARCHAR(100),
    nombre              VARCHAR(255),
    estado_cuantitativo VARCHAR(50),
    estado_quimico      VARCHAR(50),
    superficie_km2      NUMERIC(10, 2),
    demarcacion         VARCHAR(100),
    geom                GEOMETRY(MultiPolygon, 25830) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_masub_geom ON masas_agua_subterranea USING GIST (geom);
