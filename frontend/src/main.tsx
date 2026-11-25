import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { store } from './redux/store';
import App from './App';
import './index.css';
import { initLogger } from './utils/logger';
import { logoutUser, fetchCurrentUser, invalidateCachedSession } from './redux/authSlice';
import { clearChat } from './redux/chatSlice';
import { clearAgentState } from './redux/agentSlice';
import { clearDocument } from './redux/documentSlice';
import { clearLog } from './redux/logSlice';

initLogger();

// When any request receives a 401 (expired/invalid session), the stored
// profile cache becomes stale. Synchronize the whole app: reset every slice
// that could hold the previous user's data, and ask the backend to delete the
// httpOnly auth cookies.
window.addEventListener('auth:session-expired', () => {
  store.dispatch(logoutUser());
  store.dispatch(clearChat());
  store.dispatch(clearAgentState());
  store.dispatch(clearDocument());
  store.dispatch(clearLog());
});

// Session cookies are shared by tabs. A change to the cached profile signals
// that the server session may have switched; only /auth/me establishes identity.
let pendingProfileCheck: { abort: () => void } | undefined;
function validateProfile() {
  pendingProfileCheck?.abort();
  pendingProfileCheck = store.dispatch(fetchCurrentUser());
}
window.addEventListener('storage', (event) => {
  if (event.storageArea !== window.localStorage || (event.key !== 'auth_user' && event.key !== null)) return;
  const currentOwner = store.getState().auth.user?.id;
  let hintedOwner: unknown;
  try {
    hintedOwner = event.newValue ? JSON.parse(event.newValue)?.id : undefined;
  } catch {
    // A malformed profile also requires revalidation.
  }
  if (hintedOwner && hintedOwner === currentOwner) return;
  store.dispatch(invalidateCachedSession());
  validateProfile();
});

// Validate the persisted session at startup — previously the stored user was
// trusted forever (`fetchCurrentUser` was defined but never dispatched), so
// stale/tampered credentials survived full page reloads. The snapshot only
// gates whether we validate: anonymous visitors never hit a pointless 401,
// while returning users get their cookie session checked before any data shows.
if (store.getState().auth.user) {
  validateProfile();
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </React.StrictMode>
);
