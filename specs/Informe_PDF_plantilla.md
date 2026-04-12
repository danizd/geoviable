# GeoViable — Plantilla del informe PDF

## 1. Formato general

| Propiedad | Valor |
|---|---|
| Tamaño papel | A4 (210 × 297 mm) |
| Orientación | Vertical (portrait) |
| Márgenes | 20 mm (superior/inferior), 15 mm (laterales) |
| Fuente principal | Inter o Roboto (Google Fonts, embebida) |
| Fuente monoespaciada | Para coordenadas y códigos: Roboto Mono |
| Motor de renderizado | WeasyPrint (HTML/CSS → PDF) |

## 2. Branding MVP

| Elemento | Detalle |
|---|---|
| Logo | Logo genérico de GeoViable (esquina superior izquierda) |
| Color primario | Azul oscuro `#1E3A5F` |
| Color secundario | Verde `#2D8C4E` |
| Color de acento | Naranja `#E67E22` (para advertencias/riesgo alto) |
| Pie de página | "Generado por GeoViable — geoviable.movilab.es — {fecha}" |
| Numeración de páginas | "Página X de Y" en pie de página |

## 3. Estructura del informe (sección por sección)

### Página 1: Portada

```
┌──────────────────────────────────────────────┐
│  [Logo GeoViable]                            │
│                                              │
│         INFORME DE VIABILIDAD                │
│            AMBIENTAL                         │
│                                              │
│  ─────────────────────────────────────────   │
│                                              │
│  Proyecto:    {project.name}                 │
│  Autor:       {project.author || "—"}        │
│  Descripción: {project.description || "—"}   │
│                                              │
│  Fecha:       {dd/mm/yyyy HH:mm}             │
│  Referencia:  GV-{YYYYMMDD}-{hash4}          │
│                                              │
│  ─────────────────────────────────────────   │
│                                              │
│  Ubicación de la parcela:                    │
│  Centroide:   {lat}°N, {lon}°W               │
│  Superficie:  {area_ha} ha ({area_m2} m²)    │
│                                              │
│  ─────────────────────────────────────────   │
│                                              │
│  AVISO: Este informe tiene carácter          │
│  orientativo y no sustituye un estudio       │
│  de impacto ambiental oficial.               │
│                                              │
└──────────────────────────────────────────────┘
```

- `{hash4}`: Últimos 4 caracteres del hash SHA-256 de la geometría. Sirve como referencia breve única.

### Página 2: Mapa de situación

```
┌──────────────────────────────────────────────┐
│  MAPA DE SITUACIÓN                           │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │                                      │    │
│  │    [Imagen mapa estático 300 DPI]    │    │
│  │                                      │    │
│  │    - Polígono del usuario (azul)     │    │
│  │    - Afecciones superpuestas         │    │
│  │      (colores diferenciados)         │    │
│  │                                      │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Leyenda:                                    │
│  ■ Parcela analizada                         │
│  ■ Red Natura 2000 (rojo)                    │
│  ■ Zonas inundables (azul claro)             │
│  ■ DPH (azul oscuro)                         │
│  ■ Vías pecuarias (marrón)                   │
│  ■ ENP (verde)                               │
│  ■ Masas de agua (cian)                      │
│                                              │
│  Fuente cartográfica: OpenStreetMap           │
│  Sistema de coordenadas: ETRS89/UTM 30N     │
└──────────────────────────────────────────────┘
```

#### Colores de las capas en el mapa

| Capa | Color | Hex |
|---|---|---|
| Parcela del usuario | Azul | `#2563EB` |
| Red Natura 2000 | Rojo | `#DC2626` |
| Zonas inundables | Azul claro | `#60A5FA` |
| DPH | Azul oscuro | `#1E40AF` |
| Vías pecuarias | Marrón | `#92400E` |
| ENP | Verde | `#16A34A` |
| Masas de agua | Cian | `#06B6D4` |

### Página 3: Resumen ejecutivo

