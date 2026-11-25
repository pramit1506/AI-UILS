import { describe, it, expect, vi } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import chatReducer, { addUserMessage, sendMessage } from '../../src/redux/chatSlice';
import agentReducer from '../../src/redux/agentSlice';
import logReducer from '../../src/redux/logSlice';
import documentReducer, { setDocument, updateDocumentText } from '../../src/redux/documentSlice';
import { ConversationStatus } from '../../src/types/agent';
import { fetchCurrentUser } from '../../src/redux/authSlice';
import { rootReducer } from '../../src/redux/store';
import { chatService } from '../../src/services/chatService';

vi.mock('../../src/services/chatService', () => ({
  chatService: {
    sendMessage: vi.fn(),
  },
}));

describe('chatSlice thunks', () => {
  it('sends one source body on signed-in intake, omits history on follow-up, and keeps guest source metadata out', async () => {
    const store = configureStore({ reducer: rootReducer });
    const doc = {
      id: 'upload', name: 'archive.txt', rawText: 'Unique text from an uploaded shipment',
      fileType: 'txt' as const, uploadedAt: '',
    };
    const intake = `Process this uploaded document (${doc.name}):\n\n${doc.rawText}`;
    vi.mocked(chatService.sendMessage).mockResolvedValue({ success: true, message: '', data: {
      assistant_message: 'Received', conversation_id: 'workspace', draft_changes: [],
      conversation_status: ConversationStatus.COLLECTING_INFORMATION,
    } });
    store.dispatch(setDocument(doc));
    await store.dispatch(sendMessage(intake));
    expect(vi.mocked(chatService.sendMessage).mock.lastCall?.[0]).not.toHaveProperty('source_document');

    store.dispatch(fetchCurrentUser.fulfilled({
      id: 'user', username: 'user', email: 'user@example.com', role: 'user', is_active: true,
    }, 'login', undefined));
    store.dispatch(addUserMessage(intake));
    await store.dispatch(sendMessage(intake));
    const intakeRequest = vi.mocked(chatService.sendMessage).mock.lastCall![0];
    expect(intakeRequest.expected_user_id).toBe('user');
    expect(intakeRequest.source_document).toEqual({ filename: doc.name });
    expect(intakeRequest.user_message).toBe(intake);
    expect(JSON.stringify(intakeRequest).split(doc.rawText)).toHaveLength(2);

    await store.dispatch(sendMessage('Save the log'));
    expect(vi.mocked(chatService.sendMessage).mock.lastCall?.[0]).toMatchObject({
      user_message: 'Save the log', message_history: [],
    });
  });

  it('preserves a guest draft on sign-in and clears it on account switch, including a late chat response', async () => {
    const store = configureStore({ reducer: rootReducer });
    const signIn = (id: string) => store.dispatch(fetchCurrentUser.fulfilled({
      id, username: id, email: `${id}@example.com`, is_active: true, role: 'user', created_at: '',
    }, 'login', undefined));
    store.dispatch(updateDocumentText('Guest draft'));
    signIn('first-user');
    expect(store.getState().document.currentDocument?.rawText).toBe('Guest draft');
    store.dispatch(addUserMessage('First user message'));
    let finish!: (value: Awaited<ReturnType<typeof chatService.sendMessage>>) => void;
    vi.mocked(chatService.sendMessage).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const inFlight = store.dispatch(sendMessage('First user message'));

    signIn('second-user');
    expect(store.getState().document.currentDocument).toBeNull();
    expect(store.getState().chat.messages).toEqual([]);
    finish({ success: true, message: '', data: {
      assistant_message: 'Old private draft', conversation_id: 'first-conversation',
      log_draft: { fields: { private_value: 'first-owner' } }, draft_changes: [],
      conversation_status: ConversationStatus.COLLECTING_INFORMATION,
    } });
    await inFlight;
    expect(store.getState().chat.conversationId).toBeNull();
    expect(store.getState().chat.error).toBeNull();
    expect(store.getState().chat.loading).toBe(false);
    expect(store.getState().log.currentLog).toBeNull();
    expect(store.getState().agent.executionTimeline).toEqual([]);
  });

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

    vi.mocked(chatService.sendMessage).mockResolvedValue(mockResponse);

    await store.dispatch(sendMessage('Process invoice'));

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
