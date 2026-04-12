import React from 'react';
import ReactDOM from 'react-dom/client';

// ── CRITICAL: Leaflet must be imported FIRST so it's the single instance ──
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
window.L = L;

// ── Geoman attaches pm to L via L.Map.addInitHook ──
import '@geoman-io/leaflet-geoman-free';
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css';

console.log('✅ After imports — L.pm:', !!L.pm);

import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
