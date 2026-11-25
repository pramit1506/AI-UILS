import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import logReducer from '../../src/redux/logSlice';
import chatReducer from '../../src/redux/chatSlice';
import agentReducer from '../../src/redux/agentSlice';
import documentReducer from '../../src/redux/documentSlice';
import DynamicLogForm from '../../src/components/LogForm/DynamicLogForm';

window.HTMLElement.prototype.scrollIntoView = vi.fn();

const renderWithRedux = (preloadedState?: Partial<import("../../src/redux/store").RootState>) => {
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
        <DynamicLogForm />
      </Provider>
    ),
  };
};

describe('DynamicLogForm Component', () => {
  it('renders empty state when no fields are present', () => {
    renderWithRedux();
    expect(screen.getByText('No document loaded')).toBeInTheDocument();
  });

  it('renders extracted fields and bulk action buttons', () => {
    const preloadedState = {
      log: {
        currentLog: {
          schema_name: 'Invoice',
          domain: 'Finance',
          fields: {
            invoice_number: 'INV-8822',
            total_amount: '$999.00',
          },
          field_metadata: {
            invoice_number: { confidence: 0.95 },
            total_amount: { confidence: 0.8 },
          },
        },
        lastUpdatedFields: [],
        extractionStatus: 'completed',
        sessionName: 'Invoice',
        isSessionNameUserDefined: false,
        fieldStatuses: { invoice_number: 'pending', total_amount: 'pending' },
        editedFieldValues: {},
        activeFieldKey: 'invoice_number',
        viewLayoutMode: 'side-by-side',
        isShortcutsModalOpen: false,
      },
    };

    const { store } = renderWithRedux(preloadedState);

    expect(screen.getByText('INV-8822')).toBeInTheDocument();
    expect(screen.getByText('$999.00')).toBeInTheDocument();

    // Verify bulk buttons exist
    const approveAllBtn = screen.getByRole('button', { name: /approve all/i });
    expect(approveAllBtn).toBeInTheDocument();

    // Click Approve All
    fireEvent.click(approveAllBtn);
    expect(store.getState().log.fieldStatuses.invoice_number).toBe('approved');
    expect(store.getState().log.fieldStatuses.total_amount).toBe('approved');
  });

  it('supports single-field approval and rejection click', () => {
    const preloadedState = {
      log: {
        currentLog: {
          schema_name: 'Invoice',
          fields: { invoice_number: 'INV-8822' },
          field_metadata: { invoice_number: { confidence: 0.95 } },
        },
        lastUpdatedFields: [],
        extractionStatus: 'completed',
        sessionName: 'Invoice',
        isSessionNameUserDefined: false,
        fieldStatuses: { invoice_number: 'pending' },
        editedFieldValues: {},
        activeFieldKey: 'invoice_number',
        viewLayoutMode: 'side-by-side',
        isShortcutsModalOpen: false,
      },
    };

    const { store } = renderWithRedux(preloadedState);

    const approveBtn = screen.getByTitle('Approve this field (A)');
    fireEvent.click(approveBtn);
    expect(store.getState().log.fieldStatuses.invoice_number).toBe('approved');

    const rejectBtn = screen.getByTitle('Exclude this field from the saved record (R)');
    fireEvent.click(rejectBtn);
    expect(store.getState().log.fieldStatuses.invoice_number).toBe('rejected');
  });
});
