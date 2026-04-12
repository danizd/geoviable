/**
 * GeoViable — File Parser Service
 *
 * Handles parsing of multiple spatial file formats into a unified
 * GeoJSON Feature with a single Polygon/MultiPolygon geometry.
 *
 * Supported formats:
 *   - .geojson / .json  → native JSON.parse
 *   - .kml              → @turf/turf + DOMParser
 *   - .kmz              → JSZip (extract KML, then parse)
 *   - .zip (Shapefile)  → shpjs (lazy-loaded)
 *   - .dxf              → dxf-parser (lazy-loaded, LWPOLYLINE only)
 */

// ── Lazy imports to avoid loading heavy parsers unless needed ──

/**
 * Parse a .geojson / .json file.
 *
 * @param {File} file
 * @returns {Promise<Object>} GeoJSON Feature
 */
export function parseGeoJSONFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        resolve(normalizeToFeature(data));
      } catch (err) {
        reject(new Error('No se pudo parsear el archivo GeoJSON: JSON inválido.'));
      }
    };
    reader.onerror = () => reject(new Error('Error al leer el archivo.'));
    reader.readAsText(file);
  });
}

/**
 * Parse a .kml file using the browser's DOMParser.
 *
 * Converts KML <Polygon> and <LineString> elements to GeoJSON.
 *
 * @param {File} file
 * @returns {Promise<Object>} GeoJSON Feature
 */
export function parseKMLFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const kmlText = reader.result;
        const geojson = kmlToGeoJSON(kmlText);
        resolve(normalizeToFeature(geojson));
      } catch (err) {
        reject(new Error(`No se pudo parsear el archivo KML: ${err.message}`));
      }
    };
    reader.onerror = () => reject(new Error('Error al leer el archivo KML.'));
    reader.readAsText(file);
  });
}

/**
 * Parse a .kmz file (ZIP containing a KML file).
 *
 * Uses JSZip (loaded dynamically from CDN).
 *
 * @param {File} file
 * @returns {Promise<Object>} GeoJSON Feature
 */
export async function parseKMZFile(file) {
  // Dynamically load JSZip
  const JSZip = await loadJSZip();

  const zip = await JSZip.loadAsync(file);

  // Find the .kml file inside the ZIP
  const kmlEntry = Object.values(zip.files).find(
    (entry) => !entry.dir && entry.name.toLowerCase().endsWith('.kml')
  );

  if (!kmlEntry) {
    throw new Error('El archivo KMZ no contiene un archivo KML.');
  }

  const kmlText = await kmlEntry.async('string');
  const geojson = kmlToGeoJSON(kmlText);
  return normalizeToFeature(geojson);
}

/**
 * Parse a .zip file containing a Shapefile (.shp + .dbf + .shx + .prj).
 *
 * Uses shpjs (loaded dynamically from CDN).
 *
 * @param {File} file
 * @returns {Promise<Object>} GeoJSON Feature
 */
export async function parseShapefileZip(file) {
  const shpjs = await loadShpjs();

  const arrayBuffer = await file.arrayBuffer();
  const geojson = await shpjs(arrayBuffer);

  return normalizeToFeature(geojson);
}

/**
 * Parse a .dxf file, extracting closed LWPOLYLINE and POLYLINE entities.
 *
 * Uses dxf-parser (loaded dynamically from CDN).
 *
 * @param {File} file
 * @returns {Promise<Object>} GeoJSON Feature
 */
export async function parseDXFFile(file) {
  const DXFParser = await loadDXFParser();

  const text = await file.text();
  const parser = new DXFParser();
  const dxf = parser.parseSync(text);

  // Extract closed polylines
  const polygons = extractPolygonsFromDXF(dxf);

  if (polygons.length === 0) {
    throw new Error('El archivo DXF no contiene polilíneas cerradas (LWPOLYLINE/POLYLINE).');
  }

  if (polygons.length > 1) {
    throw new Error(
      `El archivo DXF contiene ${polygons.length} polilíneas cerradas. Solo se permite un polígono.`
    );
  }

  return {
    type: 'Feature',
    geometry: polygons[0],
    properties: {},
  };
}

// ==============================================================================
// Helper Functions
// ==============================================================================

/**
 * Normalize any GeoJSON input to a single Feature with Polygon/MultiPolygon geometry.
 *
 * @param {Object} data - Parsed GeoJSON (Feature, FeatureCollection, or raw geometry)
 * @returns {Object} Normalized GeoJSON Feature
 */
function normalizeToFeature(data) {
  if (data.type === 'Feature') {
    return data;
  }

  if (data.type === 'FeatureCollection') {
    if (data.features.length === 0) {
      throw new Error('El FeatureCollection está vacío.');
    }
    if (data.features.length > 1) {
      throw new Error(
        `El archivo contiene ${data.features.length} elementos. Solo se permite un polígono.`
      );
    }
    return data.features[0];
  }

  // Raw geometry object
  if (data.type && (data.type === 'Polygon' || data.type === 'MultiPolygon')) {
    return {
      type: 'Feature',
      geometry: data,
      properties: {},
    };
  }

  throw new Error(`Tipo de GeoJSON no reconocido: ${data.type || 'desconocido'}`);
}

/**
 * Convert KML text to GeoJSON using DOMParser.
 *
 * A simplified KML-to-GeoJSON converter focused on Polygon elements.
 *
 * @param {string} kmlText
 * @returns {Object} GeoJSON object
 */
