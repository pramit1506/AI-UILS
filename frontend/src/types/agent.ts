export type ToolStatus = 'idle' | 'executing' | 'success' | 'error';

export interface TimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  description?: string;
  status: ToolStatus;
}

export interface ClarificationPayload {
  required: boolean;
  question?: string;
  field_name?: string;
}

export interface ToolExecutionEvent {
  tool_name: string;
  status: ToolStatus;
  input?: unknown;
  result?: unknown;
  error?: string;
}

// Backend Schemas

export enum ConversationStatus {
  COLLECTING_INFORMATION = "COLLECTING_INFORMATION",
  AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION",
  READY_FOR_EXECUTION = "READY_FOR_EXECUTION",
  EXECUTING_TOOL = "EXECUTING_TOOL",
  COMPLETED = "COMPLETED"
}

export interface ToolExecutionResult {
  tool_name?: string;
  status: string;
  created_resource_id?: string;
  success_message?: string;
  validation_warnings?: string[];
}

export interface ClarificationState {
  tool_name: string;
  required_fields: string[];
  missing_fields: string[];
  resolved_fields: Record<string, unknown>;
  clarification_reason?: string;
  original_request: string;
  status?: string;
  is_active: boolean;
}

export interface DecisionOutput {
  reset_context?: boolean;
  action: string;
  tool_readiness: string;
  selected_tool?: string;
  clarification_message?: string;
  clarification_reason?: string;
  required_missing_fields: string[];
  optional_missing_fields: string[];
  decision_confidence: number;
  next_state: string;
}

export interface ConversationMetadata {
  /** Canonical per-conversation turn/message counter (see backend) */
  message_count?: number;
  estimated_tokens?: number;
  last_activity?: string;
  last_tool?: string;
  active_schema?: string;
  active_log_reference?: string;
  active_log_id?: string;
  clarification_state_status?: string | null;
  current_log_start_idx?: number;
  awaiting_new_log_decision?: boolean;
}

export interface AgentState {
  graphExecutionId: string | null;
  selectedTool: string | null;
  toolStatus: ToolStatus;
  clarificationRequired: ClarificationPayload | null;
  currentStep: string | null;
  executionTimeline: TimelineEvent[];
  lastToolResult: unknown;
  conversationStatus?: ConversationStatus;
}
