import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAppSelector, useAppDispatch } from './redux/hooks';
import { AppLayout } from './components/Layout/AppLayout';
import { Header } from './components/Layout/Header';
import { SettingsPage } from './components/Layout/SettingsPage';
import { LogsDashboard } from './components/Dashboard/LogsDashboard';
import { AuthModal } from './components/Auth/AuthModal';
import { GuestSaveWall } from './components/Auth/GuestSaveWall';
import { ProfileModal } from './components/Profile/ProfileModal';

const ThemeBridge: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const theme = useAppSelector((state) => state.ui.theme);
  const { palette, searchMode } = useAppSelector(state => state.ui);
  const dispatch = useAppDispatch();

  useEffect(() => {
    document.documentElement.dataset.palette = palette;
    try {
      localStorage.setItem('uils_palette', palette);
      localStorage.setItem('uils_search_mode', searchMode);
    } catch { /* preferences still work for this session */ }
  }, [palette, searchMode]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    // Keep form controls/scrollbars matched to the active theme.
    document.documentElement.style.colorScheme = theme;
    return () => {
      delete document.documentElement.dataset.theme;
    };
  }, [theme, dispatch]);

  return <>{children}</>;
};

const NotFound: React.FC = () => (
  <div style={{ padding: '2rem', textAlign: 'center', marginTop: '10vh' }}>
    <h2 style={{ color: 'var(--color-primary)', fontSize: '2rem' }}>404 - Not Found</h2>
    <p style={{ color: 'var(--color-text-secondary)', marginTop: '1rem' }}>
      The page you are looking for does not exist.
    </p>
  </div>
);

// Route guard: the dashboard lists and deletes records owned by the signed-in
// user — an unauthenticated visitor previously hit these endpoints anonymously
// (where the backend no longer serves data) and got a wall of errors.
const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
};

function App() {
  const workspaceRevision = useAppSelector((state) => state.chat.workspaceRevision);
  return (
    <ThemeBridge>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout key={workspaceRevision} />} />
          <Route path="/settings" element={<div className="app-layout"><Header /><SettingsPage /></div>} />
          <Route
            path="/logs"
            element={
              <RequireAuth>
                <div className="app-layout">
                  <Header />
                  <main className="app-main">
                    <LogsDashboard />
                  </main>
                </div>
              </RequireAuth>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>

        {/* Global Modals */}
        <AuthModal />
        <ProfileModal />
        {/* Guest-mode surfaces (theme palette: pastel grey / powder blue / black) */}
        <GuestSaveWall />
      </BrowserRouter>
    </ThemeBridge>
  );
}

export default App;
