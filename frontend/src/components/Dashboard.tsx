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
  BarChart3,
  LucideIcon,
} from 'lucide-react';
import { formatDate } from '../utils/format';
import { SkeletonCard } from './Skeleton';
import { StatCard } from './textura';

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
    if (days < 0) return 'text-danger bg-danger/10 border border-danger/20';
    if (days <= 2) return 'text-warning bg-warning/10 border border-warning/20';
    return 'text-textura-accent bg-textura-accent/10 border border-textura-accent/20';
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
        <h1 className="text-2xl font-bold text-textura-text">Dashboard</h1>
        <p className="text-sm text-textura-dim mt-1">Welcome back. Here is your practice overview.</p>
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
            <StatCard title="Total Clients" value={stats?.total_clients} icon={Users} variant="accent" className="animate-stagger-1" delay={50} />
            <StatCard title="Active Tasks" value={stats?.active_tasks} icon={CalendarCheck} variant="success" className="animate-stagger-2" delay={100} />
            <StatCard title="Overdue Tasks" value={stats?.overdue_tasks} icon={AlertTriangle} variant="danger" className="animate-stagger-3" delay={150} />
            <StatCard title="Queries Today" value={stats?.queries_today} icon={MessageSquare} variant="warm" className="animate-stagger-4" delay={200} />
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
          <div className="px-5 py-4 border-b border-textura-line-subtle flex items-center justify-between">
            <h3 className="font-semibold text-textura-text text-[15px] flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-textura-accent" /> Team Workload
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
                      <span className="text-sm text-textura-dim font-medium truncate max-w-[180px]">{member.name}</span>
                      <div className="flex items-center gap-3 text-xs text-textura-muted">
                        <span>{member.completed} done</span>
                        <span>{member.pending} pending</span>
                        {member.overdue > 0 && (
                          <span className="text-danger">{member.overdue} overdue</span>
                        )}
                      </div>
                    </div>
                    <div className="h-2 bg-textura-panel-raised/50 rounded-full overflow-hidden">
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
          <div className="px-5 py-4 border-b border-textura-line-subtle flex items-center justify-between">
            <h3 className="font-semibold text-textura-text text-[15px]">Upcoming Deadlines</h3>
            <button
              onClick={() => navigate('/compliance')}
              className="text-[13px] text-textura-accent hover:text-textura-accent/80 flex items-center gap-1 font-medium transition-colors"
            >
              View All <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-textura-line-subtle">
            {upcomingTasks.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <CheckCircle2 className="w-8 h-8 text-emerald-500/50 mx-auto mb-2" />
                <p className="text-sm text-textura-dim">No upcoming deadlines in the next 7 days</p>
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
                      <p className="text-sm font-medium text-textura-text truncate">{task.task_name || task.name}</p>
                      <p className="text-xs text-textura-muted truncate">{task.client_name || ''}</p>
                    </div>
                    <span className="text-xs text-textura-muted">{formatDate(task.due_date)}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Recent activity */}
        <div className="card overflow-hidden animate-stagger-6">
          <div className="px-5 py-4 border-b border-textura-line-subtle">
            <h3 className="font-semibold text-textura-text text-[15px]">Recent Activity</h3>
          </div>
          <div className="divide-y divide-textura-line-subtle">
            {activityItems.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <Clock className="w-8 h-8 text-textura-muted mx-auto mb-2" />
                <p className="text-sm text-textura-dim">No recent activity</p>
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
                    <div className="w-8 h-8 bg-textura-panel-raised/50 border border-textura-line-subtle rounded-xl flex items-center justify-center">
                      <Icon className="w-4 h-4 text-textura-dim" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-textura-text truncate">{item.description || item.title}</p>
                      <p className="text-xs text-textura-muted">{item.client_name || ''}</p>
                    </div>
                    <span className="text-xs text-textura-muted whitespace-nowrap">
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
