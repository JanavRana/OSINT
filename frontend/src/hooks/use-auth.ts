/**
 * Auth hooks — thin wrappers around the DataProvider auth methods.
 *
 * All hooks follow the existing `useMutation` pattern so they expose
 * `isPending`, `error`, `mutate`, and `reset` without pages needing
 * to manage that state themselves.
 */

import { useCallback, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { getDataProvider } from "@/lib/api/data-provider";
import { clearAuth, getUser } from "@/lib/auth";
import type { ApiError, User } from "@/types/domain";

// ── Generic mutation primitive (mirrors use-osint-data.ts) ───────────────────

function useMutation<TInput, TOutput>(
  fn: (input: TInput) => Promise<TOutput>
) {
  const [data, setData] = useState<TOutput | undefined>(undefined);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const mutate = useCallback(
    async (input: TInput) => {
      setIsPending(true);
      setError(null);
      try {
        const result = await fn(input);
        setData(result);
        setIsPending(false);
        return result;
      } catch (err) {
        const message =
          (err as ApiError)?.message ||
          (err instanceof Error ? err.message : null) ||
          "An unexpected error occurred.";
        const apiErr: ApiError = {
          message: message.startsWith("Request failed with status code")
            ? "Authentication error. Please check your credentials."
            : message,
          status: (err as ApiError)?.status,
          code: (err as ApiError)?.code,
        };
        setError(apiErr);
        setIsPending(false);
        throw err;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [fn]
  );

  const reset = useCallback(() => {
    setData(undefined);
    setError(null);
    setIsPending(false);
  }, []);

  return { data, isPending, error, mutate, reset };
}

// ── Auth mutations ───────────────────────────────────────────────────────────

export function useSignup() {
  return useMutation<
    { email: string; fullName: string; password: string },
    User
  >(({ email, fullName, password }) =>
    getDataProvider().signup(email, fullName, password)
  );
}

export function useVerifyOtp() {
  return useMutation<
    { email: string; otp: string },
    { token: string; user: User }
  >(({ email, otp }) => getDataProvider().verifyOtp(email, otp));
}

export function useLogin() {
  return useMutation<
    { email: string; password: string },
    { token: string; user: User }
  >(({ email, password }) => getDataProvider().login(email, password));
}

export function useResendOtp() {
  return useMutation<{ email: string }, void>(({ email }) =>
    getDataProvider().resendOtp(email)
  );
}

export function useLogout() {
  const navigate = useNavigate();
  return useCallback(async () => {
    await getDataProvider().logout();
    clearAuth();
    navigate({ to: "/auth" });
  }, [navigate]);
}

/** Returns the current user from localStorage (no HTTP call). */
export function useCurrentUser(): User | null {
  return getUser();
}
