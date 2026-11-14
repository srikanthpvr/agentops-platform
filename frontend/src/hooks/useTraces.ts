/**
 * src/hooks/useTraces.ts
 *
 * TanStack Query hooks for fetching trace data.
 * Separates data-fetching concerns from UI components.
 */

import { useQuery } from '@tanstack/react-query';
import { api, type TraceListParams } from '@/lib/api';
import { useProjectStore } from '@/stores/projectStore';

// ─────────────────────────────────────────────────────────────────────────────
// Query keys — centralised so invalidation is consistent
// ─────────────────────────────────────────────────────────────────────────────

export const traceKeys = {
  all: ['traces'] as const,
  lists: () => [...traceKeys.all, 'list'] as const,
  list: (params: TraceListParams) => [...traceKeys.lists(), params] as const,
  details: () => [...traceKeys.all, 'detail'] as const,
  detail: (id: string) => [...traceKeys.details(), id] as const,
  stats: (projectId: string, days: number) =>
    [...traceKeys.all, 'stats', projectId, days] as const,
};

// ─────────────────────────────────────────────────────────────────────────────
// Hooks
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Paginated list of traces for the current project.
 * Re-fetches whenever the filter params change.
 */
export function useTraces(params: Omit<TraceListParams, 'project_id'> = {}) {
  const { currentProject } = useProjectStore();

  return useQuery({
    queryKey: traceKeys.list({ ...params, project_id: currentProject?.id }),
    queryFn: () =>
      api.traces.list({ ...params, project_id: currentProject?.id }),
    // Don't fire until a project is selected
    enabled: !!currentProject?.id,
    // Keep previous data visible while new page loads (better UX)
    placeholderData: (prev) => prev,
    staleTime: 30_000, // 30 s — traces data is not highly volatile
  });
}

/**
 * Single trace with full span tree.
 */
export function useTrace(traceId: string | undefined) {
  return useQuery({
    queryKey: traceKeys.detail(traceId ?? ''),
    queryFn: () => api.traces.get(traceId!),
    enabled: !!traceId,
    staleTime: 60_000,
  });
}

/**
 * Aggregate dashboard stats for the current project.
 * @param days Number of days to aggregate over (default 30).
 */
export function useTraceStats(days = 30) {
  const { currentProject } = useProjectStore();

  return useQuery({
    queryKey: traceKeys.stats(currentProject?.id ?? '', days),
    queryFn: () => api.traces.stats(currentProject!.id, days),
    enabled: !!currentProject?.id,
    staleTime: 60_000,
    // Return zeros while loading so dashboard cards always render
    placeholderData: {
      total_traces: 0,
      total_tokens: 0,
      total_cost_usd: 0,
      error_rate: 0,
      daily_counts: [],
    },
  });
}
