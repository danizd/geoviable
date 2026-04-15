"""
GeoViable — Load Sample Environmental Data

Inserts minimal sample data into all 7 environmental layer tables
so the application can be tested locally without downloading real
MITECO/CNIG shapefiles.

All geometries are in EPSG:25830 (ETRS89 / UTM 30N).
"""

import os
import sys

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()

# Connect directly to the database
# For Docker local, the host is 'geoviable-db'; for host machine, it's 'localhost'
db_url = settings.database_url
print(f"Connecting to: {db_url}")

engine = create_engine(db_url)

# ── Galicia bounding box in EPSG:25830 (UTM zone 30N) ──
# Western Galicia (Ría de Arousa area): lon ~-8.6, lat ~42.98
# → UTM 25830: X≈39000-48000, Y≈4770000-4778000
# NOTE: Earlier versions used UTM zone 29N coordinates (~680000-730000)
# which did NOT overlap with polygons projected to EPSG:25830.

SAMPLE_QUERIES = [
    # ── 1. Red Natura 2000 (ZEPA + LIC/ZEC) ──
    """
    INSERT INTO red_natura_2000 (codigo, nombre, tipo, superficie_ha, geom)
    VALUES
    ('ES1140001', 'Ria de Arousa', 'LIC', 15000.0,
        ST_GeomFromText('POLYGON((35000 4765000, 50000 4765000, 50000 4780000, 35000 4780000, 35000 4765000))', 25830)),
    ('ES1140002', 'Serra do Barbanza', 'ZEPA', 8000.0,
        ST_GeomFromText('POLYGON((30000 4760000, 45000 4760000, 45000 4775000, 30000 4775000, 30000 4760000))', 25830));
    """,

    # ── 2. Zonas Inundables (SNCZI) ──
    """
    INSERT INTO zonas_inundables (periodo_retorno, nivel_peligrosidad, demarcacion, geom)
    VALUES
    ('T100', 'Alto', 'Galicia-Costa',
        ST_GeomFromText('POLYGON((38000 4768000, 48000 4768000, 48000 4778000, 38000 4778000, 38000 4768000))', 25830)),
    ('T500', 'Medio', 'Galicia-Costa',
        ST_GeomFromText('POLYGON((36000 4766000, 52000 4766000, 52000 4782000, 36000 4782000, 36000 4766000))', 25830));
    """,

    # ── 3. Dominio Público Hidráulico ──
    """
    INSERT INTO dominio_publico_hidraulico (tipo, nombre_cauce, categoria, geom)
    VALUES
    ('cauce', 'Rio Ulla', 'Principal',
        ST_Multi(ST_Buffer(ST_GeomFromText('LINESTRING(30000 4775000, 40000 4772000, 50000 4769000)', 25830), 80))),
    ('cauce', 'Rio Arnoya', 'Secundario',
        ST_Multi(ST_Buffer(ST_GeomFromText('LINESTRING(35000 4765000, 45000 4770000, 55000 4775000)', 25830), 50)));
    """,

    # ── 4. Vías Pecuarias ──
    """
    INSERT INTO vias_pecuarias (nombre, tipo_via, anchura_legal_m, longitud_m, estado_deslinde, municipio, provincia, geom)
    VALUES
    ('Colada de Vilagarcia', 'Colada', 20.0, 12000.0, 'Deslindada', 'Vilagarcia de Arousa', 'Pontevedra',
        ST_GeomFromText('LINESTRING(32000 4778000, 42000 4774000, 52000 4770000)', 25830)),
    ('Cordel de Cambados', 'Cordel', 37.5, 8000.0, 'Sin deslindar', 'Cambados', 'Pontevedra',
        ST_GeomFromText('LINESTRING(28000 4768000, 38000 4772000, 48000 4776000)', 25830));
    """,

    # ── 5. Espacios Naturales Protegidos ──
    """
    INSERT INTO espacios_naturales_protegidos (codigo, nombre, categoria, subcategoria, superficie_ha, geom)
    VALUES
    ('ENP001', 'Ria de Arousa e Illa de Arousa', 'Parque Natural', 'Maritimo-terrestre', 22000.0,
        ST_GeomFromText('POLYGON((33000 4763000, 55000 4763000, 55000 4783000, 33000 4783000, 33000 4763000))', 25830)),
    ('ENP002', 'Duna de A Lamina', 'Monumento Natural', 'Terrestre', 150.0,
        ST_GeomFromText('POLYGON((40000 4769000, 44000 4769000, 44000 4773000, 40000 4773000, 40000 4769000))', 25830));
    """,

    # ── 6. Masas de Agua Superficiales ──
    """
    INSERT INTO masas_agua_superficial (codigo_masa, nombre, tipo, categoria, estado_ecologico, estado_quimico, demarcacion, geom)
    VALUES
    ('MAS001', 'Rio Ulla - Tramo bajo', 'Rio', 'Natural', 'Bueno', 'Conforme', 'Galicia-Costa',
        ST_GeomFromText('POLYGON((38000 4770000, 50000 4770000, 50000 4776000, 38000 4776000, 38000 4770000))', 25830)),
    ('MAS002', 'Estuario de Arousa', 'Costera', 'Natural', 'Bueno', 'Conforme', 'Galicia-Costa',
        ST_GeomFromText('POLYGON((30000 4764000, 55000 4764000, 55000 4780000, 30000 4780000, 30000 4764000))', 25830));
    """,

    # ── 7. Masas de Agua Subterráneas ──
    """
    INSERT INTO masas_agua_subterranea (codigo_masa, nombre, estado_cuantitativo, estado_quimico, superficie_km2, demarcacion, geom)
    VALUES
    ('MASUB001', 'Acuifero de la Ria de Arousa', 'Bueno', 'Bueno', 180.0, 'Galicia-Costa',
        ST_GeomFromText('POLYGON((25000 4760000, 60000 4760000, 60000 4785000, 25000 4785000, 25000 4760000))', 25830)),
    ('MASUB002', 'Acuifero del Salmes', 'Bueno', 'Bueno', 95.0, 'Galicia-Costa',
        ST_GeomFromText('POLYGON((20000 4765000, 50000 4765000, 50000 4780000, 20000 4780000, 20000 4765000))', 25830));
    """,
]


