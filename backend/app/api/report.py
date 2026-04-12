"""
GeoViable — POST /report/generate Endpoint

Receives a GeoJSON Feature and project metadata, validates the geometry,
runs the spatial analysis, generates a static map, and produces a complete
PDF report. Returns the PDF as a binary download.
"""

import json
import logging

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.schemas.analysis import ErrorResponse
from app.services.geojson_validator import (
    GeoJSONValidationError,
    validate_geojson,
)
from app.services.spatial_analysis import run_spatial_analysis
from app.services.static_map import generate_static_map
from app.services.pdf_generator import generate_pdf, generate_pdf_filename

logger = logging.getLogger("geoviable")

router = APIRouter(tags=["Reports"])


@router.post(
    "/report/generate",
    summary="Generate environmental viability report (PDF)",
    description=(
        "Receives a GeoJSON Feature and project metadata, performs spatial analysis "
        "against all environmental layers, and returns a complete PDF report. "
        "This is the main production endpoint."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid GeoJSON"},
        413: {"model": ErrorResponse, "description": "Payload too large"},
        422: {"model": ErrorResponse, "description": "Validation error (missing project name)"},
        500: {"model": ErrorResponse, "description": "PDF generation failed"},
        504: {"model": ErrorResponse, "description": "Query timeout"},
    },
)
def generate_report(payload: dict):
    """
    Full pipeline: validate → analyze → map → PDF → download.

    Parameters
    ----------
    payload : dict
        Request body with 'geojson' (Feature) and 'project' (metadata).
        The 'project.name' field is required (3-100 chars).

    Returns
    -------
    Response
        Binary PDF file with Content-Disposition header for download.
    """
    # ── Extract and validate project metadata ──
    project = payload.get("project", {})
    project_name = project.get("name", "").strip()

    if not project_name or len(project_name) < 3:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "MISSING_PROJECT_NAME",
                    "message": (
                        "El nombre del proyecto es obligatorio y debe tener "
                        "entre 3 y 100 caracteres."
                    ),
                }
            },
        )

    if len(project_name) > 100:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "PROJECT_NAME_TOO_LONG",
                    "message": "El nombre del proyecto no puede exceder los 100 caracteres.",
                }
            },
        )

    # ── Extract and validate GeoJSON ──
    geojson_raw = payload.get("geojson")
    if geojson_raw is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "MISSING_GEOJSON",
                    "message": "Se requiere un objeto GeoJSON en el campo 'geojson'.",
                }
            },
        )

    try:
        geojson_str = validate_geojson(geojson_raw)
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

    # ── Run spatial analysis ──
    db = next(get_db())
    try:
        analysis = run_spatial_analysis(db, geojson_str)
    except Exception as exc:
        import traceback
        error_traceback = traceback.format_exc()
        logger.exception("Spatial analysis failed: %s\n%s", exc, error_traceback)
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
                    "message": f"Error interno al ejecutar el análisis espacial: {str(exc)}",
                }
            },
        )
    finally:
        db.close()

    # ── Generate static map ──
    try:
        map_image_base64 = generate_static_map(geojson_str, analysis)
    except Exception as exc:
        logger.exception("Static map generation failed: %s", exc)
        # Continue without map image — use a placeholder
        map_image_base64 = ""

    # ── Generate PDF ──
    try:
        pdf_bytes = generate_pdf(analysis, project, map_image_base64)
    except Exception as exc:
        logger.exception("PDF generation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "PDF_GENERICATION_FAILED",
                    "message": "Error interno al generar el informe PDF.",
                }
            },
        )

    # ── Return PDF as download ──
    filename = generate_pdf_filename(project_name)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
