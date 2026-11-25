import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../../src/redux/authSlice';
import chatReducer from '../../src/redux/chatSlice';
import logReducer from '../../src/redux/logSlice';
import agentReducer from '../../src/redux/agentSlice';
import documentReducer from '../../src/redux/documentSlice';
import { AuthModal } from '../../src/components/Auth/AuthModal';
import { apiClient } from '../../src/services/api';

vi.mock('../../src/services/authService', () => ({
  authService: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
  },
}));

function createTestStore(preloadedState?: Partial<import("../../src/redux/store").RootState>) {
  return configureStore({
    reducer: {
      auth: authReducer,
      chat: chatReducer,
      log: logReducer,
      agent: agentReducer,
      document: documentReducer,
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

    expect(screen.getByText('Trial account and data')).toBeInTheDocument();
    expect(screen.getByText('Dr. Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('Alex Rivera')).toBeInTheDocument();
  });

  it('recovers a signed-out account using an emailed code', async () => {
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

    expect(screen.getByLabelText('Account email')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Email me a code' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /back to sign in/i })).toBeInTheDocument();

    // The old reset form fields must not appear for unauthenticated users.
    expect(screen.queryByLabelText(/Current Password/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/New Password/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Confirm New Password/i)).not.toBeInTheDocument();
    const post = vi.spyOn(apiClient, 'post')
      .mockResolvedValueOnce({ data: { message: 'Check your email.' } })
      .mockResolvedValueOnce({ data: { message: 'Password updated.' } });
    try {
      fireEvent.change(screen.getByLabelText('Account email'), { target: { value: 'owner@example.org' } });
      fireEvent.click(screen.getByRole('button', { name: 'Email me a code' }));
      fireEvent.change(await screen.findByLabelText('Six-digit code'), { target: { value: '012345' } });
      fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'updated-pass' } });
      fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'updated-pass' } });
      fireEvent.click(screen.getByRole('button', { name: 'Reset password' }));
      expect(await screen.findByText('Your password has been updated.')).toBeVisible();
      expect(post).toHaveBeenLastCalledWith('/auth/recovery/confirm', { email: 'owner@example.org', code: '012345', new_password: 'updated-pass' });
    } finally {
      post.mockRestore();
    }
  });

  it('Delete Account view shows the sign-in-required notice instead of a purge form', () => {
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
        authModalTab: 'delete-account',
      },
    });

    render(
      <Provider store={store}>
        <AuthModal />
      </Provider>
    );

    // The unauthenticated by-email deletion form was a critical vulnerability;
    // it was replaced with a notice pointing to Profile → Delete Account.
    expect(screen.getByText('Delete Account')).toBeInTheDocument();
    expect(screen.getByText('Sign in required')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /back to sign in/i })).toBeInTheDocument();

    // The old purge form must not be rendered.
    expect(screen.queryByLabelText(/Email to Purge/i)).not.toBeInTheDocument();
  });
});
