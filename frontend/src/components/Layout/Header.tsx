import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Sparkles,
  Settings,
  LayoutDashboard,
  Plus,
  Database,
  LogIn,
  ChevronDown,
  User as UserIcon,
  LogOut,
  UserCheck,
  Sun,
  Moon,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { startNewRecord } from '../../redux/store';
import { toggleTheme } from '../../redux/uiSlice';
import {
  openAuthModal,
  openProfileModal,
  logoutUser,
} from '../../redux/authSlice';
import './Layout.css';

export const Header: React.FC = () => {
  const dispatch = useAppDispatch();
  const location = useLocation();
  const isCapturePage = location.pathname === '/';
  const { user, isAuthenticated } = useAppSelector((state) => state.auth);
  const theme = useAppSelector((state) => state.ui.theme);

  const handleToggleTheme = () => dispatch(toggleTheme());

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const hasContent = useAppSelector(state => Boolean(state.chat.messages.length || state.document.currentDocument || state.log.currentLog));
  const saved = useAppSelector(state => state.log.savedLogReference);
  const busy = useAppSelector(state => state.chat.loading || state.log.extractionStatus === 'extracting');
  const handleNewSession = () => {
    if (window.confirm('Discard this draft and start a new record?')) dispatch(startNewRecord());
  };


  const handleOpenLogin = () => {
    dispatch(openAuthModal('login'));
  };

  const handleOpenProfile = () => {
    setDropdownOpen(false);
    dispatch(openProfileModal());
  };

  const handleSwitchAccount = () => {
    setDropdownOpen(false);
    dispatch(openAuthModal('login'));
  };

  const handleLogout = () => {
    setDropdownOpen(false);
    dispatch(logoutUser());
    dispatch(startNewRecord());
  };

  const userInitials = user
    ? (user.full_name || user.username)
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'U';

  return (
    <header className="app-header">
      <div className="header-logo">
        <div className="header-logo-badge">
          <Database size={16} className="header-logo-icon" />
        </div>
        <div className="header-brand-wrap">
          <h1>Universal Log</h1>
        </div>
      </div>

      <nav className="header-nav">
        {/* `end` fixes the always-active "AI Capture" link — "/" matched every
            route, so it stayed highlighted on /logs and 404 pages too */}
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Sparkles size={14} className="nav-icon" />
          <span>Workspace</span>
        </NavLink>
        <NavLink to="/logs" onClick={(event) => { if (!isAuthenticated) { event.preventDefault(); handleOpenLogin(); } }} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={14} className="nav-icon" />
          <span>Saved records</span>
        </NavLink>
      </nav>

      <div className="header-right-actions">
        <NavLink to="/settings" className="theme-toggle-btn" aria-label="Settings" title="Settings"><Settings size={16}/></NavLink>
        {isCapturePage && hasContent && !saved && (
          <button
            className="new-session-btn"
            aria-label="New record"
            onClick={handleNewSession} disabled={busy}
            title="Clear the current session and start fresh"
          >
            <Plus size={14} className="new-session-icon" />
            <span>New record</span>
          </button>
        )}

        {/* Light / dark theme toggle — pastel grey default, black variant */}
        <button
          className="theme-toggle-btn"
          onClick={handleToggleTheme}
          title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        >
          {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
        </button>

        {/* User Authentication & Profile Menu */}
        {isAuthenticated && user ? (
          <div className="user-profile-container" ref={dropdownRef}>
            <button
              className={`user-profile-btn ${dropdownOpen ? 'active' : ''}`}
              onClick={() => setDropdownOpen(!dropdownOpen)}
              title="Open User Profile & Account Settings"
            >
              <div className="user-profile-avatar">{userInitials}</div>
              <div className="user-profile-info">
                <span className="user-profile-name">
                  {user.full_name || user.username}
                </span>
                <span className="user-profile-role">{user.role}</span>
              </div>
              <ChevronDown size={12} className="user-profile-chevron" />
            </button>

            {dropdownOpen && (
              <div className="user-profile-dropdown">
                <div className="dropdown-user-header">
                  <h4 className="dropdown-user-name">
                    {user.full_name || user.username}
                  </h4>
                  <p className="dropdown-user-email">@{user.username} • {user.email}</p>
                  <span className="dropdown-user-role-badge">{user.role}</span>
                </div>

                <div className="dropdown-menu-list">
                  <button className="dropdown-menu-item" onClick={handleOpenProfile}>
                    <UserIcon size={14} />
                    <span>Profile Settings</span>
                  </button>
                  <button className="dropdown-menu-item" onClick={handleSwitchAccount}>
                    <UserCheck size={14} />
                    <span>Switch Profile</span>
                  </button>
                  <button className="dropdown-menu-item logout" onClick={handleLogout}>
                    <LogOut size={14} />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            className="header-login-btn"
            onClick={handleOpenLogin}
            title="Sign in or create account to save personal logs"
          >
            <LogIn size={14} />
            <span>Sign in</span>
          </button>
        )}
      </div>
    </header>
  );
};
