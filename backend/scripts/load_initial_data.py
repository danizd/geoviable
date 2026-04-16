"""
GeoViable — Carga inicial de datos ambientales desde ZIPs locales

Lee los Shapefiles descargados manualmente de MITECO/CNIG desde el
directorio /app/data/ (configurable vía DATA_DIR), los procesa con
GeoPandas y los carga en PostGIS mediante TRUNCATE + INSERT atómico.

Uso:
    # Cargar todas las capas
    python -m scripts.load_initial_data

    # Inspeccionar columnas y CRS sin cargar datos
    python -m scripts.load_initial_data --inspect

    # Cargar solo una capa específica
    python -m scripts.load_initial_data --layer red_natura_2000
"""

import argparse
import logging
import os
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import geopandas as gpd
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Polygon,
    box,
)
from shapely.ops import transform
from sqlalchemy import create_engine, text

# Añadir el directorio padre al path para importar módulos de la app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("load_initial_data")

settings = get_settings()

# ── Constantes ──
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
TARGET_SRID = 25830
GALICIA_BBOX_WGS84 = (-9.5, 41.5, -6.5, 44.0)  # (minx, miny, maxx, maxy)


# ==============================================================================
# Configuración de capas
# ==============================================================================


@dataclass
class LocalLayerConfig:
    """Configuración para cargar una capa ambiental desde un ZIP local."""

    table_name: str
    display_name: str
    zip_files: list          # nombres de archivo dentro de DATA_DIR
    column_mapping: dict     # {campo_shapefile: columna_bd} (búsqueda case-insensitive)
    db_columns: list         # columnas de la tabla BD (sin geometría)
    filter_demarcacion: Optional[list] = None
    is_linear: bool = False  # True para vias_pecuarias (geometría lineal)
    period_hint: Optional[str] = None  # inyecta 'periodo_retorno' si no existe en datos
    truncate: bool = True    # si True, hace TRUNCATE antes del INSERT


