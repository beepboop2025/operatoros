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
import {
  Button,
  Panel,
  StatCard,
  Tabs,
  Field,
  Input,
  Select,
  DataTable,
  DataTableHeader,
  DataTableHead,
  DataTableBody,
  DataTableRow,
  DataTableCell,
} from './textura';

interface TabItem {
  id: string;
  label: string;
  icon: LucideIcon;
}

const tabItems: TabItem[] = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'compliance', label: 'Compliance', icon: CalendarCheck },
  { id: 'documents', label: 'Documents', icon: FileText },
];

const entityTypes = [
  { value: 'individual', label: 'Individual' },
  { value: 'huf', label: 'HUF' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'llp', label: 'LLP' },
  { value: 'private_limited', label: 'Private Limited' },
  { value: 'public_limited', label: 'Public Limited' },
  { value: 'trust', label: 'Trust' },
  { value: 'society', label: 'Society' },
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
        <Loader2 className="w-6 h-6 animate-spin text-textura-accent" />
      </div>
    );
  }

  if (isError || !client) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-10 h-10 text-danger mx-auto mb-3" />
        <p className="text-textura-text font-medium">Client not found</p>
        <button onClick={() => navigate('/clients')} className="text-textura-accent text-sm mt-2 hover:text-textura-text transition-colors">
          Back to Clients
        </button>
      </div>
    );
  }

  const entityLabel = (type: string | undefined): string => {
    const found = entityTypes.find(t => t.value === type);
    return found?.label || type || '--';
  };

  // Normalize task and doc lists
  const normalizedTasks = tasks as ComplianceTaskListResponse | undefined;
  const taskList: ComplianceTask[] = normalizedTasks?.items || normalizedTasks?.tasks || (Array.isArray(tasks) ? tasks : []);

  const normalizedDocs = docs as DocumentListResponse | undefined;
  const docList: Document[] = normalizedDocs?.items || normalizedDocs?.documents || (Array.isArray(docs) ? docs : []);

  const completedTasks = taskList.filter((t) => t.status === 'completed').length;
  const overdueTasks = taskList.filter((t) => t.status === 'overdue').length;
  const pendingTasks = taskList.filter((t) => t.status === 'pending' || t.status === 'in_progress').length;

  const overviewContent = (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-fade-in">
      <StatCard
        title="Completed Tasks"
        value={completedTasks}
        icon={CheckCircle2}
        variant="success"
      />
      <StatCard
        title="Pending Tasks"
        value={pendingTasks}
        icon={Clock}
        variant="warm"
      />
      <StatCard
        title="Overdue Tasks"
        value={overdueTasks}
        icon={AlertTriangle}
        variant="danger"
      />

      <Panel className="md:col-span-3 p-5">
        <h3 className="font-semibold text-textura-text mb-3">Documents</h3>
        {docList.length === 0 ? (
          <p className="text-sm text-textura-muted">No documents uploaded yet</p>
        ) : (
          <div className="space-y-2">
            {docList.slice(0, 5).map((doc, i) => (
              <div key={doc.id || i} className="flex items-center gap-3 p-2 rounded-lg row-hover transition-colors">
                <FileText className="w-4 h-4 text-textura-muted" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-textura-text truncate">{doc.filename || doc.name}</p>
                  <p className="text-xs text-textura-muted">{formatDate(doc.uploaded_at || doc.created_at)}</p>
                </div>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(doc.status || 'uploaded')}`}>
                  {doc.status || 'Uploaded'}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );

  const complianceContent = (
    <Panel className="overflow-hidden animate-fade-in">
      {taskList.length === 0 ? (
        <div className="p-12 text-center">
          <CalendarCheck className="w-10 h-10 text-textura-muted mx-auto mb-3" />
          <p className="text-textura-text font-medium">No compliance tasks</p>
          <p className="text-sm text-textura-muted mt-1">Generate a compliance calendar to get started</p>
        </div>
      ) : (
        <DataTable>
          <DataTableHeader>
            <DataTableHead>Task</DataTableHead>
            <DataTableHead className="hidden sm:table-cell">Due Date</DataTableHead>
            <DataTableHead className="hidden md:table-cell">Type</DataTableHead>
            <DataTableHead>Status</DataTableHead>
          </DataTableHeader>
          <DataTableBody>
            {taskList.map((task, i) => (
              <DataTableRow key={task.id || i}>
                <DataTableCell>
                  <p className="text-sm font-medium text-textura-text">{task.task_name || task.name}</p>
                  <p className="text-xs text-textura-muted sm:hidden">{formatDate(task.due_date)}</p>
                </DataTableCell>
                <DataTableCell className="text-textura-dim hidden sm:table-cell">{formatDate(task.due_date)}</DataTableCell>
                <DataTableCell className="text-textura-dim hidden md:table-cell">{task.task_type || '--'}</DataTableCell>
                <DataTableCell>
                  <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(task.status)}`}>
                    {task.status}
                  </span>
                </DataTableCell>
              </DataTableRow>
            ))}
          </DataTableBody>
        </DataTable>
      )}
    </Panel>
  );

  const documentsContent = (
    <Panel className="overflow-hidden animate-fade-in">
      {docList.length === 0 ? (
        <div className="p-12 text-center">
          <FileText className="w-10 h-10 text-textura-muted mx-auto mb-3" />
          <p className="text-textura-text font-medium">No documents</p>
          <p className="text-sm text-textura-muted mt-1">Upload documents from the Documents page</p>
        </div>
      ) : (
        <DataTable>
          <DataTableHeader>
            <DataTableHead>Document</DataTableHead>
            <DataTableHead className="hidden sm:table-cell">Type</DataTableHead>
            <DataTableHead className="hidden md:table-cell">Uploaded</DataTableHead>
            <DataTableHead>Status</DataTableHead>
          </DataTableHeader>
          <DataTableBody>
            {docList.map((doc, i) => (
              <DataTableRow key={doc.id || i}>
                <DataTableCell>
                  <p className="text-sm font-medium text-textura-text truncate max-w-xs">{doc.filename || doc.name}</p>
                </DataTableCell>
                <DataTableCell className="text-textura-dim hidden sm:table-cell">{doc.document_type || doc.type || '--'}</DataTableCell>
                <DataTableCell className="text-textura-dim hidden md:table-cell">{formatDate(doc.uploaded_at || doc.created_at)}</DataTableCell>
                <DataTableCell>
                  <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(doc.status || 'uploaded')}`}>
                    {doc.status || 'Uploaded'}
                  </span>
                </DataTableCell>
              </DataTableRow>
            ))}
          </DataTableBody>
        </DataTable>
      )}
    </Panel>
  );

  const tabs = tabItems.map((tab) => ({
    ...tab,
    content:
      tab.id === 'overview'
        ? overviewContent
        : tab.id === 'compliance'
          ? complianceContent
          : documentsContent,
  }));

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate('/clients')}
        className="inline-flex items-center gap-1.5 text-sm text-textura-dim hover:text-textura-text transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Clients
      </button>

      {/* Client header */}
      <Panel className="p-6 animate-stagger-1">
        <div className="flex flex-col sm:flex-row sm:items-start gap-4">
          <div className="w-14 h-14 bg-textura-accent/10 border border-textura-accent/20 text-textura-accent rounded-xl flex items-center justify-center text-xl font-bold shrink-0 glow-blue">
            {(client.firm_name || client.name || '?')[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-textura-text">{client.firm_name || client.name}</h1>
            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-3 text-sm text-textura-dim">
              {client.pan && (
                <span className="flex items-center gap-1.5">
                  <CreditCard className="w-4 h-4 text-textura-muted" /> PAN: <span className="font-mono font-medium text-textura-text">{client.pan}</span>
                </span>
              )}
              {client.gstin && (
                <span className="flex items-center gap-1.5">
                  <Hash className="w-4 h-4 text-textura-muted" /> GSTIN: <span className="font-mono font-medium text-textura-text">{client.gstin}</span>
                </span>
              )}
              {client.entity_type && (
                <span className="flex items-center gap-1.5">
                  <Building2 className="w-4 h-4 text-textura-muted" /> {entityLabel(client.entity_type)}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-2 text-sm text-textura-muted">
              {client.contact_person && (
                <span className="flex items-center gap-1.5">
                  <User className="w-4 h-4 text-textura-muted" /> {client.contact_person}
                </span>
              )}
              {client.email && (
                <span className="flex items-center gap-1.5">
                  <Mail className="w-4 h-4 text-textura-muted" /> {client.email}
                </span>
              )}
              {client.phone && (
                <span className="flex items-center gap-1.5">
                  <Phone className="w-4 h-4 text-textura-muted" /> {client.phone}
                </span>
              )}
            </div>
          </div>
          <span className={`inline-block px-3 py-1 text-xs font-medium rounded-full ${statusColor(client.status || 'active')}`}>
            {client.status || 'Active'}
          </span>
          <Button
            variant="ghost"
            size="sm"
            icon={<Edit className="w-4 h-4" />}
            onClick={() => setIsEditing(true)}
            aria-label="Edit client"
          >
            {''}
          </Button>
        </div>
      </Panel>

      {/* Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Edit client modal */}
      {isEditing && client && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md animate-backdrop"
          onClick={() => setIsEditing(false)}
        >
          <div onClick={(e) => e.stopPropagation()}>
            <Panel className="bg-textura-panel/95 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto animate-scale-in">
              <div className="flex items-center justify-between px-6 py-4 border-b border-textura-line-subtle">
                <h3 className="text-lg font-semibold text-textura-text">Edit Client</h3>
                <button
                  onClick={() => setIsEditing(false)}
                  className="p-1.5 text-textura-dim hover:text-textura-text hover:bg-textura-panel-raised rounded-lg transition-colors"
                  aria-label="Close"
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
                  <div className="p-3 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
                    {editError}
                  </div>
                )}

                <Field label="Firm / Client Name *">
                  <Input
                    type="text"
                    value={editForm.firm_name || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      setEditForm((f) => ({ ...f, firm_name: e.target.value }))}
                  />
                </Field>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="PAN">
                    <Input
                      type="text"
                      value={editForm.pan || ''}
                      onChange={(e: ChangeEvent<HTMLInputElement>) =>
                        setEditForm((f) => ({ ...f, pan: e.target.value.toUpperCase() }))}
                      maxLength={10}
                      className="uppercase font-mono"
                    />
                  </Field>
                  <Field label="GSTIN">
                    <Input
                      type="text"
                      value={editForm.gstin || ''}
                      onChange={(e: ChangeEvent<HTMLInputElement>) =>
                        setEditForm((f) => ({ ...f, gstin: e.target.value.toUpperCase() }))}
                      maxLength={15}
                      className="uppercase font-mono"
                    />
                  </Field>
                </div>

                <Field label="Entity Type">
                  <Select
                    value={editForm.entity_type || 'individual'}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                      setEditForm((f) => ({ ...f, entity_type: e.target.value }))}
                  >
                    {entityTypes.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </Select>
                </Field>

                <Field label="Contact Person">
                  <Input
                    type="text"
                    value={editForm.contact_person || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      setEditForm((f) => ({ ...f, contact_person: e.target.value }))}
                  />
                </Field>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Email">
                    <Input
                      type="email"
                      value={editForm.email || ''}
                      onChange={(e: ChangeEvent<HTMLInputElement>) =>
                        setEditForm((f) => ({ ...f, email: e.target.value }))}
                    />
                  </Field>
                  <Field label="Phone">
                    <Input
                      type="tel"
                      value={editForm.phone || ''}
                      onChange={(e: ChangeEvent<HTMLInputElement>) =>
                        setEditForm((f) => ({ ...f, phone: e.target.value }))}
                    />
                  </Field>
                </div>

                <Field label="Status">
                  <Select
                    value={editForm.status || 'active'}
                    onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                      setEditForm((f) => ({ ...f, status: e.target.value }))}
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </Select>
                </Field>

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="ghost" onClick={() => setIsEditing(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="gradient" loading={updateMutation.isPending}>
                    Save Changes
                  </Button>
                </div>
              </form>
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}
