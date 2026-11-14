/**
 * src/components/layout/AppShell.tsx
 *
 * Authenticated application shell: Sidebar + Header + main content area.
 * Manages the sidebar collapsed/expanded state.
 * On mobile (<768px) the sidebar is hidden and a hamburger button appears.
 */

import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { Toaster } from '@/components/ui/toaster';
import { useProjects } from '@/hooks/useProjects';

export function AppShell() {
  // Persist sidebar collapse preference in state (could move to localStorage)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Fetch projects on mount so the sidebar project selector is populated
  useProjects();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* ── Sidebar ───────────────────────────────────────────────────── */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((c) => !c)}
      />

      {/* ── Main area ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 animate-fade-in">
          {/* React Router outlet renders the matched child route here */}
          <Outlet />
        </main>
      </div>

      {/* ── Global toast notifications ────────────────────────────────── */}
      <Toaster />
    </div>
  );
}
