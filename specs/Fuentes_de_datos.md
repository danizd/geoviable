# GeoViable — Fuentes de datos ambientales

## 1. Resumen de capas

| # | Capa | Fuente | Formato esperado | CRS original (probable) | Frecuencia MITECO |
|---|---|---|---|---|---|
| 1 | Red Natura 2000 (ZEPA + LIC/ZEC) | MITECO | Shapefile (.zip) | EPSG:4258 (ETRS89) | Anual |
| 2 | Zonas inundables SNCZI (T100, T500) | MITECO | Shapefile (.zip) | EPSG:25830 | Irregular |
| 3 | Dominio Público Hidráulico (DPH) | MITECO | Shapefile (.zip) | EPSG:25830 | Irregular |
| 4 | Vías pecuarias | CNIG | Shapefile (.zip) | EPSG:4258 (ETRS89) | Anual |
| 5 | Espacios Naturales Protegidos (ENP) | MITECO | Shapefile (.zip) | EPSG:4258 (ETRS89) | Anual |
| 6 | Masas de agua superficiales | MITECO | Shapefile (.zip) | EPSG:25830 | Por ciclo PHC (6 años) |
| 7 | Masas de agua subterráneas | MITECO | Shapefile (.zip) | EPSG:25830 | Por ciclo PHC (6 años) |

## 2. URLs de descarga

### 2.1. Red Natura 2000

| Campo | Valor |
|---|---|
| Página de descarga | https://www.miteco.gob.es/es/biodiversidad/servicios/banco-datos-naturaleza/informacion-disponible/rednatura_2000_desc.html |
| Contenido | Incluye ZEPA y LIC/ZEC como capas separadas o unificadas |
| Filtrado necesario | Filtrar por bbox de Galicia o por campo de CCAA |
| Reproyección | Sí, de EPSG:4258 a EPSG:25830 |
| Tabla destino | `red_natura_2000` |

### 2.2. Zonas inundables (SNCZI)

| Campo | Valor |
|---|---|
| Página de descarga | https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/agua/descargas_agua_snczi.html |
| Contenido | Polígonos de inundabilidad por periodo de retorno |
| Periodos a descargar | T=100 años y T=500 años |
| Filtrado necesario | Filtrar por demarcación hidrográfica (Galicia-Costa, Miño-Sil) |
| Reproyección | Verificar; posiblemente ya en EPSG:25830 |
| Tabla destino | `zonas_inundables` |

### 2.3. Dominio Público Hidráulico (DPH)

| Campo | Valor |
|---|---|
| Página de descarga | https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/agua/dph-y-zonas-asociadas.html |
| Contenido | Cauces, riberas y márgenes cartografiados |
| Filtrado necesario | Filtrar por demarcación (Galicia-Costa, Miño-Sil) |
| Reproyección | Verificar CRS del archivo |
| Tabla destino | `dominio_publico_hidraulico` |

### 2.4. Vías pecuarias

| Campo | Valor |
|---|---|
| Página de descarga | https://centrodedescargas.cnig.es/CentroDescargas/ |
| Navegación | Sección "Rutas, ocio y tiempo libre" → Vías pecuarias |
| Contenido | Trazados lineales con anchura legal |
| Filtrado necesario | Filtrar por provincias de Galicia (A Coruña, Lugo, Ourense, Pontevedra) |
| Reproyección | Sí, de EPSG:4258 a EPSG:25830 (si aplica) |
| Tabla destino | `vias_pecuarias` |
| Nota especial | Galicia tiene muy pocas vías pecuarias deslindadas. La capa puede tener pocos registros o estar vacía para muchos municipios. |

### 2.5. Espacios Naturales Protegidos (ENP)

| Campo | Valor |
|---|---|
| Página de descarga | https://www.miteco.gob.es/es/biodiversidad/servicios/banco-datos-naturaleza/informacion-disponible/enp_descargas.html |
| Contenido | Parques nacionales, naturales, reservas, monumentos naturales |
| Filtrado necesario | Filtrar por CCAA de Galicia |
| Reproyección | Sí, de EPSG:4258 a EPSG:25830 |
| Tabla destino | `espacios_naturales_protegidos` |

### 2.6. Masas de agua superficiales

| Campo | Valor |
|---|---|
| Página de descarga | https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/agua/masas-de-agua-phc-2022-2027.html |
| Contenido | Ríos, lagos, embalses, aguas costeras y de transición |
| Ciclo | PHC 2022-2027 (vigente) |
| Filtrado necesario | Filtrar por demarcación (Galicia-Costa, Miño-Sil) |
| Reproyección | Verificar; probablemente ya en EPSG:25830 |
| Tabla destino | `masas_agua_superficial` |

### 2.7. Masas de agua subterráneas

