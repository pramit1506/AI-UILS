import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../../src/redux/authSlice';
import chatReducer from '../../src/redux/chatSlice';
import logReducer from '../../src/redux/logSlice';
import agentReducer from '../../src/redux/agentSlice';
import documentReducer from '../../src/redux/documentSlice';
import uiReducer from '../../src/redux/uiSlice';
import { AuthModal } from '../../src/components/Auth/AuthModal';
import { authService } from '../../src/services/authService';

vi.mock('../../src/services/authService', () => ({
  authService: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
  },
}));

function createTestStore(preloadedState?: any) {
  return configureStore({
    reducer: {
      auth: authReducer,
      chat: chatReducer,
      log: logReducer,
      agent: agentReducer,
      document: documentReducer,
      ui: uiReducer,
    },
    preloadedState,
  });
}

describe('AuthModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isAuthModalOpen is false', () => {
    const store = createTestStore({
      auth: {
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false,
        error: null,
        isAuthModalOpen: false,
        isProfileModalOpen: false,
        authModalTab: 'login',
      },
    });

    const { container } = render(
      <Provider store={store}>
        <AuthModal />
      </Provider>
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders Sign In tab and switches to Create Account tab', async () => {
    const store = createTestStore({
      auth: {
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false,
        error: null,
        isAuthModalOpen: true,
        isProfileModalOpen: false,
        authModalTab: 'login',
      },
    });

    render(
      <Provider store={store}>
        <AuthModal />
      </Provider>
    );

    // Should display Sign In view
    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByLabelText('Username or Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();

    // Click Create Account tab
    const registerTabBtn = screen.getByRole('button', { name: /create account/i });
    fireEvent.click(registerTabBtn);

    expect(screen.getByText('Create Your Account')).toBeInTheDocument();
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Username/i)).toBeInTheDocument();
  });

  it('displays instant demo profiles for quick user switching', () => {
    const store = createTestStore({
      auth: {
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false,
        error: null,
        isAuthModalOpen: true,
        isProfileModalOpen: false,
        authModalTab: 'login',
      },
    });

    render(
      <Provider store={store}>
        <AuthModal />
      </Provider>
    );

    expect(screen.getByText('Instant Demo Accounts')).toBeInTheDocument();
    expect(screen.getByText('Dr. Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('Alex Rivera')).toBeInTheDocument();
  });

  it('renders Forgot Password button and navigates to Reset Password form', () => {
    const store = createTestStore({
      auth: {
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false,
        error: null,
        successMessage: null,
        isAuthModalOpen: true,
        isProfileModalOpen: false,
        authModalTab: 'login',
      },
    });

    render(
      <Provider store={store}>
        <AuthModal />
      </Provider>
    );

    const forgotPwBtn = screen.getByRole('button', { name: /forgot password\?/i });
    expect(forgotPwBtn).toBeInTheDocument();
    fireEvent.click(forgotPwBtn);

    expect(screen.getByText('Reset Password')).toBeInTheDocument();
    expect(screen.getByLabelText(/Registered Email or Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^New Password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Confirm New Password/i)).toBeInTheDocument();
  });

  it('navigates to Delete Account recovery view', () => {
    const store = createTestStore({
      auth: {
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false,
        error: null,
        successMessage: null,
        isAuthModalOpen: true,
        isProfileModalOpen: false,
        authModalTab: 'reset-password',
      },
    });

    render(
      <Provider store={store}>
        <AuthModal />
      </Provider>
    );

    const wipeBtn = screen.getByRole('button', { name: /wipe \/ delete account instead/i });
    expect(wipeBtn).toBeInTheDocument();
    fireEvent.click(wipeBtn);

    expect(screen.getByText('Delete / Wipe Account')).toBeInTheDocument();
    expect(screen.getByLabelText(/Registered Email to Purge/i)).toBeInTheDocument();
  });
});
