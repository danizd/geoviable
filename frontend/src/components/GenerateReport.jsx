import React from 'react';

/**
 * GenerateReport — CTA button to trigger PDF report generation.
 *
 * Disabled states:
 *   - No polygon loaded
 *   - Project name missing or too short
 *
 * Processing state shows a spinner.
 */
function GenerateReport({
  hasPolygon,
  projectName,
  isLoadingLayers,
  isGenerating,
  onLoadLayers,
  onGenerate,
}) {
  const isLoadDisabled = !hasPolygon || isLoadingLayers || isGenerating;
  const isGenerateDisabled = !hasPolygon || !projectName || projectName.length < 3 || isLoadingLayers || isGenerating;

  // Determine tooltip message
  let loadTooltip = '';
  let generateTooltip = '';
  if (!hasPolygon) {
    loadTooltip = 'Dibuja un polígono o sube un archivo para continuar.';
    generateTooltip = 'Dibuja un polígono o sube un archivo para continuar.';
  } else if (!projectName || projectName.length < 3) {
    generateTooltip = 'Introduce un nombre para el proyecto (mínimo 3 caracteres).';
  }

  return (
    <div className="generate-report">
      <button
        className="load-layers-btn"
        disabled={isLoadDisabled}
        onClick={onLoadLayers}
        title={loadTooltip}
      >
        {isLoadingLayers ? (
          <>
            <span className="spinner"></span>
            Cargando capas...
          </>
        ) : (
          '🗺️ Cargar capas en el polígono'
        )}
      </button>

      <button
        className="generate-btn"
        disabled={isGenerateDisabled}
        onClick={onGenerate}
        title={generateTooltip}
      >
        {isGenerating ? (
          <>
            <span className="spinner"></span>
            Generando informe...
          </>
        ) : (
          '📄 Generar informe de viabilidad (PDF)'
        )}
      </button>
    </div>
  );
}

export default GenerateReport;
