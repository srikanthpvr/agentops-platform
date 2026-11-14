/**
 * src/components/layout/Sidebar.tsx
 *
 * Left navigation sidebar with icons, active state, and collapsible support.
 * When collapsed, only icons are shown with Tailwind title tooltips.
 */

import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  FlaskConical,
  Shield,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';
import { useProjectStore } from '@/stores/projectStore';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

// ─────────────────────────────────────────────────────────────────────────────
// Nav items definition
// ─────────────────────────────────────────────────────────────────────────────

interface NavItem {
  label: string;
  to: string;
  icon: React.ElementType;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard },
  { label: 'Traces', to: '/traces', icon: Activity },
  { label: 'Evaluations', to: '/evaluations', icon: FlaskConical },
  { label: 'Governance', to: '/governance', icon: Shield },
  { label: 'Settings', to: '/settings', icon: Settings },
];

// ─────────────────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────────────────

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { currentProject, projects, setCurrentProject } = useProjectStore();

  /** Get initials from a full name for the avatar fallback. */
  const initials = user?.full_name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) ?? '??';

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r border-border bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* ── Brand ─────────────────────────────────────────────────────── */}
      <div
        className={cn(
          'flex h-14 items-center border-b border-border px-4',
          collapsed ? 'justify-center' : 'justify-between',
        )}
      >
        {!collapsed && (
          <span className="text-sm font-bold tracking-tight text-foreground">
            🤖 AgentOps
          </span>
        )}
        <button
          onClick={onToggle}
          className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* ── Project selector ──────────────────────────────────────────── */}
      <div className="border-b border-border p-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm',
                'hover:bg-accent hover:text-accent-foreground transition-colors',
                collapsed && 'justify-center',
              )}
              title={collapsed ? currentProject?.name ?? 'Select project' : undefined}
            >
              <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
              {!collapsed && (
                <>
                  <span className="flex-1 truncate text-left text-xs font-medium">
                    {currentProject?.name ?? 'Select project'}
                  </span>
                  <ChevronDown className="h-3 w-3 text-muted-foreground" />
                </>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            {projects.length === 0 ? (
              <DropdownMenuItem disabled>No projects yet</DropdownMenuItem>
            ) : (
              projects.map((p) => (
                <DropdownMenuItem
                  key={p.id}
                  onSelect={() => setCurrentProject(p)}
                  className={cn(p.id === currentProject?.id && 'bg-accent')}
                >
                  {p.name}
                </DropdownMenuItem>
              ))
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => navigate('/settings')}>
              Manage projects
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* ── Nav items ─────────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto p-2">
        <ul className="space-y-0.5">
          {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                title={collapsed ? label : undefined}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    collapsed && 'justify-center',
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span>{label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* ── User section ──────────────────────────────────────────────── */}
      <div className="border-t border-border p-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent transition-colors',
                collapsed && 'justify-center',
              )}
            >
              <Avatar className="h-7 w-7 shrink-0">
                <AvatarFallback className="text-[10px]">{initials}</AvatarFallback>
              </Avatar>
              {!collapsed && (
                <div className="flex-1 overflow-hidden text-left">
                  <p className="truncate text-xs font-medium">{user?.full_name}</p>
                  <p className="truncate text-[11px] text-muted-foreground">{user?.email}</p>
                </div>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            <DropdownMenuItem onSelect={() => navigate('/settings')}>
              Profile & Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={handleLogout}
              className="text-destructive focus:text-destructive"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  );
}
