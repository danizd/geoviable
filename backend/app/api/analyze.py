"""
GeoViable — POST /analyze Endpoint

Receives a GeoJSON Feature, validates it, runs the spatial analysis
against all environmental layers, and returns results as JSON.

Used primarily for development and debugging. Production uses /report/generate.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analysis import ErrorResponse
from app.services.geojson_validator import (
    GeoJSONValidationError,
    validate_geojson,
)
from app.services.spatial_analysis import run_spatial_analysis

logger = logging.getLogger("geoviable")

router = APIRouter(tags=["Analysis"])


@router.post(
    "/analyze",
    summary="Spatial analysis (JSON response)",
    description=(
        "Receives a GeoJSON Feature with a Polygon or MultiPolygon geometry, "
        "validates it, and returns the spatial analysis results as JSON. "
        "This endpoint is intended for development and debugging."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid GeoJSON"},
        413: {"model": ErrorResponse, "description": "Payload too large"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        504: {"model": ErrorResponse, "description": "Query timeout"},
    },
)
def analyze(geojson_payload: dict[str, Any]) -> dict:
    """
    Validate the GeoJSON payload and run spatial analysis.

    Parameters
    ----------
    geojson_payload : dict
        Raw request body (automatically parsed by FastAPI).

    Returns
    -------
    dict
        Analysis result with parcel info, layer intersections, and summary.
    """
    # ── Step 1: Validate GeoJSON ──
    try:
        geojson_str = validate_geojson(geojson_payload)
    except GeoJSONValidationError as exc:
        logger.warning("GeoJSON validation failed: %s — %s", exc.code, exc.message)
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details if exc.details else None,
                }
            },
        )

    # ── Step 2: Run spatial analysis ──
    db: Session = next(get_db())
    try:
        analysis = run_spatial_analysis(db, geojson_str)
    except Exception as exc:
        logger.exception("Spatial analysis failed: %s", exc)
        # Check for timeout
        if "canceling statement due to statement timeout" in str(exc).lower():
            raise HTTPException(
                status_code=504,
                detail={
                    "error": {
                        "code": "QUERY_TIMEOUT",
                        "message": (
                            "La consulta espacial excedió el tiempo máximo de ejecución. "
                            "Reduce el área del polígono e inténtalo de nuevo."
                        ),
                    }
                },
            )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "ANALYSIS_FAILED",
                    "message": "Error interno al ejecutar el análisis espacial.",
                }
            },
        )
    finally:
        db.close()

    # ── Step 3: Wrap in the expected response structure ──
    return {"analysis": analysis}
