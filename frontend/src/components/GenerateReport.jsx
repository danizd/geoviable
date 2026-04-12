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
function GenerateReport({ hasPolygon, projectName, isGenerating, onGenerate }) {
  const isDisabled = !hasPolygon || !projectName || projectName.length < 3 || isGenerating;

  // Determine tooltip message
  let tooltip = '';
  if (!hasPolygon) {
    tooltip = 'Dibuja un polígono o sube un archivo para continuar.';
  } else if (!projectName || projectName.length < 3) {
    tooltip = 'Introduce un nombre para el proyecto (mínimo 3 caracteres).';
  }

  return (
    <div className="generate-report">
      <button
        className="generate-btn"
        disabled={isDisabled}
        onClick={onGenerate}
        title={tooltip}
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
