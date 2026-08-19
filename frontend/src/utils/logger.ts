const LOG_ENDPOINT = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL}/api/v1/system-logs`
  : 'http://localhost:8000/api/v1/system-logs';

async function sendLog(level: string, message: string, stackTrace?: string, url?: string, additionalInfo?: any) {
  try {
    await fetch(LOG_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        level,
        message,
        source: 'frontend',
        url: url || window.location.href,
        stack_trace: stackTrace,
        additional_info: additionalInfo,
      }),
    });
  } catch (e) {
    // Silently fail if logging fails to prevent infinite loops
  }
}

export function initLogger() {
  if ((window as any)._loggerInitialized) return;
  (window as any)._loggerInitialized = true;

  const originalError = console.error;
  const originalWarn = console.warn;

  console.error = (...args: any[]) => {
    originalError(...args);
    const message = args.map(a => {
        if (a instanceof Error) return `${a.message}\n${a.stack}`;
        return typeof a === 'object' ? JSON.stringify(a) : String(a);
    }).join(' ');
    sendLog('ERROR', message);
  };

  console.warn = (...args: any[]) => {
    originalWarn(...args);
    const message = args.map(a => {
        if (a instanceof Error) return `${a.message}\n${a.stack}`;
        return typeof a === 'object' ? JSON.stringify(a) : String(a);
    }).join(' ');
    sendLog('WARN', message);
  };

  window.onerror = (message, source, lineno, colno, error) => {
    sendLog(
      'ERROR',
      typeof message === 'string' ? message : JSON.stringify(message),
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
      message,
      stack,
      window.location.href,
      { reason: String(reason) }
    );
  });
}
