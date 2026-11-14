/**
 * src/components/layout/Header.tsx
 *
 * Top bar: breadcrumb, notifications, user dropdown.
 */

import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Bell, Settings, LogOut, User as UserIcon } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

// ─────────────────────────────────────────────────────────────────────────────
// Breadcrumb helper
// ─────────────────────────────────────────────────────────────────────────────

/** Convert a URL pathname to human-readable breadcrumb segments. */
function useBreadcrumbs(): string[] {
  const { pathname } = useLocation();
  if (pathname === '/') return ['Dashboard'];

  return pathname
    .split('/')
    .filter(Boolean)
    .map((segment) => {
      // If segment looks like a UUID, label it as an ID
      if (/^[0-9a-f-]{32,}$/i.test(segment)) return `#${segment.slice(0, 8)}…`;
      return segment.charAt(0).toUpperCase() + segment.slice(1);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function Header() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const breadcrumbs = useBreadcrumbs();

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
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4">
      {/* ── Breadcrumb ──────────────────────────────────────────────── */}
      <nav aria-label="Breadcrumb">
        <ol className="flex items-center gap-1.5 text-sm">
          {breadcrumbs.map((crumb, i) => (
            <React.Fragment key={i}>
              {i > 0 && (
                <span className="text-muted-foreground/50">/</span>
              )}
              <li
                className={
                  i === breadcrumbs.length - 1
                    ? 'font-medium text-foreground'
                    : 'text-muted-foreground'
                }
              >
                {crumb}
              </li>
            </React.Fragment>
          ))}
        </ol>
      </nav>

      {/* ── Right actions ───────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Notifications bell — placeholder count */}
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="h-4 w-4" />
          {/* Badge — show when there are unread notifications */}
          <span className="absolute right-1 top-1 flex h-2 w-2 items-center justify-center rounded-full bg-destructive text-[8px] text-white" />
        </Button>

        {/* User dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-md p-1 hover:bg-accent transition-colors">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="text-[10px]">{initials}</AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuLabel>
              <div>
                <p className="text-sm font-medium">{user?.full_name}</p>
                <p className="text-xs font-normal text-muted-foreground">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => navigate('/settings')}>
              <UserIcon className="h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => navigate('/settings')}>
              <Settings className="h-4 w-4" />
              Settings
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
    </header>
  );
}
