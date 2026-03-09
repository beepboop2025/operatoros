import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { dashboardApi, complianceApi } from '../api/client';
import type {
  DashboardStats,
  ComplianceTask,
  ActivityItem,
  UpcomingTasksResponse,
  RecentActivityResponse,
} from '../api/client';
import {
  Users,
  CalendarCheck,
  AlertTriangle,
  MessageSquare,
  Plus,
  Upload,
  Calculator,
  Send,
  Clock,
  ArrowRight,
  FileText,
  CheckCircle2,
  XCircle,
  TrendingUp,
  LucideIcon,
} from 'lucide-react';
import { formatDate, formatCurrency } from '../utils/format';

interface StatCardProps {
  title: string;
  value: number | string | undefined;
  icon: LucideIcon;
  color: string;
  sub?: string;
}

function StatCard({ title, value, icon: Icon, color, sub }: StatCardProps) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
  };
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500 font-medium">{title}</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{value ?? '--'}</p>
          {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color] || colors.blue}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="skeleton w-24 h-4" />
          <div className="skeleton w-16 h-8" />
        </div>
        <div className="skeleton w-10 h-10 rounded-lg" />
      </div>
    </div>
  );
}

interface QuickAction {
  label: string;
  icon: LucideIcon;
  color: string;
  to: string;
}

export default function Dashboard() {
  const navigate = useNavigate();

  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: dashboardApi.stats,
  });

  const { data: upcoming } = useQuery<UpcomingTasksResponse | ComplianceTask[]>({
    queryKey: ['compliance', 'upcoming'],
    queryFn: () => complianceApi.getUpcoming(7),
  });

  const { data: activity } = useQuery<RecentActivityResponse | ActivityItem[]>({
    queryKey: ['dashboard', 'activity'],
    queryFn: dashboardApi.recentActivity,
  });

  const quickActions: QuickAction[] = [
    { label: 'New Client', icon: Plus, color: 'bg-blue-500 hover:bg-blue-600', to: '/clients' },
    { label: 'Upload Document', icon: Upload, color: 'bg-green-500 hover:bg-green-600', to: '/documents' },
    { label: 'Tax Calculator', icon: Calculator, color: 'bg-purple-500 hover:bg-purple-600', to: '/compute' },
    { label: 'Submit Query', icon: Send, color: 'bg-amber-500 hover:bg-amber-600', to: '/queries' },
  ];

  const urgencyColor = (days: number): string => {
    if (days < 0) return 'text-red-600 bg-red-50';
    if (days <= 2) return 'text-amber-600 bg-amber-50';
    return 'text-blue-600 bg-blue-50';
  };

  const activityIcon = (type: string | undefined): LucideIcon => {
    switch (type) {
      case 'query': return MessageSquare;
      case 'document': return FileText;
      case 'computation': return Calculator;
      case 'compliance': return CalendarCheck;
      default: return Clock;
    }
  };

  // Normalize upcoming data (API may return array or object with tasks key)
  const upcomingTasks: ComplianceTask[] = (() => {
    if (!upcoming) return [];
    if (Array.isArray(upcoming)) return upcoming;
    const obj = upcoming as UpcomingTasksResponse;
    return obj.tasks || [];
  })();

  // Normalize activity data
  const activityItems: ActivityItem[] = (() => {
    if (!activity) return [];
    if (Array.isArray(activity)) return activity;
    const obj = activity as RecentActivityResponse;
    return obj.items || [];
  })();

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">Welcome back. Here is your practice overview.</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <StatCard title="Total Clients" value={stats?.total_clients} icon={Users} color="blue" />
            <StatCard title="Active Tasks" value={stats?.active_tasks} icon={CalendarCheck} color="green" />
            <StatCard title="Overdue Tasks" value={stats?.overdue_tasks} icon={AlertTriangle} color="red" />
            <StatCard title="Queries Today" value={stats?.queries_today} icon={MessageSquare} color="purple" />
          </>
        )}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.label}
              onClick={() => navigate(action.to)}
              className={`${action.color} text-white rounded-xl p-4 flex flex-col items-center gap-2 text-sm font-medium transition-colors shadow-sm`}
            >
              <Icon className="w-5 h-5" />
              {action.label}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming deadlines */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">Upcoming Deadlines</h3>
            <button
              onClick={() => navigate('/compliance')}
              className="text-sm text-blue-500 hover:text-blue-600 flex items-center gap-1"
            >
              View All <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-slate-50">
            {upcomingTasks.length === 0 ? (
              <div className="px-5 py-8 text-center">
                <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No upcoming deadlines in the next 7 days</p>
              </div>
            ) : (
              upcomingTasks.slice(0, 6).map((task, i) => {
                const daysLeft = task.days_until_due ?? Math.ceil((new Date(task.due_date).getTime() - new Date().getTime()) / 86400000);
                return (
                  <div key={task.id || i} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50">
                    <div className={`px-2 py-1 rounded text-xs font-medium ${urgencyColor(daysLeft)}`}>
                      {daysLeft < 0 ? `${Math.abs(daysLeft)}d overdue` : daysLeft === 0 ? 'Due today' : `${daysLeft}d left`}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-700 truncate">{task.task_name || task.name}</p>
                      <p className="text-xs text-slate-400 truncate">{task.client_name || ''}</p>
                    </div>
                    <span className="text-xs text-slate-400">{formatDate(task.due_date)}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Recent activity */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-800">Recent Activity</h3>
          </div>
          <div className="divide-y divide-slate-50">
            {activityItems.length === 0 ? (
              <div className="px-5 py-8 text-center">
                <Clock className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No recent activity</p>
              </div>
            ) : (
              activityItems.slice(0, 6).map((item, i) => {
                const Icon = activityIcon(item.type);
                return (
                  <div key={item.id || i} className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50">
                    <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center">
                      <Icon className="w-4 h-4 text-slate-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-700 truncate">{item.description || item.title}</p>
                      <p className="text-xs text-slate-400">{item.client_name || ''}</p>
                    </div>
                    <span className="text-xs text-slate-400 whitespace-nowrap">
                      {item.time_ago || formatDate(item.created_at)}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
