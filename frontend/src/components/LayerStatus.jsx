import React, { useState, useEffect } from 'react';

/**
 * LayerStatus — Displays the last update date of environmental data layers.
 *
 * Fetches GET /api/v1/layers/status on mount.
 * Shows a warning if data is older than 45 days.
 */
const WARNING_DAYS = 45;

function LayerStatus() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  if (loading) {
    return <span className="layer-status">Cargando estado de capas...</span>;
  }

  if (error) {
    return <span className="layer-status" style={{ color: '#DC2626' }}>⚠ Error al cargar estado</span>;
  }

  if (!status || !status.last_global_update) {
    return <span className="layer-status">Sin datos — capas no inicializadas</span>;
  }

  // Calculate age of last update
  const updateDate = new Date(status.last_global_update);
  const now = new Date();
  const ageDays = Math.floor((now - updateDate) / (1000 * 60 * 60 * 24));
  const isStale = ageDays > WARNING_DAYS;

  const formattedDate = updateDate.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });

  return (
    <span className={`layer-status ${isStale ? 'stale' : ''}`}>
      {isStale ? '⚠ ' : '✅ '}
      Datos actualizados al: {formattedDate}
      {isStale && ` (${ageDays} días — desactualizado)`}
    </span>
  );
}

export default LayerStatus;
