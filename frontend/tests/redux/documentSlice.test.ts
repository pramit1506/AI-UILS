import { describe, it, expect } from 'vitest';
import documentReducer, {
  setDocument,
  updateDocumentText,
  setActiveHighlightField,
  setSearchQuery,
  clearDocument,
} from '../../src/redux/documentSlice';

describe('documentSlice', () => {
  it('handles setDocument and clearDocument', () => {
    let state = documentReducer(
      undefined,
      setDocument({
        id: 'doc-1',
        name: 'invoice.pdf',
        fileType: 'pdf',
        rawText: 'INVOICE #1234\nTotal: $100',
        uploadedAt: '2026-08-16T12:00:00Z',
      })
    );

    expect(state.currentDocument?.name).toBe('invoice.pdf');
    expect(state.currentDocument?.rawText).toContain('INVOICE #1234');

    state = documentReducer(state, clearDocument());
    expect(state.currentDocument).toBeNull();
  });

  it('handles updateDocumentText and search query', () => {
    let state = documentReducer(undefined, updateDocumentText('Pasted text line 1\nLine 2'));
    expect(state.currentDocument?.rawText).toBe('Pasted text line 1\nLine 2');
    expect(state.currentDocument?.fileType).toBe('pasted');

    state = documentReducer(state, setSearchQuery('line 1'));
    expect(state.searchQuery).toBe('line 1');

    state = documentReducer(state, setActiveHighlightField('invoice_number'));
    expect(state.activeHighlightField).toBe('invoice_number');
  });
});
