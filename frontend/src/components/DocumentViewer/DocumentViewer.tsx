import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  FileText,
  FileCode,
  FileSpreadsheet,
  Search,
  X,
  Save,
  Edit3,
  Wand2,
  Copy,
  Check,
  Sparkles,
  Layers,
  Eye,
  Code
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import {
  setDocument,
  setSearchQuery,
  setDocumentViewType,
  setActiveHighlightField,
} from '../../redux/documentSlice';
import { editFieldValue, setLog } from '../../redux/logSlice';
import { addUserMessage, sendMessage } from '../../redux/chatSlice';
import { DynamicLogDraft } from '../../types/log';
import { useSaveLog } from '../../hooks/useSaveLog';
import './DocumentViewer.css';

type SampleDoc = {
  name: string;
  displayName: string;
  type: 'txt' | 'pdf';
  text: string;
  mockLog: DynamicLogDraft;
};

const SAMPLE_DOCS: SampleDoc[] = [
  {
    name: 'sample_invoice_INV-8492.txt',
    displayName: 'Invoice (INV-8492)',
    type: 'txt' as const,
    text: `ACME INDUSTRIAL SUPPLY CORP
1044 Innovation Way, Suite 300, Austin, TX 78701
Phone: (512) 555-0199 | Email: billing@example.com

INVOICE
Invoice Number: INV-2026-8492
Invoice Date: August 14, 2026
Due Date: September 13, 2026
Payment Terms: Net 30

BILLED TO:
Apex Logistics & Freight Inc.
Attn: Accounts Payable
450 Harbor Blvd, Long Beach, CA 90802
Customer ID: CUST-99214

DESCRIPTION OF SERVICES & MATERIALS:
1. Heavy Duty Conveyor Roller 400mm (Qty: 24) @ $125.00 = $3,000.00
2. Industrial High-Torque Drive Motor 5HP (Qty: 2) @ $1,450.00 = $2,900.00
3. Installation, Calibration & Onsite Testing (Qty: 12 hrs) @ $150.00/hr = $1,800.00
4. Freight & Hazardous Material Handling = $350.00

SUBTOTAL: $8,050.00
TAX (8.25%): $664.13
TOTAL AMOUNT DUE: $8,714.13

Wire Instructions:
Bank: First National Commercial Bank
Routing: 121000358
Account: 948201948201
Remit To: payments@example.com`,
    mockLog: {
      schema_name: 'Invoice',
      domain: 'Finance',
      source: 'txt',
      fields: {
        invoice_number: 'INV-2026-8492',
        invoice_date: 'August 14, 2026',
        due_date: 'September 13, 2026',
        vendor_name: 'ACME INDUSTRIAL SUPPLY CORP',
        vendor: 'ACME INDUSTRIAL SUPPLY CORP',
        customer_name: 'Apex Logistics & Freight Inc.',
        subtotal: '$8,050.00',
        tax_amount: '$664.13',
        total_amount: '$8,714.13',
        payment_terms: 'Net 30',
      },
      field_metadata: {
        invoice_number: { confidence: 0.98, source: 'document' },
        invoice_date: { confidence: 0.95, source: 'document' },
        due_date: { confidence: 0.92, source: 'document' },
        vendor_name: { confidence: 0.99, source: 'document' },
        vendor: { confidence: 0.99, source: 'document' },
        customer_name: { confidence: 0.94, source: 'document' },
        subtotal: { confidence: 0.91, source: 'document' },
        tax_amount: { confidence: 0.88, source: 'document' },
        total_amount: { confidence: 0.99, source: 'document' },
        payment_terms: { confidence: 0.85, source: 'document' },
      },
    },
  },
  {
    name: 'sample_medical_intake_MED-4091.txt',
    displayName: 'Medical Intake (MED-4091)',
    type: 'txt' as const,
    text: `METRO HEALTH GENERAL HOSPITAL
Department of Internal Medicine
742 Evergreen Terrace, Springfield, IL 62704
Phone: (217) 555-0143

CLINICAL INTAKE & MEDICAL RECORD
Patient Name: Sarah Connor
Patient ID: PAT-88219
Date of Birth: 1984-11-28
Date of Visit: August 18, 2026
Attending Physician: Dr. Marcus Vance
Department: Cardiology

CHIEF COMPLAINT:
Patient presents with persistent shortness of breath and mild palpitations for 2 weeks.

DIAGNOSIS:
Diagnosis: Mild Sinus Tachycardia and Stage 1 Hypertension
ICD-10 Code: I10, R00.0

PRESCRIPTION & TREATMENT:
1. Metoprolol Tartrate 25mg PO BID
2. Low sodium diet and 30 minutes daily moderate exercise
3. Follow-up 2D Echocardiogram in 4 weeks`,
    mockLog: {
      schema_name: 'Medical Record',
      domain: 'Healthcare',
      source: 'txt',
      fields: {
        patient_name: 'Sarah Connor',
        patient_id: 'PAT-88219',
        doctor_name: 'Dr. Marcus Vance',
        department: 'Cardiology',
        diagnosis: 'Mild Sinus Tachycardia and Stage 1 Hypertension',
        visit_date: 'August 18, 2026',
        treatment: 'Metoprolol Tartrate 25mg PO BID',
      },
      field_metadata: {
        patient_name: { confidence: 0.99, source: 'document' },
        patient_id: { confidence: 0.96, source: 'document' },
        doctor_name: { confidence: 0.97, source: 'document' },
        department: { confidence: 0.92, source: 'document' },
        diagnosis: { confidence: 0.95, source: 'document' },
        visit_date: { confidence: 0.91, source: 'document' },
        treatment: { confidence: 0.89, source: 'document' },
      },
    },
  },
  {
    name: 'sample_resume_HR-7720.txt',
    displayName: 'Candidate Resume (HR-7720)',
    type: 'txt' as const,
    text: `ALEXANDER MORGAN
Senior Full Stack Engineer
San Francisco, CA | (415) 555-0182 | alex.morgan@example.org

CANDIDATE PROFILE:
Candidate Name: Alexander Morgan
Position Applied: Lead Systems Architect
Years of Experience: 8 years
Highest Education: M.S. in Computer Science, Stanford University

CORE SKILLS:
Python, TypeScript, React, PostgreSQL, LangGraph, Docker, Kubernetes, Distributed Systems

WORK EXPERIENCE:
1. Staff Platform Engineer - CloudScale Inc (2022 - Present)
- Architected real-time event streaming pipeline processing 2M events/sec.
- Reduced cloud infrastructure costs by 32% via autoscaling optimizations.

2. Senior Backend Engineer - FinTech Core Systems (2018 - 2022)
- Led team of 6 engineers building multi-currency payment settlement ledger.`,
    mockLog: {
      schema_name: 'Resume',
      domain: 'HR',
      source: 'txt',
      fields: {
        candidate_name: 'Alexander Morgan',
        position_applied: 'Lead Systems Architect',
        years_of_experience: '8 years',
        highest_education: 'M.S. in Computer Science, Stanford University',
        email: 'alex.morgan@example.org',
        skills: 'Python, TypeScript, React, PostgreSQL, LangGraph, Docker, Kubernetes',
      },
      field_metadata: {
        candidate_name: { confidence: 0.99, source: 'document' },
        position_applied: { confidence: 0.94, source: 'document' },
        years_of_experience: { confidence: 0.92, source: 'document' },
        highest_education: { confidence: 0.95, source: 'document' },
        email: { confidence: 0.98, source: 'document' },
        skills: { confidence: 0.90, source: 'document' },
      },
    },
  },
  {
    name: 'sample_complaint_QC-1092.txt',
    displayName: 'Product Complaint (QC-1092)',
    type: 'txt' as const,
    text: `GLOBAL MEDTECH QUALITY ASSURANCE
Post-Market Surveillance & Incident Report

INCIDENT / COMPLAINT REPORT
Complaint ID: QC-2026-1092
Customer Name: St. Jude Medical Center
Contact Person: Dr. Elena Rostova
Product Name: Precision IV Infusion Pump Pro
Batch Number: LOT-2026-88B
Serial Number: SN-9941-X
Incident Date: August 12, 2026
Severity Level: Medium

DESCRIPTION OF ISSUE:
Pump stopped delivering fluid and triggered error code ERR-402 during routine intravenous infusion. No patient injury reported. Replacement unit dispatched.

INVESTIGATION FINDINGS:
Root Cause: Flow rate sensor calibration drift. Recommended firmware update v4.2.1.`,
    mockLog: {
      schema_name: 'Complaint',
      domain: 'Quality Management',
      source: 'txt',
      fields: {
        customer_name: 'St. Jude Medical Center',
        product_name: 'Precision IV Infusion Pump Pro',
        batch_number: 'LOT-2026-88B',
        complaint_id: 'QC-2026-1092',
        incident_date: 'August 12, 2026',
        description: 'Pump stopped delivering fluid and triggered error code ERR-402 during routine intravenous infusion.',
      },
      field_metadata: {
        customer_name: { confidence: 0.97, source: 'document' },
        product_name: { confidence: 0.98, source: 'document' },
        batch_number: { confidence: 0.96, source: 'document' },
        complaint_id: { confidence: 0.95, source: 'document' },
        incident_date: { confidence: 0.92, source: 'document' },
        description: { confidence: 0.94, source: 'document' },
      },
    },
  },
];