```
┌──────────────────────────────────────────────┐
│  RESUMEN EJECUTIVO                           │
│                                              │
│  Nivel de riesgo ambiental: [ALTO]           │
│  (Badge con color según nivel)               │
│                                              │
│  Capas analizadas:        7                  │
│  Capas con afección:      2                  │
│  Capas sin afección:      5                  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ TABLA RESUMEN                          │  │
│  ├──────────────────┬──────────┬──────────┤  │
│  │ Capa             │ Afección │ Solape   │  │
│  ├──────────────────┼──────────┼──────────┤  │
│  │ Red Natura 2000  │   ✅ Sí  │  49.15%  │  │
│  │ Zonas inundables │   ❌ No  │    —     │  │
│  │ DPH              │   ❌ No  │    —     │  │
│  │ Vías pecuarias   │   ❌ No  │    —     │  │
│  │ ENP              │   ✅ Sí  │ 100.00%  │  │
│  │ Masas agua sup.  │   ❌ No  │    —     │  │
│  │ Masas agua sub.  │   ❌ No  │    —     │  │
│  └──────────────────┴──────────┴──────────┘  │
│                                              │
└──────────────────────────────────────────────┘
```

#### Niveles de riesgo — Representación visual

| Nivel | Color de fondo | Color de texto |
|---|---|---|
| Ninguno | Verde `#16A34A` | Blanco |
| Bajo | Amarillo `#EAB308` | Negro |
| Medio | Naranja `#EA580C` | Blanco |
| Alto | Rojo `#DC2626` | Blanco |
| Muy alto | Rojo oscuro `#7F1D1D` | Blanco |

### Páginas 4+: Detalle por capa afectada

Solo se generan secciones para las capas donde se detectó afección. Cada capa afectada ocupa una sección con:

```
┌──────────────────────────────────────────────┐
│  DETALLE: {Nombre de la capa}                │
│  ─────────────────────────────────────────   │
│                                              │
│  Entidad afectada: {nombre}                  │
│  Código:           {codigo}                  │
│  Tipo/Categoría:   {tipo}                    │
│                                              │
│  Superficie de intersección: {area_m2} m²    │
│  Porcentaje de solape:       {%}%            │
│                                              │
│  ─────────────────────────────────────────   │
│                                              │
│  [Espacio reservado para legislación         │
│   aplicable — a implementar en futuras       │
│   versiones]                                 │
│                                              │
└──────────────────────────────────────────────┘
```

> **Nota MVP:** La sección de legislación aplicable se deja como placeholder preparado en la plantilla Jinja2. El contenido legal se añadirá en una versión posterior cuando se compile la base de datos normativa.

### Última página: Notas y disclaimers

```
┌──────────────────────────────────────────────┐
│  NOTAS Y CONDICIONES                         │
│                                              │
│  1. Este informe se genera de forma          │
│     automática a partir de datos públicos    │
│     obtenidos de MITECO y CNIG.              │
│                                              │
│  2. Los datos se actualizan mensualmente.    │
│     Última actualización: {fecha}.           │
│                                              │
│  3. Este documento tiene carácter            │
│     ORIENTATIVO y NO sustituye:              │
│     - Un Estudio de Impacto Ambiental.       │
│     - La consulta previa al órgano           │
│       ambiental competente.                  │
│     - El informe de compatibilidad           │
│       urbanística del ayuntamiento.          │
│                                              │
│  4. La precisión de los resultados depende   │
│     de la calidad de los datos geográficos   │
│     oficiales disponibles.                   │
│                                              │
│  ─────────────────────────────────────────   │
│  Generado por GeoViable v1.0                 │
│  geoviable.movilab.es                        │
│  {fecha y hora de generación}                │
└──────────────────────────────────────────────┘
```

## 4. Implementación técnica

### Plantilla Jinja2

La plantilla reside en `backend/app/templates/report/` y consta de:

| Archivo | Propósito |
|---|---|
| `base.html` | Layout general: header, footer, paginación |
| `cover.html` | Portada (incluida en base.html) |
| `map.html` | Sección del mapa (la imagen se inyecta como data URI base64) |
| `summary.html` | Resumen ejecutivo + tabla resumen |
| `detail.html` | Bloque reutilizable para cada capa afectada |
| `disclaimer.html` | Notas y disclaimers finales |
| `styles.css` | Estilos CSS compatibles con WeasyPrint |

### Inyección de la imagen del mapa

La imagen generada por `contextily + matplotlib` se convierte a base64 y se inyecta en el HTML como:

```html
<img src="data:image/png;base64,{{ map_image_base64 }}" alt="Mapa de situación" />
```

Esto evita dependencias de archivos externos y garantiza que el PDF sea autocontenido.

### CSS para WeasyPrint

WeasyPrint soporta un subconjunto de CSS. Consideraciones:

- Usar `@page` para definir márgenes, tamaño de papel y headers/footers.
- `page-break-before: always` para separar secciones grandes.
- No usar `flexbox` complejo ni `grid` — preferir `float` y `table`.
- Embeber fuentes como archivos TTF/WOFF en el contenedor Docker.
