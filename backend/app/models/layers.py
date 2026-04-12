"""
GeoViable — SQLAlchemy / GeoAlchemy2 Database Models

Maps every environmental layer table in PostgreSQL/PostGIS.
All geometries use EPSG:25830 (ETRS89 / UTM zone 30N).
"""

from geoalchemy2 import Geometry
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# ── SRID constant for all geometries ──
SRID = 25830


# ==============================================================================
# Metadata: Layer Update Log
# ==============================================================================
class LayerUpdateLog(Base):
    """
    Tracks every attempt to refresh an environmental layer.

    Records success, failure, source URL, record count, and file hash
    (to skip redundant re-downloads of unchanged data).
    """

    __tablename__ = "layer_update_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # 'success' | 'failed' | 'skipped'
    started_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at = Column(DateTime(timezone=True))
    records_loaded = Column(Integer)
    source_url = Column(Text)
    error_message = Column(Text)
    file_hash = Column(String(64))  # SHA-256 of downloaded ZIP


# ==============================================================================
# Environmental Layer Models
# ==============================================================================


class RedNatura2000(Base):
    """
    Red Natura 2000 — ZEPA, LIC, and ZEC protected areas.

    Source: MITECO
    Geometry: MultiPolygon
    """

    __tablename__ = "red_natura_2000"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(20), nullable=False)  # e.g. "ES1110001"
    nombre = Column(String(255), nullable=False)
    tipo = Column(String(10), nullable=False)  # 'ZEPA' | 'LIC' | 'ZEC'
    superficie_ha = Column(Numeric(12, 2))
    geom = Column(Geometry("MULTIPOLYGON", srid=SRID, spatial_index=False), nullable=False)

    __table_args__ = (
        # Explicit GIST index creation (GeoAlchemy does not auto-create)
    )

    def __repr__(self):
        return f"<RedNatura2000 codigo={self.codigo} tipo={self.tipo}>"


class ZonasInundables(Base):
    """
    Flood zones from SNCZI — T100 and T500 return periods.

    Source: MITECO
    Geometry: MultiPolygon
    """

    __tablename__ = "zonas_inundables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    periodo_retorno = Column(String(10), nullable=False)  # 'T100' | 'T500'
    nivel_peligrosidad = Column(String(50))
    demarcacion = Column(String(100))
    geom = Column(Geometry("MULTIPOLYGON", srid=SRID, spatial_index=False), nullable=False)

    def __repr__(self):
        return f"<ZonasInundables periodo={self.periodo_retorno}>"


class DominioPublicoHidraulico(Base):
    """
    Hydraulic Public Domain — river channels, banks, and margins.

    Source: MITECO
    Geometry: MultiPolygon
    """

    __tablename__ = "dominio_publico_hidraulico"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(50), nullable=False)  # 'cauce' | 'ribera' | 'margen'
    nombre_cauce = Column(String(255))
    categoria = Column(String(100))
    geom = Column(Geometry("MULTIPOLYGON", srid=SRID, spatial_index=False), nullable=False)

    def __repr__(self):
        return f"<DPH tipo={self.tipo} cauce={self.nombre_cauce}>"


class ViasPecuarias(Base):
    """
    Livestock routes (vías pecuarias) — cañadas, cordeles, veredas.

    Source: CNIG
    Geometry: MultiLineString (linear features, buffered by anchura_legal_m)
    """

    __tablename__ = "vias_pecuarias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255))
    tipo_via = Column(String(100))  # 'cañada' | 'cordel' | 'vereda' | 'colada'
    anchura_legal_m = Column(Numeric(6, 2))
    longitud_m = Column(Numeric(12, 2))
    estado_deslinde = Column(String(50))
    municipio = Column(String(100))
    provincia = Column(String(50))
    geom = Column(Geometry("MULTILINESTRING", srid=SRID, spatial_index=False), nullable=False)

    def __repr__(self):
        return f"<ViasPecuarias nombre={self.nombre}>"


class EspaciosNaturalesProtegidos(Base):
    """
    Protected Natural Spaces — national parks, natural parks, reserves.

    Source: MITECO
    Geometry: MultiPolygon
    """

    __tablename__ = "espacios_naturales_protegidos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(20))
    nombre = Column(String(255), nullable=False)
    categoria = Column(String(100), nullable=False)
    subcategoria = Column(String(100))
    superficie_ha = Column(Numeric(12, 2))
    geom = Column(Geometry("MULTIPOLYGON", srid=SRID, spatial_index=False), nullable=False)

    def __repr__(self):
        return f"<ENP nombre={self.nombre} categoria={self.categoria}>"


class MasasAguaSuperficial(Base):
    """
    Surface water masses — rivers, lakes, reservoirs, coastal waters.

    Source: MITECO (PHC 2022-2027)
    Geometry: Generic Geometry (can be Polygon or LineString for rivers)
    """

    __tablename__ = "masas_agua_superficial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_masa = Column(String(30))
    nombre = Column(String(255))
    tipo = Column(String(100))  # 'río' | 'lago' | 'embalse' | 'costera' | 'transición'
    categoria = Column(String(100))
    estado_ecologico = Column(String(50))  # 'bueno' | 'moderado' | 'deficiente' | 'malo'
    estado_quimico = Column(String(50))
    demarcacion = Column(String(100))
    geom = Column(Geometry("GEOMETRY", srid=SRID, spatial_index=False), nullable=False)

    def __repr__(self):
        return f"<MasaAguaSuperficial nombre={self.nombre} tipo={self.tipo}>"


class MasasAguaSubterranea(Base):
    """
    Groundwater masses — aquifers.

    Source: MITECO (PHC 2022-2027)
    Geometry: MultiPolygon
    """

    __tablename__ = "masas_agua_subterranea"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_masa = Column(String(30))
    nombre = Column(String(255))
    estado_cuantitativo = Column(String(50))  # 'bueno' | 'malo'
    estado_quimico = Column(String(50))  # 'bueno' | 'malo'
    superficie_km2 = Column(Numeric(10, 2))
    demarcacion = Column(String(100))
    geom = Column(Geometry("MULTIPOLYGON", srid=SRID, spatial_index=False), nullable=False)

    def __repr__(self):
        return f"<MasaAguaSubterranea nombre={self.nombre}>"
