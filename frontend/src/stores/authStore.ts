/**
 * src/stores/authStore.ts
 *
 * Zustand store for authentication state.
 * Persists token + user to localStorage so sessions survive page refreshes.
 *
 * Usage:
 *   const { user, isAuthenticated, login, logout } = useAuthStore();
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from '@/types';

// ─────────────────────────────────────────────────────────────────────────────
// State interface
// ─────────────────────────────────────────────────────────────────────────────

interface AuthState {
  /** JWT access token — null when not authenticated */
  token: string | null;
  /** Authenticated user profile — null when not authenticated */
  user: User | null;
  /** Convenience flag derived from token presence */
  isAuthenticated: boolean;

  // ── Actions ──────────────────────────────────────────────────────────────

  /**
   * Persist a successful login: store the token + user profile.
   * Also writes the token to localStorage so the Axios interceptor can
   * read it without coupling to Zustand.
   */
  login: (token: string, user: User) => void;

  /** Clear all auth state and remove persisted data. */
  logout: () => void;

  /** Update the user profile (e.g., after a /me refresh). */
  setUser: (user: User) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Store
// ─────────────────────────────────────────────────────────────────────────────

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      login: (token, user) => {
        // Write token directly to localStorage so the Axios interceptor
        // (which reads localStorage) picks it up on the very next request.
        localStorage.setItem('agentops_token', token);
        set({ token, user, isAuthenticated: true });
      },

      logout: () => {
        localStorage.removeItem('agentops_token');
        set({ token: null, user: null, isAuthenticated: false });
      },

      setUser: (user) => set({ user }),
    }),
    {
      // Persist the entire auth slice under this key
      name: 'agentops_auth',
      storage: createJSONStorage(() => localStorage),
      // Only persist token + user; isAuthenticated is derived on rehydration
      partialize: (state) => ({ token: state.token, user: state.user }),
      // Re-derive isAuthenticated whenever the store is rehydrated from storage
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isAuthenticated = !!state.token;
          // Keep the raw localStorage key in sync for the Axios interceptor
          if (state.token) {
            localStorage.setItem('agentops_token', state.token);
          }
        }
      },
    },
  ),
);
