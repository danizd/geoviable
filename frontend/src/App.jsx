import React, { useState, useCallback } from 'react';
import MapViewer from './components/MapViewer';
import ToolPanel from './components/ToolPanel';
import LayerStatus from './components/LayerStatus';
import './App.css';

/**
 * GeoViable — Main Application Component
 *
 * Layout: Header (with layer status) + Sidebar (tool panel) + Map (fullscreen).
 * Manages the shared state: the user's drawn polygon (GeoJSON) and project info.
 */
function App() {
  // ── Shared state ──
  const [polygonGeoJSON, setPolygonGeoJSON] = useState(null);
  const [project, setProject] = useState({ name: '', author: '', description: '' });
  const [isGenerating, setIsGenerating] = useState(false);
  const [toast, setToast] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ── Toast notification helper ──
  const showToast = useCallback((message, type = 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  }, []);

  // ── Handle polygon drawn/loaded from map or file ──
  const handlePolygonSet = useCallback((geojson) => {
    setPolygonGeoJSON(geojson);
    setAnalysisResults(null);
  }, []);

  const handlePolygonClear = useCallback(() => {
    setPolygonGeoJSON(null);
    setAnalysisResults(null);
  }, []);

  // ── Handle project form changes ──
  const handleProjectChange = useCallback((projectData) => {
    setProject(projectData);
  }, []);

  // ── Handle report generation ──
  const handleGenerateReport = useCallback(async () => {
    if (!polygonGeoJSON) {
      showToast('Debes dibujar o cargar un polígono antes de generar el informe.', 'warning');
      return;
    }
    if (!project.name || project.name.length < 3) {
      showToast('El nombre del proyecto es obligatorio (mínimo 3 caracteres).', 'warning');
      return;
    }

    setIsGenerating(true);
    setAnalysisResults(null);

    try {
      // Paso 1: análisis espacial → obtener geometrías de intersección para pintarlas en el mapa
      showToast('Analizando capas ambientales...', 'info');
      const analyzeRes = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(polygonGeoJSON),
      });
      if (analyzeRes.ok) {
        const analyzeData = await analyzeRes.json();
        setAnalysisResults(analyzeData.analysis);
      }

      // Paso 2: generar PDF
      showToast('Generando informe PDF...', 'info');
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
      showToast('Informe generado y descargado con éxito.', 'success');
    } catch (err) {
      showToast(err.message || 'Error al generar el informe.', 'error');
    } finally {
      setIsGenerating(false);
    }
  }, [polygonGeoJSON, project, showToast]);

  return (
    <div className="app-container">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-logo">
          <span className="logo-text">GeoViable</span>
        </div>
        <div className="header-right">
          <LayerStatus />
          <button
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen(v => !v)}
            aria-label={sidebarOpen ? 'Cerrar panel' : 'Abrir panel'}
          >
            {sidebarOpen ? '✕' : '☰'}
          </button>
        </div>
      </header>

      {/* ── Main Content ── */}
      <div className="app-body">
        {/* Sidebar */}
        <aside className={`app-sidebar${sidebarOpen ? ' open' : ''}`}>
          <ToolPanel
            polygonGeoJSON={polygonGeoJSON}
            onPolygonSet={handlePolygonSet}
            onPolygonClear={handlePolygonClear}
            project={project}
            onProjectChange={handleProjectChange}
            onGenerateReport={handleGenerateReport}
            isGenerating={isGenerating}
          />
        </aside>

        {/* Map */}
        <main className="app-map">
          <MapViewer
            polygonGeoJSON={polygonGeoJSON}
            onPolygonSet={handlePolygonSet}
            onPolygonClear={handlePolygonClear}
            onError={showToast}
            analysisResults={analysisResults}
          />
        </main>
      </div>

      {/* ── Toast Notification ── */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <span>{toast.message}</span>
          <button className="toast-close" onClick={() => setToast(null)}>×</button>
        </div>
      )}
    </div>
  );
}

export default App;
