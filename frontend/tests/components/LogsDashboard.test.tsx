import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { LogsDashboard } from '../../src/components/Dashboard/LogsDashboard';
import { logService, LogRecord } from '../../src/services/logService';

vi.mock('../../src/services/logService', () => ({
  logService: {
    getLogs: vi.fn(),
    searchPage: vi.fn(),
    getSourceText: vi.fn(),
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
    data: {
      invoice_number: 'INV-1001',
      total: '$1,200',
    },
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
    data: {
      candidate_name: 'Jane Doe',
      role: 'Software Engineer',
    },
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

describe('Searching saved records', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(logService.getLogs).mockResolvedValue(mockLogs);
  });

  const submitSearch = (query: string) => {
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: query } });
  };

  it('uses the server cursor, resets it for review, and clears back to the reviewed list', async () => {
    const sourceHit = { ...mockLogs[0], log_reference: 'LOG-ARCHIVE', source_filename: 'old-report.txt', has_source_text: true };
    vi.mocked(logService.searchPage).mockImplementation(async (_query, options) => {
      if (options.needsReview) return { records: [], nextCursor: null };
      if (options.cursor) return { records: [mockLogs[1]], nextCursor: null };
      return { records: [sourceHit], nextCursor: 'page-two' };
    });
    vi.mocked(logService.getSourceText).mockResolvedValue('Archived shipment from Verona.');
    renderDashboard();
    await screen.findByText('LOG-INV1001');
    submitSearch('  Verona  ');
    await screen.findByText('LOG-ARCHIVE');
    expect(logService.searchPage).toHaveBeenCalledWith('Verona', expect.objectContaining({ limit: 25 }));
    expect(screen.queryByText('LOG-INV1001')).not.toBeInTheDocument();
    expect(screen.getByText('old-report.txt')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Expand LOG-ARCHIVE' }));
    expect(logService.getSourceText).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'View saved text' }));
    expect(await screen.findByText('Archived shipment from Verona.')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await screen.findByText('Page 2');
    await screen.findByText('LOG-RES2002');
    expect(logService.searchPage).toHaveBeenLastCalledWith('Verona', expect.objectContaining({ cursor: 'page-two' }));
    fireEvent.click(screen.getByRole('button', { name: 'Previous' }));
    await screen.findByText('LOG-ARCHIVE');
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await screen.findByText('LOG-RES2002');
    fireEvent.click(screen.getByRole('button', { name: 'Review Queue' }));
    await screen.findByText('No matching records');
    expect(logService.searchPage).toHaveBeenLastCalledWith('Verona', expect.objectContaining({ cursor: undefined, needsReview: true }));
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
    await screen.findByText('LOG-INV1001');
    expect(logService.getLogs).toHaveBeenLastCalledWith(undefined, 0, 26, true, expect.any(AbortSignal));
  });

  it('discards a superseded search even when its response resolves last', async () => {
    let finishOld!: (page: { records: LogRecord[]; nextCursor: null }) => void;
    vi.mocked(logService.searchPage)
      .mockImplementationOnce(() => new Promise((resolve) => { finishOld = resolve; }))
      .mockResolvedValueOnce({ records: [mockLogs[1]], nextCursor: null });
    renderDashboard();
    await screen.findByText('LOG-INV1001');
    submitSearch('old');
    await waitFor(() => expect(logService.searchPage).toHaveBeenCalled());
    const signal = vi.mocked(logService.searchPage).mock.calls[0][1].signal;
    submitSearch('new');
    await screen.findByText('LOG-RES2002');
    expect(signal?.aborted).toBe(true);
    await act(async () => finishOld({ records: [mockLogs[0]], nextCursor: null }));
    expect(screen.queryByText('LOG-INV1001')).not.toBeInTheDocument();
  });

  it('retries the same search after a failure without displaying unrelated records', async () => {
    vi.mocked(logService.searchPage)
      .mockRejectedValueOnce(new Error('Search temporarily unavailable'))
      .mockResolvedValueOnce({ records: [mockLogs[1]], nextCursor: null });
    renderDashboard();
    await screen.findByText('LOG-INV1001');
    submitSearch('Engineer');
    expect(await screen.findByRole('alert')).toHaveTextContent('Search temporarily unavailable');
    expect(screen.queryByText('LOG-INV1001')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    await screen.findByText('LOG-RES2002');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(logService.searchPage).toHaveBeenLastCalledWith('Engineer', expect.objectContaining({ limit: 25 }));
  });
});
