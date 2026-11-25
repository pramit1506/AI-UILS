import { describe, it, expect } from 'vitest';
import logReducer, {
  setLog,
  setFieldStatus,
  editFieldValue,
  bulkApproveAll,
  markLogSaved,
  bulkApproveHighConfidence,
  bulkRejectAll,
  resetFieldStatuses,
  selectNextField,
  selectPrevField,
  setViewLayoutMode,
} from '../../src/redux/logSlice';

describe('logSlice review & bulk operations', () => {
  const initialDraft = {
    schema_name: 'Invoice',
    domain: 'Finance',
    fields: {
      invoice_number: 'INV-1001',
      vendor: 'Acme Corp',
      total_amount: '$1,200.00',
      low_conf_field: 'Unknown',
    },
    field_metadata: {
      invoice_number: { confidence: 0.95 },
      vendor: { confidence: 0.85 },
      total_amount: { confidence: 0.9 },
      low_conf_field: { confidence: 0.3 },
    },
  };

  it('initializes field statuses to pending when draft is set', () => {
    const state = logReducer(
      undefined,
      setLog({ draft: initialDraft, updatedFields: ['invoice_number'] })
    );

    expect(state.fieldStatuses.invoice_number).toBe('pending');
    expect(state.fieldStatuses.vendor).toBe('pending');
    expect(state.activeFieldKey).toBe('invoice_number');
  });

  it('supports bulkApproveAll', () => {
    let state = logReducer(
      undefined,
      setLog({ draft: initialDraft, updatedFields: [] })
    );
    state = logReducer(state, bulkApproveAll());

    expect(state.fieldStatuses.invoice_number).toBe('approved');
    expect(state.fieldStatuses.vendor).toBe('approved');
    expect(state.fieldStatuses.total_amount).toBe('approved');
    expect(state.fieldStatuses.low_conf_field).toBe('approved');
  });

  it('keeps the saved reference until bulk review changes which fields will be stored', () => {
    let state = logReducer(undefined, setLog({ draft: initialDraft, updatedFields: [] }));
    state = logReducer(state, markLogSaved('LOG-001'));
    state = logReducer(state, bulkApproveAll());
    expect(state.savedLogReference).toBe('LOG-001');
    state = logReducer(state, bulkRejectAll());
    expect(state.savedLogReference).toBeNull();
  });

  it('supports bulkApproveHighConfidence (≥ 0.75)', () => {
    let state = logReducer(
      undefined,
      setLog({ draft: initialDraft, updatedFields: [] })
    );
    state = logReducer(state, bulkApproveHighConfidence(0.75));

    expect(state.fieldStatuses.invoice_number).toBe('approved');
    expect(state.fieldStatuses.vendor).toBe('approved');
    expect(state.fieldStatuses.total_amount).toBe('approved');
    // Low confidence should remain pending
    expect(state.fieldStatuses.low_conf_field).toBe('pending');
  });

  it('supports bulkRejectAll and resetFieldStatuses', () => {
    let state = logReducer(
      undefined,
      setLog({ draft: initialDraft, updatedFields: [] })
    );
    state = logReducer(state, bulkRejectAll());

    expect(state.fieldStatuses.invoice_number).toBe('rejected');
    expect(state.fieldStatuses.vendor).toBe('rejected');

    state = logReducer(state, resetFieldStatuses());
    expect(state.fieldStatuses.invoice_number).toBe('pending');
    expect(state.fieldStatuses.vendor).toBe('pending');
  });

  it('supports inline edit and individual field status setting', () => {
    let state = logReducer(
      undefined,
      setLog({ draft: initialDraft, updatedFields: [] })
    );
    state = logReducer(
      state,
      editFieldValue({ fieldKey: 'total_amount', value: '$1,250.00' })
    );

    expect(state.currentLog?.fields?.total_amount).toBe('$1,250.00');
    expect(state.fieldStatuses.total_amount).toBe('edited');
    expect(state.editedFieldValues.total_amount).toBe('$1,250.00');

    state = logReducer(
      state,
      setFieldStatus({ fieldKey: 'vendor', status: 'approved' })
    );
    expect(state.fieldStatuses.vendor).toBe('approved');
  });

  it('supports cursor navigation with selectNextField and selectPrevField', () => {
    let state = logReducer(
      undefined,
      setLog({ draft: initialDraft, updatedFields: [] })
    );
    expect(state.activeFieldKey).toBe('invoice_number');

    state = logReducer(state, selectNextField());
    expect(state.activeFieldKey).toBe('vendor');

    state = logReducer(state, selectPrevField());
    expect(state.activeFieldKey).toBe('invoice_number');
  });

  it('supports setting view layout modes', () => {
    const state = logReducer(undefined, setViewLayoutMode('review-focus'));
    expect(state.viewLayoutMode).toBe('review-focus');
  });
});
