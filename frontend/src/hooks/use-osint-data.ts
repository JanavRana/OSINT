// Thin data-fetching hooks that isolate pages from the provider.
//
// The current provider resolves synchronously from local fixtures, so hooks
// hydrate immediately and preserve the existing zero-flash UX. Swap in an
// HTTP-backed `DataProvider` and these same hooks will begin exposing
// meaningful `isLoading` / `error` states without any page change — pages
// already render `<LoadingState/>`, `<EmptyState/>`, `<ErrorState/>`.

import { useCallback, useEffect, useState } from "react";
import { getDataProvider } from "@/lib/api/data-provider";
import type {
  ApiError,
  AsyncResource,
  Connector,
  DashboardStat,
  ExecutionResult,
  GeneratedReport,
  GraphData,
  Identifier,
  IdentifierType,
  IdentityProfile,
  Investigation,
  MutationResource,
  NewInvestigationInput,
  Report,
  ReportDownload,
  TimelineEvent,
} from "@/types/domain";

function useResource<T>(
  loader: () => Promise<T>,
  deps: ReadonlyArray<unknown>,
): AsyncResource<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const run = useCallback(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    loader()
      .then((value) => {
        if (cancelled) return;
        setData(value);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError({
          message: err instanceof Error ? err.message : "Unknown error",
        });
        setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  return { data, isLoading, error, refetch: run };
}

export function useInvestigations(): AsyncResource<Investigation[]> {
  return useResource(() => getDataProvider().listInvestigations(), []);
}

export function useInvestigation(id: string): AsyncResource<Investigation | undefined> {
  return useResource(() => getDataProvider().getInvestigation(id), [id]);
}

export function useIdentifiers(
  investigationId?: string,
): AsyncResource<Identifier[]> {
  return useResource(
    () => getDataProvider().listIdentifiers(investigationId),
    [investigationId],
  );
}

export function useConnectors(
  investigationId?: string,
): AsyncResource<Connector[]> {
  return useResource(
    () => getDataProvider().listConnectors(investigationId),
    [investigationId],
  );
}

export function useTimeline(
  investigationId?: string,
): AsyncResource<TimelineEvent[]> {
  return useResource(
    () => getDataProvider().listTimeline(investigationId),
    [investigationId],
  );
}

export function useReports(investigationId?: string): AsyncResource<Report[]> {
  return useResource(
    () => getDataProvider().listReports(investigationId),
    [investigationId],
  );
}

export function useDashboardStats(): AsyncResource<DashboardStat[]> {
  return useResource(() => getDataProvider().getDashboardStats(), []);
}

export function useIdentityProfile(
  subjectId?: string,
): AsyncResource<IdentityProfile> {
  return useResource(
    () => getDataProvider().getIdentityProfile(subjectId),
    [subjectId],
  );
}

export function useGraph(investigationId?: string): AsyncResource<GraphData> {
  return useResource(
    () => getDataProvider().getGraph(investigationId),
    [investigationId],
  );
}

// ---- Mutations -------------------------------------------------------------
// Small mutation primitive so pages don't need to hand-roll pending/error
// tracking around write operations. Signature intentionally matches a subset
// of React Query's `useMutation` so a future migration is mechanical.

function useMutation<TInput, TOutput>(
  fn: (input: TInput) => Promise<TOutput>,
): MutationResource<TInput, TOutput> {
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
        const apiErr: ApiError = {
          message: err instanceof Error ? err.message : "Unknown error",
        };
        setError(apiErr);
        setIsPending(false);
        throw err;
      }
    },
    [fn],
  );

  const reset = useCallback(() => {
    setData(undefined);
    setError(null);
    setIsPending(false);
  }, []);

  return { data, isPending, error, mutate, reset };
}

export function useCreateInvestigation() {
  return useMutation<NewInvestigationInput, Investigation>((input) =>
    getDataProvider().createInvestigation(input),
  );
}

export function useExecuteInvestigation() {
  return useMutation<
    { investigationId: string; identifier: { value: string; type: IdentifierType } },
    ExecutionResult
  >(({ investigationId, identifier }) =>
    getDataProvider().executeInvestigation(investigationId, identifier),
  );
}

export function useGenerateReport() {
  return useMutation<string, GeneratedReport>((investigationId) =>
    getDataProvider().generateReport(investigationId),
  );
}

export function useDownloadReport() {
  return useMutation<
    { investigationId: string; reportId?: string },
    ReportDownload
  >(({ investigationId, reportId }) =>
    getDataProvider().downloadReport(investigationId, reportId),
  );
}