| Campo | Valor |
|---|---|
| Página de descarga | Misma URL que masas superficiales (están en la misma página, archivo separado) |
| Contenido | Acuíferos y masas subterráneas |
| Filtrado | Filtrar por demarcación (Galicia-Costa, Miño-Sil) |
| Reproyección | Verificar CRS |
| Tabla destino | `masas_agua_subterranea` |

## 3. Estrategia de descarga automatizada

### Problema

Las páginas de descarga de MITECO no ofrecen URLs directas estables a los archivos. Muchas requieren:
- Navegar un formulario web.
- Hacer clic en botones de descarga.
- A veces pasar por JavaScript dinámico.

### Solución propuesta: enfoque en dos niveles

#### Nivel 1: `requests` + `BeautifulSoup` (preferido)

```python
import requests
from bs4 import BeautifulSoup

def find_download_links(page_url: str, file_pattern: str) -> list[str]:
    """
    Busca enlaces a archivos .zip en la página de descarga.
    file_pattern: regex para filtrar el nombre del archivo (ej. r'rn2000.*\.zip')
    """
    response = requests.get(page_url, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        if re.search(file_pattern, a['href'], re.IGNORECASE):
            links.append(urljoin(page_url, a['href']))
    return links
```

#### Nivel 2: Playwright headless (fallback para páginas con JS)

Si la página carga los enlaces dinámicamente con JavaScript:

```python
from playwright.sync_api import sync_playwright

def download_with_playwright(page_url: str, download_dir: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(page_url)
        # Esperar a que se carguen los enlaces de descarga
        page.wait_for_selector('a[href$=".zip"]', timeout=15000)
        # Buscar y descargar...
```

> **Nota ARM:** Playwright soporta ARM64 (Chromium). Instalar con `playwright install chromium`.

### Descarga Manual Inicial

Para la **carga inicial** de datos (primera puesta en marcha), se recomienda **descargar manualmente** los Shapefiles y cargarlos a la BD con un script `load_initial_data.py`. Esto evita problemas de scraping durante el setup.

## 4. Flujo de procesamiento por capa

```python
# Pseudocódigo del flujo en update_layers.py

def update_layer(layer_config: LayerConfig):
    """Actualiza una capa ambiental en la BD."""

    log = LayerUpdateLog(layer_name=layer_config.table_name, status='running')

    try:
        # 1. Descargar archivo
        zip_path = download_file(layer_config.download_url, layer_config.file_pattern)
        file_hash = sha256(zip_path)

        # 2. Verificar si ha cambiado respecto a la última descarga
        if file_hash == get_last_hash(layer_config.table_name):
            log.status = 'skipped'  # No hay cambios
            return

        # 3. Leer Shapefile con GeoPandas
        gdf = gpd.read_file(zip_path)

        # 4. Reproyectar si necesario
        if gdf.crs.to_epsg() != 25830:
            gdf = gdf.to_crs(epsg=25830)

        # 5. Filtrar por bbox de Galicia
        galicia_bbox = box(-9.5, 41.5, -6.5, 44.0)  # en EPSG:4326
        galicia_bbox_25830 = transform(galicia_bbox, 4326, 25830)
        gdf = gdf[gdf.intersects(galicia_bbox_25830)]

        # 6. Mapear columnas al esquema de la tabla
        gdf = map_columns(gdf, layer_config.column_mapping)

        # 7. Cargar en BD (transacción atómica)
        with db.begin() as tx:
            tx.execute(f"TRUNCATE TABLE {layer_config.table_name}")
            gdf.to_postgis(layer_config.table_name, tx, if_exists='append')

        # 8. VACUUM ANALYZE
        db.execute(f"VACUUM ANALYZE {layer_config.table_name}")

        log.status = 'success'
        log.records_loaded = len(gdf)
        log.file_hash = file_hash

    except Exception as e:
        log.status = 'failed'
        log.error_message = str(e)
        # Los datos anteriores permanecen intactos (ROLLBACK implícito)

    finally:
        log.finished_at = datetime.utcnow()
        save_log(log)
```

## 5. Demarcaciones hidrográficas de Galicia

Para filtrar capas de agua por demarcación:

| Demarcación | Ámbito en Galicia |
|---|---|
| **Galicia-Costa** | Cuencas vertientes al Atlántico dentro de Galicia (la mayoría del territorio) |
| **Miño-Sil** | Cuenca del río Miño y sus afluentes (parte este de Galicia) |
| Cantábrico Occidental | Pequeña zona en el norte de Lugo |
| Duero | Pequeña zona en el sureste de Ourense |

> Para el MVP, descargar al menos **Galicia-Costa** y **Miño-Sil**. Las demarcaciones Cantábrico y Duero afectan zonas marginales y pueden añadirse posteriormente.
