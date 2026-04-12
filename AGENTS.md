# GeoViable — Contexto global del proyecto

## Descripción del producto

**GeoViable** es una herramienta interna (Micro-SaaS B2B) que automatiza la evaluación de viabilidad ambiental de parcelas y proyectos. Permite cruzar geometrías (polígonos) con capas ambientales oficiales de forma instantánea, generando un informe técnico en PDF.

**URL de producción:** `https://geoviable.movilab.es/`

## Alcance del MVP

| Aspecto | Decisión |
|---|---|
| Zona geográfica | Comunidad Autónoma de Galicia |
| Usuarios | Equipo interno (sin registro ni autenticación) |
| Modelo de negocio | Uso interno — sin pasarela de pagos |
| Entregable | Informe PDF generado en el servidor |
| Autenticación | API abierta (sin auth en MVP) |
| Múltiples polígonos | Se rechaza — solo se acepta un polígono por análisis |

## Fuentes de datos (capas ambientales)

| # | Capa | Fuente | Detalle |
|---|---|---|---|
| 1 | Red Natura 2000 (ZEPA + LIC/ZEC) | MITECO | Nacional, filtrar por Galicia |
| 2 | Zonas inundables (SNCZI, T100+T500) | MITECO | Periodos de retorno 100 y 500 años |
| 3 | Dominio Público Hidráulico (DPH) | MITECO | Cauces cartografiados |
| 4 | Vías pecuarias | CNIG | Base nacional, filtrar por Galicia |
| 5 | Espacios Naturales Protegidos (ENP) | MITECO | Red autonómica y nacional |
| 6 | Masas de agua superficiales y subterráneas | MITECO | PHC ciclo 2022-2027 |

> Detalle completo de URLs y estrategia de descarga: ver [Fuentes_de_datos.md](specs/Fuentes_de_datos.md).

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Infraestructura | Oracle Cloud Always Free (ARM, 24 GB RAM, 200 GB disco) |
| Orquestación | Docker Compose |
| Base de datos | PostgreSQL 15+ con PostGIS 3.4+ |
| Backend | Python 3.11 + FastAPI |
| Generación PDF | WeasyPrint (plantillas Jinja2 → HTML → PDF) |
| Mapa estático (PDF) | contextily + matplotlib + geopandas |
| Frontend | React.js + React Leaflet |
| Servidor web | Nginx (proxy inverso + archivos estáticos) |
| HTTPS | Let's Encrypt / Cloudflare (dominio `geoviable.movilab.es`) |

## Sistemas de coordenadas (CRS)

| Contexto | CRS | EPSG |
|---|---|---|
| Almacenamiento en BD (capas oficiales) | ETRS89 / UTM zona 30N | **25830** |
| Entrada del frontend (usuario) | WGS 84 (Lon/Lat) | **4326** |
| Reproyección | `ST_Transform` en cada query SQL | 4326 → 25830 |

## Límites operativos del MVP

| Parámetro | Límite |
|---|---|
| Área máxima del polígono | 10.000 ha (100 km²) |
| Vértices máximos del polígono | 10.000 |
| Tamaño máximo del archivo subido | 5 MB |
| Polígonos por solicitud | 1 (se rechaza `FeatureCollection` con >1 Feature) |
| Timeout de análisis | 30 segundos |

## Índice de especificaciones

| Documento | Contenido |
|---|---|
| [Arquitectura_y_flujos.md](specs/Arquitectura_y_flujos.md) | Infraestructura, Docker Compose, flujos de datos |
| [Especificaciones_frontend.md](specs/Especificaciones_frontend.md) | Componentes UI, librerías, estados |
| [Especificaciones_backend.md](specs/Especificaciones_backend.md) | Lógica de negocio, validaciones, análisis espacial |
| [API_reference.md](specs/API_reference.md) | Endpoints, schemas de request/response, códigos HTTP |
| [Esquema_base_datos.md](specs/Esquema_base_datos.md) | DDL completo, tablas, índices |
| [Informe_PDF_plantilla.md](specs/Informe_PDF_plantilla.md) | Estructura sección a sección del PDF |
| [Fuentes_de_datos.md](specs/Fuentes_de_datos.md) | URLs de descarga, formatos, automatización |
| [Seguridad_y_configuracion.md](specs/Seguridad_y_configuracion.md) | CORS, variables de entorno, HTTPS |
| [DevOps_y_despliegue.md](specs/DevOps_y_despliegue.md) | Docker Compose, CI/CD, backups |
| [Glosario.md](specs/Glosario.md) | Términos técnicos y de dominio |