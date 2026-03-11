import { useState, FormEvent, ChangeEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { clientsApi } from '../api/client';
import type { Client, ClientCreateRequest, ClientListResponse } from '../api/client';
import {
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  Loader2,
  Users,
  Building2,
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

export default function ClientList() {
  const navigate = useNavigate();
  const [search, setSearch] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const pageSize = 20;

  const { data, isLoading, isError } = useQuery<ClientListResponse | Client[]>({
    queryKey: ['clients', { search, page, pageSize }],
    queryFn: () => clientsApi.list({ search, page, page_size: pageSize }),
  });

  const normalizedData = data as ClientListResponse | undefined;
  const clients: Client[] = normalizedData?.items || normalizedData?.clients || (Array.isArray(data) ? data : []);
  const total: number = normalizedData?.total || clients.length;
  const totalPages: number = Math.max(1, Math.ceil(total / pageSize));

  const entityLabel = (type: string | undefined): string => {
    const map: Record<string, string> = {
      individual: 'Individual', huf: 'HUF', partnership: 'Partnership', llp: 'LLP',
      private_limited: 'Pvt. Ltd.', public_limited: 'Public Ltd.', trust: 'Trust', society: 'Society',
    };
    return map[type ?? ''] || type || '--';
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

      {/* Search bar */}
      <div className="card p-4 animate-stagger-2">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e: ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name, PAN, or GSTIN..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm outline-none"
          />
        </div>
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
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Firm Name</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden sm:table-cell">PAN</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden md:table-cell">Entity Type</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden lg:table-cell">Contact</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.03]">
                  {clients.map((client, i) => (
                    <tr
                      key={client.id}
                      onClick={() => navigate(`/clients/${client.id}`)}
                      className="row-hover cursor-pointer animate-row"
                      style={{ animationDelay: `${i * 30}ms` }}
                    >
                      <td className="px-5 py-3">
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
