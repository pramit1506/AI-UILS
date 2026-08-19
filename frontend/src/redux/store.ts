import { configureStore } from '@reduxjs/toolkit';
import uiReducer from './uiSlice';
import logReducer from './logSlice';
import chatReducer from './chatSlice';
import agentReducer from './agentSlice';
import documentReducer from './documentSlice';
import authReducer from './authSlice';

export const store = configureStore({
  reducer: {
    ui: uiReducer,
    log: logReducer,
    chat: chatReducer,
    agent: agentReducer,
    document: documentReducer,
    auth: authReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
