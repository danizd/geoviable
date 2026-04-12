import React, { useState, useCallback, useRef } from 'react';
import { parseGeoJSONFile, parseKMLFile, parseKMZFile, parseShapefileZip, parseDXFFile } from '../services/fileParser';
import { validateGeoJSONGeometry } from '../utils/validation';

/**
 * FileUploader — Drag & drop zone for uploading spatial files.
 *
 * Supported formats: .geojson, .kml, .kmz, .zip (Shapefile), .dxf
 * Max size: 5 MB
 *
 * Parses files locally, validates the resulting polygon,
 * and passes the GeoJSON Feature to the parent.
 */
const MAX_FILE_SIZE_MB = 5;

const FORMAT_HANDLERS = {
  '.geojson': parseGeoJSONFile,
  '.json': parseGeoJSONFile,
  '.kml': parseKMLFile,
  '.kmz': parseKMZFile,
  '.zip': parseShapefileZip,
  '.dxf': parseDXFFile,
};

function FileUploader({ onPolygonLoaded }) {
  const [dragging, setDragging] = useState(false);
  const [detectedFormat, setDetectedFormat] = useState(null);
  const [fileName, setFileName] = useState(null);
  const fileInputRef = useRef(null);

  // ── Handle file drop ──
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);

    const file = e.dataTransfer.files[0];
    if (!file) return;

    processFile(file, onPolygonLoaded);
  }, [onPolygonLoaded]);

  // ── Handle file input change ──
  const handleFileSelect = useCallback((e) => {
    const file = e.target.files[0];
    if (!file) return;

    processFile(file, onPolygonLoaded);
  }, [onPolygonLoaded]);

  // ── Detect format from extension ──
  const detectFormat = (filename) => {
    const ext = '.' + filename.split('.').pop().toLowerCase();
    return FORMAT_HANDLERS[ext] ? ext : null;
  };

  // ── Process a single file ──
  const processFile = async (file, onPolygonLoaded) => {
    // Check file size
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > MAX_FILE_SIZE_MB) {
      alert(`El archivo es demasiado grande (${sizeMB.toFixed(1)} MB). Máximo ${MAX_FILE_SIZE_MB} MB.`);
      return;
    }

    const ext = detectFormat(file.name);
    if (!ext) {
      alert(
        'Formato de archivo no soportado. Usa GeoJSON, KML, KMZ, SHP (.zip) o DXF.'
      );
      return;
    }

    setDetectedFormat(ext);
    setFileName(file.name);

    try {
      const handler = FORMAT_HANDLERS[ext];
      const geojson = await handler(file);

      // Validate the result
      const validation = validateGeoJSONGeometry(geojson);
      if (!validation.valid) {
        alert(validation.message);
        return;
      }

      onPolygonLoaded(geojson);
    } catch (err) {
      console.error('File parse error:', err);
      alert(`Error al procesar el archivo: ${err.message || 'Formato no reconocido'}`);
    }
  };

  // ── Drag events ──
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
  };

  return (
    <div className="file-uploader">
      <div
        className={`file-drop-zone ${dragging ? 'dragover' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        <p style={{ margin: 0 }}>
          Arrastra un archivo aquí o{' '}
          <strong style={{ color: '#2563EB' }}>haz clic para seleccionar</strong>
        </p>
        <p style={{ margin: '4px 0 0', fontSize: 11, color: '#9ca3af' }}>
          .geojson · .kml · .kmz · .zip (SHP) · .dxf — máx. {MAX_FILE_SIZE_MB} MB
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".geojson,.json,.kml,.kmz,.zip,.dxf"
          onChange={handleFileSelect}
        />
      </div>

      {detectedFormat && fileName && (
        <div style={{ marginTop: 8, textAlign: 'center' }}>
          <span className="file-format-badge">{detectedFormat.toUpperCase()}</span>
          <p style={{ fontSize: 11, color: '#6b7280', margin: '4px 0 0' }}>
            {fileName}
          </p>
        </div>
      )}
    </div>
  );
}

export default FileUploader;
