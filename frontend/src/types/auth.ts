export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  role: string;
  avatar_url?: string | null;
  bio?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface LoginCredentials {
  login: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  bio?: string;
  avatar_url?: string;
  role?: string;
}

export interface ProfileUpdatePayload {
  full_name?: string;
  username?: string;
  bio?: string;
  avatar_url?: string;
}

export interface PasswordResetCredentials {
  login: string;
  new_password: string;
}

export interface AccountDeletePayload {
  email: string;
  confirm_text?: string;
}
