import React, { useState, useEffect, useRef } from 'react';

/**
 * LayerStatus — Panel expandible con el estado de datos por capa ambiental.
 *
 * Fetches GET /api/v1/layers/status on mount.
 * Muestra badge resumen en el header; al hacer click despliega el detalle por capa.
 */
function LayerStatus() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const panelRef = useRef(null);

  useEffect(() => {
    fetch('/api/v1/layers/status')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setStatus(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch layer status:', err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Cerrar panel al hacer click fuera
  useEffect(() => {
    function handleClickOutside(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  if (loading) {
    return <span className="layer-status-badge">Cargando capas...</span>;
  }

  if (error) {
    return <span className="layer-status-badge layer-status-error">⚠ Error BD</span>;
  }

  const layers = status?.layers || [];
  const withData = layers.filter((l) => l.records_count > 0).length;
  const total = layers.length;
  const allReady = withData === total;
  const noneReady = withData === 0;

  return (
    <div className="layer-status-wrapper" ref={panelRef}>
      <button
        className={`layer-status-badge ${
          noneReady ? 'layer-status-error' : allReady ? 'layer-status-ok' : 'layer-status-warn'
        }`}
        onClick={() => setOpen((v) => !v)}
        title="Ver estado de capas ambientales"
      >
        {noneReady ? '⚠' : allReady ? '✅' : '⚠'}{' '}
        Capas: {withData}/{total}{' '}
        <span className="layer-status-caret">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="layer-status-panel">
          <div className="layer-status-panel-header">Estado de datos ambientales</div>
          <ul className="layer-status-list">
            {layers.map((layer) => (
              <li key={layer.name} className="layer-status-item">
                <span className={`layer-status-dot ${layer.records_count > 0 ? 'dot-ok' : 'dot-empty'}`} />
                <span className="layer-status-name">{layer.display_name}</span>
                <span className={`layer-status-count ${layer.records_count > 0 ? 'count-ok' : 'count-empty'}`}>
                  {layer.records_count > 0
                    ? layer.records_count.toLocaleString('es-ES') + ' reg.'
                    : 'Sin datos'}
                </span>
              </li>
            ))}
          </ul>
          {noneReady && (
            <div className="layer-status-panel-warning">
              ⚠ No hay datos cargados. Los informes no mostrarán afecciones.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default LayerStatus;