LOCAL_LAYERS = [
    LocalLayerConfig(
        table_name="red_natura_2000",
        display_name="Red Natura 2000",
        zip_files=["red_natura_2000.zip"],
        column_mapping={
            "SITE_CODE": "codigo",
            "SITE_NAME": "nombre",
            "TIPO": "tipo",
            "HECTAREAS": "superficie_ha",
        },
        db_columns=["codigo", "nombre", "tipo", "superficie_ha"],
    ),
    LocalLayerConfig(
        table_name="zonas_inundables",
        display_name="Zonas inundables T100",
        zip_files=["zonas_inundables_t100.zip"],
        column_mapping={
            "DEMARCACIO": "demarcacion",
        },
        db_columns=["periodo_retorno", "nivel_peligrosidad", "demarcacion"],
        filter_demarcacion=["Galicia-Costa", "Miño-Sil"],
        period_hint="T100",
        truncate=True,
    ),
    LocalLayerConfig(
        table_name="zonas_inundables",
        display_name="Zonas inundables T500",
        zip_files=["zonas_inundables_t500.zip"],
        column_mapping={
            "DEMARCACIO": "demarcacion",
        },
        db_columns=["periodo_retorno", "nivel_peligrosidad", "demarcacion"],
        filter_demarcacion=["Galicia-Costa", "Miño-Sil"],
        period_hint="T500",
        truncate=False,  # la tabla ya fue truncada al cargar T100
    ),
    LocalLayerConfig(
        table_name="dominio_publico_hidraulico",
        display_name="Dominio Público Hidráulico",
        zip_files=["dph.zip"],
        column_mapping={
            "TIPO_ZONA": "tipo",
            "RIO": "nombre_cauce",
            "DEMARCACIO": "demarcacion",
        },
        db_columns=["tipo", "nombre_cauce", "categoria", "demarcacion"],
        filter_demarcacion=["Galicia-Costa", "Miño-Sil"],
    ),
    LocalLayerConfig(
        table_name="vias_pecuarias",
        display_name="Vías pecuarias",
        zip_files=["vias_pecuarias.zip"],
        column_mapping={
            "nombre": "nombre",
            "longitud": "longitud_m",
            "estado": "estado_deslinde",
            "provincia": "provincia",
        },
        db_columns=[
            "nombre", "tipo_via", "anchura_legal_m", "longitud_m",
            "estado_deslinde", "municipio", "provincia",
        ],
        is_linear=True,
    ),
    LocalLayerConfig(
        table_name="espacios_naturales_protegidos",
        display_name="Espacios Naturales Protegidos",
        zip_files=["enp.zip"],
        column_mapping={
            "SITE_CODE_": "codigo",
            "SITE_NAME": "nombre",
            "ODESIGNATE": "categoria",
            "DESIG_ABBR": "subcategoria",
            "Sup_ha": "superficie_ha",
        },
        db_columns=["codigo", "nombre", "categoria", "subcategoria", "superficie_ha"],
    ),
    LocalLayerConfig(
        table_name="masas_agua_superficial",
        display_name="Masas de agua superficiales",
        zip_files=["masas_agua_superficial.zip"],
        column_mapping={
            "CodMasa": "codigo_masa",
            "NombreMasa": "nombre",
            "NomTipoNa": "tipo",
            "Categoria": "categoria",
            "NomDemarc": "demarcacion",
        },
        db_columns=[
            "codigo_masa", "nombre", "tipo", "categoria",
            "estado_ecologico", "estado_quimico", "demarcacion",
        ],
        filter_demarcacion=None,  # Los códigos PHC varían entre versiones del dataset; el bbox ya filtra a Galicia
    ),
    LocalLayerConfig(
        table_name="masas_agua_subterranea",
        display_name="Masas de agua subterráneas",
        zip_files=["masas_agua_subterranea.zip"],
        column_mapping={
            "thematicId": "codigo_masa",
        },
        db_columns=[
            "codigo_masa", "nombre", "estado_cuantitativo",
            "estado_quimico", "superficie_km2", "demarcacion",
        ],
        filter_demarcacion=None,  # Solo 74 features globales; bbox de Galicia es suficiente
    ),
]


# ==============================================================================
# Funciones auxiliares de geometría
# ==============================================================================


def to_multipolygon(geom):
    """Promociona una geometría a MultiPolygon (requerido por el esquema BD)."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    if isinstance(geom, GeometryCollection):
        polys = []
        for g in geom.geoms:
            if isinstance(g, Polygon):
                polys.append(g)
            elif isinstance(g, MultiPolygon):
                polys.extend(list(g.geoms))
        if polys:
            return MultiPolygon(polys)
    return None


def to_multilinestring(geom):
    """Promociona una geometría a MultiLineString (requerido para vias_pecuarias)."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, MultiLineString):
        return geom
    if isinstance(geom, LineString):
        return MultiLineString([list(geom.coords)])
    if isinstance(geom, GeometryCollection):
        lines = []
        for g in geom.geoms:
            if isinstance(g, LineString):
                lines.append(list(g.coords))
            elif isinstance(g, MultiLineString):
                lines.extend([list(line.coords) for line in g.geoms])
        if lines:
            return MultiLineString(lines)
    return None


def promote_geometry(gdf: gpd.GeoDataFrame, cfg: LocalLayerConfig) -> gpd.GeoDataFrame:
    """
    Convierte geometrías simples a Multi* según el tipo de capa.
    masas_agua_superficial usa tipo Geometry genérico — no necesita promoción.
    """
    if cfg.table_name == "masas_agua_superficial":
        return gdf

    convert_fn = to_multilinestring if cfg.is_linear else to_multipolygon

    gdf = gdf.copy()
    before = len(gdf)
    gdf["geometry"] = gdf.geometry.apply(convert_fn)

    null_mask = gdf.geometry.isna()
    if null_mask.any():
        logger.warning(
            "[%s] Se descartan %d features con tipo de geometría no convertible",
            cfg.table_name, null_mask.sum(),
        )
        gdf = gdf[~null_mask].copy()

    logger.info("[%s] Promoción geometría: %d → %d features", cfg.table_name, before, len(gdf))
    return gdf


