import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { clientsApi, complianceApi, documentsApi } from '../api/client';
import type {
  Client,
  ComplianceTask,
  Document,
  ClientListResponse,
  ComplianceTaskListResponse,
  DocumentListResponse,
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
  LucideIcon,
} from 'lucide-react';
import { formatDate, statusColor } from '../utils/format';

// eslint-disable-next-line @typescript-eslint/no-unused-vars

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
  const [activeTab, setActiveTab] = useState<string>('overview');

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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    );
  }

  if (isError || !client) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-stone-600 font-medium">Client not found</p>
        <button onClick={() => navigate('/clients')} className="text-blue-500 text-sm mt-2 hover:underline">
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
        className="inline-flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-700"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Clients
      </button>

      {/* Client header */}
      <div className="card p-6">
        <div className="flex flex-col sm:flex-row sm:items-start gap-4">
          <div className="w-14 h-14 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center text-xl font-bold shrink-0">
            {(client.firm_name || client.name || '?')[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-stone-800">{client.firm_name || client.name}</h1>
            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-3 text-sm text-stone-600">
              {client.pan && (
                <span className="flex items-center gap-1.5">
                  <CreditCard className="w-4 h-4 text-stone-400" /> PAN: <span className="font-mono font-medium">{client.pan}</span>
                </span>
              )}
              {client.gstin && (
                <span className="flex items-center gap-1.5">
                  <Hash className="w-4 h-4 text-stone-400" /> GSTIN: <span className="font-mono font-medium">{client.gstin}</span>
                </span>
              )}
              {client.entity_type && (
                <span className="flex items-center gap-1.5">
                  <Building2 className="w-4 h-4 text-stone-400" /> {entityLabel(client.entity_type)}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-2 text-sm text-stone-500">
              {client.contact_person && (
                <span className="flex items-center gap-1.5">
                  <User className="w-4 h-4 text-stone-400" /> {client.contact_person}
                </span>
              )}
              {client.email && (
                <span className="flex items-center gap-1.5">
                  <Mail className="w-4 h-4 text-stone-400" /> {client.email}
                </span>
              )}
              {client.phone && (
                <span className="flex items-center gap-1.5">
                  <Phone className="w-4 h-4 text-stone-400" /> {client.phone}
                </span>
              )}
            </div>
          </div>
          <span className={`inline-block px-3 py-1 text-xs font-medium rounded-full ${statusColor(client.status || 'active')}`}>
            {client.status || 'Active'}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-stone-200">
        <div className="flex gap-0">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-stone-500 hover:text-stone-700 hover:border-stone-300'
                  }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white card p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 bg-green-50 text-green-600 rounded-lg flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-stone-800">{completedTasks}</p>
                <p className="text-xs text-stone-500">Completed Tasks</p>
              </div>
            </div>
          </div>
          <div className="bg-white card p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 bg-amber-50 text-amber-600 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-stone-800">{pendingTasks}</p>
                <p className="text-xs text-stone-500">Pending Tasks</p>
              </div>
            </div>
          </div>
          <div className="bg-white card p-5">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 bg-red-50 text-red-600 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-stone-800">{overdueTasks}</p>
                <p className="text-xs text-stone-500">Overdue Tasks</p>
              </div>
            </div>
          </div>

          <div className="md:col-span-3 bg-white card p-5">
            <h3 className="font-semibold text-stone-800 mb-3">Documents</h3>
            {docList.length === 0 ? (
              <p className="text-sm text-stone-400">No documents uploaded yet</p>
            ) : (
              <div className="space-y-2">
                {docList.slice(0, 5).map((doc, i) => (
                  <div key={doc.id || i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-stone-50">
                    <FileText className="w-4 h-4 text-stone-400" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-stone-700 truncate">{doc.filename || doc.name}</p>
                      <p className="text-xs text-stone-400">{formatDate(doc.uploaded_at || doc.created_at)}</p>
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
        <div className="bg-white card overflow-hidden">
          {taskList.length === 0 ? (
            <div className="p-12 text-center">
              <CalendarCheck className="w-10 h-10 text-stone-300 mx-auto mb-3" />
              <p className="text-stone-600 font-medium">No compliance tasks</p>
              <p className="text-sm text-stone-400 mt-1">Generate a compliance calendar to get started</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="bg-stone-50 border-b border-stone-200">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-stone-500 uppercase">Task</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-stone-500 uppercase hidden sm:table-cell">Due Date</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-stone-500 uppercase hidden md:table-cell">Type</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-stone-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {taskList.map((task, i) => (
                  <tr key={task.id || i} className="hover:bg-stone-50">
                    <td className="px-5 py-3">
                      <p className="text-sm font-medium text-stone-700">{task.task_name || task.name}</p>
                      <p className="text-xs text-stone-400 sm:hidden">{formatDate(task.due_date)}</p>
                    </td>
                    <td className="px-5 py-3 text-sm text-stone-600 hidden sm:table-cell">{formatDate(task.due_date)}</td>
                    <td className="px-5 py-3 text-sm text-stone-600 hidden md:table-cell">{task.task_type || '--'}</td>
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
        <div className="bg-white card overflow-hidden">
          {docList.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-10 h-10 text-stone-300 mx-auto mb-3" />
              <p className="text-stone-600 font-medium">No documents</p>
              <p className="text-sm text-stone-400 mt-1">Upload documents from the Documents page</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="bg-stone-50 border-b border-stone-200">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-stone-500 uppercase">Document</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-stone-500 uppercase hidden sm:table-cell">Type</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-stone-500 uppercase hidden md:table-cell">Uploaded</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-stone-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {docList.map((doc, i) => (
                  <tr key={doc.id || i} className="hover:bg-stone-50">
                    <td className="px-5 py-3">
                      <p className="text-sm font-medium text-stone-700 truncate max-w-xs">{doc.filename || doc.name}</p>
                    </td>
                    <td className="px-5 py-3 text-sm text-stone-600 hidden sm:table-cell">{doc.document_type || doc.type || '--'}</td>
                    <td className="px-5 py-3 text-sm text-stone-600 hidden md:table-cell">{formatDate(doc.uploaded_at || doc.created_at)}</td>
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
    </div>
  );
}
