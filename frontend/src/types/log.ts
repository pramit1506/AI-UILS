export interface FieldMetadata {
  value?: any;
  confidence?: number;
  source?: string;
  last_updated?: string;
}

export interface DynamicLogDraft {
  /** Inferred document type: "Invoice", "Resume", "Medical Intake Form", etc. */
  schema_name?: string;
  /** Business domain: "Finance", "HR", "Healthcare", etc. */
  domain?: string;
  /** How the info arrived: "pdf", "email", "text" */
  source?: string;
  /** All extracted field-value pairs — fully dynamic */
  fields?: Record<string, any>;
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
