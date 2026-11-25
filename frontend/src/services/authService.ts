import { apiClient } from './api';
import {
  AuthResponse,
  LoginCredentials,
  RegisterCredentials,
  ProfileUpdatePayload,
  UserProfile,
  PasswordResetCredentials,
} from '../types/auth';
import { APIResponse } from '../types/api';

export const authService = {
  /**
   * Log out: tells the backend to delete the httpOnly auth + CSRF cookies.
   * Idempotent — safe to call even when the session already expired.
   */
  async logout(): Promise<{ logout: boolean }> {
    const response = await apiClient.post<APIResponse<{ logout: boolean }>>(
      '/auth/logout'
    );
    return response.data.data;
  },

  /**
   * Register a new user profile.
   */
  async register(credentials: RegisterCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<APIResponse<AuthResponse>>(
      '/auth/register',
      credentials
    );
    return response.data.data;
  },

  /**
   * Log in an existing user with username/email and password.
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<APIResponse<AuthResponse>>(
      '/auth/login',
      credentials
    );
    return response.data.data;
  },

  /**
   * Change the authenticated user's password (previous password required).
   * The old unauthenticated "reset by email/username" call was an
   * account-takeover vector and has been removed server-side.
   */
  async resetPassword(credentials: PasswordResetCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<APIResponse<AuthResponse>>(
      '/auth/reset-password',
      credentials
    );
    return response.data.data;
  },

  /**
   * Permanently delete the currently authenticated user's account.
   */
  async deleteAccount(): Promise<{ deleted: boolean; username: string }> {
    const response = await apiClient.delete<APIResponse<{ deleted: boolean; username: string }>>(
      '/auth/account'
    );
    return response.data.data;
  },

  /**
   * Fetch current authenticated user's profile.
   */
  async getCurrentUser(signal?: AbortSignal): Promise<UserProfile> {
    const response = await apiClient.get<APIResponse<UserProfile>>('/auth/me', { signal });
    return response.data.data;
  },

  /**
   * Update the current authenticated user's profile.
   */
  async updateProfile(payload: ProfileUpdatePayload): Promise<UserProfile> {
    const response = await apiClient.put<APIResponse<UserProfile>>(
      '/auth/profile',
      payload
    );
    return response.data.data;
  },
};
