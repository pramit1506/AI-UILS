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
  editedFieldValues: Record<string, any>;
  /** Currently active / focused field for keyboard cursor navigation */
  activeFieldKey: string | null;
  /** Multi-panel layout configuration */
  viewLayoutMode: ViewLayoutMode;
  /** Shortcut modal visibility */
  isShortcutsModalOpen: boolean;
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
};

function getFieldKeys(draft: DynamicLogDraft | null): string[] {
  if (!draft || !draft.fields) return [];
  return Object.keys(draft.fields).filter((k) => !k.startsWith('_'));
}

const logSlice = createSlice({
  name: 'log',
  initialState,
  reducers: {
    setLog: (state, action: PayloadAction<{ draft: DynamicLogDraft | null; updatedFields: string[] }>) => {
      const newDraft = action.payload.draft;
      state.currentLog = newDraft;
      state.lastUpdatedFields = action.payload.updatedFields;

      // Auto-populate session name from AI inference, but don't override a user-defined name
      if (!state.isSessionNameUserDefined && newDraft?.schema_name) {
        state.sessionName = newDraft.schema_name;
      }

      // Initialize field statuses for any new fields without overriding existing reviewed states
      if (newDraft?.fields) {
        const currentKeys = Object.keys(newDraft.fields).filter((k) => !k.startsWith('_'));
        const nextStatuses: Record<string, FieldReviewStatus> = { ...state.fieldStatuses };

        currentKeys.forEach((key) => {
          if (!nextStatuses[key]) {
            nextStatuses[key] = 'pending';
          }
        });
        state.fieldStatuses = nextStatuses;

        if (!state.activeFieldKey && currentKeys.length > 0) {
          state.activeFieldKey = currentKeys[0];
        }
      }
    },
    /** User explicitly sets a custom session/document name */
    setSessionName: (state, action: PayloadAction<string>) => {
      state.sessionName = action.payload;
      state.isSessionNameUserDefined = true;
    },
    setFieldStatus: (
      state,
      action: PayloadAction<{ fieldKey: string; status: FieldReviewStatus }>
    ) => {
      const { fieldKey, status } = action.payload;
      state.fieldStatuses[fieldKey] = status;
    },
    editFieldValue: (
      state,
      action: PayloadAction<{ fieldKey: string; value: any }>
    ) => {
      const { fieldKey, value } = action.payload;
      if (state.currentLog && state.currentLog.fields) {
        state.currentLog.fields[fieldKey] = value;
      }
      state.editedFieldValues[fieldKey] = value;
      state.fieldStatuses[fieldKey] = 'edited';
    },
    bulkApproveAll: (state) => {
      const keys = getFieldKeys(state.currentLog);
      keys.forEach((key) => {
        state.fieldStatuses[key] = 'approved';
      });
    },
    bulkApproveHighConfidence: (state, action: PayloadAction<number | undefined>) => {
      const threshold = action.payload ?? 0.75;
      const keys = getFieldKeys(state.currentLog);
      const metadata = state.currentLog?.field_metadata || {};

      keys.forEach((key) => {
        const conf = metadata[key]?.confidence ?? 0.8;
        if (conf >= threshold) {
          state.fieldStatuses[key] = 'approved';
        }
      });
    },
    bulkRejectAll: (state) => {
      const keys = getFieldKeys(state.currentLog);
      keys.forEach((key) => {
        state.fieldStatuses[key] = 'rejected';
      });
    },
    bulkRejectUnapproved: (state) => {
      const keys = getFieldKeys(state.currentLog);
      keys.forEach((key) => {
        if (state.fieldStatuses[key] !== 'approved') {
          state.fieldStatuses[key] = 'rejected';
        }
      });
    },
    resetFieldStatuses: (state) => {
      const keys = getFieldKeys(state.currentLog);
      keys.forEach((key) => {
        state.fieldStatuses[key] = 'pending';
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
  setExtractionStatus,
} = logSlice.actions;

export default logSlice.reducer;
