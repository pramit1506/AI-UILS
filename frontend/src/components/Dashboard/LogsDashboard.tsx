import React, { useEffect, useState } from 'react';
import {
  Database,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  Calendar,
  Hash,
  Receipt,
  FileText,
  FileSignature,
  Stethoscope,
  Scale,
  BarChart3,
  FileCheck,
  Folder,
  Check,
  Inbox,
  Trash2,
  X,
  Loader2
} from 'lucide-react';
import { logService, LogRecord } from '../../services/logService';
import { useAppSelector } from '../../redux/hooks';
import './LogsDashboard.css';

function getSchemaIcon(schemaName?: string) {
  if (!schemaName) return <Folder size={16} />;
  const lower = schemaName.toLowerCase();
  if (lower.includes('invoice') || lower.includes('receipt')) return <Receipt size={16} />;
  if (lower.includes('resume')) return <FileText size={16} />;
  if (lower.includes('contract')) return <FileSignature size={16} />;
  if (lower.includes('medical') || lower.includes('doctor')) return <Stethoscope size={16} />;
  if (lower.includes('legal')) return <Scale size={16} />;
  if (lower.includes('report') || lower.includes('analytics')) return <BarChart3 size={16} />;
  if (lower.includes('complaint') || lower.includes('incident')) return <AlertTriangle size={16} />;
  if (lower.includes('form')) return <FileCheck size={16} />;
  return <Folder size={16} />;
}

