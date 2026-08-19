import { describe, it, expect, vi } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import chatReducer, { sendMessage } from '../../src/redux/chatSlice';
import agentReducer from '../../src/redux/agentSlice';
import logReducer from '../../src/redux/logSlice';
import documentReducer from '../../src/redux/documentSlice';
import { chatService } from '../../src/services/chatService';

vi.mock('../../src/services/chatService', () => ({
  chatService: {
    sendMessage: vi.fn(),
  },
}));

describe('chatSlice thunks', () => {
  it('should dispatch to log and agent slices on successful sendMessage', async () => {
    const store = configureStore({
      reducer: {
        chat: chatReducer,
        agent: agentReducer,
        log: logReducer,
        document: documentReducer,
      },
    });

    const mockResponse = {
      data: {
        assistant_message: 'I updated the document draft.',
        conversation_id: 'conv-123',
        tool_execution_result: {
          status: 'success',
          success_message: 'Extracted fields successfully',
        },
        log_draft: {
          schema_name: 'Invoice',
          domain: 'Finance',
          fields: {
            invoice_number: 'INV-900',
            total_amount: '$500.00',
          },
          field_metadata: {
            invoice_number: { confidence: 0.95 },
            total_amount: { confidence: 0.9 },
          },
        },
        draft_changes: [{ field_name: 'invoice_number' }, { field_name: 'total_amount' }],
      },
    };

    (chatService.sendMessage as any).mockResolvedValue(mockResponse);

    await store.dispatch(sendMessage('Process invoice') as any);

    const state = store.getState();

    // Check chat state
    expect(state.chat.messages.length).toBe(1);
    expect(state.chat.messages[0].role).toBe('assistant');

    // Check agent state
    expect(state.agent.executionTimeline.length).toBe(1);
    expect(state.agent.executionTimeline[0].status).toBe('success');

    // Check log state
    expect(state.log.currentLog?.fields?.invoice_number).toBe('INV-900');
    expect(state.log.lastUpdatedFields).toContain('invoice_number');
    expect(state.log.fieldStatuses.invoice_number).toBe('pending');
  });
});
