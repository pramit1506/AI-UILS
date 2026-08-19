import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import logReducer from '../../src/redux/logSlice';
import chatReducer from '../../src/redux/chatSlice';
import agentReducer from '../../src/redux/agentSlice';
import documentReducer from '../../src/redux/documentSlice';
import { DocumentViewer } from '../../src/components/DocumentViewer/DocumentViewer';

window.HTMLElement.prototype.scrollIntoView = vi.fn();

const renderWithRedux = (preloadedState?: any) => {
  const store = configureStore({
    reducer: {
      log: logReducer,
      chat: chatReducer,
      agent: agentReducer,
      document: documentReducer,
    },
    preloadedState,
  });
  return {
    store,
    ...render(
      <Provider store={store}>
        <DocumentViewer />
      </Provider>
    ),
  };
};

describe('DocumentViewer Component', () => {
  it('renders empty state initially and allows loading sample document', () => {
    const { store } = renderWithRedux();
    expect(screen.getByText('Original Document Viewer')).toBeInTheDocument();

    const loadSampleBtn = screen.getByRole('button', { name: /invoice/i });
    fireEvent.click(loadSampleBtn);

    expect(store.getState().document.currentDocument?.name).toBe('sample_invoice_INV-8492.txt');
    expect(screen.getByText(/ACME INDUSTRIAL SUPPLY CORP/i)).toBeInTheDocument();
  });

  it('renders sample options across different domains', () => {
    renderWithRedux();
    expect(screen.getByRole('button', { name: /invoice/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /medical intake/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /candidate resume/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /product complaint/i })).toBeInTheDocument();
  });

  it('renders loaded document with search bar and line numbers', () => {
    const preloadedState = {
      document: {
        currentDocument: {
          id: 'doc-1',
          name: 'invoice_test.txt',
          fileType: 'txt',
          rawText: 'Header Line 1\nInvoice #9901\nTotal: $300',
          uploadedAt: '2026-08-16T12:00:00Z',
        },
        activeHighlightField: null,
        searchQuery: '',
        documentViewType: 'text',
        selectedSnippet: null,
      },
    };

    renderWithRedux(preloadedState);

    expect(screen.getByText('invoice_test.txt')).toBeInTheDocument();
    expect(screen.getByText('Header Line 1')).toBeInTheDocument();
    expect(screen.getByText('Invoice #9901')).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText('Search document…');
    fireEvent.change(searchInput, { target: { value: '9901' } });
    expect(screen.getByText('9901')).toBeInTheDocument();
  });
});
