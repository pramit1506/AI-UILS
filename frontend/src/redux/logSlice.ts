import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { DynamicLogDraft, FieldReviewStatus, ViewLayoutMode } from '../types/log';

interface LogState {
  currentLog: DynamicLogDraft | null;
  lastUpdatedFields: string[];
  extractionStatus: 'idle' | 'extracting' | 'completed' | 'error';
  /** AI-inferred or user-overridden document/session name */
  sessionName: string | null;
  /** True once the user has manually typed a custom name */
  isSessionNameUserDefined: boolean;
  /** Review status per field key (approved, rejected, pending, edited) */
  fieldStatuses: Record<string, FieldReviewStatus>;
  /** User manual edits */
  editedFieldValues: Record<string, unknown>;
  /** Currently active / focused field for keyboard cursor navigation */
  activeFieldKey: string | null;
  /** Multi-panel layout configuration */
  viewLayoutMode: ViewLayoutMode;
  /** Shortcut modal visibility */
  isShortcutsModalOpen: boolean;
  /** Log reference assigned by the backend when this draft was saved
   *  (e.g. "LOG-3C2B3CBE"). Null while the draft has unsaved changes. */
  savedLogReference: string | null;
  /** ISO timestamp of the last successful save */
  savedAt: string | null;
}

const initialState: LogState = {
  currentLog: null,
  lastUpdatedFields: [],
  extractionStatus: 'idle',
  sessionName: null,
  isSessionNameUserDefined: false,
  fieldStatuses: {},
  editedFieldValues: {},
  activeFieldKey: null,
  viewLayoutMode: 'side-by-side',
  isShortcutsModalOpen: false,
  savedLogReference: null,
  savedAt: null,
};

function getFieldKeys(draft: DynamicLogDraft | null): string[] {
  if (!draft || !draft.fields) return [];
  return Object.keys(draft.fields).filter((k) => !k.startsWith('_'));
}

function applyReviewStatus(state: LogState, key: string, status: FieldReviewStatus) {
  if ((state.fieldStatuses[key] === 'rejected') !== (status === 'rejected')) {
    state.savedLogReference = null;
    state.savedAt = null;
  }
  state.fieldStatuses[key] = status;
}

