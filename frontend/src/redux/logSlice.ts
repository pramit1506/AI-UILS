import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { DynamicLogDraft } from '../types/log';

interface LogState {
  currentLog: DynamicLogDraft | null;
  lastUpdatedFields: string[];
  extractionStatus: 'idle' | 'extracting' | 'completed' | 'error';
}

const initialState: LogState = {
  currentLog: null,
  lastUpdatedFields: [],
  extractionStatus: 'idle',
};

const logSlice = createSlice({
  name: 'log',
  initialState,
  reducers: {
    setLog: (state, action: PayloadAction<{ draft: DynamicLogDraft | null; updatedFields: string[] }>) => {
      state.currentLog = action.payload.draft;
      state.lastUpdatedFields = action.payload.updatedFields;
    },
    clearUpdatedFields: (state) => {
      state.lastUpdatedFields = [];
    },
    clearLog: (state) => {
      state.currentLog = null;
      state.lastUpdatedFields = [];
      state.extractionStatus = 'idle';
    },
    setExtractionStatus: (state, action: PayloadAction<'idle' | 'extracting' | 'completed' | 'error'>) => {
      state.extractionStatus = action.payload;
    },
  },
});

export const { setLog, clearUpdatedFields, clearLog, setExtractionStatus } = logSlice.actions;
export default logSlice.reducer;
