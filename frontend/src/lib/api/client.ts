/**
 * HTTP client for FastAPI backend.
 *
 * Provides a configured axios instance with:
 * - Base URL from environment
 * - Timeout handling
 * - Centralized error handling
 * - JWT injection on every request (reads token from auth store)
 * - Automatic redirect to /auth on 401
 */

import axios, { type AxiosError, type AxiosInstance } from "axios";
import type { ApiError } from "@/types/domain";
import { clearAuth, getToken } from "@/lib/auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TIMEOUT = 30000; // 30 seconds

/**
 * Create and configure the axios instance.
 */
function createClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: TIMEOUT,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // ── Request interceptor: inject Bearer token ──────────────────────────────
  client.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
      config.headers = config.headers ?? {};
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  });

  // ── Response interceptor: error handling + 401 redirect ───────────────────
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      // On 401 clear local auth and redirect to /auth
      if (error.response?.status === 401) {
        clearAuth();
        // Use window.location so we don't need to import the router here
        // (avoids circular dependency with router.tsx)
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/auth")) {
          window.location.href = "/auth";
        }
      }

      // Transform axios errors into our ApiError format
      const apiError: ApiError = {
        message: error.message || "An unknown error occurred",
        code: error.code,
        status: error.response?.status,
      };

      if (error.response?.data && typeof error.response.data === "object") {
        const data = error.response.data as Record<string, unknown>;
        if (typeof data.detail === "string") {
          apiError.message = data.detail;
        } else if (typeof data.message === "string") {
          apiError.message = data.message;
        }
      }

      return Promise.reject(apiError);
    }
  );

  return client;
}

/**
 * Shared axios instance for all API calls.
 */
export const apiClient = createClient();

/**
 * Helper to check if an error is a 404 Not Found.
 */
export function isNotFoundError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    error.status === 404
  );
}

/**
 * Helper to extract filename from Content-Disposition header.
 */
export function extractFilename(contentDisposition: string | null): string {
  if (!contentDisposition) return "download";

  const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
  if (match && match[1]) {
    return match[1].replace(/['"]/g, "");
  }

  return "download";
}
