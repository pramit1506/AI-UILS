import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Sparkles,
  LayoutDashboard,
  Save,
  Plus,
  Database,
  LogIn,
  ChevronDown,
  User as UserIcon,
  LogOut,
  UserCheck,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { clearChat, addUserMessage, sendMessage } from '../../redux/chatSlice';
import { clearLog } from '../../redux/logSlice';
import { clearAgentState } from '../../redux/agentSlice';
import { clearDocument } from '../../redux/documentSlice';
import {
  openAuthModal,
  openProfileModal,
  logout,
} from '../../redux/authSlice';
import './Layout.css';

export const Header: React.FC = () => {
  const dispatch = useAppDispatch();
  const location = useLocation();
  const isCapturePage = location.pathname === '/';
  const currentLog = useAppSelector((state) => state.log.currentLog);
  const { user, isAuthenticated } = useAppSelector((state) => state.auth);

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

  const hasFields = Boolean(
    currentLog &&
      currentLog.fields &&
      Object.keys(currentLog.fields).filter((k) => !k.startsWith('_')).length > 0
  );

  const handleNewSession = () => {
    dispatch(clearChat());
    dispatch(clearLog());
    dispatch(clearAgentState());
    dispatch(clearDocument());
  };

  const handleSaveLog = () => {
    dispatch(addUserMessage('Save the log'));
    dispatch(sendMessage('Save the log') as any);
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
    dispatch(logout());
    dispatch(clearChat());
    dispatch(clearLog());
    dispatch(clearAgentState());
    dispatch(clearDocument());
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
          <span className="header-badge">AI Capture Studio</span>
        </div>
      </div>

      <nav className="header-nav">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Sparkles size={14} className="nav-icon" />
          <span>AI Capture</span>
        </NavLink>
        <NavLink to="/logs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={14} className="nav-icon" />
          <span>Dashboard</span>
        </NavLink>
      </nav>

      <div className="header-right-actions">
        {isCapturePage && hasFields && (
          <button
            className="header-save-btn"
            onClick={handleSaveLog}
            title="Save and commit current log to database (Ctrl + Enter)"
          >
            <Save size={14} />
            <span>Save Log</span>
          </button>
        )}

        {isCapturePage && (
          <button
            className="new-session-btn"
            onClick={handleNewSession}
            title="Clear the current session and start fresh"
          >
            <Plus size={14} className="new-session-icon" />
            <span>New Session</span>
          </button>
        )}

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
            <span>Sign In / Demo</span>
          </button>
        )}
      </div>
    </header>
  );
};
