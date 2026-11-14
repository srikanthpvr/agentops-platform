/**
 * src/hooks/useProjects.ts
 *
 * TanStack Query hook for fetching the authenticated user's projects list.
 * Automatically populates the projectStore on success.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useProjectStore } from '@/stores/projectStore';
import { useAuthStore } from '@/stores/authStore';

export const projectKeys = {
  all: ['projects'] as const,
  list: () => [...projectKeys.all, 'list'] as const,
  detail: (id: string) => [...projectKeys.all, 'detail', id] as const,
};

/**
 * Fetches all projects for the current user's org and syncs them into
 * the projectStore so other hooks / components can read the selection.
 */
export function useProjects() {
  const { isAuthenticated } = useAuthStore();
  const { setProjects } = useProjectStore();

  return useQuery({
    queryKey: projectKeys.list(),
    queryFn: async () => {
      const data = await api.projects.list();
      setProjects(data); // sync into Zustand
      return data;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60_000, // 5 min — project list changes infrequently
  });
}
