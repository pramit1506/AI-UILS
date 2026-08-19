import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import {
  UserProfile,
  AuthResponse,
  LoginCredentials,
  RegisterCredentials,
  ProfileUpdatePayload,
  PasswordResetCredentials,
  AccountDeletePayload,
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

function getStoredToken(): string | null {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      return window.localStorage.getItem('auth_token');
    }
  } catch {
    // Ignore storage access issues
  }
  return null;
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

function setStoredToken(token: string | null) {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage !== 'undefined') {
      if (token) {
        window.localStorage.setItem('auth_token', token);
      } else {
        window.localStorage.removeItem('auth_token');
      }
    }
  } catch {
    // Ignore storage write issues
  }
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

const initialToken = getStoredToken();
const initialUser = getStoredUser();

const initialState: AuthState = {
  user: initialUser,
  token: initialToken,
  isAuthenticated: Boolean(initialToken && initialUser),
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
    setStoredToken(data.access_token);
    setStoredUser(data.user);
    return data;
  } catch (err: any) {
    return rejectWithValue(err.message || 'Failed to login');
  }
});

export const registerUser = createAsyncThunk<
  AuthResponse,
  RegisterCredentials,
  { rejectValue: string }
>('auth/registerUser', async (credentials, { rejectWithValue }) => {
  try {
    const data = await authService.register(credentials);
    setStoredToken(data.access_token);
    setStoredUser(data.user);
    return data;
  } catch (err: any) {
    return rejectWithValue(err.message || 'Failed to register account');
  }
});

export const resetPassword = createAsyncThunk<
  AuthResponse,
  PasswordResetCredentials,
  { rejectValue: string }
>('auth/resetPassword', async (credentials, { rejectWithValue }) => {
  try {
    const data = await authService.resetPassword(credentials);
    setStoredToken(data.access_token);
    setStoredUser(data.user);
    return data;
  } catch (err: any) {
    return rejectWithValue(err.message || 'Failed to reset password');
  }
});

export const deleteAccount = createAsyncThunk<
  { deleted: boolean; username: string },
  void,
  { rejectValue: string }
>('auth/deleteAccount', async (_, { rejectWithValue }) => {
  try {
    const data = await authService.deleteAccount();
    setStoredToken(null);
    setStoredUser(null);
    return data;
  } catch (err: any) {
    return rejectWithValue(err.message || 'Failed to delete account');
  }
});

export const deleteAccountByEmail = createAsyncThunk<
  { deleted: boolean; email: string },
  AccountDeletePayload,
  { rejectValue: string }
>('auth/deleteAccountByEmail', async (payload, { rejectWithValue }) => {
  try {
    const data = await authService.deleteAccountByEmail(payload);
    return data;
  } catch (err: any) {
    return rejectWithValue(err.message || 'Failed to delete account');
  }
});

export const fetchCurrentUser = createAsyncThunk<
  UserProfile,
  void,
  { rejectValue: string }
>('auth/fetchCurrentUser', async (_, { rejectWithValue }) => {
  try {
    const user = await authService.getCurrentUser();
    setStoredUser(user);
    return user;
  } catch (err: any) {
    return rejectWithValue(err.message || 'Failed to fetch current user profile');
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
  } catch (err: any) {
    return rejectWithValue(err.message || 'Failed to update profile');
  }
});

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      setStoredToken(null);
      setStoredUser(null);
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.error = null;
      state.successMessage = null;
      state.isProfileModalOpen = false;
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

    // Delete Account by Email (Recovery)
    builder
      .addCase(deleteAccountByEmail.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteAccountByEmail.fulfilled, (state) => {
        state.loading = false;
        state.error = null;
        state.successMessage = 'Account has been removed. You can now create a fresh profile.';
        state.authModalTab = 'register';
      })
      .addCase(deleteAccountByEmail.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Account deletion failed';
      });

    // Fetch Profile
    builder
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(fetchCurrentUser.rejected, (state) => {
        // Token might have expired
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
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
