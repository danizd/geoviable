/**
 * GeoViable — Client-side Validation Utilities
 *
 * Validates GeoJSON geometries against MVP constraints before
 * sending them to the backend. Uses @turf/turf for calculations.
 */

import * as turf from '@turf/turf';

// ── Constants ──
const GALICIA_BBOX = [-9.5, 41.5, -6.5, 44.0]; // [minLon, minLat, maxLon, maxLat]
const MAX_AREA_KM2 = 100;
const MAX_VERTICES = 10000;

/**
 * Validate a GeoJSON Feature's geometry against all MVP constraints.
 *
 * @param {Object} geojson - GeoJSON Feature or FeatureCollection
 * @returns {{ valid: boolean, message?: string, code?: string }}
 */
export function validateGeoJSONGeometry(geojson) {
  if (!geojson || typeof geojson !== 'object') {
    return {
      valid: false,
      message: 'El GeoJSON debe ser un objeto válido.',
      code: 'INVALID_GEOJSON',
    };
  }

  // ── Handle FeatureCollection ──
  let feature = geojson;
  if (geojson.type === 'FeatureCollection') {
    const features = geojson.features || [];
    if (features.length !== 1) {
      return {
        valid: false,
        message: `Solo se permite un polígono por análisis. El archivo contiene ${features.length} elementos.`,
        code: 'MULTIPLE_FEATURES',
      };
    }
    feature = features[0];
  }

  if (feature.type !== 'Feature') {
    return {
      valid: false,
      message: "El GeoJSON debe ser de tipo 'Feature' o 'FeatureCollection'.",
      code: 'INVALID_GEOJSON',
    };
  }

  const geometry = feature.geometry;
  if (!geometry) {
    return {
      valid: false,
      message: 'El Feature no contiene una geometría.',
      code: 'INVALID_GEOJSON',
    };
  }

  // ── Check geometry type ──
  if (geometry.type !== 'Polygon' && geometry.type !== 'MultiPolygon') {
    return {
      valid: false,
      message: `Tipo de geometría no soportado: '${geometry.type}'. Solo se aceptan 'Polygon' o 'MultiPolygon'.`,
      code: 'INVALID_GEOMETRY_TYPE',
    };
  }

  // ── Check bounding box (Galicia) ──
  try {
    const bbox = turf.bbox(feature);
    const [minLon, minLat, maxLon, maxLat] = bbox;

    if (
      minLon < GALICIA_BBOX[0] - 0.5 ||
      minLat < GALICIA_BBOX[1] - 0.5 ||
      maxLon > GALICIA_BBOX[2] + 0.5 ||
      maxLat > GALICIA_BBOX[3] + 0.5
    ) {
      return {
        valid: false,
        message: `El polígono se encuentra fuera de los límites de Galicia. Bbox esperado: lon [${GALICIA_BBOX[0]}, ${GALICIA_BBOX[2]}], lat [${GALICIA_BBOX[1]}, ${GALICIA_BBOX[3]}].`,
        code: 'OUT_OF_BOUNDS',
      };
    }
  } catch (err) {
    return {
      valid: false,
      message: 'No se pudo calcular el bounding box del polígono.',
      code: 'INVALID_GEOMETRY',
    };
  }

  // ── Check vertex count ──
  try {
    const coordCount = turf.coordAll(feature).length;
    if (coordCount > MAX_VERTICES) {
      return {
        valid: false,
        message: `El polígono tiene demasiados vértices. Máximo permitido: ${MAX_VERTICES}. Recibidos: ${coordCount}.`,
        code: 'TOO_MANY_VERTICES',
      };
    }
  } catch (err) {
    return {
      valid: false,
      message: 'No se pudo contar los vértices del polígono.',
      code: 'INVALID_GEOMETRY',
    };
  }

  // ── Check area ──
  try {
    const areaM2 = turf.area(feature);
    const areaKm2 = areaM2 / 1_000_000;

    if (areaKm2 > MAX_AREA_KM2) {
      return {
        valid: false,
        message: `El polígono excede el área máxima permitida (${MAX_AREA_KM2} km²). Área recibida: ${areaKm2.toFixed(1)} km².`,
        code: 'AREA_TOO_LARGE',
      };
    }
  } catch (err) {
    return {
      valid: false,
      message: 'No se pudo calcular el área del polígono.',
      code: 'INVALID_GEOMETRY',
    };
  }

  return { valid: true };
}

/**
 * Calculate the area of a GeoJSON Feature in hectares.
 *
 * @param {Object} feature
 * @returns {number} Area in hectares
 */
export function calculateAreaHa(feature) {
  const areaM2 = turf.area(feature);
  return areaM2 / 10_000;
}

/**
 * Calculate the centroid of a GeoJSON Feature as [lon, lat].
 *
 * @param {Object} feature
 * @returns {[number, number]} Centroid coordinates
 */
export function calculateCentroid(feature) {
  const centroid = turf.centerOfMass(feature);
  return centroid.geometry.coordinates; // [lon, lat]
}
