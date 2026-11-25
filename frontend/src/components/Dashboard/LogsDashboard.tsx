import { editedValue, fieldInput } from '../../utils/fieldValue';
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
  Pencil,
  X,
  Search,
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

/** Compact, human-readable rendering for scalars/nested objects. */
function formatScalar(value: unknown): string {
  if (value === null || value === undefined || value === '') return '';
  const text = String(value);
  return text.length > 240 ? `${text.slice(0, 237)}…` : text;
}

/** Renders any JSON value as readable text — nested arrays ("Line Items")
 *  and objects ("Wire Instructions") previously printed "[object Object]". */
function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '—';
    const parts = value.slice(0, 6).map((item) => {
      if (item === null || item === undefined) return '—';
      if (typeof item === 'object') {
        // Item dicts render as "key: value · key: value" instead of [object Object]
        const pairs = Object.entries(item)
          .filter(([, v]) => v !== null && v !== undefined && v !== '')
          .map(([k, v]) => `${formatFieldLabel(k)}: ${formatScalar(v)}`)
          .slice(0, 6);
        return pairs.length > 0 ? pairs.join(' · ') : '—';
      }
      return formatScalar(item);
    });
    const joined = parts.join('  |  ') + (value.length > parts.length ? '…' : '');
    return joined.length > 240 ? `${joined.slice(0, 237)}…` : joined;
  }
  if (typeof value === 'object') {
    const pairs = Object.entries(value)
      .filter(([, v]) => v !== null && v !== undefined && v !== '')
      .map(([k, v]) => `${formatFieldLabel(k)}: ${formatScalar(v)}`)
      .slice(0, 8);
    if (pairs.length === 0) return '—';
    const joined = pairs.join(' · ');
    return joined.length > 200 ? `${joined.slice(0, 197)}…` : joined;
  }
  return formatScalar(value);
}

function getConfidenceLabel(confidence?: number | null): { label: string; cls: string } {
  if (confidence === undefined || confidence === null) return { label: '', cls: '' };
  if (confidence >= 0.75) return { label: 'High', cls: 'confidence-high' };
  if (confidence >= 0.45) return { label: 'Med', cls: 'confidence-med' };
  return { label: 'Low', cls: 'confidence-low' };
}

const SavedSource: React.FC<{ reference: string }> = ({ reference }) => {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    logService.getSourceText(reference, controller.signal).then(
      (value) => { if (!controller.signal.aborted) setSource(value); },
      () => { if (!controller.signal.aborted) setError('Could not load the saved text. Close and reopen to retry.'); }
    );
    return () => controller.abort();
  }, [open, reference]);

  return (
    <div className="dashboard-source" onClick={(event) => event.stopPropagation()}>
      <button className="refresh-btn" type="button" aria-expanded={open} onClick={() => {
        setOpen(!open);
        setSource(null);
        setError('');
      }}>{open ? 'Hide saved text' : 'View saved text'}</button>
      {open && (error
        ? <p role="alert">{error}</p>
        : source !== null ? <pre tabIndex={0}>{source}</pre> : <p role="status">Loading saved text…</p>)}
    </div>
  );
};

