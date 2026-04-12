"""
GeoViable — Automated Environmental Layer Update Script

Downloads the latest shapefiles from MITECO/CNIG, processes them with GeoPandas,
and loads them into the PostGIS database using TRUNCATE + INSERT within a
single atomic transaction.

Usage:
    python -m scripts.update_layers

Executed monthly by cron (see scripts/crontab).
"""

import hashlib
import logging
import os
import re
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import geopandas as gpd
import requests
from bs4 import BeautifulSoup
from shapely.geometry import box
from sqlalchemy import create_engine, text

from app.config import get_settings

# ── Configure logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("update_layers")

settings = get_settings()

# ── Galicia bounding box (EPSG:4326) ──
GALICIA_BBOX_4326 = box(-9.5, 41.5, -6.5, 44.0)

# ── Target SRID ──
TARGET_SRID = 25830

# ── HTTP Session with retries ──
session = requests.Session()
session.headers.update({
    "User-Agent": "GeoViable/1.0 (geoviable.movilab.es) — Automated data update",
})
adapter = requests.adapters.HTTPAdapter(max_retries=3)
session.mount("https://", adapter)
session.mount("http://", adapter)


# ==============================================================================
# Layer Configuration
# ==============================================================================
class LayerConfig:
    """Configuration for a single environmental layer update."""

    def __init__(
        self,
        table_name: str,
        display_name: str,
        download_url: str,
        file_pattern: str,
        column_mapping: dict[str, str],
        filter_demarcacion: Optional[list[str]] = None,
        is_linear: bool = False,
    ):
        self.table_name = table_name
        self.display_name = display_name
        self.download_url = download_url
        self.file_pattern = file_pattern  # regex to match the ZIP/shapefile name
        self.column_mapping = column_mapping  # {shapefile_field: db_column}
        self.filter_demarcacion = filter_demarcacion
        self.is_linear = is_linear


