"""
GeoViable — Spatial Analysis Service

Crosses the user's parcel against all 7 environmental layers using
PostGIS spatial queries (ST_Intersects, ST_Area, ST_Intersection).

Each query uses a CTE to reproject the user's polygon once, then
computes intersection area and overlap percentage per affected feature.
"""

import json
import logging
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("geoviable")

# ── Layer definitions for iteration ──
# Each entry maps a database table to its human-readable display name
# and defines the SELECT columns and overlap calculation approach.
LAYERS_CONFIG = [
    {
        "table": "red_natura_2000",
        "alias": "rn",
        "display_name": "Red Natura 2000",
        "columns": "rn.nombre, rn.tipo, rn.codigo",
        "extra_fields": {"tipo": "tipo", "codigo": "codigo"},
    },
    {
        "table": "zonas_inundables",
        "alias": "zi",
        "display_name": "Zonas inundables (SNCZI)",
        "columns": "zi.periodo_retorno, zi.nivel_peligrosidad, zi.demarcacion",
        "extra_fields": {"periodo_retorno": "periodo_retorno"},
    },
    {
        "table": "dominio_publico_hidraulico",
        "alias": "dph",
        "display_name": "Dominio Público Hidráulico",
        "columns": "dph.tipo, dph.nombre_cauce, dph.categoria",
        "extra_fields": {"nombre_cauce": "nombre_cauce"},
    },
    {
        "table": "vias_pecuarias",
        "alias": "vp",
        "display_name": "Vías pecuarias",
        "columns": (
            "vp.nombre, vp.tipo_via, vp.anchura_legal_m, vp.longitud_m, "
            "vp.estado_deslinde, vp.municipio, vp.provincia"
        ),
        "extra_fields": {
            "anchura_legal_m": "anchura_legal_m",
            "longitud_afectada_m": "ST_Length(ST_Intersection(vp.geom, up.geom))",
        },
        "is_linear": True,
    },
    {
        "table": "espacios_naturales_protegidos",
        "alias": "enp",
        "display_name": "Espacios Naturales Protegidos",
        "columns": "enp.nombre, enp.categoria, enp.subcategoria, enp.superficie_ha",
        "extra_fields": {"categoria": "categoria"},
    },
    {
        "table": "masas_agua_superficial",
        "alias": "mas",
        "display_name": "Masas de agua superficiales",
        "columns": (
            "mas.nombre, mas.tipo, mas.categoria, "
            "mas.estado_ecologico, mas.estado_quimico, mas.demarcacion"
        ),
        "extra_fields": {
            "tipo": "tipo",
            "estado_ecologico": "estado_ecologico",
        },
    },
    {
        "table": "masas_agua_subterranea",
        "alias": "masub",
        "display_name": "Masas de agua subterráneas",
        "columns": (
            "masub.nombre, masub.estado_cuantitativo, "
            "masub.estado_quimico, masub.superficie_km2, masub.demarcacion"
        ),
        "extra_fields": {
            "estado_cuantitativo": "estado_cuantitativo",
            "estado_quimico": "estado_quimico",
        },
    },
]


def run_spatial_analysis(db: Session, geojson_str: str) -> dict[str, Any]:
    """
    Execute the full spatial analysis against all environmental layers.

    Parameters
    ----------
    db : Session
        Active SQLAlchemy database session.
    geojson_str : str
        Validated GeoJSON Feature string (EPSG:4326) from geojson_validator.

    Returns
    -------
    dict
        Complete analysis result with parcel info, per-layer features,
        summary, and metadata.
    """
    start_time = time.perf_counter()

    # ── Parse GeoJSON to extract coordinates ──
    geojson = json.loads(geojson_str)
    geometry = geojson["geometry"]

    # ── Build the parcel CTE and compute parcel metadata ──
    parcel_info = _compute_parcel_info(db, geometry)

    # ── Query each layer ──
    layer_results = []
    for layer_cfg in LAYERS_CONFIG:
        features = _query_layer(db, geometry, layer_cfg)
        layer_results.append({
            "layer_name": layer_cfg["table"],
            "display_name": layer_cfg["display_name"],
            "affected": len(features) > 0,
            "features": features,
        })

    # ── Compute summary ──
    layers_affected = sum(1 for lr in layer_results if lr["affected"])
    overall_risk = _compute_overall_risk(layer_results)

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return {
        "parcel": parcel_info,
        "layers": layer_results,
        "summary": {
            "total_layers_checked": len(LAYERS_CONFIG),
            "layers_affected": layers_affected,
            "overall_risk": overall_risk,
        },
        "metadata": {
            "analysis_duration_ms": round(elapsed_ms, 1),
        },
    }


def _compute_parcel_info(db: Session, geometry: dict) -> dict:
    """
    Compute parcel area (m² and ha) and centroid (lon/lat).

    Uses ST_Transform to reproject from EPSG:4326 to EPSG:25830.
    """
    geom_json = json.dumps(geometry)

    query = text("""
        WITH user_parcel AS (
            SELECT ST_Transform(
                ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                25830
            ) AS geom
        )
        SELECT
            ST_Area(up.geom) AS area_m2,
            ST_X(ST_Transform(ST_Centroid(up.geom), 4326)) AS centroid_lon,
            ST_Y(ST_Transform(ST_Centroid(up.geom), 4326)) AS centroid_lat
        FROM user_parcel up
    """)

    result = db.execute(query, {"geom": geom_json}).fetchone()

    area_m2 = float(result.area_m2)
    return {
        "area_m2": round(area_m2, 2),
        "area_ha": round(area_m2 / 10_000, 2),
        "centroid": [round(result.centroid_lon, 6), round(result.centroid_lat, 6)],
        "crs_used": "EPSG:25830",
    }


