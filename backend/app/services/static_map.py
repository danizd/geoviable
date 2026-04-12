"""
GeoViable — Static Map Generation Service

Generates a PNG image of the user's parcel overlaid on a basemap tile,
using contextily (for tiles) and matplotlib + geopandas (for rendering).

The output image is embedded as base64 in the PDF report.
"""

import base64
import io
import json
import logging
from typing import Optional

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from shapely.geometry import shape
from pyproj import CRS

logger = logging.getLogger("geoviable")

# ── Map styling constants ──
DPI = 300
FIGURE_SIZE = (12, 8)  # inches → ~3600×2400 px at 300 DPI
BBOX_PADDING = 0.20  # 20% padding around parcel bounds

# Color palette for layers (matches PDF spec)
LAYER_COLORS = {
    "parcel": "#2563EB",
    "red_natura_2000": "#DC2626",
    "zonas_inundables": "#60A5FA",
    "dominio_publico_hidraulico": "#1E40AF",
    "vias_pecuarias": "#92400E",
    "espacios_naturales_protegidos": "#16A34A",
    "masas_agua_superficial": "#06B6D4",
    "masas_agua_subterranea": "#0891B2",
}


def generate_static_map(
    geojson_str: str,
    analysis_results: dict,
    basemap: str = "OpenStreetMap",
) -> str:
    """
    Generate a static map image showing the parcel and detected afecciones.

    Parameters
    ----------
    geojson_str : str
        Validated GeoJSON Feature string (EPSG:4326).
    analysis_results : dict
        Output from spatial_analysis.run_spatial_analysis().
    basemap : str
        Basemap provider for contextily. Default: "OpenStreetMap".

    Returns
    -------
    str
        Base64-encoded PNG string (ready for HTML <img src="data:...">).
    """
    geojson = json.loads(geojson_str)
    geometry = geojson["geometry"]

    # ── Step 1: Create GeoDataFrame with parcel in EPSG:25830 ──
    shapely_geom = shape(geometry)
    gdf_parcel = gpd.GeoDataFrame(
        [{"name": "Parcela analizada", "layer": "parcel"}],
        geometry=[shapely_geom],
        crs=CRS.from_epsg(4326),
    ).to_crs(epsg=25830)

    # ── Step 2: Collect geometries of affected layers ──
    # For the MVP, we overlay the parcel only. Full layer geometries
    # would require extra queries; here we mark afecciones in the legend.
    gdf_layers = gpd.GeoDataFrame(
        columns=["name", "layer", "geometry"],
        crs=CRS.from_epsg(25830),
    )

    for layer_result in analysis_results.get("layers", []):
        if not layer_result["affected"]:
            continue
        # Collect geometries from features via a separate query
        # For MVP: we skip geometry overlay and only show the parcel
        logger.debug(
            "Layer '%s' affected — %d features (overlay skipped in MVP)",
            layer_result["display_name"],
            len(layer_result["features"]),
        )

    # ── Step 3: Reproject to Web Mercator (EPSG:3857) for contextily tiles ──
    gdf_parcel = gdf_parcel.to_crs(epsg=3857)

    # ── Step 4: Set up matplotlib figure ──
    fig, ax = plt.subplots(figsize=FIGURE_SIZE, dpi=DPI)

    # Plot the parcel
    gdf_parcel.plot(
        ax=ax,
        facecolor=LAYER_COLORS["parcel"] + "33",  # 20% opacity hex suffix
        edgecolor=LAYER_COLORS["parcel"],
        linewidth=2.5,
        label="Parcela analizada",
    )

    # ── Step 5: Add basemap tiles ──
    try:
        cx.add_basemap(
            ax,
            source=getattr(cx.providers, basemap, cx.providers.OpenStreetMap.Mapnik),
            attribution="© OpenStreetMap contributors",
        )
    except Exception:
        logger.warning("Failed to load basemap tiles — rendering without basemap.")

    # ── Step 6: Build legend from affected layers ──
    legend_patches = [
        Patch(
            facecolor=LAYER_COLORS["parcel"] + "33",
            edgecolor=LAYER_COLORS["parcel"],
            label="Parcela analizada",
        )
    ]

    for layer_result in analysis_results.get("layers", []):
        if not layer_result["affected"]:
            continue
        color = LAYER_COLORS.get(layer_result["layer_name"], "#888888")
        legend_patches.append(
            Patch(facecolor=color, edgecolor="none", label=layer_result["display_name"])
        )

    ax.legend(
        handles=legend_patches,
        loc="upper right",
        framealpha=0.9,
        fontsize=9,
    )

    ax.set_axis_off()
    ax.set_title("Mapa de Situación", fontsize=14, fontweight="bold", pad=10)

    # ── Step 7: Save to in-memory PNG buffer ──
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=DPI,
        bbox_inches="tight",
        pad_inches=0.3,
    )
    plt.close(fig)

    # ── Step 8: Encode to base64 ──
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    logger.info("Static map generated: %d bytes (base64: %d chars)", len(buf.getvalue()), len(b64))

    return b64
