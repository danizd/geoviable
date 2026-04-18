import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import AnalysisPage from './pages/AnalysisPage';
import ReportPage from './pages/ReportPage';
import HowToUsePage from './pages/HowToUsePage';

/**
 * GeoViable — Main Application Router Component
 */
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/analisis" element={<AnalysisPage />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/como-usar" element={<HowToUsePage />} />
      </Routes>
    </Router>
  );
}

export default App;