const LogCard: React.FC<{
  log: LogRecord;
  onReviewed?: (id: string) => void;
  onDelete?: (log: LogRecord) => void;
  onEdit?: (log: LogRecord) => void;
}> = ({ log, onReviewed, onDelete, onEdit }) => {
  const [expanded, setExpanded] = useState(false);
  const isGenericSchema = !log.schema_name || log.schema_name === 'General Document';
  const date = log.created_at
    ? new Date(log.created_at).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Unknown date';

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
              <button
                className="log-details-toggle"
                type="button"
                aria-label={`${expanded ? 'Collapse' : 'Expand'} ${log.log_reference}`}
                aria-expanded={expanded}
              >
                {log.schema_name || 'Unknown Schema'}
              </button>
            </h3>
            <span className="log-card-domain">{log.domain || 'General'}</span>
            {log.source_filename && <div className="log-source-filename">{log.source_filename}</div>}
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
            {log.summary && <div className="log-field-item">
              <span className="log-field-label">Summary</span>
              <span className="log-field-value">{log.summary}</span>
            </div>}
            {log.source && <div className="log-field-item">
              <span className="log-field-label">Source</span>
              <span className="log-field-value">{log.source}</span>
            </div>}
            {fieldKeys.map((key) => (
              <div key={key} className="log-field-item">
                <span className="log-field-label">{formatFieldLabel(key)}</span>
                <span className="log-field-value">
                  {typeof log.data[key] === 'object' && log.data[key] !== null
                    ? JSON.stringify(log.data[key], null, 2)
                    : String(log.data[key] ?? '—')}
                </span>
              </div>
            ))}
            {fieldKeys.length === 0 && <div className="log-no-fields">No extracted fields</div>}
            {log.has_source_text && <SavedSource reference={log.log_reference} />}
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
            {onEdit && (
              <button
                type="button"
                className="log-card-btn-edit"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(log);
                }}
              >
                <Pencil size={12} />
                <span>Edit</span>
              </button>
            )}
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

/** Edit modal — PATCH /logs/{ref} with the full edited `data` dict.
 *  Nested arrays/objects are edited as JSON text; scalars as plain inputs. */
