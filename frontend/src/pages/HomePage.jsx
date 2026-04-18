import React from 'react';
import { Link } from 'react-router-dom';

function HomePage() {
  return (
    <div className="home-page">
      <header className="home-header">
        <div className="header-logo">
          <span className="logo-text">GeoViable</span>
        </div>
        <nav className="header-nav">
          <Link to="/analisis" className="nav-link">Análisis</Link>
          <Link to="/como-usar" className="nav-link">¿Cómo usar?</Link>
        </nav>
      </header>
      <div className="hero-section">
        <div className="hero-content">
          <h1>GeoViable</h1>
          <p className="hero-subtitle">Evaluación de viabilidad ambiental de parcelas</p>
          <p className="hero-description">
            Herramienta interna para automatizar la evaluación de viabilidad ambiental de parcelas y proyectos.
            Permite cruzar geometrías (polígonos) con capas ambientales oficiales de forma instantánea,
            generando un informe técnico en PDF.
          </p>
          <div className="hero-actions">
            <Link to="/analisis" className="btn-primary">
              Comenzar análisis
            </Link>
          </div>
        </div>
      </div>

      <div className="features-section">
        <h2>¿Qué hace GeoViable?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🗺️</div>
            <h3>Análisis espacial</h3>
            <p>
              Dibuja o importa un polígono y obtén de forma instantánea todas las capas ambientales
              que intersecan con tu parcela.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📋</div>
            <h3>Capas ambientales</h3>
            <p>
              Cruce automático con Red Natura 2000, zonas inundables, dominio hidráulico,
              vías pecuarias, espacios naturales protegidos y masas de agua.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📄</div>
            <h3>Informe PDF</h3>
            <p>
              Genera un informe técnico completo con toda la información ambiental de la parcela
              analizada, listo para usar en tu documentación.
            </p>
          </div>
        </div>
      </div>

      <div className="info-section">
        <h2>Alcance</h2>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Zona geográfica</span>
            <span className="info-value">Galicia</span>
          </div>
          <div className="info-item">
            <span className="info-label">Área máxima</span>
            <span className="info-value">10.000 ha (100 km²)</span>
          </div>
          <div className="info-item">
            <span className="info-label">Formatos soportados</span>
            <span className="info-value">GeoJSON, KML, KMZ, SHP, DXF</span>
          </div>
        </div>
      </div>

      <div className="howto-section">
        <h2>¿Cómo funciona?</h2>
        <ol className="steps-list">
          <li>
            <strong>Dibuja o sube un polígono</strong> — Utiliza las herramientas de dibujo en el mapa
            o importa un archivo con la geometría de tu parcela.
          </li>
          <li>
            <strong>Completa los datos del proyecto</strong> — Añade un nombre, autor y descripción.
          </li>
          <li>
            <strong>Genera el informe</strong> — Obtén una página con el análisis completo de todas
            las capas ambientales y descarga el PDF.
          </li>
        </ol>
      </div>
    </div>
  );
}

export default HomePage;