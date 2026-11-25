import { ToolExecutionEvent, ClarificationPayload, ToolExecutionResult, ClarificationState, DecisionOutput, ConversationStatus, ConversationMetadata } from './agent';
import { DynamicLogDraft, DraftStatus } from './log';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  tool_executions?: ToolExecutionEvent[];
  clarification_request?: ClarificationPayload;
}

export interface ChatRequest {
  action?: 'chat' | 'capture' | 'save_reviewed';
  excluded_fields?: string[];
  user_message: string;
  expected_user_id?: string;
  conversation_id?: string;
  message_history: { role: string; content: string }[];
  log_draft?: DynamicLogDraft;
  source_document?: { filename: string; text?: string };
}

export interface FieldChange {
  field_name: string;
  previous_value?: unknown;
  current_value?: unknown;
  change_type: string;
}

export interface ConversationResponse {
  extraction_used_fallback?: boolean;
  assistant_message: string;
  conversation_id: string;
  log_draft?: DynamicLogDraft;
  draft_status?: DraftStatus;
  draft_changes: FieldChange[];
  clarification_state?: ClarificationState;
  decision_output?: DecisionOutput;
  tool_execution_result?: ToolExecutionResult;
  conversation_status: ConversationStatus;
  conversation_metadata?: ConversationMetadata;
}
