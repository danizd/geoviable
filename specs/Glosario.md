# GeoViable — Glosario de términos

## Términos geoespaciales

| Término | Definición |
|---|---|
| **CRS** | Coordinate Reference System. Sistema de referencia de coordenadas que define cómo las coordenadas numéricas se relacionan con ubicaciones en la Tierra. |
| **EPSG** | Código numérico del European Petroleum Survey Group que identifica un CRS específico. |
| **EPSG:4326** | WGS 84. Sistema global de latitud/longitud usado por GPS y la mayoría de aplicaciones web. Unidades en grados. |
| **EPSG:25830** | ETRS89 / UTM zona 30N. Sistema proyectado oficial de España peninsular. Unidades en metros. Usado para almacenamiento en la BD. |
| **EPSG:3857** | Web Mercator. Proyección usada por los tiles de mapas web (OSM, Google Maps). |
| **GeoJSON** | Formato estándar (RFC 7946) para representar geometrías geográficas en JSON. Usa coordenadas en EPSG:4326. |
| **PostGIS** | Extensión de PostgreSQL que añade soporte para tipos de datos geométricos, índices espaciales y funciones de análisis espacial. |
| **ST_Intersects** | Función PostGIS que determina si dos geometrías comparten algún punto en común. |
| **ST_Transform** | Función PostGIS que reproyecta una geometría de un CRS a otro. |
| **ST_Area** | Función PostGIS que calcula el área de una geometría (en unidades del CRS, típicamente m²). |
| **ST_Intersection** | Función PostGIS que devuelve la geometría resultante de la intersección de dos geometrías. |
| **GIST** | Generalized Search Tree. Tipo de índice de PostgreSQL usado para indexar columnas de geometría y acelerar consultas espaciales. |
| **Shapefile** | Formato de datos geoespaciales de ESRI. Compuesto por varios archivos (.shp, .dbf, .shx, .prj). Se distribuye típicamente en .zip. |
| **bbox** | Bounding Box. Rectángulo que envuelve una geometría, definido por [min_lon, min_lat, max_lon, max_lat]. |
| **WFS** | Web Feature Service. Servicio web estándar OGC para acceder a datos geoespaciales vectoriales. |
| **WMS** | Web Map Service. Servicio web estándar OGC que devuelve imágenes de mapas renderizados. |

## Términos ambientales / legales

| Término | Definición |
|---|---|
| **Red Natura 2000** | Red ecológica europea de áreas de conservación de la biodiversidad. Compuesta por ZEC/LIC y ZEPA. |
| **ZEPA** | Zona de Especial Protección para las Aves. Espacio de Red Natura 2000 designado para la conservación de aves. |
| **LIC** | Lugar de Importancia Comunitaria. Espacio propuesto para Red Natura 2000 por su biodiversidad. |
| **ZEC** | Zona Especial de Conservación. Un LIC que ha sido aprobado formalmente con medidas de gestión. |
| **ENP** | Espacio Natural Protegido. Área con protección legal específica (parques, reservas, monumentos naturales). |
| **SNCZI** | Sistema Nacional de Cartografía de Zonas Inundables. Cartografía oficial de riesgo de inundación en España. |
| **DPH** | Dominio Público Hidráulico. Bienes del Estado que incluyen cauces, riberas y márgenes de ríos. |
| **Periodo de retorno (T)** | Intervalo estadístico medio en años entre inundaciones de una determinada magnitud. T100 = una vez cada 100 años. |
| **PHC** | Plan Hidrológico de Cuenca. Plan de gestión del agua por demarcación hidrográfica, con ciclos de 6 años. |
| **Demarcación hidrográfica** | Unidad territorial de gestión de aguas. Galicia pertenece principalmente a Galicia-Costa y Miño-Sil. |
| **Vía pecuaria** | Camino tradicional usado para el tránsito de ganado. Tiene protección legal y anchura oficial. |
| **PNOA** | Plan Nacional de Ortofotografía Aérea. Proporciona imágenes aéreas de alta resolución de España. |
| **IGN** | Instituto Geográfico Nacional de España. |

## Términos de instituciones

| Término | Definición |
|---|---|
| **MITECO** | Ministerio para la Transición Ecológica y el Reto Demográfico. Ministerio del Gobierno de España que gestiona las capas ambientales nacionales. |
| **CNIG** | Centro Nacional de Información Geográfica. Organismo del IGN que gestiona la descarga de datos geoespaciales oficiales. |
| **OCI** | Oracle Cloud Infrastructure. Plataforma cloud donde se despliega GeoViable (tier Always Free ARM). |

## Términos técnicos del proyecto

| Término | Definición |
|---|---|
| **Afección** | En el contexto de GeoViable: cuando el polígono del usuario intersecta (solapa) con una capa ambiental protegida. |
| **Porcentaje de solape** | `(área de intersección / área de la parcela) × 100`. Indica qué fracción de la parcela cae dentro de una zona protegida. |
| **Mapa estático** | Imagen PNG generada en el backend (no interactiva) que se incluye en el PDF. |
| **Capa** | En el contexto de GeoViable: una tabla de la base de datos que contiene geometrías oficiales de un tipo específico (ej. Red Natura 2000). |
| **Layer update** | Proceso automatizado mensual que descarga datos actualizados de MITECO/CNIG y los carga en la BD. |
