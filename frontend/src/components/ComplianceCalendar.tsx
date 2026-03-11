import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { complianceApi, clientsApi } from '../api/client';
import type {
  Client,
  ComplianceTask,
  ClientListResponse,
  ComplianceTaskListResponse,
} from '../api/client';
import {
  CalendarCheck,
  Filter,
  Loader2,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Play,
  ChevronDown,
  RefreshCw,
  Calendar,
  LucideIcon,
} from 'lucide-react';
import { formatDate, statusColor, getAssessmentYears } from '../utils/format';

const STATUS_OPTIONS: string[] = ['all', 'pending', 'in_progress', 'completed', 'overdue'];
const TASK_TYPES: string[] = ['all', 'itr', 'gst', 'tds', 'advance_tax', 'audit', 'roc', 'other'];

const statusIcon = (status: string | undefined): LucideIcon => {
  switch (status) {
    case 'completed': return CheckCircle2;
    case 'in_progress': return Play;
    case 'overdue': return AlertTriangle;
    default: return Clock;
  }
};

interface ComplianceFilters {
  status: string;
  type: string;
  client_id: string;
}

export default function ComplianceCalendar() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ComplianceFilters>({ status: 'all', type: 'all', client_id: '' });
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [genClientId, setGenClientId] = useState<string>('');
  const [genFY, setGenFY] = useState<string>(getAssessmentYears()[0]);
  const [showGenerate, setShowGenerate] = useState<boolean>(false);

  const params: Record<string, string> = {};
  if (filters.status !== 'all') params.status = filters.status;
  if (filters.type !== 'all') params.task_type = filters.type;
  if (filters.client_id) params.client_id = filters.client_id;

  const { data: tasks, isLoading } = useQuery<ComplianceTaskListResponse | ComplianceTask[]>({
    queryKey: ['compliance', 'tasks', params],
    queryFn: () => complianceApi.listTasks(params),
  });

  const { data: clients } = useQuery<ClientListResponse | Client[]>({
    queryKey: ['clients', 'list-all'],
    queryFn: () => clientsApi.list({ page_size: 200 }),
  });

  const normalizedClients = clients as ClientListResponse | undefined;
  const clientList: Client[] = normalizedClients?.items || normalizedClients?.clients || (Array.isArray(clients) ? clients : []);

  const normalizedTasks = tasks as ComplianceTaskListResponse | undefined;
  const taskList: ComplianceTask[] = normalizedTasks?.items || normalizedTasks?.tasks || (Array.isArray(tasks) ? tasks : []);

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { status: string } }) => complianceApi.updateTask(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['compliance'] }),
  });

  const generateMutation = useMutation({
    mutationFn: () => complianceApi.generateCalendar(genClientId, genFY),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance'] });
      setShowGenerate(false);
    },
  });

  const handleStatusUpdate = (taskId: string, newStatus: string) => {
    updateMutation.mutate({ id: taskId, data: { status: newStatus } });
  };

  // Group tasks by month
  const grouped: Record<string, ComplianceTask[]> = {};
  taskList.forEach((task) => {
    const d = new Date(task.due_date);
    const key = isNaN(d.getTime()) ? 'Unknown' : d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(task);
  });

  const sortedMonths = Object.keys(grouped).sort((a, b) => {
    const da = new Date(grouped[a][0]?.due_date);
    const db = new Date(grouped[b][0]?.due_date);
    return da.getTime() - db.getTime();
  });

  const statusColorDot = (status: string | undefined): string => {
    switch (status) {
      case 'completed': return 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)]';
      case 'in_progress': return 'bg-blue-500 shadow-[0_0_6px_rgba(59,130,246,0.5)]';
      case 'overdue': return 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]';
      default: return 'bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.5)]';
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 animate-stagger-1">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Compliance Calendar</h1>
          <p className="text-sm text-slate-400">Track deadlines and manage compliance tasks</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="inline-flex items-center gap-2 px-3 py-2.5 border border-white/[0.08] text-sm font-medium text-slate-300 rounded-xl hover:bg-white/[0.04] transition-colors"
          >
            <Filter className="w-4 h-4" /> Filters <ChevronDown className="w-3 h-3" />
          </button>
          <button
            onClick={() => setShowGenerate(!showGenerate)}
            className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white text-sm font-medium rounded-xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 hover-lift transition-all"
          >
            <Calendar className="w-4 h-4" /> Generate Calendar
          </button>
        </div>
      </div>

      {/* Generate calendar panel */}
      {showGenerate && (
        <div className="card p-5 animate-fade-in">
          <h3 className="font-semibold text-slate-200 mb-3">Generate Compliance Calendar</h3>
          <div className="flex flex-col sm:flex-row gap-3">
            <select
              value={genClientId}
              onChange={(e) => setGenClientId(e.target.value)}
              className="flex-1 px-3 py-2.5 rounded-xl text-sm outline-none"
            >
              <option value="">Select Client</option>
              {clientList.map((c) => (
                <option key={c.id} value={c.id}>{c.firm_name || c.name}</option>
              ))}
            </select>
            <select
              value={genFY}
              onChange={(e) => setGenFY(e.target.value)}
              className="px-3 py-2.5 rounded-xl text-sm outline-none"
            >
              {getAssessmentYears().map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <button
              onClick={() => generateMutation.mutate()}
              disabled={!genClientId || generateMutation.isPending}
              className="px-4 py-2.5 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 disabled:opacity-50 text-emerald-300 text-sm font-medium rounded-xl flex items-center gap-2 transition-all"
            >
              {generateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Generate
            </button>
          </div>
          {generateMutation.isError && (
            <p className="text-sm text-red-400 mt-2">
              {(generateMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to generate calendar'}
            </p>
          )}
          {generateMutation.isSuccess && (
            <p className="text-sm text-emerald-400 mt-2">Calendar generated successfully!</p>
          )}
        </div>
      )}

      {/* Filters panel */}
      {showFilters && (
        <div className="card p-5 animate-fade-in">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-500 mb-1.5">Client</label>
              <select
                value={filters.client_id}
                onChange={(e) => setFilters((f) => ({ ...f, client_id: e.target.value }))}
                className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
              >
                <option value="">All Clients</option>
                {clientList.map((c) => (
                  <option key={c.id} value={c.id}>{c.firm_name || c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
                className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s === 'all' ? 'All' : s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">Type</label>
              <select
                value={filters.type}
                onChange={(e) => setFilters((f) => ({ ...f, type: e.target.value }))}
                className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
              >
                {TASK_TYPES.map((t) => (
                  <option key={t} value={t}>{t === 'all' ? 'All Types' : t.toUpperCase()}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      {isLoading ? (
        <div className="card p-12 text-center">
          <Loader2 className="w-6 h-6 animate-spin text-blue-400 mx-auto" />
          <p className="text-sm text-slate-400 mt-2">Loading compliance tasks...</p>
        </div>
      ) : taskList.length === 0 ? (
        <div className="card p-12 text-center">
          <CalendarCheck className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-300 font-medium">No compliance tasks found</p>
          <p className="text-sm text-slate-500 mt-1">Generate a compliance calendar for a client to get started</p>
        </div>
      ) : (
        <div className="space-y-6">
          {sortedMonths.map((month, mi) => (
            <div key={month} className={`animate-stagger-${Math.min(mi + 2, 8)}`}>
              <h3 className="text-[13px] font-semibold text-slate-500 uppercase tracking-wider mb-3">{month}</h3>
              <div className="space-y-2">
                {grouped[month]
                  .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime())
                  .map((task, ti) => (
                    <div
                      key={task.id}
                      className="card-interactive p-4 flex items-center gap-4 animate-row"
                      style={{ animationDelay: `${ti * 30}ms` }}
                    >
                      <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${statusColorDot(task.status)}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-200">{task.task_name || task.name}</p>
                        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
                          <span className="text-xs text-slate-500">Due: {formatDate(task.due_date)}</span>
                          {task.client_name && <span className="text-xs text-slate-500">{task.client_name}</span>}
                          {task.task_type && <span className="text-xs text-slate-500 uppercase">{task.task_type}</span>}
                        </div>
                      </div>
                      <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full shrink-0 ${statusColor(task.status)}`}>
                        {task.status?.replace('_', ' ')}
                      </span>
                      {task.status !== 'completed' && (
                        <div className="flex gap-1 shrink-0">
                          {task.status === 'pending' && (
                            <button
                              onClick={(e) => { e.stopPropagation(); handleStatusUpdate(task.id, 'in_progress'); }}
                              title="Start"
                              className="p-1.5 text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStatusUpdate(task.id, 'completed'); }}
                            title="Mark Complete"
                            className="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
