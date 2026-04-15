import React from 'react';

/**
 * DrawTools — Info panel and delete shortcut for polygon drawing.
 *
 * The actual draw button is rendered on the map (✏️ Dibujar).
 * This component provides contextual info and a delete shortcut.
 */
function DrawTools({ hasPolygon, onDelete }) {
  return (
    <div className="draw-tools">
      <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
        Pulsa <strong>"✏️ Dibujar"</strong> sobre el mapa para dibujar un polígono,
        o sube un archivo GeoJSON/KML.
      </p>
      {hasPolygon && (
        <button
          className="draw-btn danger"
          onClick={onDelete}
          style={{ width: '100%' }}
        >
          🗑️ Borrar polígono actual
        </button>
      )}
    </div>
  );
}

export default DrawTools;
