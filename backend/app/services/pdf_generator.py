"""
GeoViable — PDF Report Generation Service

Renders a Jinja2 HTML template with analysis results and a static map
image, then converts the HTML to a PDF using WeasyPrint.

The PDF is returned as raw bytes (never written to disk).
"""

import hashlib
import logging
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

logger = logging.getLogger("geoviable")

# ── Jinja2 environment ──
# Templates are loaded from the /app/templates/report/ directory.
# In Docker, this path is mounted as a read-only volume.
template_env = Environment(
    loader=FileSystemLoader(searchpath="templates/report"),
    autoescape=select_autoescape(["html", "xml"]),
)


def generate_pdf(
    analysis: dict,
    project: dict,
    map_image_base64: str,
) -> bytes:
    """
    Generate a complete PDF report from analysis results.

    Parameters
    ----------
    analysis : dict
        Output from spatial_analysis.run_spatial_analysis().
    project : dict
        Project metadata: {name, author, description}.
    map_image_base64 : str
        Base64-encoded PNG from static_map.generate_static_map().

    Returns
    -------
    bytes
        The complete PDF file as binary data.
    """
    # ── Compute reference hash from geometry ──
    # The hash is derived from the parcel area for uniqueness.
    geo_hash = _compute_reference_hash(analysis)

    # ── Prepare template context ──
    now = datetime.now(timezone.utc)

    # Separate affected and unaffected layers for the summary table
    affected_layers = [
        lr for lr in analysis["layers"] if lr["affected"]
    ]
    unaffected_layers = [
        lr for lr in analysis["layers"] if not lr["affected"]
    ]

    # Risk badge color mapping
    risk_colors = {
        "ninguno": "#16A34A",
        "bajo": "#EAB308",
        "medio": "#EA580C",
        "alto": "#DC2626",
        "muy alto": "#7F1D1D",
    }

    context = {
        # Project
        "project_name": project.get("name", "Sin nombre"),
        "project_author": project.get("author") or "—",
        "project_description": project.get("description") or "—",

        # Date & reference
        "report_date": now.strftime("%d/%m/%Y %H:%M"),
        "report_reference": f"GV-{now.strftime('%Y%m%d')}-{geo_hash[:4]}",

        # Parcel info
        "parcel_area_ha": analysis["parcel"]["area_ha"],
        "parcel_area_m2": analysis["parcel"]["area_m2"],
        "parcel_centroid_lon": analysis["parcel"]["centroid"][0],
        "parcel_centroid_lat": analysis["parcel"]["centroid"][1],

        # Map
        "map_image_base64": map_image_base64,

        # Summary
        "overall_risk": analysis["summary"]["overall_risk"],
        "risk_color": risk_colors.get(analysis["summary"]["overall_risk"], "#888888"),
        "total_layers": analysis["summary"]["total_layers_checked"],
        "layers_affected": analysis["summary"]["layers_affected"],
        "layers_unaffected": analysis["summary"]["total_layers_checked"] - analysis["summary"]["layers_affected"],

        # Detailed results
        "affected_layers": affected_layers,
        "unaffected_layers": unaffected_layers,

        # Metadata
        "analysis_duration_ms": analysis["metadata"]["analysis_duration_ms"],
        "data_updated_at": analysis["metadata"].get("data_updated_at", "No disponible"),

        # Footer
        "footer_date": now.strftime("%d/%m/%Y %H:%M"),
    }

    # ── Render HTML from Jinja2 template ──
    template = template_env.get_template("report.html")
    html_content = template.render(**context)

    # ── Convert HTML → PDF with WeasyPrint ──
    logger.info("Rendering PDF with WeasyPrint...")
    pdf_bytes = HTML(string=html_content).write_pdf()

    logger.info("PDF generated: %d bytes (%.1f KB)", len(pdf_bytes), len(pdf_bytes) / 1024)
    return pdf_bytes


def _compute_reference_hash(analysis: dict) -> str:
    """
    Compute a short reference hash from the parcel area and centroid.

    This provides a brief unique identifier for the report.
    Uses the last 8 characters of the SHA-256 hex digest.
    """
    data = (
        f"{analysis['parcel']['area_m2']}:"
        f"{analysis['parcel']['centroid'][0]}:"
        f"{analysis['parcel']['centroid'][1]}"
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[-8:]


def generate_pdf_filename(project_name: str) -> str:
    """
    Generate a safe PDF filename from the project name and current date.

    Example: GeoViable_Informe_Proyecto_Demo_20260411.pdf
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_name = _slugify(project_name)
    return f"GeoViable_Informe_{safe_name}_{date_str}.pdf"


def _slugify(text: str, max_length: int = 40) -> str:
    """
    Convert a string to a URL-safe, filesystem-safe slug.

    Removes special characters, replaces spaces with underscores,
    and truncates to max_length characters.
    """
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    text = text[:max_length].strip("_")
    return text or "informe"
