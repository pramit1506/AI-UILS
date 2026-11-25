// Uses the same base URL as the API client (relative "/api/v1" in dev behind the
// Vite proxy, absolute in production). The previous implementation read a
// nonexistent `VITE_API_URL` variable and fell back to a hardcoded
// "http://localhost:8000", so client-side logging was silently broken outside
// bare-metal dev setups.
import { apiClient, getCsrfToken } from '../services/api';

const MAX_LOG_CHARS = 4000;

/**
 * Safely serialise a value for logging — never throws (handles cyclic
 * structures that JSON.stringify cannot handle, e.g. React state dumps).
 */
function safeStringify(value: unknown): string {
  if (value === null || value === undefined) return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    try {
      return String(value);
    } catch {
      return '[unserializable]';
    }
  }
}

function truncate(message: string): string {
  return message.length > MAX_LOG_CHARS ? `${message.slice(0, MAX_LOG_CHARS)}…` : message;
}

async function sendLog(level: string, message: string, stackTrace?: string, url?: string, additionalInfo?: unknown) {
  // `/system-logs` requires an authenticated session (JWT cookie + CSRF
  // double-submit header). The previous raw `fetch` sent neither, so every
  // transmitter call resolved to a guaranteed 403 — flooding the browser
  // console with noise on each console.error/warn. apiClient attaches the
  // CSRF header and cookie credentials like every other API call; when there
  // is no CSRF cookie the visitor is anonymous, so remote logging is skipped
  // entirely (local console logging still happens below the patch).
  if (!getCsrfToken()) return;
  try {
    await apiClient.post('/system-logs', {
      level,
      message: truncate(message),
      source: 'frontend',
      url: url || window.location.href,
      stack_trace: stackTrace ? truncate(stackTrace) : undefined,
      additional_info: additionalInfo,
    });
  } catch (e) {
    // Silently fail if logging fails to prevent infinite loops
  }
}

let initialized = false;

export function initLogger() {
  if (initialized) return;
  initialized = true;

  const originalError = console.error;
  const originalWarn = console.warn;

  const formatArgs = (args: unknown[]) =>
    truncate(args.map(a => {
      if (a instanceof Error) return `${a.message}\n${a.stack}`;
      return typeof a === 'object' ? safeStringify(a) : String(a);
    }).join(' '));

  console.error = (...args: unknown[]) => {
    originalError(...args);
    sendLog('ERROR', formatArgs(args));
  };

  console.warn = (...args: unknown[]) => {
    originalWarn(...args);
    sendLog('WARN', formatArgs(args));
  };

  window.onerror = (message, source, lineno, colno, error) => {
    sendLog(
      'ERROR',
      truncate(typeof message === 'string' ? message : safeStringify(message)),
      error?.stack,
      source,
      { lineno, colno }
    );
    return false; // Let default handler run
  };

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    let message = 'Unhandled Promise Rejection';
    let stack = '';

    if (reason instanceof Error) {
        message = reason.message;
        stack = reason.stack || '';
    } else if (typeof reason === 'string') {
        message = reason;
    }

    sendLog(
      'ERROR',
      truncate(message),
      truncate(stack),
      window.location.href,
      { reason: safeStringify(reason) }
    );
  });
}
