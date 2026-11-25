import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ChatMessage, ChatRequest, ConversationResponse } from '../types/chat';
import { chatService } from '../services/chatService';
import { RootState } from './store';
import { conversationMapper } from '../services/conversationMapper';
import { setClarificationRequired, setToolExecutionResult, setConversationStatus } from './agentSlice';
import { setLog, markLogSaved } from './logSlice';
import { openGuestSaveWall } from './uiSlice';
import { clearDocument } from './documentSlice';

/** Message ID generator — the previous `Date.now().toString()` collided when
 * multiple messages were created in the same millisecond (double-click sends,
 * rapid confirm flows), producing duplicate React keys. */
let messageIdCounter = 0;
function generateMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  messageIdCounter += 1;
  return `${Date.now().toString()}-${messageIdCounter}-${Math.random().toString(36).slice(2, 8)}`;
}

interface ChatState {
  workspaceRevision: number;
  activeRequestId: string | null;
  messages: ChatMessage[];
  conversationId: string | null;
  loading: boolean;
  error: string | null;
  extractionUsedFallback?: boolean;
  /** ISO timestamp of when the first message of this session was sent */
  sessionStartedAt: string | null;
}

const initialState: ChatState = {
  workspaceRevision: 0,
  activeRequestId: null,
  messages: [],
  conversationId: null,
  loading: false,
  error: null,
  sessionStartedAt: null,
};

export const sendMessage = createAsyncThunk<
  ConversationResponse,
  string | { message: string; action: 'capture' | 'save_reviewed' },
  { state: RootState }
>(
  'chat/sendMessage',
  async (input, { getState, dispatch, rejectWithValue, requestId }) => {
    try {
      const message = typeof input === 'string' ? input : input.message;
      const state = getState();
      const doc = state.document?.currentDocument;
      const isDocumentMessage = !!doc && (message === doc.rawText ||
        (message.startsWith('Process this uploaded document (') &&
          message === `Process this uploaded document (${doc.name}):\n\n${doc.rawText}`));
      const request: ChatRequest = {
        action: typeof input === 'string' ? 'chat' : input.action,
        excluded_fields: Object.keys(state.log.fieldStatuses).filter(key => state.log.fieldStatuses[key] === 'rejected'),
        user_message: message,
        expected_user_id: state.auth?.isAuthenticated ? state.auth.user?.id : undefined,
        conversation_id: state.chat.conversationId || undefined,
        // The backend already owns the conversation history.
        message_history: [],
        log_draft: typeof input === 'object' && input.action === 'capture' ? undefined : state.log.currentLog || undefined,
      };
      if (doc?.rawText && state.auth?.isAuthenticated) {
        request.source_document = isDocumentMessage
          ? { filename: doc.name }
          : { filename: doc.name, text: doc.rawText };
      }

      const response = await chatService.sendMessage(request);
      if (getState().chat.activeRequestId !== requestId) {
        return rejectWithValue('This conversation has changed.');
      }
      const data = response.data;
      if (request.action === 'save_reviewed' && data.tool_execution_result?.status !== 'success') {
        return rejectWithValue(data.assistant_message || 'Could not save the record.');
      }

      // Use the centralized mapper
      const mapped = conversationMapper.mapResponse(data);
      if (doc && !isDocumentMessage && data.decision_output?.reset_context &&
          getState().document?.currentDocument?.id === doc.id) {
        dispatch(clearDocument());
      }

      // Dispatch mapped data to agentSlice
      dispatch(setClarificationRequired(mapped.clarificationRequired));
      if (mapped.toolExecution) {
        dispatch(setToolExecutionResult(mapped.toolExecution));
      }
      dispatch(setConversationStatus(mapped.conversationStatus));

      // Dispatch mapped data to logSlice
      if (request.action !== 'save_reviewed') dispatch(setLog({
        draft: mapped.logDraft,
        updatedFields: mapped.updatedFields,
        newDocument: request.action === 'capture' || data.decision_output?.reset_context,
      }));

      // A successful save_log tool execution pins the returned log reference
      // so every Save button switches to "Saved" and can't duplicate the
      // record. Applied AFTER setLog so the draft re-send in the same
      // response can't reset it.
      if (
        mapped.toolExecution &&
        mapped.toolExecution.tool_name === 'save_log' &&
        mapped.toolExecution.status === 'success'
      ) {
        const match = /LOG-[A-Z0-9]+/i.exec(
          String(mapped.toolExecution.result ?? '')
        );
        const currentLog = getState().log;
        if (request.action !== 'save_reviewed' || (currentLog.currentLog === state.log.currentLog &&
            currentLog.fieldStatuses === state.log.fieldStatuses && currentLog.sessionName === state.log.sessionName)) {
          dispatch(markLogSaved(match ? match[0].toUpperCase() : null));
        }
      }

      // Guest wall (AI path): a signed-out user who asks the AI in chat to
      // save hits the backend refusal ("Login required to save..."). Raise
      // the same modal here so the outcome is unmistakable — the guest keeps
      // the draft, but saving needs an account. (? — test stores may omit
      // slices, so read defensively.)
      if (!getState().auth?.isAuthenticated && mapped.toolExecution?.tool_name === 'save_log') {
        dispatch(openGuestSaveWall());
      }

      return data;
    } catch (error) {
      return rejectWithValue((error instanceof Error && error.message) || 'Failed to send message');
    }
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addUserMessage: (state, action: PayloadAction<string>) => {
      // Record the session start time on the very first message
      if (!state.sessionStartedAt) {
        state.sessionStartedAt = new Date().toISOString();
      }
      state.messages.push({
        id: generateMessageId(),
        role: 'user',
        content: action.payload,
        timestamp: new Date().toISOString()
      });
    },
    clearChat: (state) => {
      state.workspaceRevision += 1;
      state.activeRequestId = null;
      state.loading = false;
      state.messages = [];
      state.conversationId = null;
      state.error = null;
      state.sessionStartedAt = null;
      state.extractionUsedFallback = false;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.activeRequestId = action.meta.requestId;
        state.loading = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        if (state.activeRequestId !== action.meta.requestId) return;
        state.activeRequestId = null;
        state.loading = false;

        const mapped = conversationMapper.mapResponse(action.payload);

        if (action.payload.extraction_used_fallback || (typeof action.meta.arg !== 'string' && action.meta.arg.action === 'capture')) {
          state.extractionUsedFallback = action.payload.extraction_used_fallback ?? false;
        }

        state.conversationId = mapped.conversationId;
        state.messages.push({
          id: generateMessageId(),
          role: 'assistant',
          content: mapped.assistantMessage,
          timestamp: new Date().toISOString(),
          tool_executions: mapped.toolExecution ? [mapped.toolExecution] : undefined,
          clarification_request: mapped.clarificationRequired || undefined
        });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        if (state.activeRequestId !== action.meta.requestId) return;
        state.activeRequestId = null;
        state.loading = false;
        state.error = action.payload as string;
      });
  }
});

export const { addUserMessage, clearChat } = chatSlice.actions;
export default chatSlice.reducer;
