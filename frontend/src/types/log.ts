export interface FieldMetadata {
  value?: unknown;
  confidence?: number;
  source?: string;
  last_updated?: string;
  original_text_snippet?: string;
}

export type FieldReviewStatus = 'pending' | 'approved' | 'rejected' | 'edited';

export interface FieldReviewState {
  status: FieldReviewStatus;
  editedValue?: unknown;
  rejectedReason?: string;
  lastModified?: string;
}

export interface DynamicLogDraft {
  /** Inferred document type: "Invoice", "Resume", "Medical Intake Form", etc. */
  schema_name?: string;
  /** Business domain: "Finance", "HR", "Healthcare", etc. */
  domain?: string;
  /** How the info arrived: "pdf", "email", "text" */
  source?: string;
  /** All extracted field-value pairs — fully dynamic */
  fields?: Record<string, unknown>;
  /** Per-field AI confidence metadata */
  field_metadata?: Record<string, FieldMetadata>;
}

export enum DraftStatus {
  EMPTY = 'EMPTY',
  PARTIAL = 'PARTIAL',
  READY = 'READY',
  CONFIRMED = 'CONFIRMED',
  SAVED = 'SAVED',
}

export type ViewLayoutMode = 'side-by-side' | 'review-focus' | 'fields-only' | 'chat-focus';

export interface OriginalDocument {
  id: string;
  name: string;
  fileType: 'pdf' | 'docx' | 'txt' | 'eml' | 'pasted';
  rawText: string;
  fileUrl?: string | null;
  uploadedAt: string;
  fileSize?: number;
}
