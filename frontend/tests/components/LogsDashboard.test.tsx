import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LogsDashboard } from '../../src/components/Dashboard/LogsDashboard';
import { logService, LogRecord } from '../../src/services/logService';

vi.mock('../../src/services/logService', () => ({
  logService: {
    getLogs: vi.fn(),
    deleteLog: vi.fn(),
    markAsReviewed: vi.fn(),
  },
}));

const mockLogs: LogRecord[] = [
  {
    id: '1',
    log_reference: 'LOG-INV1001',
    schema_name: 'Invoice',
    domain: 'Finance',
    source: 'pdf',
    version: 1,
    data: {
      invoice_number: 'INV-1001',
      total: '$1,200',
    },
    field_metadata: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    requires_review: false,
    overall_confidence: 0.95,
  },
  {
    id: '2',
    log_reference: 'LOG-RES2002',
    schema_name: 'Resume',
    domain: 'HR',
    source: 'pdf',
    version: 1,
    data: {
      candidate_name: 'Jane Doe',
      role: 'Software Engineer',
    },
    field_metadata: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    requires_review: true,
    overall_confidence: 0.5,
  },
];

import { Provider } from 'react-redux';
import { store } from '../../src/redux/store';

const renderDashboard = () => render(
  <Provider store={store}>
    <LogsDashboard />
  </Provider>
);

describe('LogsDashboard Component - Delete Log Feature', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(logService.getLogs).mockResolvedValue([...mockLogs]);
    vi.mocked(logService.deleteLog).mockResolvedValue();
  });

  it('renders log records correctly', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('LOG-INV1001')).toBeInTheDocument();
      expect(screen.getByText('LOG-RES2002')).toBeInTheDocument();
    });

    expect(screen.getByText('Invoice')).toBeInTheDocument();
    expect(screen.getByText('Resume')).toBeInTheDocument();
  });

  it('opens confirmation modal when delete button is clicked', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('LOG-INV1001')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByLabelText('Delete LOG-INV1001');
    fireEvent.click(deleteBtn);

    // Modal should appear
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Delete Log Record')).toBeInTheDocument();
    expect(
      screen.getByText(/Are you sure you want to permanently delete log record/i)
    ).toBeInTheDocument();
  });

  it('cancels deletion when Cancel button is clicked', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('LOG-INV1001')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByLabelText('Delete LOG-INV1001');
    fireEvent.click(deleteBtn);

    const cancelBtn = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelBtn);

    // Modal should close and log remains
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByText('LOG-INV1001')).toBeInTheDocument();
    expect(logService.deleteLog).not.toHaveBeenCalled();
  });

  it('successfully deletes log and removes it from dashboard', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('LOG-INV1001')).toBeInTheDocument();
      expect(screen.getByText('LOG-RES2002')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByLabelText('Delete LOG-INV1001');
    fireEvent.click(deleteBtn);

    const confirmBtn = screen.getByRole('button', { name: /delete record/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(logService.deleteLog).toHaveBeenCalledWith('LOG-INV1001');
    });

    // LOG-INV1001 should be removed from view, LOG-RES2002 remains
    await waitFor(() => {
      expect(screen.queryByText('LOG-INV1001')).not.toBeInTheDocument();
      expect(screen.getByText('LOG-RES2002')).toBeInTheDocument();
    });

    // Modal should be closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('displays error message if delete API fails', async () => {
    vi.mocked(logService.deleteLog).mockRejectedValue(new Error('Network error deleting log'));

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('LOG-INV1001')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByLabelText('Delete LOG-INV1001');
    fireEvent.click(deleteBtn);

    const confirmBtn = screen.getByRole('button', { name: /delete record/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText('Network error deleting log')).toBeInTheDocument();
    });

    // Log card should still be present in the list
    expect(screen.getByTestId('log-card-LOG-INV1001')).toBeInTheDocument();
  });
});
