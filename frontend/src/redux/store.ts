import { combineReducers, configureStore, type UnknownAction } from '@reduxjs/toolkit';
import logReducer, { clearLog } from './logSlice';
import chatReducer, { clearChat } from './chatSlice';
import agentReducer, { clearAgentState } from './agentSlice';
import documentReducer, { clearDocument } from './documentSlice';
import authReducer from './authSlice';
import uiReducer from './uiSlice';

const appReducer = combineReducers({
  log: logReducer,
  chat: chatReducer,
  agent: agentReducer,
  document: documentReducer,
  auth: authReducer,
  ui: uiReducer,
});

export type RootState = ReturnType<typeof appReducer>;

export function rootReducer(state: RootState | undefined, action: UnknownAction): RootState {
  const next = appReducer(state, action);
  const previousOwner = state?.auth.user?.id;
  if (!previousOwner || previousOwner === next.auth.user?.id) return next;

  // A guest can carry a draft into their first login. A signed-in workspace
  // belongs to its owner, including the in-flight chat and upload responses.
  return {
    ...next,
    chat: chatReducer(next.chat, clearChat()),
    log: logReducer(next.log, clearLog()),
    document: documentReducer(next.document, clearDocument()),
    agent: agentReducer(next.agent, clearAgentState()),
  };
}

export const store = configureStore({ reducer: rootReducer });
let previewUrl = store.getState().document.fileObjectUrl;
store.subscribe(() => {
  const currentUrl = store.getState().document.fileObjectUrl;
  if (previewUrl && previewUrl !== currentUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = currentUrl;
});

export type AppDispatch = typeof store.dispatch;
