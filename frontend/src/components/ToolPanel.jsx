import React from 'react';
import DrawTools from './DrawTools';
import FileUploader from './FileUploader';
import ProjectForm from './ProjectForm';
import GenerateReport from './GenerateReport';

/**
 * ToolPanel — Sidebar containing all user interaction sections:
 *   1. Drawing tools
 *   2. File upload
 *   3. Project metadata form
 *   4. Generate report button
 */
function ToolPanel({
  polygonGeoJSON,
  onPolygonSet,
  onPolygonClear,
  project,
  onProjectChange,
  onLoadLayers,
  isLoadingLayers,
  onGenerateReport,
  isGenerating,
}) {
  return (
    <div className="tool-panel">
      {/* ── Section 1: Drawing Tools ── */}
      <div className="sidebar-section">
        <h3>Dibujo del polígono</h3>
        <DrawTools
          hasPolygon={!!polygonGeoJSON}
          onDelete={onPolygonClear}
        />
      </div>

      {/* ── Section 2: File Upload ── */}
      <div className="sidebar-section">
        <h3>Subir archivo</h3>
        <FileUploader
          onPolygonLoaded={onPolygonSet}
        />
      </div>

      {/* ── Section 3: Project Info ── */}
      <div className="sidebar-section">
        <h3>Datos del proyecto</h3>
        <ProjectForm
          project={project}
          onChange={onProjectChange}
        />
      </div>

      {/* ── Section 4: Generate Report ── */}
      <div className="sidebar-section">
        <GenerateReport
          hasPolygon={!!polygonGeoJSON}
          projectName={project.name}
          onLoadLayers={onLoadLayers}
          isLoadingLayers={isLoadingLayers}
          isGenerating={isGenerating}
          onGenerate={onGenerateReport}
        />
      </div>
    </div>
  );
}

export default ToolPanel;
