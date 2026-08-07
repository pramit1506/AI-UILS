import React, { useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../../redux/store';
import { clearLog } from '../../redux/logSlice';
import { addUserMessage, sendMessage } from '../../redux/chatSlice';
import './LogForm.css';

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

function formatFieldValue(value: any): { display: string; isEmpty: boolean } {
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

const DynamicLogForm: React.FC = () => {
  const dispatch = useDispatch();
  const currentLog = useSelector((state: RootState) => state.log.currentLog);
  const lastUpdatedFields = useSelector((state: RootState) => state.log.lastUpdatedFields);

  const hasFields = Boolean(
    currentLog && (currentLog.schema_name || (currentLog.fields && Object.keys(currentLog.fields).length > 0))
  );

  const handleSave = useCallback(() => {
    dispatch(addUserMessage('Save the log'));
    dispatch(sendMessage('Save the log') as any);
  }, [dispatch]);

  const handleReset = useCallback(() => {
    dispatch(clearLog());
  }, [dispatch]);

  // Empty / idle state
  if (!hasFields) {
    return (
      <div className="dynamic-log-form">
        <div className="dlf-header">
          <div className="dlf-title-row">
            <span className="dlf-icon">📋</span>
            <span className="dlf-schema-badge">Universal Log</span>
          </div>
        </div>
        <div className="dlf-empty">
          <div className="dlf-empty-icon">✨</div>
          <p className="dlf-empty-title">No document loaded</p>
          <p className="dlf-empty-subtitle">
            Upload a PDF or paste text in the chat. The AI will extract the fields here automatically.
          </p>
        </div>
      </div>
    );
  }

  const { schema_name, domain, source, fields = {}, field_metadata = {} } = currentLog;
  const fieldEntries = Object.entries(fields).filter(([k]) => !k.startsWith('_'));
  const fieldCount = fieldEntries.length;

  return (
    <div className="dynamic-log-form">
      {/* Header */}
      <div className="dlf-header">
        <div className="dlf-title-row">
          <span className="dlf-icon">{getSchemaIcon(schema_name)}</span>
          <span className="dlf-schema-badge">
            {schema_name || 'Unknown Schema'}
          </span>
          {domain && <span className="dlf-domain-tag">{domain}</span>}
          {source && <span className="dlf-source-tag">📎 {source.toUpperCase()}</span>}
          <span className="dlf-field-count">{fieldCount} field{fieldCount !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {/* Fields List */}
      <div className="dlf-fields">
        {fieldEntries.map(([key, value], idx) => {
          const { display, isEmpty } = formatFieldValue(value);
          const meta = field_metadata[key];
          const confidence = meta?.confidence;
          const { label: confLabel, cls: confCls } = getConfidenceLabel(confidence);
          const isUpdated = lastUpdatedFields.includes(key);

          return (
            <div
              key={key}
              className={`dlf-field ${isUpdated ? 'updated' : ''}`}
              style={{ animationDelay: `${idx * 30}ms` }}
            >
              <div className="dlf-field-header">
                <span className="dlf-field-label">{formatFieldLabel(key)}</span>
                {confLabel && (
                  <span className={`dlf-confidence ${confCls}`}>{confLabel}</span>
                )}
              </div>
              <div className={`dlf-field-value ${isEmpty ? 'empty' : ''}`}>
                {display}
              </div>
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="dlf-actions">
        <button
          className="dlf-btn-save"
          onClick={handleSave}
          title="Say 'save the log' to commit this record"
        >
          💾 Save Log
        </button>
        <button
          className="dlf-btn-reset"
          onClick={handleReset}
          title="Clear the current draft"
        >
          ✕ Clear
        </button>
      </div>
    </div>
  );
};

export default DynamicLogForm;
