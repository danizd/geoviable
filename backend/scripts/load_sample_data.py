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

# ── Galicia bounding box in EPSG:25830 (approximate) ──
# Southwest: ~41.8N, -9.3W → UTM 25830: ~637000, 4630000
# Northeast: ~43.8N, -6.7W → UTM 25830: ~870000, 4850000
# Central point (Santiago): ~42.88N, -8.54W → UTM: ~705000, 4749000

SAMPLE_QUERIES = [
    # ── 1. Red Natura 2000 (ZEPA + LIC/ZEC) ──
    """
    INSERT INTO red_natura_2000 (nombre, tipo, codigo, geom)
    VALUES
    (
        'Ría de Arousa',
        'LIC',
        'ES1140001',
        ST_GeomFromText(
            'POLYGON((680000 4720000, 720000 4720000, 720000 4740000, 680000 4740000, 680000 4720000))',
            25830
        )
    ),
    (
        'Serra do Courel',
        'ZEPA',
        'ES1140002',
        ST_GeomFromText(
            'POLYGON((700000 4690000, 730000 4690000, 730000 4710000, 700000 4710000, 700000 4690000))',
            25830
        )
    );
    """,

    # ── 2. Zonas Inundables (SNCZI) ──
    """
    INSERT INTO zonas_inundables (periodo_retorno, nivel_peligrosidad, demarcacion, geom)
    VALUES
    (
        'T100',
        'Alto',
        'Galicia-Costa',
        ST_GeomFromText(
            'POLYGON((690000 4740000, 710000 4740000, 710000 4750000, 690000 4750000, 690000 4740000))',
            25830
        )
    ),
    (
        'T500',
        'Medio',
        'Miño-Sil',
        ST_GeomFromText(
            'POLYGON((660000 4680000, 690000 4680000, 690000 4700000, 660000 4700000, 660000 4680000))',
            25830
        )
    );
    """,

    # ── 3. Dominio Público Hidráulico ──
    # Column expects MultiPolygon — we use ST_Multi to wrap the LineString
    # Actually DPH may accept both, but if schema is strict, use polygon buffer
    """
    INSERT INTO dominio_publico_hidraulico (tipo, nombre_cauce, categoria, geom)
    VALUES
    (
        'Río',
        'Río Ulla',
        'Principal',
        ST_Multi(
            ST_Buffer(
                ST_GeomFromText(
                    'LINESTRING(680000 4745000, 690000 4748000, 700000 4750000, 710000 4752000)',
                    25830
                ),
                50
            )
        )
    ),
    (
        'Río',
        'Río Miño',
        'Principal',
        ST_Multi(
            ST_Buffer(
                ST_GeomFromText(
                    'LINESTRING(640000 4690000, 660000 4700000, 680000 4710000)',
                    25830
                ),
                50
            )
        )
    );
    """,

    # ── 4. Vías Pecuarias ──
    """
    INSERT INTO vias_pecuarias (nombre, tipo_via, anchura_legal_m, longitud_m, estado_deslinde, municipio, provincia, geom)
    VALUES
    (
        'Colada de Lemos',
        'Colada',
        20.0,
        5000.0,
        'Deslindada',
        'Monforte de Lemos',
        'Lugo',
        ST_GeomFromText(
            'LINESTRING(670000 4700000, 675000 4705000, 680000 4710000)',
            25830
        )
    ),
    (
        'Cordel de Sarria',
        'Cordel',
        37.5,
        8000.0,
        'Sin deslindar',
        'Sarria',
        'Lugo',
        ST_GeomFromText(
            'LINESTRING(655000 4720000, 660000 4725000, 665000 4730000)',
            25830
        )
    );
    """,

    # ── 5. Espacios Naturales Protegidos ──
    """
    INSERT INTO espacios_naturales_protegidos (nombre, categoria, subcategoria, superficie_ha, geom)
    VALUES
    (
        'Parque Nacional de las Islas Atlánticas',
        'Parque Nacional',
        'Marítimo-terrestre',
        8480.0,
        ST_GeomFromText(
            'POLYGON((620000 4700000, 650000 4700000, 650000 4720000, 620000 4720000, 620000 4700000))',
            25830
        )
    ),
    (
        'Parque Natural de Ancares',
        'Parque Natural',
        'Terrestre',
        53500.0,
        ST_GeomFromText(
            'POLYGON((600000 4730000, 640000 4730000, 640000 4760000, 600000 4760000, 600000 4730000))',
            25830
        )
    );
    """,

    # ── 6. Masas de Agua Superficiales ──
    """
    INSERT INTO masas_agua_superficial (nombre, tipo, categoria, estado_ecologico, estado_quimico, demarcacion, geom)
    VALUES
    (
        'Río Ulla - Tramo medio',
        'Río',
        'Natural',
        'Bueno',
        'Conforme',
        'Galicia-Costa',
        ST_GeomFromText(
            'POLYGON((685000 4745000, 705000 4745000, 705000 4755000, 685000 4755000, 685000 4745000))',
            25830
        )
    ),
    (
        'Embalse de Belesar',
        'Lago',
        'Artificial',
        'Aceptable',
        'Conforme',
        'Miño-Sil',
        ST_GeomFromText(
            'POLYGON((640000 4720000, 660000 4720000, 660000 4730000, 640000 4730000, 640000 4720000))',
            25830
        )
    );
    """,

    # ── 7. Masas de Agua Subterráneas ──
    """
    INSERT INTO masas_agua_subterranea (nombre, estado_cuantitativo, estado_quimico, superficie_km2, demarcacion, geom)
    VALUES
    (
        'Acuífero de la Ría de Arousa',
        'Bueno',
        'Bueno',
        150.0,
        'Galicia-Costa',
        ST_GeomFromText(
            'POLYGON((670000 4710000, 710000 4710000, 710000 4735000, 670000 4735000, 670000 4710000))',
            25830
        )
    ),
    (
        'Acuífero de la Limia',
        'Aceptable',
        'Bueno',
        200.0,
        'Miño-Sil',
        ST_GeomFromText(
            'POLYGON((640000 4660000, 670000 4660000, 670000 4680000, 640000 4680000, 640000 4660000))',
            25830
        )
    );
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