LAYERS = [
    LayerConfig(
        table_name="red_natura_2000",
        display_name="Red Natura 2000",
        download_url=(
            "https://www.miteco.gob.es/es/biodiversidad/servicios/"
            "banco-datos-naturaleza/informacion-disponible/rednatura_2000_desc.html"
        ),
        file_pattern=r"red_natura.*\.zip",
        column_mapping={
            "CODIGO": "codigo",
            "NOMBRE": "nombre",
            "TIPO": "tipo",
            "SUP_HA": "superficie_ha",
            "geometry": "geom",
        },
    ),
    LayerConfig(
        table_name="zonas_inundables",
        display_name="Zonas inundables (SNCZI)",
        download_url=(
            "https://www.miteco.gob.es/es/cartografia-y-sig/ide/"
            "descargas/agua/descargas_agua_snczi.html"
        ),
        file_pattern=r"inundabilidad.*\.zip",
        column_mapping={
            "PERIODO": "periodo_retorno",
            "PELIGROSID": "nivel_peligrosidad",
            "DEMARCA": "demarcacion",
            "geometry": "geom",
        },
        filter_demarcacion=["Galicia-Costa", "Miño-Sil", "Miño-Sil "],
    ),
    LayerConfig(
        table_name="dominio_publico_hidraulico",
        display_name="Dominio Público Hidráulico",
        download_url=(
            "https://www.miteco.gob.es/es/cartografia-y-sig/ide/"
            "descargas/agua/dph-y-zonas-asociadas.html"
        ),
        file_pattern=r"dph.*\.zip",
        column_mapping={
            "TIPO": "tipo",
            "NOMBRE": "nombre_cauce",
            "CATEGORIA": "categoria",
            "geometry": "geom",
        },
        filter_demarcacion=["Galicia-Costa", "Miño-Sil"],
    ),
    LayerConfig(
        table_name="vias_pecuarias",
        display_name="Vías pecuarias",
        download_url="https://centrodedescargas.cnig.es/CentroDescargas/",
        file_pattern=r"vias_pecuarias.*\.zip",
        column_mapping={
            "NOMBRE": "nombre",
            "TIPO_VIA": "tipo_via",
            "ANCHO_M": "anchura_legal_m",
            "LONGITUD_M": "longitud_m",
            "DESlinde": "estado_deslinde",
            "MUNICIPIO": "municipio",
            "PROVINCIA": "provincia",
            "geometry": "geom",
        },
    ),
    LayerConfig(
        table_name="espacios_naturales_protegidos",
        display_name="Espacios Naturales Protegidos",
        download_url=(
            "https://www.miteco.gob.es/es/biodiversidad/servicios/"
            "banco-datos-naturaleza/informacion-disponible/enp_descargas.html"
        ),
        file_pattern=r"enp.*\.zip",
        column_mapping={
            "CODIGO": "codigo",
            "NOMBRE": "nombre",
            "CATEGORIA": "categoria",
            "SUBCATE": "subcategoria",
            "SUP_HA": "superficie_ha",
            "geometry": "geom",
        },
    ),
    LayerConfig(
        table_name="masas_agua_superficial",
        display_name="Masas de agua superficiales",
        download_url=(
            "https://www.miteco.gob.es/es/cartografia-y-sig/ide/"
            "descargas/agua/masas-de-agua-phc-2022-2027.html"
        ),
        file_pattern=r"masas_agua_sup.*\.zip",
        column_mapping={
            "COD_MASA": "codigo_masa",
            "NOMBRE": "nombre",
            "TIPO": "tipo",
            "CATEGORIA": "categoria",
            "EST_ECOL": "estado_ecologico",
            "EST_QUIM": "estado_quimico",
            "DEMARCA": "demarcacion",
            "geometry": "geom",
        },
        filter_demarcacion=["Galicia-Costa", "Miño-Sil"],
    ),
    LayerConfig(
        table_name="masas_agua_subterranea",
        display_name="Masas de agua subterráneas",
        download_url=(
            "https://www.miteco.gob.es/es/cartografia-y-sig/ide/"
            "descargas/agua/masas-de-agua-phc-2022-2027.html"
        ),
        file_pattern=r"masas_agua_sub.*\.zip",
        column_mapping={
            "COD_MASA": "codigo_masa",
            "NOMBRE": "nombre",
            "EST_CUANT": "estado_cuantitativo",
            "EST_QUIM": "estado_quimico",
            "SUP_KM2": "superficie_km2",
            "DEMARCA": "demarcacion",
            "geometry": "geom",
        },
        filter_demarcacion=["Galicia-Costa", "Miño-Sil"],
    ),
]


# ==============================================================================
# Core Functions
# ==============================================================================


def find_download_links(page_url: str, file_pattern: str) -> list[str]:
    """
    Scrape a MITECO/CNIG download page for ZIP file links matching a pattern.

    Parameters
    ----------
    page_url : str
        URL of the download page.
    file_pattern : str
        Regex pattern to filter relevant links (case-insensitive).

    Returns
    -------
    list[str]
        Matching download URLs.
    """
    try:
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch page %s: %s", page_url, exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if re.search(file_pattern, href, re.IGNORECASE):
            full_url = urljoin(page_url, href)
            links.append(full_url)

    logger.info("Found %d matching download link(s) on %s", len(links), page_url)
    return links


def download_file(url: str) -> Optional[bytes]:
    """
    Download a file from the given URL.

    Returns the raw bytes, or None on failure.
    """
    try:
        response = session.get(url, timeout=120)
        response.raise_for_status()
        logger.info("Downloaded %d bytes from %s", len(response.content), url)
        return response.content
    except requests.RequestException as exc:
        logger.error("Failed to download %s: %s", url, exc)
        return None


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of the given bytes."""
    return hashlib.sha256(data).hexdigest()


def get_last_file_hash(table_name: str) -> Optional[str]:
    """Retrieve the SHA-256 hash from the last successful update."""
    engine = create_engine(settings.database_url)
    query = text("""
        SELECT file_hash FROM layer_update_log
        WHERE layer_name = :name AND status = 'success'
        ORDER BY started_at DESC LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"name": table_name}).fetchone()
    return row.file_hash if row else None


