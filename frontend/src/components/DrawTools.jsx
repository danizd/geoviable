import React from 'react';

/**
 * DrawTools — Minimal info panel about drawing tools.
 *
 * Actual drawing is handled by Leaflet-Geoman in MapViewer.
 * This component provides informational context and a delete shortcut.
 */
function DrawTools({ hasPolygon, onDelete }) {
  return (
    <div className="draw-tools">
      <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
        Usa el botón <strong>"✏️ Dibujar"</strong> sobre el mapa para dibujar un polígono.
        También puedes editar o borrar el polígono existente.
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
