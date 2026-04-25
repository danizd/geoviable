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

# Color palette for layers (sincronizado con MapViewer.jsx del frontend)
LAYER_COLORS = {
    "parcel": "#334155",
    "red_natura_2000": "#F97316",
    "zonas_inundables": "#A21CAF",
    "dominio_publico_hidraulico": "#7C3AED",
    "vias_pecuarias": "#CA8A04",
    "espacios_naturales_protegidos": "#BE185D",
    "masas_agua_superficial": "#0D9488",
    "masas_agua_subterranea": "#6D28D9",
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

    # ── Step 2: Collect intersection geometries from analysis results ──
    layer_gdfs = {}  # layer_name → GeoDataFrame in EPSG:3857

    for layer_result in analysis_results.get("layers", []):
        if not layer_result["affected"]:
            continue

        geometries = []
        for feat in layer_result["features"]:
            geom_dict = feat.get("intersection_geometry")
            if not geom_dict:
                continue
            try:
                geom = shape(geom_dict)
                if geom and not geom.is_empty:
                    geometries.append(geom)
            except Exception as exc:
                logger.warning(
                    "Error parseando geometría de '%s': %s",
                    layer_result["display_name"], exc,
                )

        if geometries:
            try:
                gdf = gpd.GeoDataFrame(
                    geometry=geometries,
                    crs=CRS.from_epsg(4326),  # intersection_geometry viene en EPSG:4326
                ).to_crs(epsg=3857)
                layer_gdfs[layer_result["layer_name"]] = (gdf, layer_result["display_name"])
                logger.debug(
                    "Capa '%s': %d geometrías de intersección para el mapa",
                    layer_result["display_name"], len(geometries),
                )
            except Exception as exc:
                logger.warning(
                    "Error creando GeoDataFrame para '%s': %s",
                    layer_result["display_name"], exc,
                )

    # ── Step 3: Reproject to Web Mercator (EPSG:3857) for contextily tiles ──
    gdf_parcel = gdf_parcel.to_crs(epsg=3857)

    # ── Step 4: Set up matplotlib figure ──
    fig, ax = plt.subplots(figsize=FIGURE_SIZE, dpi=DPI)

    # Plot the parcel (encima de todo — última en dibujarse)
    # Primero pintar las capas afectadas para que la parcela quede visible
    for layer_name, (gdf_layer, display_name) in layer_gdfs.items():
        color = LAYER_COLORS.get(layer_name, "#888888")
        try:
            gdf_layer.plot(
                ax=ax,
                facecolor=color + "66",   # ~40% opacidad
                edgecolor=color,
                linewidth=1.5,
            )
        except Exception as exc:
            logger.warning("Error pintando capa '%s' en mapa: %s", display_name, exc)

    gdf_parcel.plot(
        ax=ax,
        facecolor=LAYER_COLORS["parcel"] + "33",  # 20% opacity hex suffix
        edgecolor=LAYER_COLORS["parcel"],
        linewidth=2.5,
        label="Parcela analizada",
    )

    # ── Step 5: Add basemap tiles ──
    # Calcula zoom adecuado al tamaño de la parcela para minimizar tiles descargados
    bounds = gdf_parcel.total_bounds  # [minx, miny, maxx, maxy] en EPSG:3857
    extent_m = max(bounds[2] - bounds[0], bounds[3] - bounds[1])
    if extent_m < 500:
        zoom = 17
    elif extent_m < 2000:
        zoom = 15
    elif extent_m < 10000:
        zoom = 13
    else:
        zoom = 11

    _basemap_loaded = False
    
    # ── Determine providers list based on choice ──
    providers = []
    if basemap.upper() == "PNOA":
        # IGN PNOA Spain — URL format for contextily
        pnoa_url = (
            "https://www.ign.es/wmts/pnoa-ma?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
            "&LAYER=OI.OrthoimageCoverage&STYLE=default&FORMAT=image/jpeg&TILEMATRIXSET=GoogleMapsCompatible"
            "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
        )
        providers.append(pnoa_url)
    
    # Fallback to standard providers
    providers.extend([
        cx.providers.OpenStreetMap.Mapnik,
        cx.providers.CartoDB.Positron,
    ])

    for provider in providers:
        try:
            cx.add_basemap(
                ax,
                source=provider,
                zoom=zoom,
                attribution="© IGN PNOA" if provider == providers[0] and basemap.upper() == "PNOA" else "© OpenStreetMap contributors",
            )
            _basemap_loaded = True
            break
        except Exception as exc:
            logger.warning("Basemap provider failed (%s): %s", provider, exc)

    if not _basemap_loaded:
        logger.warning("All basemap providers failed — rendering without basemap.")

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
