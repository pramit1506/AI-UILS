import { apiClient } from './api';
import {
  AuthResponse,
  LoginCredentials,
  RegisterCredentials,
  ProfileUpdatePayload,
  UserProfile,
  PasswordResetCredentials,
  AccountDeletePayload,
} from '../types/auth';
import { APIResponse } from '../types/api';

export const authService = {
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
   * Reset user password and obtain authenticated session.
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
   * Unauthenticated recovery deletion to purge a stuck account by email.
   */
  async deleteAccountByEmail(payload: AccountDeletePayload): Promise<{ deleted: boolean; email: string }> {
    const response = await apiClient.post<APIResponse<{ deleted: boolean; email: string }>>(
      '/auth/delete-account',
      payload
    );
    return response.data.data;
  },

  /**
   * Fetch current authenticated user's profile.
   */
  async getCurrentUser(): Promise<UserProfile> {
    const response = await apiClient.get<APIResponse<UserProfile>>('/auth/me');
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
