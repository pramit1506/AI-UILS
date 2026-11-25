import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import chatReducer from '../../src/redux/chatSlice';
import logReducer from '../../src/redux/logSlice';
import agentReducer from '../../src/redux/agentSlice';
import documentReducer from '../../src/redux/documentSlice';
import { ChatPanel } from '../../src/components/Chat/ChatPanel';

// Mock scrollToBottom behavior
window.HTMLElement.prototype.scrollIntoView = vi.fn();

const renderWithRedux = (
  component: React.ReactElement,
  preloadedState?: Partial<import("../../src/redux/store").RootState>
) => {
  const store = configureStore({
    reducer: {
      chat: chatReducer,
      log: logReducer,
      agent: agentReducer,
      document: documentReducer,
    },
    preloadedState,
  });
  return render(<Provider store={store}>{component}</Provider>);
};

describe('ChatPanel Component', () => {
  it('renders EmptyState initially', () => {
    renderWithRedux(<ChatPanel />);
    expect(screen.getByText('Add a document')).toBeInTheDocument();
  });

  it('dispatches message when sending', () => {
    renderWithRedux(<ChatPanel />);
    const input = screen.getByPlaceholderText('Message the AI or drop a file…');
    const form = input.closest('form');

    fireEvent.change(input, { target: { value: 'Test message' } });
    if (form) {
      fireEvent.submit(form);
    }

    // The message should appear in the panel
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });
});
