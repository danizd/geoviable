"""
GeoViable — GeoJSON Validator Service

Validates and sanitizes incoming GeoJSON geometries against MVP constraints:
  1. Valid JSON structure
  2. Valid GeoJSON (Feature or FeatureCollection with exactly 1 Feature)
  3. Single Polygon or MultiPolygon geometry type
  4. Valid topology (no self-intersections), with auto-repair attempt
  5. Within Galicia bounding box (extended)
  6. Area ≤ 100 km² (calculated in EPSG:25830)
  7. Vertices ≤ 10,000

Returns a cleaned GeoJSON string ready for PostGIS queries, or raises
a ValidationError with a machine-readable error code.
"""

import json
from typing import Any

from shapely import wkt
from shapely.errors import TopologicalError
from shapely.geometry import shape, MultiPolygon, Polygon
from shapely.validation import make_valid
from pyproj import Transformer

from app.config import get_settings

settings = get_settings()

# ── Galicia bounding box (EPSG:4326) — extended margins ──
GALICIA_BBOX = {
    "min_lon": -9.5,
    "min_lat": 41.5,
    "max_lon": -6.5,
    "max_lat": 44.0,
}

# ── Coordinate transformer: 4326 → 25830 ──
_transformer_4326_to_25830 = Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)


class GeoJSONValidationError(Exception):
    """
    Raised when GeoJSON validation fails.

    Attributes:
        code: Machine-readable error code (e.g. 'INVALID_JSON').
        message: Human-readable description in Spanish.
        details: Optional dict with extra context (e.g. received vs max area).
    """

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def validate_geojson(raw: str | dict) -> str:
    """
    Validate and repair a GeoJSON Feature.

    Parameters
    ----------
    raw : str or dict
        The raw GeoJSON as a JSON string or already-parsed dict.

    Returns
    -------
    str
        A cleaned GeoJSON string with a single valid Polygon/MultiPolygon
        geometry, guaranteed to be within bounds and under size limits.

    Raises
    ------
    GeoJSONValidationError
        With a specific error code for each validation failure.
    """

    # ── Step 1: Parse JSON if string ──
    if isinstance(raw, str):
        try:
            geojson = json.loads(raw)
        except json.JSONDecodeError:
            raise GeoJSONValidationError(
                code="INVALID_JSON",
                message="El cuerpo de la solicitud no es un JSON válido.",
            )
    else:
        geojson = raw

    # ── Step 2: Validate GeoJSON structure ──
    if not isinstance(geojson, dict):
        raise GeoJSONValidationError(
            code="INVALID_GEOJSON",
            message="El GeoJSON debe ser un objeto Feature o FeatureCollection.",
        )

    feature_type = geojson.get("type", "")

    # Handle FeatureCollection — extract single feature
    if feature_type == "FeatureCollection":
        features = geojson.get("features", [])
        if len(features) != 1:
            raise GeoJSONValidationError(
                code="MULTIPLE_FEATURES",
                message=(
                    f"Solo se permite un polígono por análisis. "
                    f"El archivo contiene {len(features)} elementos."
                ),
                details={"feature_count": len(features)},
            )
        geojson = features[0]
        feature_type = geojson.get("type", "")

    if feature_type != "Feature":
        raise GeoJSONValidationError(
            code="INVALID_GEOJSON",
            message="El GeoJSON debe ser de tipo 'Feature' o 'FeatureCollection'.",
        )

    geometry = geojson.get("geometry")
    if geometry is None:
        raise GeoJSONValidationError(
            code="INVALID_GEOJSON",
            message="El Feature no contiene una geometría.",
        )

    # ── Step 3: Validate geometry type ──
    geom_type = geometry.get("type", "")
    if geom_type not in ("Polygon", "MultiPolygon"):
        raise GeoJSONValidationError(
            code="INVALID_GEOMETRY_TYPE",
            message=(
                f"Tipo de geometría no soportado: '{geom_type}'. "
                f"Solo se aceptan 'Polygon' o 'MultiPolygon'."
            ),
            details={"received_type": geom_type},
        )

    # ── Step 4: Convert to Shapely and validate topology ──
    try:
        shapely_geom = shape(geometry)
    except (ValueError, TypeError) as exc:
        raise GeoJSONValidationError(
            code="INVALID_TOPOLOGY",
            message=f"No se pudo parsear la geometría: {exc}",
        )

    if not shapely_geom.is_valid:
        # Attempt automatic repair
        try:
            shapely_geom = make_valid(shapely_geom)
            if shapely_geom is None or shapely_geom.is_empty:
                raise TopologicalError("make_valid returned empty geometry")
        except (TopologicalError, Exception):
            raise GeoJSONValidationError(
                code="INVALID_TOPOLOGY",
                message=(
                    "El polígono tiene errores de topología (auto-intersección) "
                    "y no se pudo reparar automáticamente."
                ),
            )

    # Ensure the repaired geometry is still a Polygon or MultiPolygon
    if not isinstance(shapely_geom, (Polygon, MultiPolygon)):
        raise GeoJSONValidationError(
            code="INVALID_GEOMETRY_TYPE",
            message=(
                "Tras la reparación, la geometría no es un Polygon o MultiPolygon válido."
            ),
        )

    # ── Step 5: Check bounding box (Galicia) ──
    minx, miny, maxx, maxy = shapely_geom.bounds
    if (
        minx < GALICIA_BBOX["min_lon"]
        or miny < GALICIA_BBOX["min_lat"]
        or maxx > GALICIA_BBOX["max_lon"]
        or maxy > GALICIA_BBOX["max_lat"]
    ):
        raise GeoJSONValidationError(
            code="OUT_OF_BOUNDS",
            message=(
                "El polígono se encuentra fuera de los límites de Galicia. "
                f"Bbox esperado: lon [{GALICIA_BBOX['min_lon']}, {GALICIA_BBOX['max_lon']}], "
                f"lat [{GALICIA_BBOX['min_lat']}, {GALICIA_BBOX['max_lat']}]. "
                f"Recibido: [{minx}, {miny}, {maxx}, {maxy}]."
            ),
            details={"bounds": [minx, miny, maxx, maxy]},
        )

    # ── Step 6: Check vertex count ──
    vertex_count = len(shapely_geom.exterior.coords) if isinstance(shapely_geom, Polygon) else sum(
        len(poly.exterior.coords) for poly in shapely_geom.geoms
    )
    if vertex_count > settings.max_polygon_vertices:
        raise GeoJSONValidationError(
            code="TOO_MANY_VERTICES",
            message=(
                f"El polígono tiene demasiados vértices. "
                f"Máximo permitido: {settings.max_polygon_vertices}. "
                f"Recibidos: {vertex_count}."
            ),
            details={
                "max_vertices": settings.max_polygon_vertices,
                "received_vertices": vertex_count,
            },
        )

    # ── Step 7: Check area (reproject to EPSG:25830) ──
    geom_25830 = _transformer_4326_to_25830.transform_geom(geometry)
    shapely_geom_25830 = shape(geom_25830)
    area_m2 = shapely_geom_25830.area
    area_km2 = area_m2 / 1_000_000

    if area_km2 > settings.max_polygon_area_km2:
        raise GeoJSONValidationError(
            code="AREA_TOO_LARGE",
            message=(
                f"El polígono excede el área máxima permitida ({settings.max_polygon_area_km2} km²). "
                f"Área recibida: {area_km2:.1f} km²."
            ),
            details={
                "max_area_km2": settings.max_polygon_area_km2,
                "received_area_km2": round(area_km2, 1),
            },
        )

    # ── All checks passed — return the original (or repaired) GeoJSON as string ──
    # Rebuild a clean Feature dict.
    cleaned_feature = {
        "type": "Feature",
        "geometry": {
            "type": shapely_geom.geom_type,
            "coordinates": _get_coordinates(shapely_geom),
        },
        "properties": geojson.get("properties", {}),
    }

    return json.dumps(cleaned_feature)


def _get_coordinates(geom) -> list:
    """
    Extract coordinates from a Shapely geometry in GeoJSON format.

    Works for both Polygon and MultiPolygon, returning the appropriate
    nested list structure.
    """
    if isinstance(geom, Polygon):
        return [list(geom.exterior.coords)] + [
            list(interior.coords) for interior in geom.interiors
        ]
    elif isinstance(geom, MultiPolygon):
        return [
            [list(poly.exterior.coords)] + [
                list(interior.coords) for interior in poly.interiors
            ]
            for poly in geom.geoms
        ]
    else:
        raise ValueError(f"Unsupported geometry type: {geom.geom_type}")
