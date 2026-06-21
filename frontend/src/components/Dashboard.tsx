import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { dashboardApi, complianceApi } from '../api/client';
import type {
  DashboardStats,
  ComplianceTask,
  ActivityItem,
  UpcomingTasksResponse,
  RecentActivityResponse,
  WorkloadResponse,
  TeamMemberWorkload,
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
  BarChart3,
  LucideIcon,
} from 'lucide-react';
import { formatDate } from '../utils/format';
import { SkeletonCard } from './Skeleton';

interface StatCardProps {
  title: string;
  value: number | string | undefined;
  icon: LucideIcon;
  gradient: string;
  iconColor: string;
  glowClass: string;
  sub?: string;
  delay: number;
}

function StatCard({ title, value, icon: Icon, gradient, iconColor, glowClass, sub, delay }: StatCardProps) {
  return (
    <div
      className={`rounded-xl p-5 ${gradient} card-interactive`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between animate-stagger-1" style={{ animationDelay: `${delay}ms` }}>
        <div>
          <p className="text-[13px] text-slate-400 font-medium">{title}</p>
          <p className="text-2xl font-bold text-slate-100 mt-1 animate-count">{value ?? '--'}</p>
          {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconColor} ${glowClass}`}>
          <Icon className="w-5 h-5" />
        </div>
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

  const { data: workload } = useQuery<WorkloadResponse>({
    queryKey: ['dashboard', 'workload'],
    queryFn: dashboardApi.workload,
  });

  const quickActions: QuickAction[] = [
    { label: 'New Client', icon: Plus, gradient: 'gradient-brand', to: '/clients' },
    { label: 'Upload Document', icon: Upload, gradient: 'bg-emerald-500 hover:bg-emerald-600', to: '/documents' },
    { label: 'Tax Calculator', icon: Calculator, gradient: 'bg-violet-500 hover:bg-violet-600', to: '/compute' },
    { label: 'AI Query', icon: Send, gradient: 'bg-amber-500 hover:bg-amber-600', to: '/queries' },
  ];

  const urgencyColor = (days: number): string => {
    if (days < 0) return 'text-red-400 bg-red-500/10 border border-red-500/20';
    if (days <= 2) return 'text-amber-400 bg-amber-500/10 border border-amber-500/20';
    return 'text-blue-400 bg-blue-500/10 border border-blue-500/20';
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
      <div className="animate-stagger-1">
        <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-400 mt-1">Welcome back. Here is your practice overview.</p>
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
            <div className="animate-stagger-1">
              <StatCard title="Total Clients" value={stats?.total_clients} icon={Users} gradient="stat-blue" iconColor="bg-blue-500/20 text-blue-400" glowClass="glow-blue" delay={50} />
            </div>
            <div className="animate-stagger-2">
              <StatCard title="Active Tasks" value={stats?.active_tasks} icon={CalendarCheck} gradient="stat-green" iconColor="bg-emerald-500/20 text-emerald-400" glowClass="glow-green" delay={100} />
            </div>
            <div className="animate-stagger-3">
              <StatCard title="Overdue Tasks" value={stats?.overdue_tasks} icon={AlertTriangle} gradient="stat-red" iconColor="bg-red-500/20 text-red-400" glowClass="glow-red" delay={150} />
            </div>
            <div className="animate-stagger-4">
              <StatCard title="Queries Today" value={stats?.queries_today} icon={MessageSquare} gradient="stat-purple" iconColor="bg-violet-500/20 text-violet-400" glowClass="glow-purple" delay={200} />
            </div>
          </>
        )}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {quickActions.map((action, i) => {
          const Icon = action.icon;
          return (
            <button
              key={action.label}
              onClick={() => navigate(action.to)}
              className={`animate-stagger-${i + 3} ${action.gradient} text-white rounded-xl p-4 flex flex-col items-center gap-2 text-sm font-medium shadow-lg hover:shadow-xl hover-lift transition-all`}
            >
              <Icon className="w-5 h-5" />
              {action.label}
            </button>
          );
        })}
      </div>

      {/* Workload distribution */}
      {workload?.team && workload.team.length > 0 && (
        <div className="card overflow-hidden animate-stagger-5">
          <div className="px-5 py-4 border-b border-white/[0.04] flex items-center justify-between">
            <h3 className="font-semibold text-slate-200 text-[15px] flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-violet-400" /> Team Workload
            </h3>
          </div>
          <div className="p-5">
            <div className="space-y-3">
              {workload.team.slice(0, 8).map((member: TeamMemberWorkload, i: number) => {
                const maxTasks = Math.max(...workload.team.map((m: TeamMemberWorkload) => m.total_tasks), 1);
                const barWidth = Math.max((member.total_tasks / maxTasks) * 100, 2);
                return (
                  <div key={member.user_id} className="animate-row" style={{ animationDelay: `${i * 40}ms` }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-slate-300 font-medium truncate max-w-[180px]">{member.name}</span>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span>{member.completed} done</span>
                        <span>{member.pending} pending</span>
                        {member.overdue > 0 && (
                          <span className="text-red-400">{member.overdue} overdue</span>
                        )}
                      </div>
                    </div>
                    <div className="h-2 bg-slate-800/50 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${barWidth}%`,
                          background: member.overdue > 0
                            ? 'linear-gradient(90deg, #ef4444 0%, #f59e0b 100%)'
                            : 'linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%)',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming deadlines */}
        <div className="card overflow-hidden animate-stagger-5">
          <div className="px-5 py-4 border-b border-white/[0.04] flex items-center justify-between">
            <h3 className="font-semibold text-slate-200 text-[15px]">Upcoming Deadlines</h3>
            <button
              onClick={() => navigate('/compliance')}
              className="text-[13px] text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium transition-colors"
            >
              View All <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-white/[0.03]">
            {upcomingTasks.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <CheckCircle2 className="w-8 h-8 text-emerald-500/50 mx-auto mb-2" />
                <p className="text-sm text-slate-400">No upcoming deadlines in the next 7 days</p>
              </div>
            ) : (
              upcomingTasks.slice(0, 6).map((task, i) => {
                const daysLeft = task.days_until_due ?? Math.ceil((new Date(task.due_date).getTime() - new Date().getTime()) / 86400000);
                return (
                  <div
                    key={task.id}
                    className="px-5 py-3 flex items-center gap-3 row-hover transition-colors animate-row"
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    <div className={`px-2 py-1 rounded-lg text-xs font-semibold ${urgencyColor(daysLeft)}`}>
                      {daysLeft < 0 ? `${Math.abs(daysLeft)}d overdue` : daysLeft === 0 ? 'Due today' : `${daysLeft}d left`}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">{task.task_name || task.name}</p>
                      <p className="text-xs text-slate-500 truncate">{task.client_name || ''}</p>
                    </div>
                    <span className="text-xs text-slate-500">{formatDate(task.due_date)}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Recent activity */}
        <div className="card overflow-hidden animate-stagger-6">
          <div className="px-5 py-4 border-b border-white/[0.04]">
            <h3 className="font-semibold text-slate-200 text-[15px]">Recent Activity</h3>
          </div>
          <div className="divide-y divide-white/[0.03]">
            {activityItems.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <Clock className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-400">No recent activity</p>
              </div>
            ) : (
              activityItems.slice(0, 6).map((item, i) => {
                const Icon = activityIcon(item.type);
                return (
                  <div
                    key={item.id || item.created_at}
                    className="px-5 py-3 flex items-center gap-3 row-hover transition-colors animate-row"
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    <div className="w-8 h-8 bg-slate-800/50 border border-white/[0.06] rounded-xl flex items-center justify-center">
                      <Icon className="w-4 h-4 text-slate-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200 truncate">{item.description || item.title}</p>
                      <p className="text-xs text-slate-500">{item.client_name || ''}</p>
                    </div>
                    <span className="text-xs text-slate-500 whitespace-nowrap">
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
