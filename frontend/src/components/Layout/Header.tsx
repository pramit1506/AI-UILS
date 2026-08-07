import React from 'react';
import { NavLink } from 'react-router-dom';
import './Layout.css';

export const Header: React.FC = () => (
  <header className="app-header">
    <div className="header-logo">
      <h1>Universal Log</h1>
      <span className="header-badge">AI-Powered Information Logger</span>
    </div>
    <nav className="header-nav">
      <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <span className="nav-icon">✨</span>
        AI Capture
      </NavLink>
      <NavLink to="/logs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <span className="nav-icon">🗄️</span>
        Dashboard
      </NavLink>
    </nav>
  </header>
);
