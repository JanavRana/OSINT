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

function formatApiErrorMessage(error: AxiosError): string {
  const status = error.response?.status;
  const data = error.response?.data as Record<string, unknown> | undefined;

  // 1. Check if backend returned detail or message string
  if (data) {
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail.trim();
    }
    if (typeof data.message === "string" && data.message.trim()) {
      return data.message.trim();
    }
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (first && typeof first === "object" && typeof first.msg === "string") {
        return first.msg;
      }
    }
  }

  // 2. Map status codes to human-readable explanations
  if (status === 401) {
    return "Incorrect email or password. Please check your credentials.";
  }
  if (status === 409) {
    return "An account with this email address already exists. Please log in instead.";
  }
  if (status === 403) {
    return "Access forbidden. Email is unverified or your account lacks permissions.";
  }
  if (status === 404) {
    return "The requested record or user account was not found.";
  }
  if (status === 422) {
    return "Validation error. Please check your input form fields.";
  }
  if (status === 429) {
    return "Too many requests. Please wait a moment before trying again.";
  }
  if (status && status >= 500) {
    return "Server error. Please try again later or contact support.";
  }

  if (error.message && !error.message.startsWith("Request failed with status code")) {
    return error.message;
  }

  return "An unexpected error occurred. Please check your connection.";
}

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
      // On 401 clear local auth and redirect to /auth ONLY if not on /auth page
      if (error.response?.status === 401) {
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/auth")) {
          clearAuth();
          window.location.href = "/auth";
        }
      }

      // Transform axios errors into clean human-readable ApiError format
      const apiError: ApiError = {
        message: formatApiErrorMessage(error),
        code: error.code,
        status: error.response?.status,
      };

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
