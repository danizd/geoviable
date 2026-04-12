import React from 'react';

/**
 * ProjectForm — Fields for project metadata (name, author, description).
 *
 * Only the name is required. Changes are debounced and passed to the parent.
 */
function ProjectForm({ project, onChange }) {
  const handleChange = (field, value) => {
    onChange({ ...project, [field]: value });
  };

  return (
    <div className="project-form">
      <label htmlFor="project-name">
        Nombre del proyecto <span style={{ color: '#DC2626' }}>*</span>
      </label>
      <input
        id="project-name"
        type="text"
        placeholder="Ej: Ampliación nave industrial — Parcela 234"
        value={project.name || ''}
        onChange={(e) => handleChange('name', e.target.value)}
        maxLength={100}
        required
      />

      <label htmlFor="project-author">Autor / responsable</label>
      <input
        id="project-author"
        type="text"
        placeholder="Ej: Estudio Técnico López"
        value={project.author || ''}
        onChange={(e) => handleChange('author', e.target.value)}
        maxLength={100}
      />

      <label htmlFor="project-description">Descripción breve</label>
      <textarea
        id="project-description"
        placeholder="Ej: Evaluación previa para licencia urbanística"
        value={project.description || ''}
        onChange={(e) => handleChange('description', e.target.value)}
        maxLength={500}
        rows={3}
      />
    </div>
  );
}

export default ProjectForm;
