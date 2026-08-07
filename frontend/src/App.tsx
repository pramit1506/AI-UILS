import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/Layout/AppLayout';
import { Header } from './components/Layout/Header';
import { LogsDashboard } from './components/Dashboard/LogsDashboard';

const NotFound: React.FC = () => (
  <div style={{ padding: '2rem', textAlign: 'center', marginTop: '10vh' }}>
    <h2 style={{ color: 'var(--color-primary)', fontSize: '2rem' }}>404 - Not Found</h2>
    <p style={{ color: 'var(--color-text-secondary)', marginTop: '1rem' }}>The page you are looking for does not exist.</p>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />} />
        <Route path="/logs" element={
          <div className="app-layout">
            <Header />
            <main className="app-main">
              <LogsDashboard />
            </main>
          </div>
        } />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
