import { editedValue, fieldInput } from '../../utils/fieldValue';
import React, { useCallback, useState, useRef, useEffect, useMemo } from 'react';
import {
  Receipt,
  FileText,
  FileSignature,
  Stethoscope,
  Scale,
  BarChart3,
  AlertTriangle,
  FileCheck,
  ClipboardList,
  Folder,
  Check,
  CheckCircle2,
  X,
  XCircle,
  Edit2,
  Clock,
  Sparkles,
  RotateCcw,
  Zap,
  Search,
  MessageSquare,
  CheckCheck
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import {
  setSessionName,
  setFieldStatus,
  editFieldValue,
  bulkApproveAll,
  bulkApproveHighConfidence,
  bulkRejectAll,
  resetFieldStatuses,
  setActiveFieldKey,
} from '../../redux/logSlice';
import { setActiveHighlightField } from '../../redux/documentSlice';
import { addUserMessage, sendMessage } from '../../redux/chatSlice';
import { useReviewShortcuts } from '../../hooks/useReviewShortcuts';
import { useSaveLog } from '../../hooks/useSaveLog';
import { FieldReviewStatus } from '../../types/log';
import './LogForm.css';

function getSchemaIcon(schemaName?: string) {
  if (!schemaName) return <ClipboardList size={16} />;
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

function formatFieldValue(value: unknown): { display: string; isEmpty: boolean } {
  if (value === null || value === undefined || value === '') {
    return { display: '—', isEmpty: true };
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return { display: '—', isEmpty: true };
    return { display: value.join(', '), isEmpty: false };
  }
  if (typeof value === 'object') {
    return { display: JSON.stringify(value, null, 2), isEmpty: false };
  }
  return { display: String(value), isEmpty: false };
}

function getConfidenceLabel(confidence?: number): { label: string; cls: string } {
  if (confidence === undefined || confidence === null) return { label: '', cls: '' };
  if (confidence >= 0.75) return { label: 'High', cls: 'confidence-high' };
  if (confidence >= 0.45) return { label: 'Med', cls: 'confidence-med' };
  return { label: 'Low', cls: 'confidence-low' };
}

function formatSessionDate(isoString: string | null): string {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Inline editable document/session name badge */
const EditableSessionName: React.FC<{
  value: string | null;
  isUserDefined: boolean;
  onSave: (name: string) => void;
}> = ({ value, isUserDefined, onSave }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const startEdit = () => {
    setDraft(value || '');
    setEditing(true);
  };

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commit = () => {
    const trimmed = draft.trim();
    if (trimmed) onSave(trimmed);
    setEditing(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') commit();
    if (e.key === 'Escape') setEditing(false);
  };

  if (editing) {
    return (
      <div className="dlf-name-editing">
        <input
          ref={inputRef}
          className="dlf-name-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={onKeyDown}
          placeholder="Enter document name…"
          maxLength={60}
        />
        {/* onClick guard prevents the double commit: blur already commits
            when the confirm button steals focus, so ignore click events that
            arrive after the input has left editing mode. */}
        <button
          className="dlf-name-confirm-btn"
          onMouseDown={(e) => e.preventDefault()}
          onClick={commit}
          title="Confirm name"
        >
          <Check size={12} />
        </button>
      </div>
    );
  }

  const isGeneric = !value || value === 'General Document';

  return (
    <div className="dlf-name-display">
      <span
        className={`dlf-schema-badge ${
          isGeneric && !isUserDefined ? 'dlf-schema-detecting' : ''
        }`}
        title={
          isGeneric && !isUserDefined
            ? 'AI is detecting document type — click to rename'
            : value || ''
        }
      >
        {isGeneric && !isUserDefined ? 'Detecting schema…' : value || 'Document'}
      </span>
      <button className="dlf-edit-name-btn" onClick={startEdit} title="Rename this session">
        <Edit2 size={12} />
      </button>
    </div>
  );
};

export const DynamicLogForm: React.FC<{ onSource?: () => void; onChat?: () => void; commitRef?: React.Ref<() => boolean> }> = ({ onSource, onChat, commitRef }) => {
  const dispatch = useAppDispatch();
  const currentLog = useAppSelector((state) => state.log.currentLog);
  const lastUpdatedFields = useAppSelector((state) => state.log.lastUpdatedFields);
  const sessionName = useAppSelector((state) => state.log.sessionName);
  const isSessionNameUserDefined = useAppSelector(
    (state) => state.log.isSessionNameUserDefined
  );
  const sessionStartedAt = useAppSelector((state) => state.chat.sessionStartedAt);
  const fieldStatuses = useAppSelector((state) => state.log.fieldStatuses);
  const activeFieldKey = useAppSelector((state) => state.log.activeFieldKey);

  // Filter state for reviewing (all, pending, approved, rejected, edited)
  const [statusFilter, setStatusFilter] = useState<'all' | FieldReviewStatus>('all');

  // Inline editing state for active card
  const [editingFieldKey, setEditingFieldKey] = useState<string | null>(null);
  const [editDraftValue, setEditDraftValue] = useState<string>('');
  const [editError, setEditError] = useState('');
  const inlineEditInputRef = useRef<HTMLInputElement>(null);

  const hasFields = Boolean(
    currentLog &&
      (currentLog.schema_name ||
        (currentLog.fields && Object.keys(currentLog.fields).length > 0))
  );

  const handleSaveName = useCallback(
    (name: string) => {
      dispatch(setSessionName(name));
    },
    [dispatch]
  );

  const { triggerSave } = useSaveLog();


  // Conversational AI correction trigger
  const handleConversationalCorrection = useCallback(
    (fieldKey: string) => {
      const currentVal = currentLog?.fields?.[fieldKey];
      const prompt = `Please correct the field "${fieldKey}" (currently "${currentVal}") based on the original document.`;
      dispatch(addUserMessage(prompt));
      dispatch(sendMessage(prompt));
      onChat?.();
    },
    [currentLog, dispatch, onChat]
  );

  // Trigger inline edit
  const handleStartInlineEdit = useCallback(
    (fieldKey: string) => {
      const val = currentLog?.fields?.[fieldKey];
      setEditingFieldKey(fieldKey);
      setEditError('');
      setEditDraftValue(fieldInput(val));
    },
    [currentLog]
  );

  useEffect(() => {
    if (editingFieldKey) {
      inlineEditInputRef.current?.focus();
    }
  }, [editingFieldKey]);

  const handleCommitInlineEdit = useCallback(
    (fieldKey: string) => {
      try {
        dispatch(editFieldValue({ fieldKey, value: editedValue(currentLog?.fields?.[fieldKey], editDraftValue) }));
      } catch (error) {
        setEditError(error instanceof Error ? error.message : 'Invalid field value.');
        inlineEditInputRef.current?.focus();
        return false;
      }
      setEditingFieldKey(null);
      return true;
    },
    [dispatch, editDraftValue, currentLog]
  );

  // Bind speed shortcuts
  const commitPending = useCallback(() => !editingFieldKey || handleCommitInlineEdit(editingFieldKey), [editingFieldKey, handleCommitInlineEdit]);
  React.useImperativeHandle(commitRef, () => commitPending, [commitPending]);
  useReviewShortcuts({
    onSave: () => { if (commitPending()) triggerSave(); },
    onEditActiveField: handleStartInlineEdit,
    onConversationalCorrect: handleConversationalCorrection,
    enabled: true,
  });

  const sessionDateLine = sessionStartedAt ? (
    <div className="dlf-session-info">
      <Clock size={12} className="dlf-session-clock" />
      <span className="dlf-session-date">
        Started {formatSessionDate(sessionStartedAt)}
      </span>
    </div>
  ) : null;

  // Compute metrics & filtered fields
  const { schema_name, domain, source, fields = {}, field_metadata = {} } =
    currentLog || {};
  const allFieldEntries = useMemo(
    () => Object.entries(fields).filter(([k]) => !k.startsWith('_')),
    [fields]
  );

  const metrics = useMemo(() => {
    const total = allFieldEntries.length;
    let approved = 0;
    let rejected = 0;
    let edited = 0;
    let pending = 0;

    allFieldEntries.forEach(([key]) => {
      const st = fieldStatuses[key] || 'pending';
      if (st === 'approved') approved++;
      else if (st === 'rejected') rejected++;
      else if (st === 'edited') edited++;
      else pending++;
    });

    const reviewed = approved + rejected + edited;
    const progressPct = total > 0 ? Math.round((reviewed / total) * 100) : 0;

    return { total, approved, rejected, edited, pending, progressPct };
  }, [allFieldEntries, fieldStatuses]);

  const visibleFieldEntries = useMemo(() => {
    if (statusFilter === 'all') return allFieldEntries;
    return allFieldEntries.filter(([key]) => {
      const st = fieldStatuses[key] || 'pending';
      return st === statusFilter;
    });
  }, [allFieldEntries, statusFilter, fieldStatuses]);

  // ── Empty / idle state ────────────────────────────────────────────────────
  if (!hasFields) {
    return (
      <div className="dynamic-log-form">
        <div className="dlf-header">
          <div className="dlf-title-row">
            <div className="dlf-icon-badge">
              <ClipboardList size={16} />
            </div>
            <EditableSessionName
              value={sessionName}
              isUserDefined={isSessionNameUserDefined}
              onSave={handleSaveName}
            />
          </div>
          {sessionDateLine}
        </div>
        <div className="dlf-empty">
          <div className="dlf-empty-icon-wrap">
            <Sparkles size={28} />
          </div>
          <p className="dlf-empty-title">No document loaded</p>
          <p className="dlf-empty-subtitle">
            Upload a PDF, TXT or paste text in chat. The AI will extract structured fields
            and populate them here for verification.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="dynamic-log-form">
      {/* ─── Header ────────────────────────────────────────── */}
      <div className="dlf-header">
        <div className="dlf-title-row">
          <div className="dlf-icon-badge">
            {getSchemaIcon(schema_name)}
          </div>
          <EditableSessionName
            value={sessionName}
            isUserDefined={isSessionNameUserDefined}
            onSave={handleSaveName}
          />
          {domain && <span className="dlf-domain-tag">{domain}</span>}
          {source && <span className="dlf-source-tag">{source.toUpperCase()}</span>}
        </div>
        {sessionDateLine}

        {/* ── Review Progress Bar ── */}
        <div className="dlf-progress-wrapper">
          <div className="dlf-progress-bar-bg">
            <div
              className="dlf-progress-bar-fill"
              style={{ width: `${metrics.progressPct}%` }}
            />
          </div>
          <div className="dlf-progress-labels">
            <span className="dlf-progress-pct">{metrics.progressPct}% Reviewed</span>
            <span className="dlf-progress-counts">
              <strong className="count-approved">{metrics.approved} approved</strong> ·{' '}
              <strong className="count-rejected">{metrics.rejected} rejected</strong> ·{' '}
              <span className="count-pending">{metrics.pending} pending</span>
            </span>
          </div>
        </div>
      </div>

      {/* ─── Bulk Actions & Speed Controls ──────────────────── */}
      <div className="dlf-bulk-bar">
        <div className="dlf-bulk-actions" role="group" aria-label="Bulk review actions">
          <button
            className="dlf-bulk-btn bulk-approve"
            onClick={() => dispatch(bulkApproveAll())}
            title="Approve all fields (Shift + A)"
          >
            <CheckCheck size={13} />
            <span>Approve All</span>
            <kbd>⇧A</kbd>
          </button>
          <button
            className="dlf-bulk-btn bulk-high-conf"
            onClick={() => dispatch(bulkApproveHighConfidence(0.75))}
            title="Approve all fields with ≥75% AI confidence (Shift + H)"
          >
            <Zap size={13} />
            <span>High-Conf ≥75%</span>
            <kbd>⇧H</kbd>
          </button>
          <button
            className="dlf-bulk-btn bulk-reject"
            onClick={() => dispatch(bulkRejectAll())}
            title="Exclude all fields from the saved record (Shift + R)"
          >
            <X size={13} />
            <span>Reject All</span>
            <kbd>⇧R</kbd>
          </button>
          <button
            className="dlf-bulk-btn bulk-reset"
            onClick={() => dispatch(resetFieldStatuses())}
            title="Reset decisions back to pending (Shift + X)"
          >
            <RotateCcw size={12} />
            <span>Reset</span>
          </button>
        </div>

        {/* Filter tabs */}
        <div className="dlf-filter-tabs">
          <button
            className={`dlf-tab ${statusFilter === 'all' ? 'active' : ''}`}
            onClick={() => setStatusFilter('all')}
          >
            All ({metrics.total})
          </button>
          <button
            className={`dlf-tab ${statusFilter === 'pending' ? 'active' : ''}`}
            onClick={() => setStatusFilter('pending')}
          >
            Pending ({metrics.pending})
          </button>
          <button
            className={`dlf-tab ${statusFilter === 'approved' ? 'active' : ''}`}
            onClick={() => setStatusFilter('approved')}
          >
            Approved ({metrics.approved})
          </button>
          <button
            className={`dlf-tab ${statusFilter === 'rejected' ? 'active' : ''}`}
            onClick={() => setStatusFilter('rejected')}
          >
            Rejected ({metrics.rejected})
          </button>
        </div>
      </div>

      {/* ─── Fields List ───────────────────────────────────── */}
      <div className="dlf-fields">
        {visibleFieldEntries.length === 0 ? (
          <div className="dlf-filter-empty">
            No fields match filter "{statusFilter}".
          </div>
        ) : (
          visibleFieldEntries.map(([key, value], idx) => {
            const { display, isEmpty } = formatFieldValue(value);
            const meta = field_metadata[key];
            const confidence = meta?.confidence;
            const { label: confLabel, cls: confCls } = getConfidenceLabel(confidence);
            const isUpdated = lastUpdatedFields.includes(key);
            const status: FieldReviewStatus = fieldStatuses[key] || 'pending';
            const isActive = activeFieldKey === key;
            const isEditing = editingFieldKey === key;

            return (
              <div
                key={key}
                className={`dlf-field ${status} ${isActive ? 'dlf-field-active' : ''} ${
                  isUpdated ? 'updated' : ''
                }`}
                style={{ animationDelay: `${idx * 20}ms` }}
                onClick={() => {
                  dispatch(setActiveFieldKey(key));
                  dispatch(setActiveHighlightField(key));
                }}
              >
                {/* Field Card Header */}
                <div className="dlf-field-header">
                  <div className="dlf-field-label-group">
                    {isActive && <div className="dlf-active-indicator" />}
                    <span className="dlf-field-label">{formatFieldLabel(key)}</span>
                  </div>

                  <div className="dlf-field-meta-badges">
                    {confLabel && (
                      <span className={`dlf-confidence ${confCls}`}>
                        <span className="dlf-conf-dot" />
                        {confidence ? `${Math.round(confidence * 100)}%` : confLabel}
                      </span>
                    )}
                    <span className={`dlf-status-pill status-${status}`}>
                      {status === 'approved' && <CheckCircle2 size={12} />}
                      {status === 'rejected' && <XCircle size={12} />}
                      {status === 'edited' && <Edit2 size={11} />}
                      {status === 'pending' && <Clock size={11} />}
                      <span>
                        {status === 'approved' && 'Approved'}
                        {status === 'rejected' && 'Rejected'}
                        {status === 'edited' && 'Edited'}
                        {status === 'pending' && 'Pending'}
                      </span>
                    </span>
                  </div>
                </div>

                {/* Field Value or Inline Editor */}
                {isEditing ? (
                  <div
                    className="dlf-field-editor"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      aria-label={'Edit ' + formatFieldLabel(key)}
                      ref={inlineEditInputRef}
                      type="text"
                      className="dlf-inline-input"
                      value={editDraftValue}
                      onChange={(e) => setEditDraftValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCommitInlineEdit(key);
                        if (e.key === 'Escape') setEditingFieldKey(null);
                      }}
                    />
                    {editError && <span role="alert">{editError}</span>}
                    <button
                      className="dlf-editor-btn save"
                      onClick={() => handleCommitInlineEdit(key)}
                      title="Save edit (Enter)"
                    >
                      <Check size={13} />
                    </button>
                    <button
                      className="dlf-editor-btn cancel"
                      onClick={() => setEditingFieldKey(null)}
                      title="Cancel (Esc)"
                    >
                      <X size={13} />
                    </button>
                  </div>
                ) : (
                  <div className={`dlf-field-value ${isEmpty ? 'empty' : ''}`}>
                    {display}
                  </div>
                )}

                {/* Field Card Interactive Action Buttons */}
                <div className="dlf-field-actions-row" onClick={(e) => e.stopPropagation()}>
                  <button
                    className={`dlf-action-btn approve ${status === 'approved' ? 'selected' : ''}`}
                    onClick={() => {
                      dispatch(setFieldStatus({ fieldKey: key, status: 'approved' }));
                    }}
                    title="Approve this field (A)"
                  >
                    <Check size={12} />
                    <span>Approve</span>
                    <span className="hotkey-hint">A</span>
                  </button>

                  <button
                    className={`dlf-action-btn reject ${status === 'rejected' ? 'selected' : ''}`}
                    onClick={() => {
                      dispatch(setFieldStatus({ fieldKey: key, status: 'rejected' }));
                    }}
                    title="Exclude this field from the saved record (R)"
                  >
                    <X size={12} />
                    <span>Reject</span>
                    <span className="hotkey-hint">R</span>
                  </button>

                  <button
                    className="dlf-action-btn edit"
                    onClick={() => handleStartInlineEdit(key)}
                    title="Inline edit value (E)"
                  >
                    <Edit2 size={12} />
                    <span>Edit</span>
                    <span className="hotkey-hint">E</span>
                  </button>

                  <button
                    className="dlf-action-btn ai-correct"
                    onClick={() => handleConversationalCorrection(key)}
                    title="Ask AI in chat to correct this field (C)"
                  >
                    <MessageSquare size={12} />
                    <span>AI Fix</span>
                    <span className="hotkey-hint">C</span>
                  </button>

                  <button
                    className="dlf-action-btn find-doc"
                    onClick={() => {
                      dispatch(setActiveFieldKey(key));
                      dispatch(setActiveHighlightField(key));
                      onSource?.();
                    }}
                    disabled={!onSource}
                    title="Locate & highlight in source document"
                  >
                    <Search size={12} />
                    <span>Find</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default DynamicLogForm;
