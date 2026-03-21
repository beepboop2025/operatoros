import { useState, useEffect, useCallback, useRef, FormEvent, ChangeEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { clientsApi } from '../api/client';
import type { Client, ClientCreateRequest, ClientListResponse } from '../api/client';
import {
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  X,
  Loader2,
  Users,
  Building2,
  Filter,
  Download,
  Trash2,
  UserPlus,
  CheckSquare,
  Square,
} from 'lucide-react';
import { statusColor } from '../utils/format';
import { AxiosError } from 'axios';

const PAN_REGEX = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

interface AddClientModalProps {
  onClose: () => void;
  onSuccess?: () => void;
}

function AddClientModal({ onClose, onSuccess }: AddClientModalProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ClientCreateRequest>({
    firm_name: '',
    pan: '',
    gstin: '',
    entity_type: 'individual',
    contact_person: '',
    email: '',
    phone: '',
  });
  const [error, setError] = useState<string>('');

  const mutation = useMutation({
    mutationFn: clientsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      onSuccess?.();
      onClose();
    },
    onError: (err: AxiosError<{ detail?: string }>) => {
      setError(err.response?.data?.detail || 'Failed to create client');
    },
  });

  const update = (field: keyof ClientCreateRequest, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!form.firm_name.trim()) {
      setError('Firm name is required');
      return;
    }
    if (form.pan && !PAN_REGEX.test(form.pan)) {
      setError('PAN must be in format: ABCDE1234F (5 letters, 4 digits, 1 letter)');
      return;
    }
    if (form.gstin && !GSTIN_REGEX.test(form.gstin)) {
      setError('GSTIN must be a valid 15-character GST number');
      return;
    }
    setError('');
    mutation.mutate(form);
  };

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md animate-backdrop" onClick={onClose}>
      <div className="bg-[#161b26]/95 backdrop-blur-xl rounded-2xl shadow-2xl shadow-black/50 border border-white/[0.08] w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto animate-scale-in" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h3 className="text-lg font-semibold text-slate-100">Add New Client</h3>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400 animate-fade-in">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Firm / Client Name *</label>
            <input
              type="text"
              value={form.firm_name}
              onChange={(e: ChangeEvent<HTMLInputElement>) => update('firm_name', e.target.value)}
              placeholder="e.g. Sharma & Associates"
              className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">PAN</label>
              <input
                type="text"
                value={form.pan || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => update('pan', e.target.value.toUpperCase())}
                placeholder="ABCDE1234F"
                maxLength={10}
                className="w-full px-3 py-2.5 rounded-xl text-sm outline-none uppercase font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">GSTIN</label>
              <input
                type="text"
                value={form.gstin || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => update('gstin', e.target.value.toUpperCase())}
                placeholder="22ABCDE1234F1Z5"
                maxLength={15}
                className="w-full px-3 py-2.5 rounded-xl text-sm outline-none uppercase font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Entity Type</label>
            <select
              value={form.entity_type || 'individual'}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => update('entity_type', e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
            >
              {entityTypes.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Contact Person</label>
            <input
              type="text"
              value={form.contact_person || ''}
              onChange={(e: ChangeEvent<HTMLInputElement>) => update('contact_person', e.target.value)}
              placeholder="Full Name"
              className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
              <input
                type="email"
                value={form.email || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => update('email', e.target.value)}
                placeholder="client@example.com"
                className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Phone</label>
              <input
                type="tel"
                value={form.phone || ''}
                onChange={(e: ChangeEvent<HTMLInputElement>) => update('phone', e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2.5 rounded-xl text-sm outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-5 py-2.5 text-sm font-medium gradient-brand text-white rounded-xl flex items-center gap-2 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 hover-lift disabled:opacity-50 transition-all"
            >
              {mutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Add Client
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState<T>(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

type SortField = 'firm_name' | 'pan' | 'entity_type' | 'created_at' | 'status';
type SortDir = 'asc' | 'desc';

export default function ClientList() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState<string>('');
  const search = useDebounce(searchInput, 300);
  const [page, setPage] = useState<number>(1);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [filterEntityType, setFilterEntityType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [sortField, setSortField] = useState<SortField>('firm_name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const pageSize = 20;

  // Reset page when search/filter changes
  useEffect(() => { setPage(1); }, [search, filterEntityType, filterStatus]);

  const { data, isLoading, isError } = useQuery<ClientListResponse | Client[]>({
    queryKey: ['clients', { search, page, pageSize, filterEntityType, filterStatus }],
    queryFn: () => {
      const params: Record<string, unknown> = { search, page, page_size: pageSize };
      if (filterEntityType) params.entity_type = filterEntityType;
      if (filterStatus) params.status = filterStatus;
      return clientsApi.list(params);
    },
  });

  const normalizedData = data as ClientListResponse | undefined;
  const clients: Client[] = normalizedData?.items || normalizedData?.clients || (Array.isArray(data) ? data : []);
  const total: number = normalizedData?.total || clients.length;
  const totalPages: number = Math.max(1, Math.ceil(total / pageSize));

  // Client-side sorting
  const sortedClients = [...clients].sort((a, b) => {
    const aVal = (a[sortField] || '').toString().toLowerCase();
    const bVal = (b[sortField] || '').toString().toLowerCase();
    const cmp = aVal.localeCompare(bVal);
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === sortedClients.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sortedClients.map(c => c.id)));
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ChevronDown className="w-3 h-3 opacity-30" />;
    return sortDir === 'asc'
      ? <ChevronUp className="w-3 h-3 text-blue-400" />
      : <ChevronDown className="w-3 h-3 text-blue-400" />;
  };

  const entityTypes = [
    { value: 'individual', label: 'Individual' },
    { value: 'huf', label: 'HUF' },
    { value: 'partnership', label: 'Partnership' },
    { value: 'llp', label: 'LLP' },
    { value: 'private_limited', label: 'Pvt. Ltd.' },
    { value: 'public_limited', label: 'Public Ltd.' },
    { value: 'trust', label: 'Trust' },
    { value: 'society', label: 'Society' },
  ];

  const entityLabel = (type: string | undefined): string => {
    const found = entityTypes.find(t => t.value === type);
    return found?.label || type || '--';
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 animate-stagger-1">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Clients</h1>
          <p className="text-sm text-slate-400">Manage your client portfolio</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white text-sm font-medium rounded-xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 hover-lift transition-all"
        >
          <Plus className="w-4 h-4" /> Add Client
        </button>
      </div>

      {/* Search bar and filters */}
      <div className="card p-4 animate-stagger-2 space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchInput}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchInput(e.target.value)}
              placeholder="Search by name, PAN, or GSTIN..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-2 px-3 py-2.5 border text-sm font-medium rounded-xl transition-colors ${
              showFilters || filterEntityType || filterStatus
                ? 'border-blue-500/30 text-blue-400 bg-blue-500/5'
                : 'border-white/[0.08] text-slate-300 hover:bg-white/[0.04]'
            }`}
          >
            <Filter className="w-4 h-4" /> Filters
            {(filterEntityType || filterStatus) && (
              <span className="ml-1 px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                {[filterEntityType, filterStatus].filter(Boolean).length}
              </span>
            )}
          </button>
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <span>{selectedIds.size} selected</span>
              <button
                onClick={() => {
                  // Export selected as CSV
                  const selected = sortedClients.filter(c => selectedIds.has(c.id));
                  const csv = ['Name,PAN,GSTIN,Type,Email,Phone']
                    .concat(selected.map(c =>
                      `"${c.firm_name || c.name || ''}","${c.pan || ''}","${c.gstin || ''}","${c.entity_type || ''}","${c.email || ''}","${c.phone || ''}"`
                    )).join('\n');
                  const blob = new Blob([csv], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url; a.download = 'clients_export.csv'; a.click();
                  URL.revokeObjectURL(url);
                }}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-emerald-400 border border-emerald-500/20 rounded-lg hover:bg-emerald-500/5 transition-colors"
              >
                <Download className="w-3 h-3" /> Export CSV
              </button>
              <button
                onClick={() => setSelectedIds(new Set())}
                className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                Clear
              </button>
            </div>
          )}
        </div>

        {showFilters && (
          <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-white/[0.04] animate-fade-in">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Entity Type</label>
              <select
                value={filterEntityType}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterEntityType(e.target.value)}
                className="px-3 py-2 rounded-xl text-sm outline-none min-w-[160px]"
              >
                <option value="">All Types</option>
                {entityTypes.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Status</label>
              <select
                value={filterStatus}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterStatus(e.target.value)}
                className="px-3 py-2 rounded-xl text-sm outline-none min-w-[140px]"
              >
                <option value="">All</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            {(filterEntityType || filterStatus) && (
              <button
                onClick={() => { setFilterEntityType(''); setFilterStatus(''); }}
                className="self-end px-3 py-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                Clear Filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden animate-stagger-3">
        {isLoading ? (
          <div className="p-8 text-center">
            <Loader2 className="w-6 h-6 animate-spin text-blue-400 mx-auto" />
            <p className="text-sm text-slate-400 mt-2">Loading clients...</p>
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-sm text-red-400">Failed to load clients. Please try again.</div>
        ) : clients.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-300 font-medium">No clients found</p>
            <p className="text-sm text-slate-500 mt-1">
              {search ? 'Try a different search term' : 'Add your first client to get started'}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-white/[0.02] border-b border-white/[0.06]">
                    <th className="px-3 py-3 w-10">
                      <button onClick={toggleSelectAll} className="text-slate-500 hover:text-slate-300 transition-colors">
                        {selectedIds.size === sortedClients.length && sortedClients.length > 0
                          ? <CheckSquare className="w-4 h-4 text-blue-400" />
                          : <Square className="w-4 h-4" />
                        }
                      </button>
                    </th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer select-none" onClick={() => toggleSort('firm_name')}>
                      <span className="inline-flex items-center gap-1">Firm Name <SortIcon field="firm_name" /></span>
                    </th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden sm:table-cell cursor-pointer select-none" onClick={() => toggleSort('pan')}>
                      <span className="inline-flex items-center gap-1">PAN <SortIcon field="pan" /></span>
                    </th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden md:table-cell cursor-pointer select-none" onClick={() => toggleSort('entity_type')}>
                      <span className="inline-flex items-center gap-1">Entity Type <SortIcon field="entity_type" /></span>
                    </th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden lg:table-cell">Contact</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer select-none" onClick={() => toggleSort('status')}>
                      <span className="inline-flex items-center gap-1">Status <SortIcon field="status" /></span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.03]">
                  {sortedClients.map((client, i) => (
                    <tr
                      key={client.id}
                      className="row-hover cursor-pointer animate-row"
                      style={{ animationDelay: `${i * 30}ms` }}
                    >
                      <td className="px-3 py-3" onClick={(e) => { e.stopPropagation(); toggleSelect(client.id); }}>
                        {selectedIds.has(client.id)
                          ? <CheckSquare className="w-4 h-4 text-blue-400" />
                          : <Square className="w-4 h-4 text-slate-600 hover:text-slate-400" />
                        }
                      </td>
                      <td className="px-5 py-3" onClick={() => navigate(`/clients/${client.id}`)}>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-500/15 border border-blue-500/20 text-blue-400 rounded-lg flex items-center justify-center text-xs font-bold shrink-0">
                            {(client.firm_name || client.name || '?')[0].toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-slate-200 truncate">{client.firm_name || client.name}</p>
                            <p className="text-xs text-slate-500 truncate sm:hidden">{client.pan || ''}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-sm text-slate-400 font-mono hidden sm:table-cell">
                        {client.pan || '--'}
                      </td>
                      <td className="px-5 py-3 text-sm text-slate-400 hidden md:table-cell">
                        {entityLabel(client.entity_type)}
                      </td>
                      <td className="px-5 py-3 hidden lg:table-cell">
                        <div className="text-sm text-slate-300">{client.contact_person || '--'}</div>
                        <div className="text-xs text-slate-500">{client.email || client.phone || ''}</div>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`inline-block px-2.5 py-0.5 text-xs font-medium rounded-full ${statusColor(client.status || 'active')}`}>
                          {client.status || 'Active'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-white/[0.04]">
                <p className="text-sm text-slate-400">
                  Showing {((page - 1) * pageSize) + 1}--{Math.min(page * pageSize, total)} of {total}
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-1.5 rounded-lg text-slate-400 hover:bg-white/[0.06] disabled:opacity-30 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="px-3 py-1 text-sm text-slate-400">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-1.5 rounded-lg text-slate-400 hover:bg-white/[0.06] disabled:opacity-30 transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {showAddModal && <AddClientModal onClose={() => setShowAddModal(false)} />}
    </div>
  );
}