def main():
    print("Loading sample environmental data into PostgreSQL...")
    layer_names = [
        "Red Natura 2000",
        "Zonas Inundables",
        "Dominio Público Hidráulico",
        "Vías Pecuarias",
        "Espacios Naturales Protegidos",
        "Masas de Agua Superficiales",
        "Masas de Agua Subterráneas",
    ]
    with engine.connect() as conn:
        for i, query in enumerate(SAMPLE_QUERIES):
            name = layer_names[i] if i < len(layer_names) else f"Layer {i + 1}"
            try:
                conn.execute(text(query))
                conn.commit()  # Commit each layer individually
                print(f"  ✓ {name}: 2 features inserted")
            except Exception as e:
                conn.rollback()
                print(f"  ✗ {name}: {e}")
        conn.commit()

    # Verify
    print("\nVerifying data:")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 'red_natura_2000' as tabla, COUNT(*) FROM red_natura_2000
            UNION ALL SELECT 'zonas_inundables', COUNT(*) FROM zonas_inundables
            UNION ALL SELECT 'dominio_publico_hidraulico', COUNT(*) FROM dominio_publico_hidraulico
            UNION ALL SELECT 'vias_pecuarias', COUNT(*) FROM vias_pecuarias
            UNION ALL SELECT 'espacios_naturales_protegidos', COUNT(*) FROM espacios_naturales_protegidos
            UNION ALL SELECT 'masas_agua_superficial', COUNT(*) FROM masas_agua_superficial
            UNION ALL SELECT 'masas_agua_subterranea', COUNT(*) FROM masas_agua_subterranea;
        """))
        for row in result:
            print(f"  {row[0]:40s} → {row[1]} rows")

    print("\n✅ Sample data loaded successfully!")


if __name__ == "__main__":
    main()
