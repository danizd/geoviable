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

// ── Colores por capa ambiental (coinciden con el mapa estático del PDF) ──
const LAYER_COLORS = {
  red_natura_2000:              '#DC2626',
  zonas_inundables:             '#60A5FA',
  dominio_publico_hidraulico:   '#1E40AF',
  vias_pecuarias:               '#92400E',
  espacios_naturales_protegidos:'#16A34A',
  masas_agua_superficial:       '#06B6D4',
  masas_agua_subterranea:       '#0891B2',
};

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

    // Expose draw control methods on map instance
    map._geomanDrawnLayerRef = drawnLayerRef;
    map._geomanEnableDraw = () => map.pm.enableDraw('Polygon');
    map._geomanDisableDraw = () => map.pm.disableDraw('Polygon');
    map._geomanRemoveCurrentLayer = () => {
      if (drawnLayerRef.current) {
        map.pm.disableDraw('Polygon');
        map.removeLayer(drawnLayerRef.current);
        drawnLayerRef.current = null;
      }
    };

    geomanInitialized.current = true;
  }, [map, onPolygonSet, onPolygonClear, onError]);

  return null;
}

// ── Custom "✏️ Dibujar" button that sits over the map ──
function DrawButton({ isDrawing, onToggle }) {
  return (
    <div
      style={{
        position: 'absolute',
        top: 10,
        left: 60,
        zIndex: 1000,
        pointerEvents: 'auto',
      }}
    >
      <button
        onClick={onToggle}
        style={{
          padding: '8px 14px',
          fontSize: 14,
          fontWeight: 600,
          border: isDrawing ? '2px solid var(--color-blue)' : '2px solid #fff',
          borderRadius: 6,
          background: isDrawing ? 'var(--color-blue)' : '#fff',
          color: isDrawing ? '#fff' : 'var(--color-gray-700)',
          cursor: 'pointer',
          boxShadow: '0 2px 6px rgba(0,0,0,0.25)',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          transition: 'all 0.15s',
        }}
        title={isDrawing ? 'Cancelar dibujo' : 'Activar modo dibujo de polígono'}
      >
        ✏️ Dibujar
      </button>
    </div>
  );
}

// ── Main MapViewer component ──
function MapViewer({ polygonGeoJSON, onPolygonSet, onPolygonClear, onError, analysisResults }) {
  const mapRef = useRef(null);
  const analysisLayersRef = useRef([]);

  // ── Capture map reference ──
  const onMapReady = useCallback((event) => {
    const map = event.target || event;
    mapRef.current = map;
  }, []);

  // ── Listen to Geoman draw state changes to sync button ──
  const [isDrawing, setIsDrawing] = useState(false);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.pm) return;

    const onDrawStart = () => setIsDrawing(true);
    const onDrawEnd = () => setIsDrawing(false);
    const onDrawCancel = () => setIsDrawing(false);

    map.on('pm:drawstart', onDrawStart);
    map.on('pm:drawend', onDrawEnd);
    map.on('pm:drawcancel', onDrawCancel);

    return () => {
      map.off('pm:drawstart', onDrawStart);
      map.off('pm:drawend', onDrawEnd);
      map.off('pm:drawcancel', onDrawCancel);
    };
  }, [polygonGeoJSON]);

  // ── Toggle drawing mode ──
  const toggleDrawing = useCallback(() => {
    const map = mapRef.current;
    if (!map || !map.pm) return;

    if (isDrawing) {
      // Disable drawing
      map.pm.disableDraw('Polygon');
      setIsDrawing(false);
    } else {
      // If a polygon already exists, don't allow new drawing
      if (map._geomanDrawnLayerRef?.current) {
        onError('Ya existe un polígono. Bórralo antes de dibujar uno nuevo.');
        return;
      }
      // Cancel any existing drawing before starting new
      map.pm.disableDraw('Polygon');
      map.pm.enableDraw('Polygon');
      setIsDrawing(true);
    }
  }, [isDrawing, onError]);

  // ── When drawing completes (polygonGeoJSON set), ensure drawing mode is off ──
  useEffect(() => {
    if (polygonGeoJSON && isDrawing) {
      const map = mapRef.current;
      if (map?.pm) map.pm.disableDraw('Polygon');
      setIsDrawing(false);
    }
  }, [polygonGeoJSON]);

  // ── Pintar/limpiar geometrías de afecciones cuando cambia analysisResults ──
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Limpiar capas anteriores
    analysisLayersRef.current.forEach((layer) => map.removeLayer(layer));
    analysisLayersRef.current = [];

    if (!analysisResults) return;

    const newLayers = [];
    (analysisResults.layers || []).forEach((layerResult) => {
      if (!layerResult.affected) return;
      const color = LAYER_COLORS[layerResult.layer_name] || '#888888';

      layerResult.features.forEach((feature) => {
        if (!feature.intersection_geometry) return;
        try {
          const geoJsonLayer = L.geoJSON(
            { type: 'Feature', geometry: feature.intersection_geometry, properties: {} },
            {
              style: {
                color,
                weight: 2,
                fillColor: color,
                fillOpacity: 0.35,
                dashArray: '4 3',
              },
            }
          );
          // Tooltip con nombre de capa y nombre del feature
          const label = feature.nombre || feature.nombre_cauce || feature.codigo_masa || '';
          geoJsonLayer.bindTooltip(
            `<strong>${layerResult.display_name}</strong>${label ? '<br/>' + label : ''}`,
            { sticky: true, opacity: 0.9 }
          );
          geoJsonLayer.addTo(map);
          newLayers.push(geoJsonLayer);
        } catch (e) {
          console.warn('Error pintando afección:', e);
        }
      });
    });

    analysisLayersRef.current = newLayers;
  }, [analysisResults]);

  // ── Cuando se elimina el polígono, limpiar también las capas de análisis ──

  // ── When polygonGeoJSON changes externally (file upload or deletion) ──
  useEffect(() => {
    if (!mapRef.current) return;

    const map = mapRef.current;

    if (polygonGeoJSON) {
      // Remove any existing Geoman layer first
      if (map._geomanDrawnLayerRef?.current) {
        map.removeLayer(map._geomanDrawnLayerRef.current);
        map._geomanDrawnLayerRef.current = null;
      }

      // Add the external polygon (from file upload)
      const geojsonLayer = L.geoJSON(polygonGeoJSON, {
        style: () => POLYGON_STYLE,
      });

      geojsonLayer.addTo(map);
      map._geomanDrawnLayerRef.current = geojsonLayer.getLayers()[0];
      map.fitBounds(geojsonLayer.getBounds(), { padding: [50, 50] });
    } else {
      // polygonGeoJSON is null → remove the drawn layer from the map
      map._geomanRemoveCurrentLayer?.();
      // Also cancel any active drawing
      if (isDrawing) {
        map.pm.disableDraw('Polygon');
        setIsDrawing(false);
      }
    }
  }, [polygonGeoJSON]);

  return (
    <div className="map-viewer-container" style={{ width: '100%', height: '100%', position: 'relative' }}>
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

      {/* Custom draw toggle button */}
      <DrawButton isDrawing={isDrawing} onToggle={toggleDrawing} />
    </div>
  );
}

export default MapViewer;