# ==============================================================================
# Funciones de procesamiento
# ==============================================================================


def read_zip_to_gdf(zip_path: Path) -> gpd.GeoDataFrame:
    """Lee el primer Shapefile encontrado dentro de un archivo ZIP."""
    with zipfile.ZipFile(zip_path) as zf:
        shp_files = [f for f in zf.namelist() if f.lower().endswith(".shp")]
        if not shp_files:
            raise ValueError(f"No se encontró ningún .shp en {zip_path.name}")
        # Preferir shapefile peninsular (descartar Macaronesia/Canarias si hay varios)
        _SKIP_KW = ("mac", "_can", "canaria", "macarone")
        preferred = [
            f for f in shp_files
            if not any(kw in Path(f).stem.lower() for kw in _SKIP_KW)
        ]
        selected_shp = preferred[0] if preferred else shp_files[0]
        if len(shp_files) > 1:
            logger.warning(
                "%s contiene %d shapefiles — usando: %s",
                zip_path.name, len(shp_files), selected_shp,
            )
        with tempfile.TemporaryDirectory() as tmpdir:
            zf.extractall(tmpdir)
            shp_path = Path(tmpdir) / selected_shp
            gdf = gpd.read_file(str(shp_path))

    if gdf.empty:
        raise ValueError(f"El shapefile en {zip_path.name} está vacío")

    logger.info("[%s] Leídos %d features de %s", zip_path.stem, len(gdf), zip_path.name)
    return gdf


def get_galicia_bbox_25830():
    """Retorna el bbox de Galicia como geometría Shapely en EPSG:25830."""
    return (
        gpd.GeoSeries([box(*GALICIA_BBOX_WGS84)], crs=4326)
        .to_crs(epsg=TARGET_SRID)
        .iloc[0]
    )


def _force_2d(geom):
    """Elimina la coordenada Z de una geometría (PostGIS rechaza 3D en columnas 2D)."""
    if geom is None or geom.is_empty:
        return geom
    return transform(lambda x, y, z=None: (x, y), geom)


def filter_by_galicia(gdf: gpd.GeoDataFrame, table_name: str) -> gpd.GeoDataFrame:
    """Elimina features fuera del bbox de Galicia. Sanea geometrías inválidas antes del predicado."""
    galicia_geom = get_galicia_bbox_25830()

    invalid_mask = ~gdf.geometry.is_valid
    if invalid_mask.any():
        logger.warning(
            "[%s] Sanando %d geometrías inválidas antes del filtro bbox",
            table_name, int(invalid_mask.sum()),
        )
        gdf = gdf.copy()
        gdf.loc[invalid_mask, gdf.geometry.name] = (
            gdf.geometry[invalid_mask].buffer(0)
        )

    mask = gdf.intersects(galicia_geom)
    result = gdf[mask].copy()
    logger.info("[%s] Filtro Galicia bbox: %d → %d features", table_name, len(gdf), len(result))
    return result


def filter_by_demarcacion(
    gdf: gpd.GeoDataFrame, allowed: list, table_name: str
) -> gpd.GeoDataFrame:
    """Filtra por demarcación hidrográfica con búsqueda de columna case-insensitive."""
    _DEMARC_VARIANTS = {
        "DEMARCA", "DEMARCATIO", "DEMARCACION", "DEMARC",
        "DEMARCACIO", "NOMDEMARC", "CODDEMAR", "CODDEMARC",
    }
    demarc_col = next(
        (c for c in gdf.columns if c.upper() in _DEMARC_VARIANTS),
        None,
    )
    if demarc_col is None:
        logger.warning(
            "[%s] Filtro demarcación solicitado pero no se encontró columna DEMARCA en: %s",
            table_name, list(gdf.columns),
        )
        return gdf

    before = len(gdf)
    result = gdf[gdf[demarc_col].isin(allowed)].copy()
    logger.info(
        "[%s] Filtro demarcación '%s': %d → %d features",
        table_name, demarc_col, before, len(result),
    )
    return result


