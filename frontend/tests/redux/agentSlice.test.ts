import { describe, it, expect } from 'vitest';
import agentReducer, {
  setToolExecutionStart,
  setToolExecutionResult,
  setClarificationRequired
} from '../../src/redux/agentSlice';

describe('agentSlice', () => {
  const initialState = {
    graphExecutionId: null,
    selectedTool: null,
    toolStatus: 'idle' as const,
    clarificationRequired: null,
    currentStep: null,
    executionTimeline: [],
    lastToolResult: null,
  };

  it('should handle setToolExecutionStart', () => {
    const action = setToolExecutionStart({ toolName: 'UpdateCRM' });
    const state = agentReducer(initialState, action);
    
    expect(state.selectedTool).toBe('UpdateCRM');
    expect(state.toolStatus).toBe('executing');
    expect(state.executionTimeline.length).toBe(1);
    expect(state.executionTimeline[0].title).toBe('Executing UpdateCRM');
    expect(state.executionTimeline[0].status).toBe('executing');
  });

  it('should handle setToolExecutionResult', () => {
    // Set executing state first
    let state = agentReducer(initialState, setToolExecutionStart({ toolName: 'UpdateCRM' }));
    
    const resultAction = setToolExecutionResult({
      tool_name: 'UpdateCRM',
      status: 'success',
      result: { success: true }
    });
    
    state = agentReducer(state, resultAction);
    
    expect(state.toolStatus).toBe('success');
    expect(state.lastToolResult).toEqual({ success: true });
    expect(state.executionTimeline[0].status).toBe('success');
  });

  it('should handle setClarificationRequired', () => {
    const payload = {
      required: true,
      question: 'Which HCP?',
      options: ['Dr. Smith', 'Dr. Jones']
    };
    
    const state = agentReducer(initialState, setClarificationRequired(payload));
    
    expect(state.clarificationRequired).toEqual(payload);
  });
});
