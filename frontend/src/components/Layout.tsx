import { useState, useEffect, ReactNode, useCallback } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  LayoutDashboard,
  Users,
  CalendarCheck,
  FileText,
  Calculator,
  MessageSquare,
  AlertTriangle,
  LogOut,
  Bell,
  Menu,
  X,
  ChevronDown,
  Shield,
  LucideIcon,
} from 'lucide-react';

interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
}

const navItems: NavItem[] = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/clients', icon: Users, label: 'Clients' },
  { to: '/compliance', icon: CalendarCheck, label: 'Compliance' },
  { to: '/documents', icon: FileText, label: 'Documents' },
  { to: '/compute', icon: Calculator, label: 'Tax Calculator' },
  { to: '/queries', icon: MessageSquare, label: 'AI Queries' },
  { to: '/notices', icon: AlertTriangle, label: 'Notices' },
];

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [userMenuOpen, setUserMenuOpen] = useState<boolean>(false);
  const location = useLocation();

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() || 'U';

  // ESC key to close menus
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      setUserMenuOpen(false);
      setSidebarOpen(false);
    }
  }, []);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="flex h-screen overflow-hidden bg-[#0f1219]">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-md lg:hidden animate-backdrop"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-[260px] flex flex-col
          bg-[#0c1017]/95 backdrop-blur-xl border-r border-white/[0.04]
          transform transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
          lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-white/[0.04]">
          <div className="w-9 h-9 gradient-brand rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20 glow-blue">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">AuditMind</h1>
            <p className="text-[10px] text-slate-500 uppercase tracking-[0.15em]">OperatorOS</p>
          </div>
          <button
            className="ml-auto lg:hidden text-slate-500 hover:text-white transition-colors"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {navItems.map((item, index) => {
            const Icon = item.icon;
            const isActive = item.to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium
                  transition-all duration-200 group relative
                  ${isActive
                    ? 'bg-blue-500/15 text-blue-400 shadow-lg shadow-blue-500/10'
                    : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200'
                  }
                `}
                style={{ animationDelay: `${index * 30}ms` }}
              >
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-blue-400 rounded-r-full shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                )}
                <Icon className={`w-[18px] h-[18px] shrink-0 transition-transform duration-200 group-hover:scale-110 ${isActive ? 'text-blue-400' : ''}`} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Sidebar footer */}
        <div className="p-4 border-t border-white/[0.04]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500/20 to-blue-600/20 border border-blue-500/20 rounded-full flex items-center justify-center text-xs font-bold text-blue-300">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate text-slate-200">{user?.name || user?.email || 'User'}</p>
              <p className="text-xs text-slate-500 truncate">{user?.role || 'CA Firm'}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-[#0f1219]/80 backdrop-blur-xl border-b border-white/[0.04] flex items-center justify-between px-4 lg:px-6 shrink-0">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden p-2 text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] rounded-xl transition-colors"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="w-5 h-5" />
            </button>
            <h2 className="text-[15px] font-semibold text-slate-200 hidden sm:block">
              {navItems.find((n) =>
                n.to === '/' ? location.pathname === '/' : location.pathname.startsWith(n.to)
              )?.label || 'AuditMind'}
            </h2>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Notification bell */}
            <button className="relative p-2 text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] rounded-xl transition-all">
              <Bell className="w-[18px] h-[18px]" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full notification-dot shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
            </button>

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 px-2 py-1.5 text-slate-300 hover:bg-white/[0.04] rounded-xl transition-all"
              >
                <div className="w-7 h-7 gradient-brand rounded-full flex items-center justify-center text-[11px] font-bold text-white shadow-md shadow-blue-500/20">
                  {initials}
                </div>
                <span className="hidden sm:inline text-[13px] font-medium">{user?.name || user?.email}</span>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-500 transition-transform duration-200 ${userMenuOpen ? 'rotate-180' : ''}`} />
              </button>
              {userMenuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                  <div className="absolute right-0 mt-2 w-52 bg-[#161b26]/95 backdrop-blur-xl border border-white/[0.08] rounded-xl shadow-2xl shadow-black/40 z-50 py-1 animate-scale-in overflow-hidden">
                    <div className="px-4 py-2.5 border-b border-white/[0.04]">
                      <p className="text-sm font-medium text-slate-200">{user?.name || 'User'}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{user?.email}</p>
                    </div>
                    <button
                      onClick={() => { setUserMenuOpen(false); logout(); }}
                      className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign Out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <div className="animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