def apply_column_mapping(
    gdf: gpd.GeoDataFrame, cfg: LocalLayerConfig
) -> gpd.GeoDataFrame:
    """Renombra columnas del shapefile a los nombres de la BD (case-insensitive)."""
    cols_lower = {c.lower(): c for c in gdf.columns}
    rename_map = {}
    for src, dst in cfg.column_mapping.items():
        actual = cols_lower.get(src.lower())
        if actual:
            rename_map[actual] = dst
        else:
            logger.warning(
                "[%s] Columna '%s' → '%s': no encontrada en shapefile (será NULL)",
                cfg.table_name, src, dst,
            )
    return gdf.rename(columns=rename_map)


def process_gdf(gdf: gpd.GeoDataFrame, cfg: LocalLayerConfig) -> gpd.GeoDataFrame:
    """Pipeline completo: reproyectar → filtrar → renombrar → promocionar → seleccionar."""

    # 1. Asignar CRS si falta
    if gdf.crs is None:
        logger.warning("[%s] CRS no detectado — asumiendo EPSG:4258", cfg.table_name)
        gdf = gdf.set_crs(epsg=4258)

    # 2. Reproyectar a EPSG:25830
    original_epsg = gdf.crs.to_epsg()
    if original_epsg != TARGET_SRID:
        gdf = gdf.to_crs(epsg=TARGET_SRID)
        logger.info("[%s] Reproyectado EPSG:%s → EPSG:25830", cfg.table_name, original_epsg)

    # 2b. Eliminar coordenada Z si existe (PostGIS rechaza geometrías 3D en columnas 2D)
    if gdf.geometry.has_z.any():
        logger.info("[%s] Eliminando coordenada Z (forzando 2D)", cfg.table_name)
        gdf = gdf.copy()
        gdf[gdf.geometry.name] = gdf.geometry.apply(_force_2d)

    # 3. Filtrar por bbox de Galicia
    gdf = filter_by_galicia(gdf, cfg.table_name)
    if gdf.empty:
        raise ValueError(f"[{cfg.table_name}] Sin features tras el filtro de Galicia")

    # 4. Filtrar por demarcación hidrográfica
    if cfg.filter_demarcacion:
        gdf = filter_by_demarcacion(gdf, cfg.filter_demarcacion, cfg.table_name)
        if gdf.empty:
            raise ValueError(f"[{cfg.table_name}] Sin features tras el filtro de demarcación")

    # 5. Renombrar columnas según el mapping
    gdf = apply_column_mapping(gdf, cfg)

    # 6. Inyectar periodo_retorno si no existe y se ha indicado un hint
    if cfg.period_hint and "periodo_retorno" not in gdf.columns:
        gdf = gdf.copy()
        gdf["periodo_retorno"] = cfg.period_hint
        logger.info("[%s] Inyectado periodo_retorno = '%s'", cfg.table_name, cfg.period_hint)

    # 7. Promocionar geometrías a tipo Multi*
    gdf = promote_geometry(gdf, cfg)

    # 8. Renombrar columna de geometría a 'geom'
    if gdf.geometry.name != "geom":
        gdf = gdf.rename_geometry("geom")

    # 9. Añadir columnas NULL para las que no se encontraron en el shapefile
    for col in cfg.db_columns:
        if col not in gdf.columns:
            gdf[col] = None

    # 10. Seleccionar solo las columnas que necesita la tabla
    gdf = gdf[cfg.db_columns + ["geom"]].copy()

    return gdf


