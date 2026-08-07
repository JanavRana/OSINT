/**
 * Auth store backed by localStorage.
 *
 * Provides a thin read/write API so every module that needs the current
 * token or user goes through the same keys and never hard-codes them.
 */

import type { User } from "@/types/domain";

const TOKEN_KEY = "axiom_access_token";
const USER_KEY = "axiom_user";

// ── Token ─────────────────────────────────────────────────────────────────────

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignore — private-browsing quota errors */
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

// ── User ──────────────────────────────────────────────────────────────────────

export function getUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setUser(user: User): void {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    /* ignore */
  }
}

export function clearUser(): void {
  try {
    localStorage.removeItem(USER_KEY);
  } catch {
    /* ignore */
  }
}

// ── Combined ──────────────────────────────────────────────────────────────────

export function clearAuth(): void {
  clearToken();
  clearUser();
}

export function isAuthenticated(): boolean {
  return Boolean(getToken() && getUser());
}

/** Persist the full auth response (token + user) after login/verify-OTP. */
export function saveAuth(token: string, user: User): void {
  setToken(token);
  setUser(user);
}
