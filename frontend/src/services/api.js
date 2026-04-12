/**
 * GeoViable — API Client
 *
 * Thin wrapper around fetch for the GeoViable API endpoints.
 * Uses the dev proxy (package.json "proxy") in development,
 * and relative paths (/api/v1/...) in production.
 */

const API_BASE = '/api/v1';

/**
 * POST /analyze — Spatial analysis (JSON response)
 *
 * @param {Object} geojson - GeoJSON Feature object
 * @returns {Promise<Object>} Analysis result
 */
export async function analyzeGeoJSON(geojson) {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(geojson),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => null);
    throw new APIError(
      response.status,
      errData?.error?.code || `HTTP_${response.status}`,
      errData?.error?.message || `Error ${response.status}`
    );
  }

  return response.json();
}

/**
 * POST /report/generate — Generate PDF report
 *
 * @param {Object} geojson - GeoJSON Feature object
 * @param {Object} project - { name, author?, description? }
 * @returns {Promise<Blob>} PDF binary
 */
export async function generateReport(geojson, project) {
  const response = await fetch(`${API_BASE}/report/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ geojson, project }),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => null);
    throw new APIError(
      response.status,
      errData?.error?.code || `HTTP_${response.status}`,
      errData?.error?.message || `Error ${response.status}`
    );
  }

  return response.blob();
}

/**
 * GET /layers/status — Check layer update status
 *
 * @returns {Promise<Object>} Layer status data
 */
export async function getLayersStatus() {
  const response = await fetch(`${API_BASE}/layers/status`);

  if (!response.ok) {
    throw new APIError(
      response.status,
      `HTTP_${response.status}`,
      `Error ${response.status}`
    );
  }

  return response.json();
}

/**
 * GET /health — Health check
 *
 * @returns {Promise<Object>} Health status
 */
export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}

/**
 * Custom API Error class with machine-readable code.
 */
export class APIError extends Error {
  constructor(httpStatus, code, message) {
    super(message);
    this.name = 'APIError';
    this.httpStatus = httpStatus;
    this.code = code;
  }
}
