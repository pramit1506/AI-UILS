import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import {
  UserProfile,
  AuthResponse,
  LoginCredentials,
  RegisterCredentials,
  ProfileUpdatePayload,
  PasswordResetCredentials,
} from '../types/auth';
import { authService } from '../services/authService';

export type AuthModalTab = 'login' | 'register' | 'reset-password' | 'delete-account';

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  successMessage: string | null;
  isAuthModalOpen: boolean;
  isProfileModalOpen: boolean;
  authModalTab: AuthModalTab;
}

function getStoredUser(): UserProfile | null {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      const raw = window.localStorage.getItem('auth_user');
      return raw ? JSON.parse(raw) : null;
    }
  } catch {
    // Ignore JSON parse or storage access issues
  }
  return null;
}

/**
 * One-time cleanup: older builds persisted the raw JWT in localStorage
 * ('auth_token'). The token now lives in an httpOnly cookie the browser
 * manages; drop any leftover key so an expired token never lingers.
 */
try {
  if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
    window.localStorage.removeItem('auth_token');
  }
} catch {
  // Ignore storage access issues
}

function setStoredUser(user: UserProfile | null) {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      if (user) {
        window.localStorage.setItem('auth_user', JSON.stringify(user));
      } else {
        window.localStorage.removeItem('auth_user');
      }
    }
  } catch {
    // Ignore storage write issues
  }
}

const initialUser = getStoredUser();

const initialState: AuthState = {
  user: initialUser,
  token: null, // JWT lives in the httpOnly cookie; never client-persisted
  isAuthenticated: Boolean(initialUser), // revalidated at boot via fetchCurrentUser
  loading: false,
  error: null,
  successMessage: null,
  isAuthModalOpen: false,
  isProfileModalOpen: false,
  authModalTab: 'login',
};

export const loginUser = createAsyncThunk<
  AuthResponse,
  LoginCredentials,
  { rejectValue: string }
>('auth/loginUser', async (credentials, { rejectWithValue }) => {
  try {
    const data = await authService.login(credentials);
    setStoredUser(data.user);
    return data;
  } catch (err) {
    return rejectWithValue((err instanceof Error && err.message) || 'Failed to login');
  }
});

export const registerUser = createAsyncThunk<
  AuthResponse,
  RegisterCredentials,
  { rejectValue: string }
>('auth/registerUser', async (credentials, { rejectWithValue }) => {
  try {
    const data = await authService.register(credentials);
    setStoredUser(data.user);
    return data;
  } catch (err) {
    return rejectWithValue((err instanceof Error && err.message) || 'Failed to register account');
  }
});

export const resetPassword = createAsyncThunk<
  AuthResponse,
  PasswordResetCredentials,
  { rejectValue: string }
>('auth/resetPassword', async (credentials, { rejectWithValue }) => {
  try {
    const data = await authService.resetPassword(credentials);
    setStoredUser(data.user);
    return data;
  } catch (err) {
    return rejectWithValue((err instanceof Error && err.message) || 'Failed to reset password');
  }
});

export const deleteAccount = createAsyncThunk<
  { deleted: boolean; username: string },
  void,
  { rejectValue: string }
>('auth/deleteAccount', async (_, { rejectWithValue }) => {
  try {
    const data = await authService.deleteAccount();
    setStoredUser(null);
    return data;
  } catch (err) {
    return rejectWithValue((err instanceof Error && err.message) || 'Failed to delete account');
  }
});

export const logoutUser = createAsyncThunk<
  void,
  void,
  { rejectValue: never }
>('auth/logoutUser', async () => {
  // Best-effort server logout — clears the httpOnly auth cookies. A network
  // failure must not block the local UI reset (they are retried never; cookies
  // expire on their own via Max-Age).
  try {
    await authService.logout();
  } catch {
    // ignore — local state is cleared regardless
  }
  setStoredUser(null);
});

export const fetchCurrentUser = createAsyncThunk<
  UserProfile,
  void,
  { rejectValue: string }
