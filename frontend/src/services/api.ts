/// <reference types="vite/client" />
import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach JWT Bearer Token if available
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Format error messages & handle 401
apiClient.interceptors.response.use(
  (response: any) => response,
  (error: any) => {
    let errorMessage = 'An unexpected error occurred';

    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      // FastAPI HTTPException uses `detail`, custom handlers use `message`
      errorMessage =
        data?.message ||
        data?.detail ||
        `Server error (${status})`;

      // If token expired or unauthorized on protected routes (excluding login/register attempts)
      if (status === 401 && !error.config?.url?.includes('/auth/login') && !error.config?.url?.includes('/auth/register')) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
      }
    } else if (error.request) {
      errorMessage =
        'Cannot reach the server — is the backend running on port 8000?';
    } else {
      errorMessage = error.message;
    }

    return Promise.reject(new Error(errorMessage));
  }
);
