import React, { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import MapViewer from '../components/MapViewer';
import ToolPanel from '../components/ToolPanel';
import LayerStatus from '../components/LayerStatus';
import '../App.css';

/**
 * GeoViable — Analysis Page Component
 *
 * Layout: Header (with layer status) + Sidebar (tool panel) + Map (fullscreen).
 * Manages the shared state: the user's drawn polygon (GeoJSON) and project info.
 */
function AnalysisPage() {
  const navigate = useNavigate();
  // ── Shared state ──
  const [polygonGeoJSON, setPolygonGeoJSON] = useState(null);
  const [project, setProject] = useState({ name: '', author: '', description: '' });
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoadingLayers, setIsLoadingLayers] = useState(false);
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

  // ── Execute spatial analysis and paint affected layers on the map ──
  const runSpatialAnalysis = useCallback(async () => {
    if (!polygonGeoJSON) {
      showToast('Debes dibujar o cargar un polígono antes de cargar capas.', 'warning');
      return null;
    }

    const analyzeRes = await fetch('/api/v1/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(polygonGeoJSON),
    });

    if (!analyzeRes.ok) {
      const errData = await analyzeRes.json().catch(() => null);
      throw new Error(errData?.error?.message || 'No se pudo analizar el polígono.');
    }

    const analyzeData = await analyzeRes.json();
    setAnalysisResults(analyzeData.analysis);
    return analyzeData.analysis;
  }, [polygonGeoJSON, showToast]);

  // ── Handle layer load over current polygon ──
  const handleLoadLayers = useCallback(async () => {
    if (!polygonGeoJSON) {
      showToast('Debes dibujar o cargar un polígono antes de cargar capas.', 'warning');
      return;
    }

    setIsLoadingLayers(true);
    setAnalysisResults(null);

    try {
      showToast('Analizando capas ambientales...', 'info');
      await runSpatialAnalysis();
      showToast('Capas cargadas correctamente sobre el polígono.', 'success');
    } catch (err) {
      showToast(err.message || 'Error al cargar capas.', 'error');
    } finally {
      setIsLoadingLayers(false);
    }
  }, [polygonGeoJSON, runSpatialAnalysis, showToast]);

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

    try {
      // Paso 1: usar el análisis ya cargado o ejecutarlo si aún no existe
      showToast('Preparando análisis para el informe...', 'info');
      const analysis = analysisResults || (await runSpatialAnalysis());

      // Paso 2: navegar a la página de informe
      showToast('Redirigiendo al informe...', 'info');
      navigate('/report', { state: { polygonGeoJSON, project, analysisResults: analysis } });
    } catch (err) {
      showToast(err.message || 'Error al generar el informe.', 'error');
    } finally {
      setIsGenerating(false);
    }
  }, [analysisResults, navigate, polygonGeoJSON, project, runSpatialAnalysis, showToast]);

  return (
    <div className="app-container">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-logo">
          <span className="logo-text">GeoViable</span>
        </div>
        <nav className="header-nav">
          <Link to="/" className="nav-link">Inicio</Link>
          <Link to="/como-usar" className="nav-link">¿Cómo usar?</Link>
        </nav>
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
            onLoadLayers={handleLoadLayers}
            isLoadingLayers={isLoadingLayers}
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

export default AnalysisPage;