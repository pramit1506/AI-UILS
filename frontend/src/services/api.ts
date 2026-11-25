/// <reference types="vite/client" />
import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const CSRF_COOKIE_NAME = 'uils_csrf';
export const CSRF_HEADER_NAME = 'x-csrf-token';

export const apiClient = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  // The backend keeps the JWT in an httpOnly cookie (uils_access) and
  // validates CSRF via double-submit; cookies must travel with every request.
  withCredentials: true,
});

// Request Interceptor: attach the CSRF double-submit header for state-changing
// requests. The JWT itself stays in the httpOnly cookie and is attached by the
// browser — it must never be read or stored by application code.
export function getCsrfToken(): string | null {
  try {
    if (typeof document === 'undefined') return null;
    const match = document.cookie.match(
      new RegExp(`(?:^|;\\s*)${CSRF_COOKIE_NAME}=([^;]*)`)
    );
    return match ? decodeURIComponent(match[1]) : null;
  } catch {
    return null;
  }
}

// Request Interceptor: attach the CSRF double-submit header for state-changing
// requests. The JWT itself stays in the httpOnly cookie and is attached by the
// browser — it must never be read or stored by application code.
apiClient.interceptors.request.use(
  (config) => {
    const method = (config.method || 'get').toLowerCase();
    if (['post', 'put', 'patch', 'delete'].includes(method) && config.headers) {
      const csrf = getCsrfToken();
      if (csrf) {
        config.headers[CSRF_HEADER_NAME] = csrf;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Format error messages & handle 401
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (!axios.isAxiosError<{ message?: string; detail?: string | { msg?: string }[] }>(error)) return Promise.reject(error);
    let errorMessage = 'An unexpected error occurred';

    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      // FastAPI HTTPException uses `detail`, custom handlers use `message`
      const detail = data?.detail;
      const validationMessage = Array.isArray(detail)
        ? detail.map(issue => issue?.msg).filter(Boolean).join(' ')
        : typeof detail === 'string' ? detail : '';
      errorMessage = data?.message || validationMessage || `Server error (${status})`;

      // If token expired or unauthorized on protected routes (excluding
      // login/register/reset-password attempts — where a 401 is an expected
      // business response, not an expired session; wiping storage there used
      // to silently de-authorize users on a wrong password)
      const url = error.config?.url ?? '';
      const isAuthAttempt =
        url.includes('/auth/login') ||
        url.includes('/auth/register') ||
        url.includes('/auth/reset-password');

      if (status === 401 && !isAuthAttempt) {
        // The persisted profile cache is stale (the JWT lives in the httpOnly
        // cookie and was never client-readable). Broadcast an event so the app
        // root can dispatch `logoutUser()` and keep Redux / UI in sync.
        try {
          localStorage.removeItem('auth_user');
        } catch {
          // Ignore storage access issues
        }
        window.dispatchEvent(new CustomEvent('auth:session-expired'));
      }

    } else if (error.request) {
      errorMessage =
        'Could not reach the server. Check your connection and try again.';
    } else {
      errorMessage = error.message;
    }

    return Promise.reject(new Error(errorMessage));
  }
);