const EditLogModal: React.FC<{
  log: LogRecord;
  isSaving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (values: Record<string, unknown>) => void;
}> = ({ log, isSaving, error, onClose, onSave }) => {
  const fieldKeys = Object.keys(log.data || {}).filter((k) => !k.startsWith('_'));
  const [values, setValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    fieldKeys.forEach((k) => {
      const v = log.data[k];
      initial[k] = fieldInput(v);
    });
    return initial;
  });
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSave = () => {
    const data: Record<string, unknown> = { ...(log.data || {}) };
    for (const key of fieldKeys) {
      try {
        data[key] = editedValue(log.data[key], values[key]);
      } catch (error) {
        setLocalError(formatFieldLabel(key) + ' — ' + (error instanceof Error ? error.message : 'Invalid value.'));
        return;
      }
    }
    setLocalError(null);
    onSave(data);
  };

  return (
    <div className="edit-modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="edit-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="edit-modal-header">
          <div className="edit-modal-icon-wrap">
            <Pencil size={18} />
          </div>
          <div className="edit-modal-titles">
            <h3>Edit Log Record</h3>
            <p>
              {log.log_reference}
              {log.schema_name ? ` · ${log.schema_name}` : ''}
            </p>
          </div>
          <button
            type="button"
            className="edit-modal-close"
            onClick={onClose}
            disabled={isSaving}
            aria-label="Close dialog"
          >
            <X size={16} />
          </button>
        </div>

        <div className="edit-modal-body">
          <div className="edit-fields-list">
            {fieldKeys.map((key) => {
              const isNested =
                log.data[key] !== null &&
                log.data[key] !== undefined &&
                typeof log.data[key] === 'object';
              return (
                <div key={key} className="edit-field-item">
                  <label className="edit-field-label" htmlFor={`edit-field-${key}`}>
                    {formatFieldLabel(key)}
                  </label>
                  {isNested ? (
                    <textarea
                      id={`edit-field-${key}`}
                      className="edit-field-input nested"
                      rows={4}
                      value={values[key] ?? ''}
                      onChange={(e) => setValues((prev) => ({ ...prev, [key]: e.target.value }))}
                      disabled={isSaving}
                      spellCheck={false}
                    />
                  ) : (
                    <input
                      id={`edit-field-${key}`}
                      type="text"
                      className="edit-field-input"
                      value={values[key] ?? ''}
                      onChange={(e) => setValues((prev) => ({ ...prev, [key]: e.target.value }))}
                      disabled={isSaving}
                    />
                  )}
                </div>
              );
            })}
            {fieldKeys.length === 0 && (
              <div className="edit-no-fields">This record has no editable fields.</div>
            )}
          </div>
          {error && <div className="edit-modal-error">{error}</div>}
          {!error && localError && <div className="edit-modal-error">{localError}</div>}
        </div>

        <div className="edit-modal-footer">
          <button
            type="button"
            className="edit-modal-btn-cancel"
            onClick={onClose}
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            type="button"
            className="edit-modal-btn-save"
            onClick={handleSave}
            disabled={isSaving || fieldKeys.length === 0}
          >
            {isSaving ? (
              <>
                <Loader2 size={13} className="spin-icon" />
                <span>Saving…</span>
              </>
            ) : (
              <>
                <Check size={13} />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

const PAGE_SIZE = 25;
type PageStart = { cursor?: string; skip?: number };

export const LogsDashboard: React.FC = () => {
  const userId = useAppSelector((state) => state.auth.user?.id);
  return <UserLogsDashboard key={userId} />;
};

const UserLogsDashboard: React.FC = () => {
  const searchMode = useAppSelector(state => state.ui?.searchMode ?? 'related');
  const [logs, setLogs] = useState<LogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'review'>('all');
  const [input, setInput] = useState('');
  const [query, setQuery] = useState('');
  const [pages, setPages] = useState<PageStart[]>([{}]);
  const [nextPage, setNextPage] = useState<PageStart | null>(null);
  const page = pages[pages.length - 1];

  // Deletion modal & state
  const [logToDelete, setLogToDelete] = useState<LogRecord | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Edit modal & state
  const [logToEdit, setLogToEdit] = useState<LogRecord | null>(null);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const needsReview = activeTab === 'review' ? true : undefined;
    setLoading(true);
    setLogs([]);
    setNextPage(null);
    setError(null);

    async function load() {
      try {
        if (query) {
          if (!/[\p{L}\p{N}]/u.test(query)) return;
          const result = await logService.searchPage(query, { needsReview, limit: PAGE_SIZE, cursor: page.cursor, signal, related: searchMode === 'related' });
          if (signal.aborted) return;
          setLogs(result.records);
          setNextPage(result.nextCursor ? { cursor: result.nextCursor } : null);
        } else {
          const skip = page.skip ?? 0;
          const records = await logService.getLogs(undefined, skip, PAGE_SIZE + 1, needsReview, signal);
          if (signal.aborted) return;
          setLogs(records.slice(0, PAGE_SIZE));
          setNextPage(records.length > PAGE_SIZE ? { skip: skip + PAGE_SIZE } : null);
        }
      } catch (err) {
        if (!signal.aborted) setError(err instanceof Error ? err.message : 'Failed to load records');
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [activeTab, query, page, searchMode]);

  useEffect(() => {
    const next = input.trim();
    if (next === query) return;
    const timer = window.setTimeout(() => { setPages([{}]); setQuery(next); }, 220);
    return () => window.clearTimeout(timer);
  }, [input, query]);

  const restartPages = () => setPages([{}]);

  const selectTab = (tab: 'all' | 'review') => {
    if (tab !== activeTab) {
      setActiveTab(tab);
      restartPages();
    }
  };

  const applyQuery = (value: string) => {
    setQuery(value.trim());
    restartPages();
  };

  const handleReviewed = async (logReference: string) => {
    try {
      await logService.markAsReviewed(logReference);
      if (activeTab === 'review' && (pages.length > 1 || nextPage)) {
        restartPages();
      } else if (activeTab === 'review') {
        setLogs((prev) => prev.filter((l) => l.log_reference !== logReference));
      } else {
        setLogs((prev) =>
          prev.map((l) =>
            l.log_reference === logReference ? { ...l, requires_review: false } : l
          )
        );
      }
    } catch (err) {
      // Surface through the dashboard's own error banner instead of a native
      // alert() that breaks the app's styling and blocks the UI thread.
      setError((err instanceof Error && err.message) || 'Failed to mark as reviewed');
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
      if (pages.length > 1 || nextPage) restartPages();
      setLogToDelete(null);
    } catch (err) {
      setDeleteError((err instanceof Error && err.message) || 'Failed to delete log record.');
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

  const handleRequestEdit = (log: LogRecord) => {
    setEditError(null);
    setLogToEdit(log);
  };

  const handleSaveEdit = async (values: Record<string, unknown>) => {
    if (!logToEdit) return;
    try {
      setIsSavingEdit(true);
      setEditError(null);
      const updated = await logService.editLog(logToEdit.log_reference, { data: values });
      if (query) restartPages();
      else setLogs((prev) => prev.map((l) => l.log_reference === updated.log_reference ? updated : l));
      setLogToEdit(null);
    } catch (err) {
      setEditError((err instanceof Error && err.message) || 'Failed to save changes.');
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleCancelEdit = () => {
    if (!isSavingEdit) {
      setLogToEdit(null);
      setEditError(null);
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
              aria-pressed={activeTab === 'all'}
              onClick={() => selectTab('all')}
            >
              <Database size={13} />
              <span>All Logs</span>
            </button>
            <button
              className={`dashboard-tab review-tab ${activeTab === 'review' ? 'active' : ''}`}
              aria-pressed={activeTab === 'review'}
              onClick={() => selectTab('review')}
            >
              <AlertTriangle size={13} />
              <span>Review Queue</span>
            </button>
          </div>

          <button
            className="refresh-btn"
            onClick={restartPages}
            disabled={loading}
          >
            <RotateCcw size={13} className={loading ? 'spin-icon' : ''} />
            <span>{loading ? 'Refreshing…' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      <form className="dashboard-search" role="search" onSubmit={(event) => {
        event.preventDefault();
        applyQuery(input);
      }}>
        <Search size={16} aria-hidden="true" />
        <input
          aria-label="Search saved records"
          type="search"
          placeholder={searchMode === 'related' ? 'Search by word, related term, or reference' : 'Search by exact word or reference'}
          maxLength={256}
          value={input}
          onChange={(event) => {
            setInput(event.target.value);
            if (!event.target.value && query) applyQuery('');
          }}
        />
        {(query || input) && <button type="button" className="refresh-btn" onClick={() => {
          setInput('');
          applyQuery('');
        }}>Clear</button>}
        <button type="submit" className="refresh-btn">Search</button>
      </form>

      <div className="dashboard-content" aria-busy={loading}>
        {loading && query && <p className="dashboard-result-status" role="status">Searching for “{query}”…</p>}
        {error && <div className="dashboard-error" role="alert">{error}</div>}
        {!loading && !error && query && (
          <p className="dashboard-result-status" role="status">
            {logs.length} {logs.length === 1 ? 'match' : 'matches'} on this page for “{query}”
          </p>
        )}

        {!loading && !error && logs.length === 0 && (
          <div className="dashboard-empty">
            <div className="dashboard-empty-icon-wrap">
              {activeTab === 'review' ? <CheckCircle2 size={32} /> : <Inbox size={32} />}
            </div>
            <h3>{query ? 'No matching records' : activeTab === 'review' ? 'Queue is empty' : 'No records found'}</h3>
            <p>
              {query ? 'Try a different word or clear your search.' : activeTab === 'review'
                ? "Great job, all records have been verified!"
                : "Open Workspace to capture your first document."}
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
              onEdit={handleRequestEdit}
            />
          ))}
        </div>
        {(pages.length > 1 || nextPage) && (
          <nav className="dashboard-pagination" aria-label="Record pages">
            <button type="button" className="refresh-btn" disabled={loading || pages.length === 1}
              onClick={() => setPages((prev) => prev.slice(0, -1))}>Previous</button>
            <span>Page {pages.length}</span>
            <button type="button" className="refresh-btn" disabled={loading || !nextPage}
              onClick={() => { if (nextPage) setPages((prev) => [...prev, nextPage]); }}>Next</button>
          </nav>
        )}
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

      {/* Edit Modal for Log Record */}
      {logToEdit && (
        <EditLogModal
          log={logToEdit}
          isSaving={isSavingEdit}
          error={editError}
          onClose={handleCancelEdit}
          onSave={handleSaveEdit}
        />
      )}
    </div>
  );
};

