import { useState, useEffect, FormEvent, ChangeEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clientsApi, complianceApi, documentsApi, getErrorMessage } from '../api/client';
import { useToast } from './Toast';
import type {
  Client,
  ComplianceTask,
  Document,
  ComplianceTaskListResponse,
  DocumentListResponse,
  ClientUpdateRequest,
} from '../api/client';
import {
  ArrowLeft,
  Building2,
  CreditCard,
  Hash,
  User,
  Mail,
  Phone,
  Loader2,
  CalendarCheck,
  FileText,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Edit,
  X,
  LucideIcon,
} from 'lucide-react';
import { formatDate, statusColor } from '../utils/format';

interface TabItem {
  id: string;
  label: string;
  icon: LucideIcon;
}

const tabs: TabItem[] = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'compliance', label: 'Compliance', icon: CalendarCheck },
  { id: 'documents', label: 'Documents', icon: FileText },
];

export default function ClientDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editForm, setEditForm] = useState<ClientUpdateRequest>({});
  const [editError, setEditError] = useState<string>('');

  const { data: client, isLoading, isError } = useQuery<Client>({
    queryKey: ['clients', id],
    queryFn: () => clientsApi.get(id!),
    enabled: Boolean(id),
  });

  const { data: tasks } = useQuery<ComplianceTaskListResponse | ComplianceTask[]>({
    queryKey: ['compliance', 'tasks', { client_id: id }],
    queryFn: () => complianceApi.listTasks({ client_id: id }),
    enabled: Boolean(id),
  });

  const { data: docs } = useQuery<DocumentListResponse | Document[]>({
    queryKey: ['documents', { client_id: id }],
    queryFn: () => documentsApi.list({ client_id: id }),
    enabled: Boolean(id),
  });

  const updateMutation = useMutation({
    mutationFn: (data: ClientUpdateRequest) => clientsApi.update(id!, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['clients', id], updated);
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      toast.success('Client updated successfully');
      setIsEditing(false);
      setEditError('');
    },
    onError: (err) => {
      setEditError(getErrorMessage(err, 'Failed to update client'));
    },
  });

  useEffect(() => {
    if (client) {
      setEditForm({
        firm_name: client.firm_name,
        pan: client.pan,
        gstin: client.gstin,
        entity_type: client.entity_type,
        contact_person: client.contact_person,
        email: client.email,
        phone: client.phone,
        status: client.status,
      });
    }
  }, [client]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
      </div>
    );
  }

  if (isError || !client) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-slate-300 font-medium">Client not found</p>
        <button onClick={() => navigate('/clients')} className="text-blue-400 text-sm mt-2 hover:text-blue-300 transition-colors">
          Back to Clients
        </button>
      </div>
    );
  }

  const entityLabel = (type: string | undefined): string => {
    const map: Record<string, string> = { individual: 'Individual', huf: 'HUF', partnership: 'Partnership', llp: 'LLP', pvt_ltd: 'Pvt. Ltd.', public_ltd: 'Public Ltd.', trust: 'Trust', society: 'Society' };
    return map[type ?? ''] || type || '--';
  };

  // Normalize task and doc lists
  const normalizedTasks = tasks as ComplianceTaskListResponse | undefined;
  const taskList: ComplianceTask[] = normalizedTasks?.items || normalizedTasks?.tasks || (Array.isArray(tasks) ? tasks : []);

  const normalizedDocs = docs as DocumentListResponse | undefined;
  const docList: Document[] = normalizedDocs?.items || normalizedDocs?.documents || (Array.isArray(docs) ? docs : []);

  const completedTasks = taskList.filter((t) => t.status === 'completed').length;
  const overdueTasks = taskList.filter((t) => t.status === 'overdue').length;
  const pendingTasks = taskList.filter((t) => t.status === 'pending' || t.status === 'in_progress').length;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate('/clients')}
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Clients
      </button>

      {/* Client header */}
      <div className="card p-6 animate-stagger-1">
        <div className="flex flex-col sm:flex-row sm:items-start gap-4">
          <div className="w-14 h-14 bg-blue-500/15 border border-blue-500/20 text-blue-400 rounded-xl flex items-center justify-center text-xl font-bold shrink-0 glow-blue">
            {(client.firm_name || client.name || '?')[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-slate-100">{client.firm_name || client.name}</h1>
            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-3 text-sm text-slate-300">
              {client.pan && (
                <span className="flex items-center gap-1.5">
                  <CreditCard className="w-4 h-4 text-slate-500" /> PAN: <span className="font-mono font-medium text-slate-200">{client.pan}</span>
                </span>
              )}
              {client.gstin && (
                <span className="flex items-center gap-1.5">
                  <Hash className="w-4 h-4 text-slate-500" /> GSTIN: <span className="font-mono font-medium text-slate-200">{client.gstin}</span>
                </span>
              )}
              {client.entity_type && (
                <span className="flex items-center gap-1.5">
                  <Building2 className="w-4 h-4 text-slate-500" /> {entityLabel(client.entity_type)}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-2 text-sm text-slate-400">
              {client.contact_person && (
                <span className="flex items-center gap-1.5">
                  <User className="w-4 h-4 text-slate-500" /> {client.contact_person}
                </span>
              )}
              {client.email && (
                <span className="flex items-center gap-1.5">
                  <Mail className="w-4 h-4 text-slate-500" /> {client.email}
                </span>
              )}
              {client.phone && (
                <span className="flex items-center gap-1.5">
                  <Phone className="w-4 h-4 text-slate-500" /> {client.phone}
                </span>
              )}
            </div>
          </div>
          <span className={`inline-block px-3 py-1 text-xs font-medium rounded-full ${statusColor(client.status || 'active')}`}>
            {client.status || 'Active'}
          </span>
          <button
            onClick={() => setIsEditing(true)}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] rounded-xl transition-colors"
            title="Edit client"
          >
            <Edit className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-white/[0.06] animate-stagger-2">
        <div className="flex gap-0">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all
                  ${isActive
                    ? 'text-blue-400'
                    : 'text-slate-500 hover:text-slate-300'
                  }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
                {isActive && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-blue-400 rounded-full" style={{ animation: 'tab-underline 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards', transformOrigin: 'left' }} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-fade-in">
          <div className="card-interactive p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100 animate-count">{completedTasks}</p>
                <p className="text-xs text-slate-500">Completed Tasks</p>
              </div>
            </div>
          </div>
          <div className="card-interactive p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100 animate-count">{pendingTasks}</p>
                <p className="text-xs text-slate-500">Pending Tasks</p>
              </div>
            </div>
          </div>
          <div className="card-interactive p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100 animate-count">{overdueTasks}</p>
                <p className="text-xs text-slate-500">Overdue Tasks</p>
              </div>
            </div>
          </div>

          <div className="md:col-span-3 card p-5">
            <h3 className="font-semibold text-slate-200 mb-3">Documents</h3>
            {docList.length === 0 ? (
              <p className="text-sm text-slate-500">No documents uploaded yet</p>
            ) : (
              <div className="space-y-2">
                {docList.slice(0, 5).map((doc, i) => (
                  <div key={doc.id || i} className="flex items-center gap-3 p-2 rounded-lg row-hover transition-colors">
                    <FileText className="w-4 h-4 text-slate-500" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200 truncate">{doc.filename || doc.name}</p>
                      <p className="text-xs text-slate-500">{formatDate(doc.uploaded_at || doc.created_at)}</p>
                    </div>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(doc.status || 'uploaded')}`}>
                      {doc.status || 'Uploaded'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'compliance' && (
        <div className="card overflow-hidden animate-fade-in">
          {taskList.length === 0 ? (
            <div className="p-12 text-center">
              <CalendarCheck className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-300 font-medium">No compliance tasks</p>
              <p className="text-sm text-slate-500 mt-1">Generate a compliance calendar to get started</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="bg-white/[0.02] border-b border-white/[0.06]">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">Task</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase hidden sm:table-cell">Due Date</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase hidden md:table-cell">Type</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {taskList.map((task, i) => (
                  <tr key={task.id || i} className="row-hover animate-row" style={{ animationDelay: `${i * 30}ms` }}>
                    <td className="px-5 py-3">
                      <p className="text-sm font-medium text-slate-200">{task.task_name || task.name}</p>
                      <p className="text-xs text-slate-500 sm:hidden">{formatDate(task.due_date)}</p>
                    </td>
                    <td className="px-5 py-3 text-sm text-slate-400 hidden sm:table-cell">{formatDate(task.due_date)}</td>
                    <td className="px-5 py-3 text-sm text-slate-400 hidden md:table-cell">{task.task_type || '--'}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(task.status)}`}>
                        {task.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'documents' && (
        <div className="card overflow-hidden animate-fade-in">
          {docList.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-300 font-medium">No documents</p>
              <p className="text-sm text-slate-500 mt-1">Upload documents from the Documents page</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="bg-white/[0.02] border-b border-white/[0.06]">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">Document</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase hidden sm:table-cell">Type</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase hidden md:table-cell">Uploaded</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {docList.map((doc, i) => (
                  <tr key={doc.id || i} className="row-hover animate-row" style={{ animationDelay: `${i * 30}ms` }}>
                    <td className="px-5 py-3">
                      <p className="text-sm font-medium text-slate-200 truncate max-w-xs">{doc.filename || doc.name}</p>
                    </td>
                    <td className="px-5 py-3 text-sm text-slate-400 hidden sm:table-cell">{doc.document_type || doc.type || '--'}</td>
                    <td className="px-5 py-3 text-sm text-slate-400 hidden md:table-cell">{formatDate(doc.uploaded_at || doc.created_at)}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(doc.status || 'uploaded')}`}>
                        {doc.status || 'Uploaded'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Edit client modal */}
      {isEditing && client && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md animate-backdrop"
          onClick={() => setIsEditing(false)}
        >
          <div
            className="bg-[#161b26]/95 backdrop-blur-xl rounded-2xl shadow-2xl shadow-black/50 border border-white/[0.08] w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
              <h3 className="text-lg font-semibold text-slate-100">Edit Client</h3>
              <button
                onClick={() => setIsEditing(false)}
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form
              onSubmit={(e: FormEvent<HTMLFormElement>) => {
                e.preventDefault();
                setEditError('');
                if (!editForm.firm_name?.trim()) {
                  setEditError('Firm / client name is required');
                  return;
                }
                if (editForm.pan && !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(editForm.pan)) {
                  setEditError('PAN must be in format ABCDE1234F');
                  return;
                }
                if (editForm.gstin && !/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(editForm.gstin)) {
                  setEditError('GSTIN must be a valid 15-character number');
                  return;
                }
                updateMutation.mutate(editForm);
              }}
              className="p-6 space-y-4"
            >
              {editError && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400 animate-fade-in">
                  {editError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Firm / Client Name *</label>
                <input
                  type="text"
                  value={editForm.firm_name || ''}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setEditForm((f) => ({ ...f, firm_name: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">PAN</label>
                  <input
                    type="text"
                    value={editForm.pan || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      setEditForm((f) => ({ ...f, pan: e.target.value.toUpperCase() }))}
                    maxLength={10}
                    className="w-full px-3 py-2.5 rounded-xl text-sm outline-none uppercase font-mono"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">GSTIN</label>
                  <input
                    type="text"
                    value={editForm.gstin || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      setEditForm((f) => ({ ...f, gstin: e.target.value.toUpperCase() }))}
                    maxLength={15}
                    className="w-full px-3 py-2.5 rounded-xl text-sm outline-none uppercase font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Entity Type</label>
                <select
                  value={editForm.entity_type || 'individual'}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                    setEditForm((f) => ({ ...f, entity_type: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                >
                  {[
                    { value: 'individual', label: 'Individual' },
                    { value: 'huf', label: 'HUF' },
                    { value: 'partnership', label: 'Partnership' },
                    { value: 'llp', label: 'LLP' },
                    { value: 'private_limited', label: 'Private Limited' },
                    { value: 'public_limited', label: 'Public Limited' },
                    { value: 'trust', label: 'Trust' },
                    { value: 'society', label: 'Society' },
                  ].map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Contact Person</label>
                <input
                  type="text"
                  value={editForm.contact_person || ''}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setEditForm((f) => ({ ...f, contact_person: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
                  <input
                    type="email"
                    value={editForm.email || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      setEditForm((f) => ({ ...f, email: e.target.value }))}
                    className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Phone</label>
                  <input
                    type="tel"
                    value={editForm.phone || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      setEditForm((f) => ({ ...f, phone: e.target.value }))}
                    className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Status</label>
                <select
                  value={editForm.status || 'active'}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                    setEditForm((f) => ({ ...f, status: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2.5 text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="px-5 py-2.5 text-sm font-medium gradient-brand text-white rounded-xl flex items-center gap-2 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 hover-lift disabled:opacity-50 transition-all"
                >
                  {updateMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