function kmlToGeoJSON(kmlText) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(kmlText, 'text/xml');

  // Check for parse errors
  const parseError = doc.querySelector('parsererror');
  if (parseError) {
    throw new Error('El archivo KML tiene un formato XML inválido.');
  }

  const features = [];

  // Parse Placemark elements
  const placemarks = doc.getElementsByTagName('Placemark');
  for (let i = 0; i < placemarks.length; i++) {
    const placemark = placemarks[i];
    const name = placemark.getElementsByTagName('name')[0]?.textContent || '';

    // Try Polygon first
    const polygons = placemark.getElementsByTagName('Polygon');
    if (polygons.length > 0) {
      const coords = extractCoordsFromPolygon(polygons[0]);
      if (coords && coords.length > 0) {
        features.push({
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: coords,
          },
          properties: { name },
        });
      }
    }

    // Try LineString (as fallback)
    const lineStrings = placemark.getElementsByTagName('LineString');
    if (lineStrings.length > 0 && features.length === 0) {
      const coords = extractCoordsText(lineStrings[0].getElementsByTagName('coordinates')[0]);
      if (coords) {
        features.push({
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: coords,
          },
          properties: { name },
        });
      }
    }
  }

  if (features.length === 0) {
    throw new Error('El archivo KML no contiene elementos Placemark con geometrías.');
  }

  if (features.length === 1) {
    return features[0];
  }

  return {
    type: 'FeatureCollection',
    features,
  };
}

/**
 * Extract coordinates array from a KML <coordinates> element.
 *
 * @param {Element} coordEl
 * @returns {Array<Array<number>>} [[lon, lat], ...]
 */
function extractCoordsText(coordEl) {
  if (!coordEl || !coordEl.textContent) return null;

  return coordEl.textContent
    .trim()
    .split(/\s+/)
    .map((pair) => {
      const parts = pair.split(',').map(Number);
      return [parts[0], parts[1]];  // [lon, lat] — ignore altitude
    });
}

/**
 * Extract polygon coordinates from a KML <Polygon> element.
 *
 * @param {Element} polygonEl
 * @returns {Array<Array<Array<number>>>} GeoJSON Polygon coordinates
 */
function extractCoordsFromPolygon(polygonEl) {
  const outerRing = polygonEl.getElementsByTagName('outerBoundaryIs')[0];
  if (!outerRing) return null;

  const outerCoords = outerRing.getElementsByTagName('coordinates')[0];
  if (!outerCoords) return null;

  const coords = [extractCoordsText(outerCoords)];

  // Inner boundaries (holes)
  const innerRings = polygonEl.getElementsByTagName('innerBoundaryIs');
  for (let i = 0; i < innerRings.length; i++) {
    const innerCoords = innerRings[i].getElementsByTagName('coordinates')[0];
    if (innerCoords) {
      coords.push(extractCoordsText(innerCoords));
    }
  }

  return coords;
}

/**
 * Extract closed polylines from a parsed DXF object.
 *
 * @param {Object} dxf
 * @returns {Array<Object>} GeoJSON Polygon geometries
 */
function extractPolygonsFromDXF(dxf) {
  const polygons = [];
  const entities = dxf?.entities || [];

  for (const entity of entities) {
    if (entity.type !== 'LWPOLYLINE' && entity.type !== 'POLYLINE') continue;

    const vertices = entity.vertices || [];
    if (vertices.length < 3) continue;

    // Check if closed (flag or first == last)
    const isClosed = entity.shape ||
      (vertices.length > 2 &&
        vertices[0].x === vertices[vertices.length - 1].x &&
        vertices[0].y === vertices[vertices.length - 1].y);

    if (!isClosed) continue;

    const coordinates = vertices.map((v) => [v.x, v.y]);

    // Close the ring if needed
    if (
      coordinates.length > 1 &&
      (coordinates[0][0] !== coordinates[coordinates.length - 1][0] ||
       coordinates[0][1] !== coordinates[coordinates.length - 1][1])
    ) {
      coordinates.push([coordinates[0][0], coordinates[0][1]]);
    }

    polygons.push({
      type: 'Polygon',
      coordinates: [coordinates],
    });
  }

  return polygons;
}

// ==============================================================================
// Lazy-load external parsers from CDN
// ==============================================================================

/**
 * Load JSZip from CDN.
 * @returns {Promise<Object>} JSZip constructor
 */
function loadJSZip() {
  if (window.JSZip) return Promise.resolve(window.JSZip);

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/jszip@3.10.1/dist/jszip.min.js';
    script.onload = () => resolve(window.JSZip);
    script.onerror = () => reject(new Error('No se pudo cargar JSZip desde el CDN.'));
    document.head.appendChild(script);
  });
}

/**
 * Load shpjs (shapefile-to-geojson) from CDN.
 * @returns {Promise<Function>} shpjs parser function
 */
function loadShpjs() {
  if (window.shp) return Promise.resolve(window.shp);

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/shpjs@4.0.4/dist/shp.js';
    script.onload = () => resolve(window.shp);
    script.onerror = () => reject(new Error('No se pudo cargar shpjs desde el CDN.'));
    document.head.appendChild(script);
  });
}

/**
 * Load dxf-parser from CDN.
 * @returns {Promise<Object>} DXFParser constructor
 */
function loadDXFParser() {
  if (window.DXFParser) return Promise.resolve(window.DXFParser);

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/dxf-parser@1.1.3/dist/dxf-parser.min.js';
    script.onload = () => resolve(window.DXFParser);
    script.onerror = () => reject(new Error('No se pudo cargar dxf-parser desde el CDN.'));
    document.head.appendChild(script);
  });
}
