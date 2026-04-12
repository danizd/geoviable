import React, { useEffect, useRef, useState, useCallback } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import { validateGeoJSONGeometry } from '../utils/validation';

const L = window.L;

/**
 * MapViewer — Leaflet map centered on Galicia with drawing tools.
 *
 * Integrates react-leaflet + Leaflet-Geoman for polygon drawing/editing.
 * Communicates the drawn polygon as a GeoJSON Feature to the parent.
 */

// ── Galicia default view ──
const GALICIA_CENTER = [42.8, -8.0];
const GALICIA_ZOOM = 8;

// ── Polygon style ──
const POLYGON_STYLE = {
  color: '#2563EB',
  weight: 2.5,
  fillColor: '#2563EB',
  fillOpacity: 0.2,
};

// ── Internal component: initializes Geoman on the map ──
function GeomanController({ onPolygonSet, onPolygonClear, onError }) {
  const map = useMap();
  const drawnLayerRef = useRef(null);
  const geomanInitialized = useRef(false);

  useEffect(() => {
    if (geomanInitialized.current) return;

    if (!map.pm) {
      console.error('map.pm is undefined. L.pm:', !!L?.pm);
      onError('Leaflet-Geoman plugin not available.');
      return;
    }

    // Initialize Geoman controls — only polygon draw, edit, delete
    map.pm.addControls({
      position: 'topleft',
      drawPolygon: true,
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawCircle: false,
      drawRectangle: false,
      editMode: true,
      dragMode: false,
      cutPolygon: false,
      removalMode: true,
    });

    map.pm.setGlobalOptions({ allowEditing: true, allowRemoval: true });

    // Event: layer created
    map.on('pm:create', (e) => {
      const layer = e.layer;
      if (drawnLayerRef.current && drawnLayerRef.current !== layer) {
        map.removeLayer(drawnLayerRef.current);
      }
      drawnLayerRef.current = layer;

      const geojson = layer.toGeoJSON();
      geojson.properties = {};

      const validation = validateGeoJSONGeometry(geojson);
      if (!validation.valid) {
        onError(validation.message);
        map.removeLayer(layer);
        drawnLayerRef.current = null;
        onPolygonClear();
        return;
      }

      layer.setStyle(POLYGON_STYLE);
      onPolygonSet(geojson);
      map.fitBounds(layer.getBounds(), { padding: [50, 50] });
    });

    // Event: layer removed
    map.on('pm:remove', () => {
      drawnLayerRef.current = null;
      onPolygonClear();
    });

    // Event: layer edited
    map.on('pm:edit', (e) => {
      const layer = e.layer || e.layers?.getLayers?.()?.[0];
      if (layer) {
        const geojson = layer.toGeoJSON();
        geojson.properties = {};
        const validation = validateGeoJSONGeometry(geojson);
        if (!validation.valid) {
          onError(validation.message);
          return;
        }
        onPolygonSet(geojson);
      }
    });

    // Expose on map instance for external access
    map._geomanDrawnLayerRef = drawnLayerRef;

    geomanInitialized.current = true;
  }, [map, onPolygonSet, onPolygonClear, onError]);

  return null;
}

// ── Main MapViewer component ──
function MapViewer({ polygonGeoJSON, onPolygonSet, onPolygonClear, onError }) {
  const mapRef = useRef(null);

  // ── Capture map reference ──
  const onMapReady = useCallback((event) => {
    const map = event.target || event;
    mapRef.current = map;
  }, []);

  // ── When polygonGeoJSON changes externally (file upload), draw it ──
  useEffect(() => {
    if (!polygonGeoJSON || !mapRef.current) return;

    const drawnRef = mapRef.current._geomanDrawnLayerRef;
    if (drawnRef?.current) {
      mapRef.current.removeLayer(drawnRef.current);
    }

    const geojsonLayer = L.geoJSON(polygonGeoJSON, {
      style: () => POLYGON_STYLE,
    });

    geojsonLayer.addTo(mapRef.current);
    if (drawnRef) drawnRef.current = geojsonLayer.getLayers()[0];

    mapRef.current.fitBounds(geojsonLayer.getBounds(), { padding: [50, 50] });
  }, [polygonGeoJSON]);

  return (
    <div className="map-viewer-container" style={{ width: '100%', height: '100%' }}>
      <MapContainer
        center={GALICIA_CENTER}
        zoom={GALICIA_ZOOM}
        minZoom={6}
        maxZoom={18}
        style={{ width: '100%', height: '100%' }}
        whenReady={onMapReady}
      >
        <GeomanController
          onPolygonSet={onPolygonSet}
          onPolygonClear={onPolygonClear}
          onError={onError}
        />

        {/* ── Basemap: OpenStreetMap ── */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* ── Basemap: PNOA-IGN Satellite (optional layer) ── */}
        <TileLayer
          attribution='&copy; <a href="https://www.ign.es">PNOA-IGN</a>'
          url="https://www.ign.es/wmts/pnoa-ma?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=OI.OrthoimageCoverage&FORMAT=image/jpeg&TILEMATRIXSET=GoogleMapsCompatible&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
          opacity={0}
        />
      </MapContainer>
    </div>
  );
}

export default MapViewer;