const logSlice = createSlice({
  name: 'log',
  initialState,
  reducers: {
    setLog: (state, action: PayloadAction<{ draft: DynamicLogDraft | null; updatedFields: string[]; newDocument?: boolean }>) => {
      const newDraft = action.payload.draft;
      if (action.payload.newDocument) {
        state.fieldStatuses = {};
        state.editedFieldValues = {};
        state.activeFieldKey = null;
        state.sessionName = null;
        state.isSessionNameUserDefined = false;
      }
      // Capture the previous field values BEFORE the draft is replaced so we
      // can detect whether a field's value actually changed.
      const prevValues = state.currentLog?.fields || {};
      const prevStatuses = state.fieldStatuses;
      state.currentLog = newDraft;
      state.lastUpdatedFields = action.payload.updatedFields;

      // Any genuinely new/changed field means the saved snapshot no longer
      // matches the draft — reset the saved state so the user can save again
      // (and so duplicate-save prevention is lifted correctly).
      if (action.payload.newDocument || action.payload.updatedFields.length > 0) {
        state.savedLogReference = null;
        state.savedAt = null;
      }

      // Review statuses are per-document. Previously same-named fields in a
      // *different* document silently inherited the old document's
      // approved/rejected state. A field keeps its status only while its
      // value is unchanged; new or changed fields reset to `pending`.
      const nextStatuses: Record<string, FieldReviewStatus> = {};
      if (newDraft?.fields) {
        const draftFields = newDraft.fields;
        const currentKeys = Object.keys(draftFields).filter((k) => !k.startsWith('_'));

        currentKeys.forEach((key) => {
          const value = draftFields[key];
          const previousValue = prevValues[key];
          const unchanged =
            key in prevStatuses && JSON.stringify(value) === JSON.stringify(previousValue);
          nextStatuses[key] = unchanged ? prevStatuses[key] : 'pending';
        });
        state.fieldStatuses = nextStatuses;

        if (!state.activeFieldKey && currentKeys.length > 0) {
          state.activeFieldKey = currentKeys[0];
        }
      } else {
        state.fieldStatuses = {};
      }

      // Drop edit-value bookkeeping for fields that no longer exist.
      const survivingEdited: Record<string, unknown> = {};
      Object.keys(state.editedFieldValues).forEach((key) => {
        if (newDraft?.fields && key in newDraft.fields) {
          survivingEdited[key] = state.editedFieldValues[key];
        }
      });
      state.editedFieldValues = survivingEdited;
      // A user-defined name only persists within the same document set.
      state.isSessionNameUserDefined = newDraft?.schema_name
        ? state.isSessionNameUserDefined
        : false;

      // Auto-populate session name from AI inference, but don't override a user-defined name
      if (!state.isSessionNameUserDefined && newDraft?.schema_name) {
        state.sessionName = newDraft.schema_name;
      }
    },
    /** User explicitly sets a custom session/document name */
    setSessionName: (state, action: PayloadAction<string>) => {
      if (state.sessionName !== action.payload) {
        state.savedLogReference = null;
        state.savedAt = null;
        if (state.currentLog) state.currentLog.schema_name = action.payload;
      }
      state.sessionName = action.payload;
      state.isSessionNameUserDefined = true;
    },
    setFieldStatus: (
      state,
      action: PayloadAction<{ fieldKey: string; status: FieldReviewStatus }>
    ) => {
      const { fieldKey, status } = action.payload;
      applyReviewStatus(state, fieldKey, status);
    },
    editFieldValue: (
      state,
      action: PayloadAction<{ fieldKey: string; value: unknown }>
    ) => {
      const { fieldKey, value } = action.payload;
      if (state.currentLog && state.currentLog.fields) {
        state.currentLog.fields[fieldKey] = value;
      }
      state.editedFieldValues[fieldKey] = value;
      state.fieldStatuses[fieldKey] = 'edited';
      // Manual edits invalidate the previously saved record.
      state.savedLogReference = null;
      state.savedAt = null;
    },
    bulkApproveAll: (state) => {
      const keys = getFieldKeys(state.currentLog);
      keys.forEach((key) => {
        applyReviewStatus(state, key, 'approved');
      });
    },
    bulkApproveHighConfidence: (state, action: PayloadAction<number | undefined>) => {
      const threshold = action.payload ?? 0.75;
      const keys = getFieldKeys(state.currentLog);
      const metadata = state.currentLog?.field_metadata || {};

      keys.forEach((key) => {
        // Fields with NO confidence metadata are the least trustworthy —
        // treating missing data as a high 0.8 confidence silently approved
        // unknown-quality fields. Missing confidence now never auto-approves.
        const conf = metadata[key]?.confidence;
        if (typeof conf === 'number' && conf >= threshold) {
          applyReviewStatus(state, key, 'approved');
        }
      });
    },
    bulkRejectAll: (state) => {
      const keys = getFieldKeys(state.currentLog);
      keys.forEach((key) => {
        applyReviewStatus(state, key, 'rejected');
      });
    },
    bulkRejectUnapproved: (state) => {
      const keys = getFieldKeys(state.currentLog);
      keys.forEach((key) => {
        if (state.fieldStatuses[key] !== 'approved') {
          applyReviewStatus(state, key, 'rejected');
        }
      });
    },
    resetFieldStatuses: (state) => {
      const keys = getFieldKeys(state.currentLog);
      keys.forEach((key) => {
        applyReviewStatus(state, key, 'pending');
      });
    },
    setActiveFieldKey: (state, action: PayloadAction<string | null>) => {
      state.activeFieldKey = action.payload;
    },
    selectNextField: (state) => {
      const keys = getFieldKeys(state.currentLog);
      if (keys.length === 0) return;
      if (!state.activeFieldKey) {
        state.activeFieldKey = keys[0];
        return;
      }
      const currentIndex = keys.indexOf(state.activeFieldKey);
      const nextIndex = currentIndex < keys.length - 1 ? currentIndex + 1 : 0;
      state.activeFieldKey = keys[nextIndex];
    },
    selectPrevField: (state) => {
      const keys = getFieldKeys(state.currentLog);
      if (keys.length === 0) return;
      if (!state.activeFieldKey) {
        state.activeFieldKey = keys[keys.length - 1];
        return;
      }
      const currentIndex = keys.indexOf(state.activeFieldKey);
      const prevIndex = currentIndex > 0 ? currentIndex - 1 : keys.length - 1;
      state.activeFieldKey = keys[prevIndex];
    },
    setViewLayoutMode: (state, action: PayloadAction<ViewLayoutMode>) => {
      state.viewLayoutMode = action.payload;
    },
    setShortcutsModalOpen: (state, action: PayloadAction<boolean>) => {
      state.isShortcutsModalOpen = action.payload;
    },
    toggleShortcutsModal: (state) => {
      state.isShortcutsModalOpen = !state.isShortcutsModalOpen;
    },
    clearUpdatedFields: (state) => {
      state.lastUpdatedFields = [];
    },
    clearLog: (state) => {
      state.currentLog = null;
      state.lastUpdatedFields = [];
      state.extractionStatus = 'idle';
      state.sessionName = null;
      state.isSessionNameUserDefined = false;
      state.fieldStatuses = {};
      state.editedFieldValues = {};
      state.activeFieldKey = null;
      state.savedLogReference = null;
      state.savedAt = null;
    },
    /** Record a successful save (backend save_log tool execution). */
    markLogSaved: (state, action: PayloadAction<string | null>) => {
      state.savedLogReference = action.payload;
      state.savedAt = action.payload ? new Date().toISOString() : null;
    },
    setExtractionStatus: (
      state,
      action: PayloadAction<'idle' | 'extracting' | 'completed' | 'error'>
    ) => {
      state.extractionStatus = action.payload;
    },
  },
});

export const {
  setLog,
  setSessionName,
  setFieldStatus,
  editFieldValue,
  bulkApproveAll,
  bulkApproveHighConfidence,
  bulkRejectAll,
  bulkRejectUnapproved,
  resetFieldStatuses,
  setActiveFieldKey,
  selectNextField,
  selectPrevField,
  setViewLayoutMode,
  setShortcutsModalOpen,
  toggleShortcutsModal,
  clearUpdatedFields,
  clearLog,
  markLogSaved,
  setExtractionStatus,
} = logSlice.actions;

export default logSlice.reducer;