export const DocumentViewer: React.FC<{ onSaveRecord?: () => void }> = ({ onSaveRecord }) => {
  const dispatch = useAppDispatch();
  const currentDocument = useAppSelector((state) => state.document.currentDocument);
  const activeHighlightField = useAppSelector((state) => state.document.activeHighlightField);
  const searchQuery = useAppSelector((state) => state.document.searchQuery);
  const documentViewType = useAppSelector((state) => state.document.documentViewType);
  const currentLog = useAppSelector((state) => state.log.currentLog);
  const activeFieldKey = useAppSelector((state) => state.log.activeFieldKey);

  const [selectedText, setSelectedText] = useState<string>('');
  const [selectionPosition, setSelectionPosition] = useState<{ x: number; y: number } | null>(null);
  const [copied, setCopied] = useState(false);

  const textViewerRef = useRef<HTMLDivElement>(null);
  const activeHighlightRef = useRef<HTMLElement | null>(null);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setSearchQuery(e.target.value));
  };

  const { saved: logSaved, savedReference, triggerSave } = useSaveLog();

  const handleSaveLog = useCallback(() => {
    triggerSave();
  }, [triggerSave]);

  const activeFieldValue = useMemo(() => {
    if (!currentLog?.fields || !activeHighlightField) return null;
    const val = currentLog.fields[activeHighlightField];
    if (val === null || val === undefined || typeof val === 'object') return null;
    const str = String(val).trim();
    return str.length >= 2 ? str : null;
  }, [currentLog, activeHighlightField]);

  const docStats = useMemo(() => {
    if (!currentDocument?.rawText) return { lines: 0, words: 0, chars: 0 };
    const raw = currentDocument.rawText;
    const lines = raw.split('\n').length;
    const words = raw.trim().split(/\s+/).filter(Boolean).length;
    const chars = raw.length;
    return { lines, words, chars };
  }, [currentDocument]);

  const hasFields = Boolean(
    currentLog &&
      currentLog.fields &&
      Object.keys(currentLog.fields).filter((k) => !k.startsWith('_')).length > 0
  );

  const handleMouseUp = () => {
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) {
      const text = selection.toString().trim();
      if (text.length > 0) {
        setSelectedText(text);
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        setSelectionPosition({
          x: Math.max(10, rect.left + rect.width / 2),
          y: Math.max(10, rect.top - 44),
        });
        return;
      }
    }
    setSelectedText('');
    setSelectionPosition(null);
  };

  useEffect(() => {
    if (activeHighlightRef.current) {
      activeHighlightRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [activeHighlightField, activeFieldValue]);

  const handleLoadSample = (index: number) => {
    const sample = SAMPLE_DOCS[index];
    dispatch(
      setDocument({
        id: Date.now().toString(),
        name: sample.name,
        fileType: sample.type,
        rawText: sample.text,
        uploadedAt: new Date().toISOString(),
      })
    );
    dispatch(
      setLog({
        draft: sample.mockLog,
        newDocument: true,
        updatedFields: Object.keys(sample.mockLog.fields ?? {}),
      })
    );
    dispatch(addUserMessage(`Opened sample document: ${sample.name}`));
  };

  const handleAssignToActiveField = () => {
    if (activeFieldKey && selectedText) {
      dispatch(editFieldValue({ fieldKey: activeFieldKey, value: selectedText }));
      setSelectedText('');
      setSelectionPosition(null);
    }
  };

  const handleCorrectWithAI = () => {
    if (selectedText) {
      const prompt = activeFieldKey
        ? `Please update the field "${activeFieldKey}" to "${selectedText}" based on the document.`
        : `Please extract this value from document: "${selectedText}"`;
      dispatch(addUserMessage(prompt));
      dispatch(sendMessage(prompt));
      setSelectedText('');
      setSelectionPosition(null);
    }
  };

  const handleCopySelectedText = () => {
    if (selectedText) {
      // Clipboard API rejects in non-secure contexts — swallow instead of
      // surfacing an unhandled rejection to the global error logger.
      navigator.clipboard.writeText(selectedText).catch(() => {
        /* clipboard unavailable — non-fatal */
      });
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
        setSelectedText('');
        setSelectionPosition(null);
      }, 1000);
    }
  };

  const getDocTypeIcon = () => {
    if (!currentDocument) return <FileText size={15} />;
    switch (currentDocument.fileType) {
      case 'pdf':
        return <FileCode size={15} className="doc-icon-pdf" />;
      case 'docx':
        return <FileSpreadsheet size={15} className="doc-icon-docx" />;
      default:
        return <FileText size={15} className="doc-icon-txt" />;
    }
  };

  const renderHighlightedDocument = useCallback(() => {
    if (!currentDocument?.rawText) return null;

    const lines = currentDocument.rawText.split('\n');
    const query = searchQuery.trim().toLowerCase();
    const targetValue = activeFieldValue ? activeFieldValue.toLowerCase() : null;

    return lines.map((line, lineIdx) => {
      const lineNum = lineIdx + 1;

      if (!line) {
        return (
          <div key={lineIdx} className="doc-line doc-line-empty">
            <span className="doc-line-num">{lineNum}</span>
            <span className="doc-line-text">&nbsp;</span>
          </div>
        );
      }

      let elements: React.ReactNode[] = [];

      if (targetValue || query) {
        const patterns: { text: string; type: 'active' | 'search' }[] = [];
        if (targetValue && line.toLowerCase().includes(targetValue)) {
          patterns.push({ text: targetValue, type: 'active' });
        }
        if (query && line.toLowerCase().includes(query)) {
          patterns.push({ text: query, type: 'search' });
        }

        if (patterns.length > 0) {
          const regexStr = patterns
            .map((p) => p.text.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&'))
            .join('|');
          const regex = new RegExp(`(${regexStr})`, 'gi');

          const parts = line.split(regex);
          elements = parts.map((part, pIdx) => {
            const lowerPart = part.toLowerCase();
            if (targetValue && lowerPart === targetValue) {
              return (
                <mark
                  key={`${pIdx}-${activeHighlightField ?? ''}`}
                  ref={(el) => {
                    // Overwrite the ref for the current highlight so the
                    // "Find" scroll always targets the *active* field — the
                    // old `!activeHighlightRef.current` guard kept the first
                    // mark (possibly detached) forever.
                    if (el) {
                      activeHighlightRef.current = el;
                    }
                  }}
                  className="doc-highlight-active"
                  title={`Extracted field: ${activeHighlightField}`}
                >
                  {part}
                </mark>
              );
            }
            if (query && lowerPart === query) {
              return (
                <mark key={pIdx} className="doc-highlight-search">
                  {part}
                </mark>
              );
            }
            return <span key={pIdx}>{part}</span>;
          });
        } else {
          elements = [<span key={0}>{line}</span>];
        }
      } else {
        elements = [<span key={0}>{line}</span>];
      }

      return (
        <div key={lineIdx} className="doc-line">
          <span className="doc-line-num">{lineNum}</span>
          <span className="doc-line-text">{elements}</span>
        </div>
      );
    });
  }, [currentDocument, searchQuery, activeFieldValue, activeHighlightField]);

  if (!currentDocument) {
    return (
      <div className="doc-viewer-container doc-viewer-empty">
        <div className="doc-viewer-empty-card">
          <div className="doc-empty-icon-wrap">
            <Layers size={28} />
          </div>
          <h3>Sample documents</h3>
          <div className="doc-sample-actions">
            <span className="doc-sample-label">Choose a document to review its fields.</span>
            <div className="doc-sample-grid">
              {SAMPLE_DOCS.map((doc, idx) => (
                <button
                  key={doc.name}
                  className="doc-sample-btn"
                  onClick={() => handleLoadSample(idx)}
                >
                  <Sparkles size={14} className="doc-sample-sparkle" />
                  <div className="doc-sample-btn-info">
                    <span className="doc-sample-name">{doc.displayName}</span>
                    <span className="doc-sample-domain-badge">{doc.mockLog.domain}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="doc-viewer-container" onMouseUp={handleMouseUp}>
      {/* Top Document Header */}
      <div className="doc-viewer-header">
        <div className="doc-meta-main">
          <div className="doc-type-badge">
            {getDocTypeIcon()}
          </div>
          <div className="doc-info-block">
            <span className="doc-title" title={currentDocument.name}>
              {currentDocument.name}
            </span>
            <div className="doc-tags">
              <span className="doc-format-badge">{currentDocument.fileType.toUpperCase()}</span>
              <span className="doc-stat-tag">{docStats.lines} lines</span>
              <span className="doc-stat-tag">{docStats.words} words</span>
            </div>
          </div>
        </div>

        {/* Right Toolbar Actions */}
        <div className="doc-header-actions">
          {/* Search Toolbar */}
          <div className="doc-search-bar">
            <Search size={13} className="doc-search-icon" />
            <input
              type="text"
              className="doc-search-input"
              placeholder="Search document…"
              value={searchQuery}
              onChange={handleSearchChange}
            />
            {searchQuery && (
              <button
                className="doc-search-clear"
                onClick={() => dispatch(setSearchQuery(''))}
                title="Clear search"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* View mode toggle (Text vs PDF if PDF URL exists) */}
          {currentDocument.fileUrl && (
            <div className="doc-mode-toggle">
              <button
                className={`doc-mode-btn ${documentViewType === 'text' ? 'active' : ''}`}
                onClick={() => dispatch(setDocumentViewType('text'))}
              >
                <Code size={12} />
                <span>Text</span>
              </button>
              <button
                className={`doc-mode-btn ${documentViewType === 'preview' ? 'active' : ''}`}
                onClick={() => dispatch(setDocumentViewType('preview'))}
              >
                <Eye size={12} />
                <span>Preview</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Active Cross-Reference Indicator Banner */}
      {activeHighlightField && activeFieldValue && (
        <div className="doc-active-field-banner">
          <span className="doc-banner-dot" />
          <span className="doc-banner-label">
            Highlighting source for: <strong>{activeHighlightField.replace(/_/g, ' ')}</strong>
          </span>
          <span className="doc-banner-val">"{activeFieldValue}"</span>
          <button
            className="doc-banner-clear"
            onClick={() => dispatch(setActiveHighlightField(null))}
            title="Clear highlight"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* BUG-003 fix: show hint when field is selected but value isn't found in doc */}
      {activeHighlightField && activeFieldValue &&
        currentDocument?.rawText &&
        !currentDocument.rawText.toLowerCase().includes(activeFieldValue.toLowerCase()) && (
        <div className="doc-no-match-banner">
          <Eye size={12} className="doc-no-match-icon" />
          <span>
            Value <strong>"{activeFieldValue}"</strong> not found verbatim in document — it may have been inferred or reformatted by the AI.
          </span>
        </div>
      )}

      {/* Document Content View */}
      <div className="doc-viewer-content" ref={textViewerRef}>
        {documentViewType === 'preview' && currentDocument.fileUrl ? (
          <iframe
            src={currentDocument.fileUrl}
            title="Document PDF Preview"
            className="doc-pdf-frame"
            // Sandboxed: PDFs can embed JavaScript; without this a crafted
            // PDF preview runs scripts with full page-origin access.
            sandbox="allow-same-origin"
          />
        ) : (
          <div className="doc-text-grid">{renderHighlightedDocument()}</div>
        )}
      </div>

      {/* Floating Selection Action Popover */}
      {selectionPosition && selectedText && (
        <div
          className="doc-selection-popover"
          style={{
            left: `${selectionPosition.x}px`,
            top: `${selectionPosition.y}px`,
          }}
          onMouseDown={(e) => e.stopPropagation()}
          onMouseUp={(e) => e.stopPropagation()}
        >
          <span className="doc-popover-text" title={selectedText}>
            "{selectedText.slice(0, 20)}
            {selectedText.length > 20 ? '…' : ''}"
          </span>
          <button
            className="doc-popover-btn assign"
            onClick={handleAssignToActiveField}
            title={
              activeFieldKey
                ? `Set selected text as value for "${activeFieldKey}"`
                : 'Select a field first to assign'
            }
            disabled={!activeFieldKey}
          >
            <Edit3 size={12} />
            <span>Set to {activeFieldKey ? activeFieldKey.replace(/_/g, ' ') : 'Field'}</span>
          </button>
          <button
            className="doc-popover-btn ai"
            onClick={handleCorrectWithAI}
            title="Ask conversational AI to update field with this value"
          >
            <Wand2 size={12} />
            <span>AI Fix</span>
          </button>
          {hasFields && !logSaved && (
            <button
              className="doc-popover-btn save"
              onClick={onSaveRecord ?? handleSaveLog}
              title="Save current log record"
            >
              <Save size={12} />
              <span>Save</span>
            </button>
          )}
          {hasFields && logSaved && (
            <span className="doc-popover-btn save saved" title={`Already saved as ${savedReference}`}>
              <Check size={12} />
              <span>Saved</span>
            </span>
          )}
          <button
            className="doc-popover-btn copy"
            onClick={handleCopySelectedText}
            title="Copy selected text"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      )}
    </div>
  );
};
