import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { OriginalDocument } from '../types/log';

interface DocumentState {
  currentDocument: OriginalDocument | null;
  activeHighlightField: string | null;
  searchQuery: string;
  documentViewType: 'text' | 'preview';
  selectedSnippet: string | null;
  /** Object URL backing an uploaded file — revoked by callers when replaced */
  fileObjectUrl: string | null;
}

const initialState: DocumentState = {
  currentDocument: null,
  activeHighlightField: null,
  searchQuery: '',
  documentViewType: 'text',
  selectedSnippet: null,
  fileObjectUrl: null,
};

const documentSlice = createSlice({
  name: 'document',
  initialState,
  reducers: {
    setDocument: (state, action: PayloadAction<OriginalDocument | null>) => {
      state.currentDocument = action.payload;
      state.activeHighlightField = null;
      // Reset artifacts of the previous document so stale search terms and
      // preview modes no longer bleed into the newly loaded one.
      state.searchQuery = '';
      state.documentViewType = 'text';
      state.selectedSnippet = null;
      state.fileObjectUrl = null;
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
    setFileObjectUrl: (state, action: PayloadAction<string | null>) => {
      state.fileObjectUrl = action.payload;
    },
    clearDocument: (state) => {
      state.currentDocument = null;
      state.activeHighlightField = null;
      state.searchQuery = '';
      state.selectedSnippet = null;
      state.documentViewType = 'text';
      state.fileObjectUrl = null;
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
  setFileObjectUrl,
  clearDocument,
} = documentSlice.actions;

export default documentSlice.reducer;