>('auth/fetchCurrentUser', async (_, { rejectWithValue, signal }) => {
  try {
    const user = await authService.getCurrentUser(signal);
    if (signal.aborted) return rejectWithValue('Session check superseded.');
    setStoredUser(user);
    return user;
  } catch (err) {
    return rejectWithValue((err instanceof Error && err.message) || 'Failed to fetch current user profile');
  }
});

export const updateUserProfile = createAsyncThunk<
  UserProfile,
  ProfileUpdatePayload,
  { rejectValue: string }
>('auth/updateUserProfile', async (payload, { rejectWithValue }) => {
  try {
    const updatedUser = await authService.updateProfile(payload);
    setStoredUser(updatedUser);
    return updatedUser;
  } catch (err) {
    return rejectWithValue((err instanceof Error && err.message) || 'Failed to update profile');
  }
});

/** Shared local reset for every logout path (reducer + thunk). */
function clearLocalAuth(state: AuthState) {
  setStoredUser(null);
  state.user = null;
  state.token = null;
  state.isAuthenticated = false;
  state.error = null;
  state.successMessage = null;
  state.isProfileModalOpen = false;
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    invalidateCachedSession: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.isProfileModalOpen = false;
    },
    logout: (state) => {
      clearLocalAuth(state);
    },
    openAuthModal: (
      state,
      action: PayloadAction<AuthModalTab | undefined>
    ) => {
      state.isAuthModalOpen = true;
      state.authModalTab = action.payload || 'login';
      state.error = null;
      state.successMessage = null;
    },
    closeAuthModal: (state) => {
      state.isAuthModalOpen = false;
      state.error = null;
      state.successMessage = null;
    },
    setAuthModalTab: (state, action: PayloadAction<AuthModalTab>) => {
      state.authModalTab = action.payload;
      state.error = null;
      state.successMessage = null;
    },
    openProfileModal: (state) => {
      state.isProfileModalOpen = true;
      state.error = null;
      state.successMessage = null;
    },
    closeProfileModal: (state) => {
      state.isProfileModalOpen = false;
      state.error = null;
      state.successMessage = null;
    },
    clearAuthError: (state) => {
      state.error = null;
    },
    setSuccessMessage: (state, action: PayloadAction<string | null>) => {
      state.successMessage = action.payload;
    },
  },
  extraReducers: (builder) => {
    // Login
    builder
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
        state.isAuthenticated = true;
        state.isAuthModalOpen = false;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Login failed';
      });

    // Register
    builder
      .addCase(registerUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
        state.isAuthenticated = true;
        state.isAuthModalOpen = false;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Registration failed';
      });

    // Reset Password
    builder
      .addCase(resetPassword.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(resetPassword.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.access_token;
        state.isAuthenticated = true;
        state.isAuthModalOpen = false;
        state.error = null;
        state.successMessage = 'Password reset successfully!';
      })
      .addCase(resetPassword.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Password reset failed';
      });

    // Delete Account (Authenticated)
    builder
      .addCase(deleteAccount.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteAccount.fulfilled, (state) => {
        state.loading = false;
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
        state.isProfileModalOpen = false;
        state.error = null;
        state.successMessage = 'Account deleted successfully.';
      })
      .addCase(deleteAccount.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Account deletion failed';
      });

    // Fetch Profile
    builder
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(fetchCurrentUser.rejected, (state, action) => {
        if (action.meta.aborted) return;
        // Cookie session is invalid/expired
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
      })

      // Server-aware logout (clears the httpOnly cookies backend-side)
      .addCase(logoutUser.fulfilled, (state) => {
        clearLocalAuth(state);
      })
      .addCase(logoutUser.rejected, (state) => {
        clearLocalAuth(state);
      });

    // Update Profile
    builder
      .addCase(updateUserProfile.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateUserProfile.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
        state.error = null;
      })
      .addCase(updateUserProfile.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Profile update failed';
      });
  },
});

export const {
  invalidateCachedSession,
  logout,
  openAuthModal,
  closeAuthModal,
  setAuthModalTab,
  openProfileModal,
  closeProfileModal,
  clearAuthError,
  setSuccessMessage,
} = authSlice.actions;

export default authSlice.reducer;
