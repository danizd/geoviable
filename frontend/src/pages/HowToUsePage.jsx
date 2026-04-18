import React from 'react';
import { Link } from 'react-router-dom';

function HowToUsePage() {
  return (
    <div className="how-to-page">
      <header className="how-to-header">
        <Link to="/" className="logo-link">
          <span className="logo-text">GeoViable</span>
        </Link>
        <nav className="nav-links">
          <Link to="/" className="nav-link">Inicio</Link>
          <Link to="/analisis" className="nav-link">Análisis</Link>
          <Link to="/report" className="nav-link">Informe</Link>
        </nav>
      </header>

      <div className="how-to-content">
        <h1>¿Cómo usar GeoViable?</h1>

        <section className="section">
          <h2>¿Qué es GeoViable?</h2>
          <p>
            GeoViable es una herramienta interna de Movilab para automatizar la evaluación de viabilidad ambiental
            de parcelas y proyectos. Permite cruzar geometrías (polígonos) con capas ambientales oficiales de Galicia
            de forma instantánea, generando un informe técnico en PDF.
          </p>
          <p>
            La herramienta está diseñada para equipos internos y no requiere registro ni autenticación.
            Está limitada a la Comunidad Autónoma de Galicia y parcelas de hasta 10.000 ha.
          </p>
        </section>

        <section className="section">
          <h2>Capas ambientales analizadas</h2>
          <ul>
            <li><strong>Red Natura 2000</strong> - Zonas de Especial Protección para las Aves (ZEPA) y Lugares de Importancia Comunitaria (LIC/ZEC)</li>
            <li><strong>Zonas inundables</strong> - Áreas con riesgo de inundación según periodos de retorno (T100 y T500 años)</li>
            <li><strong>Dominio Público Hidráulico</strong> - Cauces cartografiados y áreas de protección</li>
            <li><strong>Vías pecuarias</strong> - Red nacional de caminos para el ganado</li>
            <li><strong>Espacios Naturales Protegidos</strong> - Red autonómica y nacional de espacios protegidos</li>
            <li><strong>Masas de agua</strong> - Superficiales y subterráneas según el Plan Hidrológico de Galicia</li>
          </ul>
        </section>

        <section className="section">
          <h2>Pasos para usar la aplicación</h2>
          <ol>
            <li>
              <strong>Accede a la aplicación:</strong> Ve a la página de inicio y haz clic en "Comenzar análisis"
              para ir a la página de análisis.
            </li>
            <li>
              <strong>Dibuja o carga un polígono:</strong> Usa las herramientas de dibujo del mapa para trazar
              la geometría de tu parcela, o importa un archivo GeoJSON, KML, KMZ, SHP o DXF.
            </li>
            <li>
              <strong>Completa los datos del proyecto:</strong> Introduce un nombre obligatorio (mínimo 3 caracteres),
              y opcionalmente un autor y descripción.
            </li>
            <li>
              <strong>Genera el informe:</strong> Haz clic en "Generar informe". El sistema analizará automáticamente
              todas las capas ambientales que intersecan con tu polígono.
            </li>
            <li>
              <strong>Revisa los resultados:</strong> Serás redirigido a una página con el resumen del análisis,
              incluyendo capas afectadas, riesgos globales y detalles de cada intersección.
            </li>
            <li>
              <strong>Descarga el PDF:</strong> Desde la página de informe, haz clic en "Descargar PDF" para obtener
              el informe técnico completo.
            </li>
          </ol>
        </section>

        <section className="section">
          <h2>Requisitos y limitaciones</h2>
          <ul>
            <li><strong>Zona geográfica:</strong> Solo Galicia (España)</li>
            <li><strong>Tamaño máximo:</strong> 10.000 ha (100 km²) por parcela</li>
            <li><strong>Vértices:</strong> Máximo 10.000 vértices por polígono</li>
            <li><strong>Archivo:</strong> Tamaño máximo 5 MB</li>
            <li><strong>Polígonos:</strong> Solo se acepta un polígono por análisis (no FeatureCollections múltiples)</li>
            <li><strong>Tiempo:</strong> El análisis puede tardar hasta 30 segundos</li>
          </ul>
        </section>

        <section className="section">
          <h2>Sistemas de coordenadas</h2>
          <p>
            La aplicación maneja automáticamente la reproyección de coordenadas:
          </p>
          <ul>
            <li><strong>Entrada:</strong> WGS 84 (EPSG:4326) para datos del usuario</li>
            <li><strong>Almacenamiento:</strong> ETRS89 / UTM zona 30N (EPSG:25830) para capas oficiales</li>
            <li><strong>Reproyección:</strong> Automática usando ST_Transform en PostGIS</li>
          </ul>
        </section>

        <section className="section">
          <h2>Interpretación de resultados</h2>
          <p>
            Cada capa analizada puede tener diferentes niveles de afección:
          </p>
          <ul>
            <li><strong>Sin riesgo:</strong> No hay intersección con la capa</li>
            <li><strong>Riesgo bajo:</strong> Intersección mínima, generalmente tolerable</li>
            <li><strong>Riesgo medio:</strong> Intersección significativa, requiere evaluación</li>
            <li><strong>Riesgo alto:</strong> Intersección importante, puede requerir modificación del proyecto</li>
            <li><strong>Riesgo muy alto:</strong> Intersección crítica, proyecto no viable sin cambios mayores</li>
          </ul>
          <p>
            El <strong>riesgo global</strong> se calcula considerando todas las capas y sus pesos relativos.
          </p>
        </section>

        <section className="section">
          <h2>Soporte y contacto</h2>
          <p>
            Esta es una herramienta interna de Movilab. Para soporte técnico o preguntas sobre los resultados,
            contacta al equipo de desarrollo.
          </p>
          <p>
            Los datos ambientales se actualizan periódicamente. La fecha de última actualización se muestra
            en cada informe generado.
          </p>
        </section>
      </div>
    </div>
  );
}

export default HowToUsePage;