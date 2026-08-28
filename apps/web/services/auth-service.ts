import { fetchApi } from '../lib/api-client';
import { AuthResponse, User } from '../types';

export const authService = {
  async register(data: { email: string; password: string; first_name?: string; last_name?: string }): Promise<User> {
    return fetchApi<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    return fetchApi<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async getCurrentUser(): Promise<any> {
    return fetchApi<any>('/auth/me');
  },

  async logout(): Promise<void> {
    await fetchApi<{ status: string }>('/auth/logout', { method: 'POST' });
  },

  async verifyEmail(token: string): Promise<void> {
    await fetchApi<{ status: string }>('/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  },

  async requestPasswordReset(email: string): Promise<void> {
    await fetchApi<{ status: string }>('/auth/password-reset/request', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  async confirmPasswordReset(token: string, new_password: string): Promise<void> {
    await fetchApi<{ status: string }>('/auth/password-reset/confirm', {
      method: 'POST',
      body: JSON.stringify({ token, new_password }),
    });
  },
};
