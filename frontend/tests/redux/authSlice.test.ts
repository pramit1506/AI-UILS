import { describe, it, expect, beforeEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import authReducer, {
  logout,
  logoutUser,
  openAuthModal,
  closeAuthModal,
  setAuthModalTab,
  openProfileModal,
  closeProfileModal,
  loginUser,
  registerUser,
  resetPassword,
  deleteAccount,
  updateUserProfile,
} from '../../src/redux/authSlice';
import * as authSliceModule from '../../src/redux/authSlice';
import { UserProfile } from '../../src/types/auth';

describe('authSlice Redux operations', () => {
  const mockUser: UserProfile = {
    id: 'user-1234',
    email: 'dr.jane@hospital.org',
    username: 'dr_jane',
    full_name: 'Dr. Jane Smith',
    role: 'Quality Assurance',
    avatar_url: null,
    bio: 'Lead QMS Auditor',
    is_active: true,
    created_at: '2026-08-19T20:00:00Z',
  };

  beforeEach(() => {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.clear();
    }
  });

  it('initializes with default unauthenticated state if storage is empty', () => {
    const state = authReducer(undefined, { type: '@@INIT' });
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isAuthModalOpen).toBe(false);
  });

  it('handles modal open, close, and tab switching', () => {
    let state = authReducer(undefined, openAuthModal('register'));
    expect(state.isAuthModalOpen).toBe(true);
    expect(state.authModalTab).toBe('register');

    state = authReducer(state, setAuthModalTab('login'));
    expect(state.authModalTab).toBe('login');

    state = authReducer(state, setAuthModalTab('reset-password'));
    expect(state.authModalTab).toBe('reset-password');

    state = authReducer(state, closeAuthModal());
    expect(state.isAuthModalOpen).toBe(false);

    state = authReducer(state, openProfileModal());
    expect(state.isProfileModalOpen).toBe(true);

    state = authReducer(state, closeProfileModal());
    expect(state.isProfileModalOpen).toBe(false);
  });

  it('handles loginUser.fulfilled', () => {
    const state = authReducer(
      undefined,
      loginUser.fulfilled(
        { access_token: 'jwt-mock-token', token_type: 'bearer', user: mockUser },
        'req-1',
        { login: 'dr_jane', password: 'password123' }
      )
    );

    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.username).toBe('dr_jane');
    expect(state.token).toBe('jwt-mock-token');
    expect(state.isAuthModalOpen).toBe(false);
  });

  it('handles registerUser.fulfilled', () => {
    const state = authReducer(
      undefined,
      registerUser.fulfilled(
        { access_token: 'jwt-register-token', token_type: 'bearer', user: mockUser },
        'req-2',
        {
          email: 'dr.jane@hospital.org',
          username: 'dr_jane',
          password: 'password123',
        }
      )
    );

    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe('dr.jane@hospital.org');
    expect(state.token).toBe('jwt-register-token');
    expect(state.isAuthModalOpen).toBe(false);
  });

  it('handles resetPassword.fulfilled', () => {
    const state = authReducer(
      undefined,
      resetPassword.fulfilled(
        { access_token: 'jwt-reset-token', token_type: 'bearer', user: mockUser },
        'req-reset',
        {
          current_password: 'old_password123',
          new_password: 'new_password123',
        }
      )
    );

    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.username).toBe('dr_jane');
    expect(state.token).toBe('jwt-reset-token');
    expect(state.isAuthModalOpen).toBe(false);
    expect(state.successMessage).toBe('Password reset successfully!');
  });

  it('handles deleteAccount.fulfilled', () => {
    const state = authReducer(
      {
        user: mockUser,
        token: 'sample-token',
        isAuthenticated: true,
        loading: false,
        error: null,
        successMessage: null,
        isAuthModalOpen: false,
        isProfileModalOpen: true,
        authModalTab: 'login',
      },
      deleteAccount.fulfilled({ deleted: true, username: 'dr_jane' }, 'req-del', undefined)
    );

    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isProfileModalOpen).toBe(false);
    expect(state.successMessage).toBe('Account deleted successfully.');
  });

  it('no longer exports deleteAccountByEmail (insecure endpoint removed)', () => {
    // The unauthenticated by-email deletion endpoint was a critical
    // vulnerability; the thunk was removed along with the endpoint.
    // If someone reintroduces it, this test fails and forces a review.
    const exported = Object.keys(authSliceModule);
    expect(exported).not.toContain('deleteAccountByEmail');
  });

  it('handles updateUserProfile.fulfilled', () => {
    const updatedUser = { ...mockUser, full_name: 'Dr. Jane Walker-Smith', bio: 'VP of QMS' };
    const state = authReducer(
      {
        user: mockUser,
        token: 'token',
        isAuthenticated: true,
        loading: false,
        error: null,
        successMessage: null,
        isAuthModalOpen: false,
        isProfileModalOpen: true,
        authModalTab: 'login',
      },
      updateUserProfile.fulfilled(updatedUser, 'req-3', {
        full_name: 'Dr. Jane Walker-Smith',
        bio: 'VP of QMS',
      })
    );

    expect(state.user?.full_name).toBe('Dr. Jane Walker-Smith');
    expect(state.user?.bio).toBe('VP of QMS');
  });

  it('handles logoutUser.fulfilled and clears the profile cache', async () => {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem('auth_user', JSON.stringify(mockUser));
    }

    const store = configureStore({ reducer: { auth: authReducer } });
    store.dispatch(logoutUser.fulfilled(undefined, 'req-logout'));

    const state = store.getState().auth;
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    if (typeof window !== 'undefined' && window.localStorage) {
      // The JWT itself is never client-readable (httpOnly cookie), so only
      // the profile cache is cleared.
      expect(window.localStorage.getItem('auth_user')).toBeNull();
      expect(window.localStorage.getItem('auth_token')).toBeNull();
    }
  });

  it('handles logout and resets user credentials', () => {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem('auth_user', JSON.stringify(mockUser));
    }

    const state = authReducer(
      {
        user: mockUser,
        token: 'sample-token',
        isAuthenticated: true,
        loading: false,
        error: null,
        successMessage: null,
        isAuthModalOpen: false,
        isProfileModalOpen: false,
        authModalTab: 'login',
      },
      logout()
    );

    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    if (typeof window !== 'undefined' && window.localStorage) {
      expect(window.localStorage.getItem('auth_token')).toBeNull();
    }
  });
});
