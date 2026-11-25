import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import App from '../src/App';
import { rootReducer } from '../src/redux/store';
import { setLog } from '../src/redux/logSlice';
import { updateDocumentText } from '../src/redux/documentSlice';
import { chatService } from '../src/services/chatService';
import { ConversationStatus } from '../src/types/agent';

describe('Capture workflow', () => {
  it('saves an active field edit by clicking Save record without pressing Enter', async () => {
    HTMLElement.prototype.scrollIntoView = vi.fn();
    const state = rootReducer(undefined, { type: 'init' });
    const store = configureStore({ reducer: rootReducer, preloadedState: { ...state,
      auth: { ...state.auth, isAuthenticated: true } } });
    store.dispatch(setLog({ draft: { schema_name: 'Inventory', fields: { quantity: 4 } }, updatedFields: [] }));
    const send = vi.spyOn(chatService, 'sendMessage').mockResolvedValueOnce({ success: true, message: 'Saved', data: {
      assistant_message: 'Saved LOG-1234', draft_changes: [], conversation_id: 'test',
      conversation_status: ConversationStatus.COMPLETED,
      tool_execution_result: { tool_name: 'save_log', status: 'success', success_message: 'Saved LOG-1234', validation_warnings: [] },
    } });
    try {
      render(<Provider store={store}><App /></Provider>);
      fireEvent.click(screen.getByTitle('Inline edit value (E)'));
      fireEvent.change(screen.getByLabelText('Edit Quantity'), { target: { value: '7' } });
      fireEvent.click(screen.getByRole('button', { name: 'Save record' }));
      expect(await screen.findByRole('heading', { name: 'Record saved' })).toBeVisible();
      expect(send).toHaveBeenCalledTimes(1);
      expect(send.mock.calls[0][0]).toMatchObject({ action: 'save_reviewed', log_draft: { fields: { quantity: 7 } } });
    } finally {
      send.mockRestore();
    }
  });
  it('opens at intake, then offers review, source comparison and one save action', () => {
    HTMLElement.prototype.scrollIntoView = vi.fn();
    const store = configureStore({ reducer: rootReducer });
    render(<Provider store={store}><App /></Provider>);
    expect(screen.getByRole('heading', {name: 'Capture a record'})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', {name: 'Paste text'}));
    expect(screen.getByLabelText('Document text')).toBeInTheDocument();
    act(() => {
      store.dispatch(updateDocumentText('Material: linen'));
      store.dispatch(setLog({draft: {fields: {material: 'linen'}}, updatedFields: ['material']}));
    });
    expect(screen.getAllByRole('button', {name: 'Save record'})).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', {name: 'Compare original'}));
    expect(screen.getByRole('region', {name: 'Original document'})).toBeVisible();
    fireEvent.click(screen.getByRole('button', {name: 'Conversation'}));
    expect(screen.getByRole('region', {name: 'Conversation'})).toBeVisible();
    fireEvent.click(screen.getByRole('button', {name: 'Save record'}));
    expect(screen.getByRole('dialog')).toHaveTextContent('Log in to save');
  });
});
