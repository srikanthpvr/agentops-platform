/**
 * src/stores/projectStore.ts
 *
 * Zustand store for the currently selected project context.
 * The currentProject drives which project's data is shown across the app.
 *
 * Usage:
 *   const { currentProject, setCurrentProject } = useProjectStore();
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { Project } from '@/types';

// ─────────────────────────────────────────────────────────────────────────────
// State interface
// ─────────────────────────────────────────────────────────────────────────────

interface ProjectState {
  /** The project that is currently selected in the sidebar. */
  currentProject: Project | null;
  /** All projects fetched for the authenticated user's org. */
  projects: Project[];

  // ── Actions ──────────────────────────────────────────────────────────────

  /** Replace the full projects list (e.g., after a fresh API fetch). */
  setProjects: (projects: Project[]) => void;

  /** Switch the active project context. */
  setCurrentProject: (project: Project) => void;

  /** Append a newly created project to the list (optimistic update). */
  addProject: (project: Project) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Store
// ─────────────────────────────────────────────────────────────────────────────

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      currentProject: null,
      projects: [],

      setProjects: (projects) =>
        set((state) => ({
          projects,
          // Auto-select the first project if none is currently set
          currentProject:
            state.currentProject ?? (projects.length > 0 ? projects[0] : null),
        })),

      setCurrentProject: (project) => set({ currentProject: project }),

      addProject: (project) =>
        set((state) => ({
          projects: [...state.projects, project],
          // If this is the first project, auto-select it
          currentProject: state.currentProject ?? project,
        })),
    }),
    {
      name: 'agentops_project',
      storage: createJSONStorage(() => localStorage),
      // Only persist the current project selection; the full list is always
      // re-fetched from the API on mount to avoid stale data.
      partialize: (state) => ({ currentProject: state.currentProject }),
    },
  ),
);