function formatFieldLabel(key: string): string {
  return key
    .replace(/^_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
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

function getConfidenceLabel(confidence?: number | null): { label: string; cls: string } {
  if (confidence === undefined || confidence === null) return { label: '', cls: '' };
  if (confidence >= 0.75) return { label: 'High', cls: 'confidence-high' };
  if (confidence >= 0.45) return { label: 'Med', cls: 'confidence-med' };
  return { label: 'Low', cls: 'confidence-low' };
}

const LogCard: React.FC<{
  log: LogRecord;
  onReviewed?: (id: string) => void;
  onDelete?: (log: LogRecord) => void;
}> = ({ log, onReviewed, onDelete }) => {
  const [expanded, setExpanded] = useState(false);
  const isGenericSchema = !log.schema_name || log.schema_name === 'General Document';
  const date = new Date(log.created_at).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const fieldKeys = Object.keys(log.data || {}).filter((k) => !k.startsWith('_'));
  const previewKeys = fieldKeys.slice(0, 3);
  const hasMore = fieldKeys.length > 3;

  const { label: confLabel, cls: confCls } = getConfidenceLabel(log.overall_confidence);

  return (
    <div
      className={`log-card ${expanded ? 'expanded' : ''} ${
        log.requires_review ? 'requires-review' : ''
      }`}
      onClick={() => setExpanded(!expanded)}
      data-testid={`log-card-${log.log_reference}`}
    >
      {log.requires_review && (
        <div className="log-card-review-banner">
          <AlertTriangle size={13} />
          <span>Low Confidence — Requires Human Review</span>
        </div>
      )}
      <div className="log-card-header">
        <div className="log-card-title-group">
          <div className="log-card-icon-wrap">
            {getSchemaIcon(log.schema_name)}
          </div>
          <div className="log-card-titles">
            <h3 className={isGenericSchema ? 'log-schema-generic' : ''}>
              {log.schema_name || 'Unknown Schema'}
            </h3>
            <span className="log-card-domain">{log.domain || 'General'}</span>
          </div>
        </div>
        <div className="log-card-header-actions">
          <div className="log-card-meta">
            <span className="log-card-ref">
              <Hash size={11} />
              {log.log_reference}
            </span>
            <span className="log-card-date">
              <Calendar size={11} />
              {date}
            </span>
          </div>
          {onDelete && (
            <button
              type="button"
              className="log-card-action-btn delete-btn"
              title={`Delete ${log.log_reference}`}
              aria-label={`Delete ${log.log_reference}`}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(log);
              }}
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      <div className="log-card-metrics">
        {log.overall_confidence !== null && log.overall_confidence !== undefined && (
          <span className={`log-card-confidence ${confCls}`}>
            <span className="confidence-dot" />
            {Math.round(log.overall_confidence * 100)}% {confLabel} Confidence
          </span>
        )}
      </div>

      <div className="log-card-body">
        {expanded ? (
          <div className="log-fields-full">
            {fieldKeys.map((key) => {
              const meta = log.field_metadata?.[key];
              const fieldConf = meta?.confidence;
              const { label: fLabel, cls: fCls } = getConfidenceLabel(fieldConf);

              return (
                <div key={key} className="log-field-item">
                  <span className="log-field-label">
                    {formatFieldLabel(key)}
                    {fLabel && (
                      <span className={`log-field-conf-inline ${fCls}`}>
                        {Math.round((fieldConf || 0) * 100)}%
                      </span>
                    )}
                  </span>
                  <span className="log-field-value">{formatFieldValue(log.data[key])}</span>
                </div>
              );
            })}
            {fieldKeys.length === 0 && <div className="log-no-fields">No extracted fields</div>}
          </div>
        ) : (
          <div className="log-fields-preview">
            {previewKeys.map((key) => (
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
          <span className="log-card-collapse">Click to collapse</span>
          <div className="log-card-footer-actions">
            {onDelete && (
              <button
                type="button"
                className="log-card-btn-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(log);
                }}
              >
                <Trash2 size={12} />
                <span>Delete</span>
              </button>
            )}
            {log.requires_review && onReviewed && (
              <button
                type="button"
                className="log-card-btn-review"
                onClick={(e) => {
                  e.stopPropagation();
                  onReviewed(log.log_reference);
                }}
              >
                <Check size={12} />
                <span>Mark as Reviewed</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const LogsDashboard: React.FC = () => {
  const user = useAppSelector((state) => state.auth.user);
  const [logs, setLogs] = useState<LogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'review'>('all');
  
  // Deletion modal & state
  const [logToDelete, setLogToDelete] = useState<LogRecord | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchLogs = async (tab: 'all' | 'review') => {
    try {
      setLoading(true);
      setError(null);
      const data = await logService.getLogs(undefined, 0, 50, tab === 'review' ? true : undefined);
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(activeTab);
  }, [activeTab, user?.id]);

  const handleReviewed = async (logReference: string) => {
    try {
      await logService.markAsReviewed(logReference);
      if (activeTab === 'review') {
        setLogs((prev) => prev.filter((l) => l.log_reference !== logReference));
      } else {
        setLogs((prev) =>
          prev.map((l) =>
            l.log_reference === logReference ? { ...l, requires_review: false } : l
          )
        );
      }
    } catch (err: any) {
      alert(err.message || 'Failed to mark as reviewed');
    }
  };

  const handleRequestDelete = (log: LogRecord) => {
    setDeleteError(null);
    setLogToDelete(log);
  };

  const handleConfirmDelete = async () => {
    if (!logToDelete) return;
    try {
      setIsDeleting(true);
      setDeleteError(null);
      await logService.deleteLog(logToDelete.log_reference);
      setLogs((prev) => prev.filter((l) => l.log_reference !== logToDelete.log_reference));
      setLogToDelete(null);
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to delete log record.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    if (!isDeleting) {
      setLogToDelete(null);
      setDeleteError(null);
    }
  };

  return (
    <div className="logs-dashboard">
      <div className="dashboard-header">
        <div className="dashboard-header-title-block">
          <h2>Universal Logs Database</h2>
          <p>Structured repository of all AI-extracted and verified records.</p>
        </div>

        <div className="dashboard-header-controls">
          <div className="dashboard-tabs">
            <button
              className={`dashboard-tab ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              <Database size={13} />
              <span>All Logs</span>
            </button>
            <button
              className={`dashboard-tab review-tab ${activeTab === 'review' ? 'active' : ''}`}
              onClick={() => setActiveTab('review')}
            >
              <AlertTriangle size={13} />
              <span>Review Queue</span>
            </button>
          </div>

          <button
            className="refresh-btn"
            onClick={() => fetchLogs(activeTab)}
            disabled={loading}
          >
            <RotateCcw size={13} className={loading ? 'spin-icon' : ''} />
            <span>{loading ? 'Refreshing…' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        {error && <div className="dashboard-error">{error}</div>}

        {!loading && !error && logs.length === 0 && (
          <div className="dashboard-empty">
            <div className="dashboard-empty-icon-wrap">
              {activeTab === 'review' ? <CheckCircle2 size={32} /> : <Inbox size={32} />}
            </div>
            <h3>{activeTab === 'review' ? 'Queue is empty' : 'No records found'}</h3>
            <p>
              {activeTab === 'review'
                ? "Great job, all records have been verified!"
                : "Navigate to the AI Capture tab to process your first document."}
            </p>
          </div>
        )}

        <div className="logs-grid">
          {logs.map((log) => (
            <LogCard
              key={log.id}
              log={log}
              onReviewed={handleReviewed}
              onDelete={handleRequestDelete}
            />
          ))}
        </div>
      </div>

      {/* Confirmation Modal for Deleting Log */}
      {logToDelete && (
        <div className="delete-modal-overlay" onClick={handleCancelDelete} role="dialog" aria-modal="true">
          <div className="delete-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="delete-modal-header">
              <div className="delete-modal-icon-wrap">
                <Trash2 size={20} />
              </div>
              <div className="delete-modal-titles">
                <h3>Delete Log Record</h3>
                <p>Confirm permanent deletion of this record</p>
              </div>
              <button
                type="button"
                className="delete-modal-close"
                onClick={handleCancelDelete}
                disabled={isDeleting}
                aria-label="Close dialog"
              >
                <X size={16} />
              </button>
            </div>

            <div className="delete-modal-body">
              <p>
                Are you sure you want to permanently delete log record{' '}
                <strong className="delete-target-ref">{logToDelete.log_reference}</strong>
                {logToDelete.schema_name ? ` (${logToDelete.schema_name})` : ''}?
              </p>
              <div className="delete-modal-warning">
                <AlertTriangle size={14} />
                <span>This action is permanent and cannot be undone.</span>
              </div>
              {deleteError && (
                <div className="delete-modal-error">
                  {deleteError}
                </div>
              )}
            </div>

            <div className="delete-modal-footer">
              <button
                type="button"
                className="delete-modal-btn-cancel"
                onClick={handleCancelDelete}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="delete-modal-btn-confirm"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? (
                  <>
                    <Loader2 size={13} className="spin-icon" />
                    <span>Deleting…</span>
                  </>
                ) : (
                  <>
                    <Trash2 size={13} />
                    <span>Delete Record</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

