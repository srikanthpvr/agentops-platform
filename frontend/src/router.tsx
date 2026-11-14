import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { AppShell } from '@/components/layout/AppShell';

// Pages
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { TracesPage } from '@/pages/TracesPage';
import { TraceDetailPage } from '@/pages/TraceDetailPage';
import { EvaluationsPage } from '@/pages/EvaluationsPage';
import { GovernancePage } from '@/pages/GovernancePage';
import { SettingsPage } from '@/pages/SettingsPage';

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, token } = useAuthStore();
  const hasToken = isAuthenticated || !!token || !!localStorage.getItem('agentops_token');

  if (!hasToken) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <AppShell />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'traces',
        element: <TracesPage />,
      },
      {
        path: 'traces/:traceId',
        element: <TraceDetailPage />,
      },
      {
        path: 'evaluations',
        element: <EvaluationsPage />,
      },
      {
        path: 'governance',
        element: <GovernancePage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
