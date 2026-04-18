import React, { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';

function ReportPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);
  const [toast, setToast] = useState(null);

  const { polygonGeoJSON, project, analysisResults } = location.state || {};

  const showToast = useCallback((message, type = 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  }, []);

  useEffect(() => {
    if (!polygonGeoJSON || !project) {
      navigate('/analisis');
    }
  }, [polygonGeoJSON, project, navigate]);

  const handleGeneratePDF = async () => {
    if (!polygonGeoJSON || !project) return;

    setIsGeneratingPDF(true);
    try {
      const reportRes = await fetch('/api/v1/report/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ geojson: polygonGeoJSON, project }),
      });

      if (!reportRes.ok) {
        const err = await reportRes.json().catch(() => null);
        throw new Error(err?.error?.message || `Error ${reportRes.status}`);
      }

      const blob = await reportRes.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `GeoViable_Informe_${project.name.replace(/[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ ]/g, '')}_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast('PDF descargado con éxito.', 'success');
    } catch (err) {
      showToast(err.message || 'Error al generar el PDF.', 'error');
    } finally {
      setIsGeneratingPDF(false);
    }
  };

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'ninguno': return '#22c55e';
      case 'bajo': return '#84cc16';
      case 'medio': return '#eab308';
      case 'alto': return '#f97316';
      case 'muy alto': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getRiskLabel = (risk) => {
    switch (risk) {
      case 'ninguno': return 'Sin riesgo';
      case 'bajo': return 'Riesgo bajo';
      case 'medio': return 'Riesgo medio';
      case 'alto': return 'Riesgo alto';
      case 'muy alto': return 'Riesgo muy alto';
      default: return 'Desconocido';
    }
  };

  if (!polygonGeoJSON || !project) {
    return null;
  }

  const { parcel, layers, summary } = analysisResults || {};

  return (
    <div className="report-page">
      <header className="report-header">
        <Link to="/" className="logo-link">
          <span className="logo-text">GeoViable</span>
        </Link>
        <nav className="header-nav">
          <Link to="/" className="nav-link">Inicio</Link>
          <Link to="/analisis" className="nav-link">Análisis</Link>
          <Link to="/como-usar" className="nav-link">¿Cómo usar?</Link>
        </nav>
        <Link to="/analisis" className="back-link">← Volver al análisis</Link>
      </header>

      <div className="report-content">
        <div className="report-title-section">
          <h1>Informe de viabilidad ambiental</h1>
          <p className="project-name">{project.name}</p>
          {project.author && <p className="project-author">Autor: {project.author}</p>}
          {project.description && <p className="project-description">{project.description}</p>}
        </div>

        <div className="report-actions">
          <button
            className="btn-primary"
            onClick={handleGeneratePDF}
            disabled={isGeneratingPDF}
          >
            {isGeneratingPDF ? 'Generando PDF...' : '📄 Descargar PDF'}
          </button>
        </div>

        {parcel && (
          <section className="report-section">
            <h2>Parcela analizada</h2>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Área</span>
                <span className="info-value">{parcel.area_ha?.toFixed(2)} ha ({parcel.area_m2?.toLocaleString()} m²)</span>
              </div>
              <div className="info-item">
                <span className="info-label">Centroide</span>
                <span className="info-value">{parcel.centroid?.[0]?.toFixed(5)}, {parcel.centroid?.[1]?.toFixed(5)}</span>
              </div>
              <div className="info-item">
                <span className="info-label">CRS</span>
                <span className="info-value">{parcel.crs_used}</span>
              </div>
            </div>
          </section>
        )}

        {summary && (
          <section className="report-section">
            <h2>Resumen</h2>
            <div className="summary-box">
              <div className="summary-item">
                <span className="summary-label">Capas analizadas</span>
                <span className="summary-value">{summary.total_layers_checked}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Capas afectadas</span>
                <span className="summary-value">{summary.layers_affected}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Riesgo global</span>
                <span 
                  className="summary-value risk-badge"
                  style={{ backgroundColor: getRiskColor(summary.overall_risk) }}
                >
                  {getRiskLabel(summary.overall_risk)}
                </span>
              </div>
            </div>
          </section>
        )}

        {layers && layers.length > 0 && (
          <section className="report-section">
            <h2>Capas ambientales</h2>
            <div className="layers-list">
              {layers.map((layer, index) => (
                <div 
                  key={index} 
                  className={`layer-card ${layer.affected ? 'affected' : 'not-affected'}`}
                >
                  <div className="layer-header">
                    <h3>{layer.layer_name}</h3>
                    <span className={`status-badge ${layer.affected ? 'affected' : 'not-affected'}`}>
                      {layer.affected ? 'Afectado' : 'Sin afección'}
                    </span>
                  </div>
                  {layer.affected && layer.features && layer.features.length > 0 && (
                    <div className="layer-features">
                      <table className="features-table">
                        <thead>
                          <tr>
                            <th>Nombre</th>
                            {layer.features[0]?.tipo && <th>Tipo</th>}
                            {layer.features[0]?.categoria && <th>Categoría</th>}
                            {layer.features[0]?.codigo && <th>Código</th>}
                            <th>Área intersección</th>
                            <th>% Solape</th>
                          </tr>
                        </thead>
                        <tbody>
                          {layer.features.map((feature, fIndex) => (
                            <tr key={fIndex}>
                              <td>{feature.nombre}</td>
                              {feature.tipo && <td>{feature.tipo}</td>}
                              {feature.categoria && <td>{feature.categoria}</td>}
                              {feature.codigo && <td>{feature.codigo}</td>}
                              <td>{feature.area_interseccion_m2?.toLocaleString()} m²</td>
                              <td>{feature.porcentaje_solape?.toFixed(2)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {analysisResults?.metadata && (
          <section className="report-section report-metadata">
            <p>Fecha de análisis: {new Date().toLocaleString('es-ES')}</p>
            <p>Datos actualizados: {new Date(analysisResults.metadata.data_updated_at).toLocaleDateString('es-ES')}</p>
            <p>Duración del análisis: {analysisResults.metadata.analysis_duration_ms} ms</p>
          </section>
        )}
      </div>

      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <span>{toast.message}</span>
          <button className="toast-close" onClick={() => setToast(null)}>×</button>
        </div>
      )}
    </div>
  );
}

export default ReportPage;