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
  TrendingUp,
  LucideIcon,
} from 'lucide-react';
import { formatDate } from '../utils/format';

interface StatCardProps {
  title: string;
  value: number | string | undefined;
  icon: LucideIcon;
  gradient: string;
  iconColor: string;
  sub?: string;
}

function StatCard({ title, value, icon: Icon, gradient, iconColor, sub }: StatCardProps) {
  return (
    <div className={`rounded-xl p-5 ${gradient} transition-all hover:shadow-md`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[13px] text-stone-500 font-medium">{title}</p>
          <p className="text-2xl font-bold text-stone-800 mt-1">{value ?? '--'}</p>
          {sub && <p className="text-xs text-stone-400 mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconColor}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-stone-200 p-5">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="skeleton w-24 h-4" />
          <div className="skeleton w-16 h-8" />
        </div>
        <div className="skeleton w-10 h-10 rounded-xl" />
      </div>
    </div>
  );
}

interface QuickAction {
  label: string;
  icon: LucideIcon;
  gradient: string;
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
    { label: 'New Client', icon: Plus, gradient: 'gradient-brand', to: '/clients' },
    { label: 'Upload Document', icon: Upload, gradient: 'bg-emerald-500 hover:bg-emerald-600', to: '/documents' },
    { label: 'Tax Calculator', icon: Calculator, gradient: 'bg-violet-500 hover:bg-violet-600', to: '/compute' },
    { label: 'AI Query', icon: Send, gradient: 'bg-amber-500 hover:bg-amber-600', to: '/queries' },
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

  // Normalize data (API may return array or object)
  const upcomingTasks: ComplianceTask[] = (() => {
    if (!upcoming) return [];
    if (Array.isArray(upcoming)) return upcoming;
    return (upcoming as UpcomingTasksResponse).tasks || [];
  })();

  const activityItems: ActivityItem[] = (() => {
    if (!activity) return [];
    if (Array.isArray(activity)) return activity;
    return (activity as RecentActivityResponse).items || [];
  })();

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-stone-800">Dashboard</h1>
        <p className="text-sm text-stone-500 mt-1">Welcome back. Here is your practice overview.</p>
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
            <StatCard title="Total Clients" value={stats?.total_clients} icon={Users} gradient="stat-blue border border-blue-100" iconColor="bg-blue-500 text-white" />
            <StatCard title="Active Tasks" value={stats?.active_tasks} icon={CalendarCheck} gradient="stat-green border border-green-100" iconColor="bg-emerald-500 text-white" />
            <StatCard title="Overdue Tasks" value={stats?.overdue_tasks} icon={AlertTriangle} gradient="stat-red border border-red-100" iconColor="bg-red-500 text-white" />
            <StatCard title="Queries Today" value={stats?.queries_today} icon={MessageSquare} gradient="stat-purple border border-purple-100" iconColor="bg-violet-500 text-white" />
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
              className={`${action.gradient} text-white rounded-xl p-4 flex flex-col items-center gap-2 text-sm font-medium transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5`}
            >
              <Icon className="w-5 h-5" />
              {action.label}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming deadlines */}
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-stone-100 flex items-center justify-between">
            <h3 className="font-semibold text-stone-800 text-[15px]">Upcoming Deadlines</h3>
            <button
              onClick={() => navigate('/compliance')}
              className="text-[13px] text-blue-500 hover:text-blue-600 flex items-center gap-1 font-medium"
            >
              View All <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-stone-50">
            {upcomingTasks.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                <p className="text-sm text-stone-500">No upcoming deadlines in the next 7 days</p>
              </div>
            ) : (
              upcomingTasks.slice(0, 6).map((task) => {
                const daysLeft = task.days_until_due ?? Math.ceil((new Date(task.due_date).getTime() - new Date().getTime()) / 86400000);
                return (
                  <div key={task.id} className="px-5 py-3 flex items-center gap-3 hover:bg-stone-50 transition-colors">
                    <div className={`px-2 py-1 rounded-lg text-xs font-semibold ${urgencyColor(daysLeft)}`}>
                      {daysLeft < 0 ? `${Math.abs(daysLeft)}d overdue` : daysLeft === 0 ? 'Due today' : `${daysLeft}d left`}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-stone-700 truncate">{task.task_name || task.name}</p>
                      <p className="text-xs text-stone-400 truncate">{task.client_name || ''}</p>
                    </div>
                    <span className="text-xs text-stone-400">{formatDate(task.due_date)}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Recent activity */}
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-stone-100">
            <h3 className="font-semibold text-stone-800 text-[15px]">Recent Activity</h3>
          </div>
          <div className="divide-y divide-stone-50">
            {activityItems.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <Clock className="w-8 h-8 text-stone-300 mx-auto mb-2" />
                <p className="text-sm text-stone-500">No recent activity</p>
              </div>
            ) : (
              activityItems.slice(0, 6).map((item) => {
                const Icon = activityIcon(item.type);
                return (
                  <div key={item.id || item.created_at} className="px-5 py-3 flex items-center gap-3 hover:bg-stone-50 transition-colors">
                    <div className="w-8 h-8 bg-stone-100 rounded-lg flex items-center justify-center">
                      <Icon className="w-4 h-4 text-stone-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-stone-700 truncate">{item.description || item.title}</p>
                      <p className="text-xs text-stone-400">{item.client_name || ''}</p>
                    </div>
                    <span className="text-xs text-stone-400 whitespace-nowrap">
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