# ==============================================================================
# Funciones de base de datos
# ==============================================================================


def load_to_db(gdf: gpd.GeoDataFrame, cfg: LocalLayerConfig):
    """
    Carga datos en la BD.
    TRUNCATE + INSERT en transacción atómica.
    VACUUM ANALYZE fuera de la transacción (requiere AUTOCOMMIT).
    """
    engine = create_engine(settings.database_url)

    with engine.begin() as conn:
        if cfg.truncate:
            conn.execute(text(f"TRUNCATE TABLE {cfg.table_name}"))
            logger.info("[%s] Tabla truncada", cfg.table_name)

        gdf.to_postgis(
            name=cfg.table_name,
            con=conn,
            if_exists="append",
            index=False,
            schema="public",
        )
        logger.info("[%s] %d registros insertados", cfg.table_name, len(gdf))

    # VACUUM no puede ejecutarse dentro de una transacción — requiere AUTOCOMMIT
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"VACUUM ANALYZE {cfg.table_name}"))
        logger.info("[%s] VACUUM ANALYZE completado", cfg.table_name)


def log_update(
    table_name: str,
    status: str,
    records_loaded: Optional[int] = None,
    source_url: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """Registra el intento de carga en la tabla layer_update_log."""
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO layer_update_log
                    (layer_name, status, finished_at, records_loaded, source_url, error_message)
                VALUES
                    (:name, :status, NOW(), :records, :url, :error)
            """),
            {
                "name": table_name,
                "status": status,
                "records": records_loaded,
                "url": source_url,
                "error": error_message,
            },
        )


# ==============================================================================
# Modo inspección
# ==============================================================================


def inspect_layer(cfg: LocalLayerConfig):
    """Imprime metadatos del shapefile y estado del column mapping sin cargar datos."""
    print(f"\n{'═' * 65}")
    print(f"  {cfg.display_name}")
    print(f"{'═' * 65}")

    for zip_file in cfg.zip_files:
        zip_path = DATA_DIR / zip_file
        print(f"  ZIP : {zip_path}")

        if not zip_path.exists():
            print(f"  ❌  Fichero no encontrado!")
            continue

        try:
            gdf = read_zip_to_gdf(zip_path)
            epsg = gdf.crs.to_epsg() if gdf.crs else "Desconocido"
            geom_types = gdf.geom_type.value_counts().to_dict()

            print(f"  CRS : EPSG:{epsg}")
            print(f"  Geom: {geom_types}")
            print(f"  Rows: {len(gdf):,}")
            print(f"  Columnas ({len(gdf.columns)}): {sorted(gdf.columns.tolist())}")
            print(f"\n  Estado del column mapping:")

            cols_lower = {c.lower(): c for c in gdf.columns}
            for src, dst in cfg.column_mapping.items():
                actual = cols_lower.get(src.lower())
                if actual:
                    sample = gdf[actual].dropna().head(1).values
                    sample_str = f"  (ej: {sample[0]!r})" if len(sample) else ""
                    print(f"    ✓  {src:<15} → {dst}{sample_str}")
                else:
                    print(f"    ✗  {src:<15} → NO ENCONTRADO → {dst} será NULL")

            if cfg.filter_demarcacion:
                _DEMARC_VARIANTS = {
                    "DEMARCA", "DEMARCATIO", "DEMARCACION", "DEMARC",
                    "DEMARCACIO", "NOMDEMARC", "CODDEMAR", "CODDEMARC",
                }
                demarc_col = next(
                    (c for c in gdf.columns if c.upper() in _DEMARC_VARIANTS),
                    None,
                )
                print(f"\n  Filtro demarcación: {cfg.filter_demarcacion}")
                if demarc_col:
                    unique_vals = sorted(gdf[demarc_col].dropna().unique().tolist())
                    print(f"  Valores en '{demarc_col}': {unique_vals}")
                else:
                    print(f"  ⚠️  No se encontró columna de demarcación!")

        except Exception as exc:
            print(f"  ❌  Error: {exc}")


# ==============================================================================
# Carga de una capa
# ==============================================================================


def load_layer(cfg: LocalLayerConfig) -> int:
    """
    Pipeline completo para una capa: leer → procesar → cargar → registrar.
    Retorna el número de registros cargados.
    """
    logger.info("─" * 65)
    logger.info("Cargando: %s", cfg.display_name)

    start = time.perf_counter()

    zip_path = DATA_DIR / cfg.zip_files[0]
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP no encontrado: {zip_path}")

    gdf = read_zip_to_gdf(zip_path)
    gdf = process_gdf(gdf, cfg)

    if gdf.empty:
        raise ValueError(f"Sin features para cargar en {cfg.display_name}")

    load_to_db(gdf, cfg)
    log_update(
        cfg.table_name,
        "success",
        records_loaded=len(gdf),
        source_url=str(zip_path),
    )

    elapsed = time.perf_counter() - start
    logger.info("✓ %s: %d registros en %.1fs", cfg.display_name, len(gdf), elapsed)
    return len(gdf)


# ==============================================================================
# Verificación de carga
# ==============================================================================


def verify_counts():
    """Imprime el conteo final de registros en las 7 tablas ambientales."""
    engine = create_engine(settings.database_url)
    tables = [
        "red_natura_2000",
        "zonas_inundables",
        "dominio_publico_hidraulico",
        "vias_pecuarias",
        "espacios_naturales_protegidos",
        "masas_agua_superficial",
        "masas_agua_subterranea",
    ]
    print(f"\n{'═' * 55}")
    print("  VERIFICACIÓN DE REGISTROS EN BD")
    print(f"{'═' * 55}")
    with engine.connect() as conn:
        for table in tables:
            row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
            count = row[0] if row else 0
            status = "✓" if count > 0 else "⚠  VACÍA"
            print(f"  {status}  {table:<42} {count:>8,}")
    print(f"{'═' * 55}\n")


# ==============================================================================
# Punto de entrada
# ==============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Carga inicial de datos ambientales desde ZIPs locales",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Inspecciona columnas y CRS sin cargar datos",
    )
    parser.add_argument(
        "--layer",
        metavar="TABLA",
        help="Carga solo esta tabla (ej. red_natura_2000)",
    )
    args = parser.parse_args()

    layers = LOCAL_LAYERS
    if args.layer:
        layers = [cfg for cfg in LOCAL_LAYERS if cfg.table_name == args.layer]
        if not layers:
            available = sorted({cfg.table_name for cfg in LOCAL_LAYERS})
            print(f"Capa desconocida: '{args.layer}'")
            print(f"Disponibles: {available}")
            sys.exit(1)

    if args.inspect:
        for cfg in layers:
            inspect_layer(cfg)
        print()
        return

    # ── Carga completa ──
    results = {}
    for cfg in layers:
        try:
            count = load_layer(cfg)
            results[cfg.display_name] = ("✓", f"{count:,} registros")
        except Exception as exc:
            logger.exception("Error al cargar %s: %s", cfg.display_name, exc)
            try:
                log_update(cfg.table_name, "failed", error_message=str(exc))
            except Exception:
                pass
            results[cfg.display_name] = ("✗", str(exc))

    # ── Resumen ──
    print(f"\n{'═' * 65}")
    print("  RESUMEN DE CARGA")
    print(f"{'═' * 65}")
    for name, (status, info) in results.items():
        print(f"  {status}  {name:<42} {info}")

    # ── Verificación de conteos finales ──
    if not args.layer:
        try:
            verify_counts()
        except Exception as exc:
            logger.warning("No se pudo verificar los conteos: %s", exc)


if __name__ == "__main__":
    main()
