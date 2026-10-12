import { Link, Outlet, useLocation } from '@tanstack/react-router';
import {
  Building2,
  Calendar,
  Clock,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Stethoscope,
  UserCog,
  Users,
  X,
} from 'lucide-react';
import React from 'react';
import { useAuthStore } from '@/lib/auth-store';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  {
    href: '/today',
    label: 'Today',
    icon: LayoutDashboard,
    roles: ['ADMIN', 'RECEPTIONIST'] as const,
  },
  {
    href: '/appointments',
    label: 'Appointments',
    icon: Calendar,
    roles: ['ADMIN', 'RECEPTIONIST', 'DENTIST'] as const,
  },
  {
    href: '/patients',
    label: 'Patients',
    icon: Users,
    roles: ['ADMIN', 'RECEPTIONIST', 'DENTIST'] as const,
  },
  {
    href: '/services',
    label: 'Services',
    icon: Package,
    roles: ['ADMIN', 'RECEPTIONIST', 'DENTIST'] as const,
  },
  {
    href: '/provider-schedules',
    label: 'Provider Schedules',
    icon: Clock,
    roles: ['ADMIN', 'RECEPTIONIST', 'DENTIST'] as const,
  },
  { href: '/my-schedule', label: 'My Schedule', icon: Stethoscope, roles: ['DENTIST'] as const },
  { href: '/staff', label: 'Staff', icon: UserCog, roles: ['ADMIN'] as const },
] as const;

export function RootLayout() {
  const { user, clearAuth } = useAuthStore();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const filteredNav = NAV_ITEMS.filter((item) =>
    user ? (item.roles as readonly string[]).includes(user.role) : false
  );

  if (!user) {
    return <Outlet />;
  }

  const isActive = (href: string) =>
    location.pathname === href || location.pathname.startsWith(`${href}/`);

  return (
    <div className="min-h-screen bg-bg-canvas">
      {/* Mobile header */}
      <header className="lg:hidden bg-bg-card border-b border-border-subtle sticky top-0 z-40">
        <div className="flex items-center justify-between p-4">
          <Link
            to="/today"
            className="flex items-center gap-2 text-brand-primary font-bold text-lg"
          >
            <Building2 className="w-6 h-6" />
            <span>Raven Dental</span>
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg hover:bg-bg-elevated transition-colors"
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
        {mobileMenuOpen && (
          <nav className="px-4 pb-4 space-y-1 border-t border-border-subtle">
            {filteredNav.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive(item.href)
                    ? 'bg-brand-primary text-brand-on-primary'
                    : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary'
                )}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {item.label}
              </Link>
            ))}
            <hr className="border-border-subtle my-2" />
            <button
              onClick={() => clearAuth()}
              className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-text-secondary hover:bg-bg-elevated hover:text-status-error transition-colors"
            >
              <LogOut className="w-5 h-5" />
              Sign Out
            </button>
          </nav>
        )}
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={cn(
            'hidden lg:flex lg:flex-col h-screen fixed lg:static w-64 bg-bg-card border-r border-border-subtle transition-all duration-200 z-30',
            'flex-col'
          )}
        >
          <div className="flex flex-col h-full">
            {/* Brand */}
            <Link
              to="/today"
              className="flex items-center gap-2 px-6 py-5 border-b border-border-subtle text-brand-primary font-bold text-lg"
            >
              <Building2 className="w-7 h-7" />
              <span>Raven Dental</span>
            </Link>

            {/* Navigation */}
            <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
              {filteredNav.map((item) => (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive(item.href)
                      ? 'bg-brand-primary text-brand-on-primary'
                      : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary'
                  )}
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  {item.label}
                </Link>
              ))}
            </nav>

            {/* User info & sign out */}
            <div className="p-4 border-t border-border-subtle">
              <div className="flex items-center gap-3 px-3 py-2">
                <div className="w-8 h-8 rounded-full bg-brand-primary/10 flex items-center justify-center">
                  <UserCog className="w-5 h-5 text-brand-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{user.fullName}</p>
                  <p className="text-xs text-text-muted capitalize">{user.role.toLowerCase()}</p>
                </div>
              </div>
              <button
                onClick={() => clearAuth()}
                className="mt-3 w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-text-secondary hover:bg-bg-elevated hover:text-status-error transition-colors"
              >
                <LogOut className="w-5 h-5" />
                Sign Out
              </button>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 lg:ml-64 min-h-screen">
          <div className="p-4 lg:p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