def log_update(
    table_name: str,
    status: str,
    records_loaded: Optional[int] = None,
    source_url: Optional[str] = None,
    error_message: Optional[str] = None,
    file_hash: Optional[str] = None,
):
    """Record an update attempt in the layer_update_log table."""
    engine = create_engine(settings.database_url)
    query = text("""
        INSERT INTO layer_update_log
            (layer_name, status, finished_at, records_loaded, source_url, error_message, file_hash)
        VALUES
            (:name, :status, NOW(), :records, :url, :error, :hash)
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "name": table_name,
            "status": status,
            "records": records_loaded,
            "url": source_url,
            "error": error_message,
            "hash": file_hash,
        })


def extract_shapefile_from_zip(zip_bytes: bytes) -> gpd.GeoDataFrame:
    """
    Extract and read a shapefile from an in-memory ZIP file.

    Parameters
    ----------
    zip_bytes : bytes
        Raw ZIP file content.

    Returns
    -------
    GeoDataFrame
        The first layer found in the ZIP archive.
    """
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        # Find the .shp file inside the archive
        shp_files = [f for f in zf.namelist() if f.lower().endswith(".shp")]
        if not shp_files:
            raise ValueError("No shapefile (.shp) found in the ZIP archive.")

        # GeoPandas can read directly from the ZIP via a virtual /vsizip/ path
        shp_path = f"/vsizip/{BytesIO(zip_bytes).getbuffer().name}/{shp_files[0]}"

        # Alternative: write to a temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            zf.extractall(tmpdir)
            shp_full_path = str(Path(tmpdir) / shp_files[0])
            gdf = gpd.read_file(shp_full_path)

    if gdf.empty:
        raise ValueError("Shapefile is empty (no features).")

    logger.info("Read %d features from shapefile", len(gdf))
    return gdf


def process_gdf(gdf: gpd.GeoDataFrame, layer_cfg: LayerConfig) -> gpd.GeoDataFrame:
    """
    Process a GeoDataFrame: reproject, filter by Galicia bbox, rename columns.

    Parameters
    ----------
    gdf : GeoDataFrame
        Raw data from the shapefile.
    layer_cfg : LayerConfig
        Layer configuration with column mapping.

    Returns
    -------
    GeoDataFrame
        Cleaned and reprojected data ready for database insertion.
    """
    # ── Reproject to target SRID if needed ──
    if gdf.crs is None:
        logger.warning("No CRS found — assuming EPSG:4258 (ETRS89)")
        gdf = gdf.set_crs(epsg=4258)

    if gdf.crs.to_epsg() != TARGET_SRID:
        gdf = gdf.to_crs(epsg=TARGET_SRID)
        logger.info("Reprojected from EPSG:%s to EPSG:%s", gdf.crs.to_epsg(), TARGET_SRID)

    # ── Filter by Galicia bounding box ──
    galicia_bbox_25830 = GALICIA_BBOX_4326.to_crs(4326, TARGET_SRID)
    gdf = gdf[gdf.intersects(galicia_bbox_25830)]
    logger.info("Filtered to %d features within Galicia bbox", len(gdf))

    # ── Demarcation filter (for water-related layers) ──
    if layer_cfg.filter_demarcacion:
        demarc_col = None
        for col in gdf.columns:
            if col.upper() in ("DEMARCA", "DEMARCATIO", "DEMACRACION"):
                demarc_col = col
                break
        if demarc_col and demarc_col in gdf.columns:
            gdf = gdf[gdf[demarc_col].isin(layer_cfg.filter_demarcacion)]
            logger.info(
                "Filtered to %d features after demarcation filter", len(gdf)
            )

    # ── Rename columns to match the database schema ──
    rename_map = {
        src: dst for src, dst in layer_cfg.column_mapping.items() if src != "geometry"
    }
    gdf = gdf.rename(columns=rename_map)

    # Ensure 'geom' column exists
    if gdf.geometry.name != "geom" and "geometry" in gdf.columns:
        gdf = gdf.rename_geometry("geom")

    return gdf


def load_to_db(gdf: gpd.GeoDataFrame, table_name: str):
    """
    Load a GeoDataFrame into the database using TRUNCATE + INSERT in a single
    atomic transaction. If anything fails, the transaction is rolled back
    and the previous data remains intact.

    Parameters
    ----------
    gdf : GeoDataFrame
        Processed data ready for insertion.
    table_name : str
        Target database table name.
    """
    engine = create_engine(settings.database_url)

    with engine.begin() as conn:
        # Set statement timeout for this session
        conn.execute(text(f"SET statement_timeout = '{settings.query_timeout_seconds}s'"))

        # Truncate the table
        conn.execute(text(f"TRUNCATE TABLE {table_name}"))

        # Insert using GeoPandas to_postgis
        gdf.to_postgis(
            name=table_name,
            con=conn,
            if_exists="append",
            index=False,
            schema="public",
        )

        # VACUUM ANALYZE for query planner optimization
        conn.execute(text(f"VACUUM ANALYZE {table_name}"))

    logger.info("Successfully loaded %d records into %s", len(gdf), table_name)


# ==============================================================================
# Main Update Loop
# ==============================================================================


def update_layer(layer_cfg: LayerConfig):
    """
    Update a single environmental layer from its source URL.

    Flow:
        1. Find download links
        2. Download the ZIP file
        3. Check if the file has changed (SHA-256)
        4. Extract and process the shapefile
        5. Load into the database (atomic transaction)
    """
    logger.info("=" * 60)
    logger.info("Updating layer: %s", layer_cfg.display_name)
    logger.info("=" * 60)

    start_time = time.time()

    try:
        # ── Step 1: Find download links ──
        links = find_download_links(layer_cfg.download_url, layer_cfg.file_pattern)
        if not links:
            logger.warning("No download links found for %s — skipping", layer_cfg.display_name)
            log_update(
                layer_cfg.table_name,
                "failed",
                source_url=layer_cfg.download_url,
                error_message="No download links found on the source page.",
            )
            return

        download_url = links[0]

        # ── Step 2: Download the file ──
        zip_bytes = download_file(download_url)
        if zip_bytes is None:
            log_update(
                layer_cfg.table_name,
                "failed",
                source_url=download_url,
                error_message="Download failed — could not retrieve the file.",
            )
            return

        file_hash = compute_sha256(zip_bytes)

        # ── Step 3: Check if the file has changed ──
        last_hash = get_last_file_hash(layer_cfg.table_name)
        if last_hash == file_hash:
            logger.info(
                "File hash unchanged for %s — skipping update", layer_cfg.display_name
            )
            log_update(
                layer_cfg.table_name,
                "skipped",
                source_url=download_url,
                file_hash=file_hash,
            )
            return

        # ── Step 4: Extract and process shapefile ──
        gdf = extract_shapefile_from_zip(zip_bytes)
        gdf = process_gdf(gdf, layer_cfg)

        if gdf.empty:
            logger.warning(
                "No features remaining after filtering for %s — skipping load",
                layer_cfg.display_name,
            )
            log_update(
                layer_cfg.table_name,
                "failed",
                source_url=download_url,
                error_message="No features remaining after spatial filtering.",
                file_hash=file_hash,
            )
            return

        # ── Step 5: Load to database ──
        load_to_db(gdf, layer_cfg.table_name)

        elapsed = time.time() - start_time
        log_update(
            layer_cfg.table_name,
            "success",
            records_loaded=len(gdf),
            source_url=download_url,
            file_hash=file_hash,
        )
        logger.info(
            "Layer %s updated successfully in %.1fs (%d records)",
            layer_cfg.display_name,
            elapsed,
            len(gdf),
        )

    except Exception as exc:
        elapsed = time.time() - start_time
        logger.exception(
            "Failed to update layer %s after %.1fs: %s",
            layer_cfg.display_name,
            elapsed,
            exc,
        )
        log_update(
            layer_cfg.table_name,
            "failed",
            source_url=layer_cfg.download_url,
            error_message=str(exc),
        )


def main():
    """
    Entry point: iterate over all configured layers and update each one.

    Called by the cron job on the 1st of every month at 03:00 UTC.
    """
    logger.info("=" * 60)
    logger.info(
        "GeoViable — Layer update started at %s UTC",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    )
    logger.info("=" * 60)

    for layer_cfg in LAYERS:
        update_layer(layer_cfg)

    logger.info("=" * 60)
    logger.info("All layer updates completed.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