def _query_layer(
    db: Session,
    geometry: dict,
    layer_cfg: dict,
) -> list[dict]:
    """
    Query a single environmental layer for intersections with the parcel.

    For linear features (vías pecuarias), uses ST_Buffer with anchura_legal_m
    to create a polygon before computing the intersection.

    Parameters
    ----------
    db : Session
        Database session.
    geometry : dict
        GeoJSON geometry dict (EPSG:4326).
    layer_cfg : dict
        Layer configuration from LAYERS_CONFIG.

    Returns
    -------
    list[dict]
        List of intersected features with overlap metrics.
    """
    geom_json = json.dumps(geometry)
    table_alias = layer_cfg["alias"]
    cols = layer_cfg["columns"]

    if layer_cfg.get("is_linear"):
        # Linear layer: buffer by legal width, then compute intersection
        query = text(f"""
            WITH user_parcel AS (
                SELECT ST_Transform(
                    ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                    25830
                ) AS geom
            ),
            parcel_area AS (
                SELECT ST_Area(geom) AS area FROM user_parcel
            )
            SELECT
                {cols},
                ST_Area(
                    ST_Intersection(
                        ST_Buffer(vp.geom, vp.anchura_legal_m / 2),
                        up.geom
                    )
                ) AS area_interseccion_m2,
                ROUND(
                    (100.0 * ST_Area(
                        ST_Intersection(
                            ST_Buffer(vp.geom, vp.anchura_legal_m / 2),
                            up.geom
                        )
                    ) / pa.area)::numeric,
                    2
                ) AS porcentaje_solape,
                ROUND(
                    ST_Length(ST_Intersection(vp.geom, up.geom))::numeric,
                    2
                ) AS longitud_afectada_m,
                ST_AsGeoJSON(
                    ST_Transform(
                        ST_Buffer(vp.geom, vp.anchura_legal_m / 2),
                        4326
                    )
                ) AS intersection_geojson
            FROM vias_pecuarias vp, user_parcel up, parcel_area pa
            WHERE ST_Intersects(
                ST_Buffer(vp.geom, vp.anchura_legal_m / 2),
                up.geom
            )
        """)
    else:
        # Polygon layer: direct intersection
        query = text(f"""
            WITH user_parcel AS (
                SELECT ST_Transform(
                    ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                    25830
                ) AS geom
            ),
            parcel_area AS (
                SELECT ST_Area(geom) AS area FROM user_parcel
            )
            SELECT
                {cols},
                ST_Area(ST_Intersection({table_alias}.geom, up.geom)) AS area_interseccion_m2,
                ROUND(
                    (100.0 * ST_Area(ST_Intersection({table_alias}.geom, up.geom)) / pa.area)::numeric,
                    2
                ) AS porcentaje_solape,
                ST_AsGeoJSON(
                    ST_Transform(
                        ST_Intersection({table_alias}.geom, up.geom),
                        4326
                    )
                ) AS intersection_geojson
            FROM {layer_cfg["table"]} {table_alias}, user_parcel up, parcel_area pa
            WHERE ST_Intersects({table_alias}.geom, up.geom)
        """)

    rows = db.execute(query, {"geom": geom_json}).fetchall()

    features = []
    for row in rows:
        feature = {}
        row_dict = dict(row._mapping)
        # Extraer y parsear geometría de intersección
        raw_geojson = row_dict.pop("intersection_geojson", None)
        if raw_geojson:
            try:
                feature["intersection_geometry"] = json.loads(raw_geojson)
            except (json.JSONDecodeError, TypeError):
                feature["intersection_geometry"] = None
        else:
            feature["intersection_geometry"] = None
        # Convertir Decimal a float para serialización JSON
        for key, value in row_dict.items():
            if hasattr(value, "__float__"):
                value = float(value)
            feature[key] = value
        features.append(feature)

    return features


def _compute_overall_risk(layer_results: list[dict]) -> str:
    """
    Derive the overall risk indicator from layer analysis results.

    Rules (from spec):
    - 0 layers affected       → "ninguno"
    - 1-2 affected, all <10%  → "bajo"
    - 1-2 affected, some ≥10% → "medio"
    - 3+ affected, or Red Natura/ENP ≥50% → "alto"
    - DPH or flood zone T100  → "muy alto"
    """
    layers_affected = [lr for lr in layer_results if lr["affected"]]
    count = len(layers_affected)

    if count == 0:
        return "ninguno"

    # Check for "muy alto" triggers first (highest severity)
    for lr in layers_affected:
        if lr["layer_name"] == "dominio_publico_hidraulico":
            return "muy alto"
        if lr["layer_name"] == "zonas_inundables":
            for feat in lr["features"]:
                if feat.get("periodo_retorno") == "T100":
                    return "muy alto"

    # Check for "alto" triggers
    if count >= 3:
        return "alto"

    for lr in layers_affected:
        if lr["layer_name"] in ("red_natura_2000", "espacios_naturales_protegidos"):
            for feat in lr["features"]:
                if feat.get("porcentaje_solape", 0) >= 50:
                    return "alto"

    # Check for "medio" vs "bajo"
    max_overlap = 0.0
    for lr in layers_affected:
        for feat in lr["features"]:
            overlap = feat.get("porcentaje_solape", 0) or 0.0
            max_overlap = max(max_overlap, overlap)

    if max_overlap >= 10:
        return "medio"

    return "bajo"
