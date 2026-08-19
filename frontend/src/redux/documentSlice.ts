import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { OriginalDocument } from '../types/log';

interface DocumentState {
  currentDocument: OriginalDocument | null;
  activeHighlightField: string | null;
  searchQuery: string;
  documentViewType: 'text' | 'preview';
  selectedSnippet: string | null;
}

const initialState: DocumentState = {
  currentDocument: null,
  activeHighlightField: null,
  searchQuery: '',
  documentViewType: 'text',
  selectedSnippet: null,
};

const documentSlice = createSlice({
  name: 'document',
  initialState,
  reducers: {
    setDocument: (state, action: PayloadAction<OriginalDocument | null>) => {
      state.currentDocument = action.payload;
      state.activeHighlightField = null;
      state.selectedSnippet = null;
    },
    updateDocumentText: (state, action: PayloadAction<string>) => {
      if (state.currentDocument) {
        state.currentDocument.rawText = action.payload;
      } else {
        state.currentDocument = {
          id: Date.now().toString(),
          name: 'Pasted Document',
          fileType: 'pasted',
          rawText: action.payload,
          uploadedAt: new Date().toISOString(),
        };
      }
    },
    setActiveHighlightField: (state, action: PayloadAction<string | null>) => {
      state.activeHighlightField = action.payload;
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
    },
    setDocumentViewType: (state, action: PayloadAction<'text' | 'preview'>) => {
      state.documentViewType = action.payload;
    },
    setSelectedSnippet: (state, action: PayloadAction<string | null>) => {
      state.selectedSnippet = action.payload;
    },
    clearDocument: (state) => {
      state.currentDocument = null;
      state.activeHighlightField = null;
      state.searchQuery = '';
      state.selectedSnippet = null;
    },
  },
});

export const {
  setDocument,
  updateDocumentText,
  setActiveHighlightField,
  setSearchQuery,
  setDocumentViewType,
  setSelectedSnippet,
  clearDocument,
} = documentSlice.actions;

export default documentSlice.reducer;
