import React, { useEffect, useState } from 'react';
import { logService, LogRecord } from '../../services/logService';
import './LogsDashboard.css';

const SCHEMA_ICONS: Record<string, string> = {
  Invoice: '🧾',
  Resume: '📄',
  Contract: '📋',
  'Medical Record': '🏥',
  'Medical Intake Form': '🩺',
  Receipt: '🧾',
  Complaint: '⚠️',
  'Legal Document': '⚖️',
  Report: '📊',
  Form: '📝',
  'General Document': '📁',
};

function getSchemaIcon(schemaName?: string): string {
  if (!schemaName) return '📋';
  for (const [key, icon] of Object.entries(SCHEMA_ICONS)) {
    if (schemaName.toLowerCase().includes(key.toLowerCase())) return icon;
  }
  return '📋';
}

function formatFieldLabel(key: string): string {
  return key
    .replace(/^_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function formatFieldValue(value: any): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '—';
    return value.join(', ');
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

const LogCard: React.FC<{ log: LogRecord }> = ({ log }) => {
  const [expanded, setExpanded] = useState(false);
  const icon = getSchemaIcon(log.schema_name);
  const date = new Date(log.created_at).toLocaleDateString(undefined, { 
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
  });
  
  const fieldKeys = Object.keys(log.data || {}).filter(k => !k.startsWith('_'));
  const previewKeys = fieldKeys.slice(0, 3);
  const hasMore = fieldKeys.length > 3;

  return (
    <div className={`log-card ${expanded ? 'expanded' : ''}`} onClick={() => setExpanded(!expanded)}>
      <div className="log-card-header">
        <div className="log-card-title-group">
          <span className="log-card-icon">{icon}</span>
          <div className="log-card-titles">
            <h3>{log.schema_name || 'Unknown Schema'}</h3>
            <span className="log-card-domain">{log.domain || 'General'}</span>
          </div>
        </div>
        <div className="log-card-meta">
          <span className="log-card-ref">#{log.log_reference}</span>
          <span className="log-card-date">{date}</span>
        </div>
      </div>
      
      <div className="log-card-body">
        {expanded ? (
          <div className="log-fields-full">
            {fieldKeys.map(key => (
              <div key={key} className="log-field-item">
                <span className="log-field-label">{formatFieldLabel(key)}</span>
                <span className="log-field-value">{formatFieldValue(log.data[key])}</span>
              </div>
            ))}
            {fieldKeys.length === 0 && <div className="log-no-fields">No extracted fields</div>}
          </div>
        ) : (
          <div className="log-fields-preview">
            {previewKeys.map(key => (
              <div key={key} className="preview-pill">
                <strong>{formatFieldLabel(key)}:</strong> {formatFieldValue(log.data[key])}
              </div>
            ))}
            {hasMore && <div className="preview-pill more">+{fieldKeys.length - 3} more</div>}
            {fieldKeys.length === 0 && <div className="preview-pill empty">Empty record</div>}
          </div>
        )}
      </div>
      
      {expanded && (
        <div className="log-card-footer">
          Click to collapse
        </div>
      )}
    </div>
  );
};

export const LogsDashboard: React.FC = () => {
  const [logs, setLogs] = useState<LogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await logService.getLogs();
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="logs-dashboard">
      <div className="dashboard-header">
        <h2>Universal Logs Database</h2>
        <p>View all your heterogeneous stored records.</p>
        <button className="refresh-btn" onClick={fetchLogs} disabled={loading}>
          {loading ? '↻ Loading...' : '↻ Refresh'}
        </button>
      </div>

      <div className="dashboard-content">
        {error && <div className="dashboard-error">{error}</div>}
        
        {!loading && !error && logs.length === 0 && (
          <div className="dashboard-empty">
            <span className="dashboard-empty-icon">🗄️</span>
            <h3>No logs found</h3>
            <p>Go to the AI Capture tab and save your first log.</p>
          </div>
        )}
        
        <div className="logs-grid">
          {logs.map(log => (
            <LogCard key={log.id} log={log} />
          ))}
        </div>
      </div>
    </div>
  );
};
