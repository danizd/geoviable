"""
GeoViable — Pydantic Schemas for Analysis Requests & Responses

Defines the structure of the GeoJSON payload, project metadata,
analysis results per layer, and the overall risk assessment.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ==============================================================================
# Request Schemas
# ==============================================================================


class ProjectInfo(BaseModel):
    """Metadata about the project being evaluated."""

    name: str = Field(..., min_length=3, max_length=100, description="Project name (required)")
    author: Optional[str] = Field(None, max_length=100, description="Author / responsible party")
    description: Optional[str] = Field(
        None, max_length=500, description="Brief project description"
    )


class AnalyzeRequest(BaseModel):
    """
    Request body for POST /analyze.

    Accepts a single GeoJSON Feature with a Polygon or MultiPolygon geometry.
    """

    # Raw GeoJSON as a Python dict.
    # Validated downstream by geojson_validator.py using shapely.
    type: str
    geometry: dict
    properties: Optional[dict] = None


class ReportRequest(BaseModel):
    """
    Request body for POST /report/generate.

    Wraps the GeoJSON feature and project metadata.
    """

    geojson: AnalyzeRequest
    project: ProjectInfo


# ==============================================================================
# Response Schemas — Analysis
# ==============================================================================


class ParcelInfo(BaseModel):
    """Computed metadata about the user's parcel."""

    area_m2: float = Field(..., description="Area in square meters")
    area_ha: float = Field(..., description="Area in hectares")
    centroid: tuple[float, float] = Field(
        ..., description="Centroid as [longitude, latitude]"
    )
    crs_used: str = Field("EPSG:25830", description="CRS used for area calculation")


class LayerFeature(BaseModel):
    """A single affected entity from an environmental layer."""

    nombre: Optional[str] = None
    tipo: Optional[str] = None
    codigo: Optional[str] = None
    categoria: Optional[str] = None
    periodo_retorno: Optional[str] = None
    nombre_cauce: Optional[str] = None
    anchura_legal_m: Optional[float] = None
    estado_ecologico: Optional[str] = None
    estado_quimico: Optional[str] = None
    estado_cuantitativo: Optional[str] = None
    area_interseccion_m2: Optional[float] = None
    porcentaje_solape: Optional[float] = None
    longitud_afectada_m: Optional[float] = None

    class Config:
        extra = "allow"  # Allow additional fields from raw query results


class LayerResult(BaseModel):
    """Analysis result for a single environmental layer."""

    layer_name: str
    display_name: str
    affected: bool
    features: list[LayerFeature] = []


class AnalysisSummary(BaseModel):
    """High-level summary of the full analysis."""

    total_layers_checked: int
    layers_affected: int
    overall_risk: str  # 'ninguno' | 'bajo' | 'medio' | 'alto' | 'muy alto'


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis run."""

    data_updated_at: Optional[str] = None
    analysis_duration_ms: float


class AnalysisResponse(BaseModel):
    """Full response body for POST /analyze (JSON)."""

    analysis: dict  # Contains parcel, layers, summary, metadata


# ==============================================================================
# Response Schemas — Layer Status
# ==============================================================================


class LayerStatusItem(BaseModel):
    """Status of a single environmental layer."""

    name: str
    display_name: str
    last_updated: Optional[str] = None
    status: str  # 'success' | 'failed' | 'no_data'
    records_count: int = 0


class LayersStatusResponse(BaseModel):
    """Response for GET /layers/status."""

    layers: list[LayerStatusItem]
    last_global_update: Optional[str] = None


# ==============================================================================
# Error Response Schema
# ==============================================================================


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: dict  # {code, message, details (optional)}
