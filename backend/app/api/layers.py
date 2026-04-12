"""
GeoViable — GET /layers/status Endpoint

Returns the current status of all environmental data layers,
including last update time, record counts, and success/failure state.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger("geoviable")

router = APIRouter(tags=["Layers"])

# ── Layer display metadata ──
LAYERS_META = [
    {
        "name": "red_natura_2000",
        "display_name": "Red Natura 2000",
    },
    {
        "name": "zonas_inundables",
        "display_name": "Zonas inundables (SNCZI)",
    },
    {
        "name": "dominio_publico_hidraulico",
        "display_name": "Dominio Público Hidráulico",
    },
    {
        "name": "vias_pecuarias",
        "display_name": "Vías pecuarias",
    },
    {
        "name": "espacios_naturales_protegidos",
        "display_name": "Espacios Naturales Protegidos",
    },
    {
        "name": "masas_agua_superficial",
        "display_name": "Masas de agua superficiales",
    },
    {
        "name": "masas_agua_subterranea",
        "display_name": "Masas de agua subterráneas",
    },
]


@router.get(
    "/layers/status",
    summary="Check environmental data layer status",
    description=(
        "Returns the last update status, timestamp, and record count "
        "for each environmental data layer."
    ),
)
def get_layers_status(db: Session = Depends(get_db)) -> dict:
    """
    Query the layer_update_log table for the latest status of each layer,
    and compute record counts from the actual data tables.
    """
    layers_response = []
    last_global_update = None

    for meta in LAYERS_META:
        table_name = meta["name"]
        display_name = meta["display_name"]

        # ── Query latest log entry ──
        log_query = text("""
            SELECT status, finished_at
            FROM layer_update_log
            WHERE layer_name = :layer_name
            ORDER BY started_at DESC
            LIMIT 1
        """)
        log_row = db.execute(log_query, {"layer_name": table_name}).fetchone()

        status = "no_data"
        last_updated = None
        if log_row:
            status = log_row.status
            if log_row.finished_at:
                last_updated = log_row.finished_at.isoformat()

        # ── Query record count from the data table ──
        count_query = text(
            f"SELECT COUNT(*) AS cnt FROM {table_name}"
        )
        count_row = db.execute(count_query).fetchone()
        records_count = count_row.cnt if count_row else 0

        # ── Track the most recent global update ──
        if last_updated:
            if last_global_update is None or last_updated > last_global_update:
                last_global_update = last_updated

        layers_response.append({
            "name": table_name,
            "display_name": display_name,
            "last_updated": last_updated,
            "status": status,
            "records_count": records_count,
        })

    return {
        "layers": layers_response,
        "last_global_update": last_global_update,
    }
