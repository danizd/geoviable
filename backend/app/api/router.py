"""
GeoViable — API Router

Central router that includes all versioned API endpoints
under the /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.analyze import router as analyze_router
from app.api.report import router as report_router
from app.api.layers import router as layers_router

# ── Create versioned router ──
# All routes added to this router will be prefixed with /api/v1.
api_router = APIRouter()

# Register individual route modules
api_router.include_router(analyze_router)
api_router.include_router(report_router)
api_router.include_router(layers_router)
