import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { clientsApi } from '../api/client';
import {
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  Loader2,
  Users,
  Building2,
  Phone,
  Mail,
} from 'lucide-react';
import { statusColor } from '../utils/format';

function AddClientModal({ onClose, onSuccess }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    firm_name: '',
    pan: '',
    gstin: '',
    entity_type: 'individual',
    contact_person: '',
    email: '',
    phone: '',
  });
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: clientsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      onSuccess?.();
      onClose();
    },
    onError: (err) => {
      setError(err.response?.data?.detail || 'Failed to create client');
    },
  });

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.firm_name.trim()) {
      setError('Firm name is required');
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
    { value: 'pvt_ltd', label: 'Private Limited' },
    { value: 'public_ltd', label: 'Public Limited' },
    { value: 'trust', label: 'Trust' },
    { value: 'society', label: 'Society' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">Add New Client</h3>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Firm / Client Name *</label>
            <input
              type="text"
              value={form.firm_name}
              onChange={(e) => update('firm_name', e.target.value)}
              placeholder="e.g. Sharma & Associates"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">PAN</label>
              <input
                type="text"
                value={form.pan}
                onChange={(e) => update('pan', e.target.value.toUpperCase())}
                placeholder="ABCDE1234F"
                maxLength={10}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none uppercase"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">GSTIN</label>
              <input
                type="text"
                value={form.gstin}
                onChange={(e) => update('gstin', e.target.value.toUpperCase())}
                placeholder="22ABCDE1234F1Z5"
                maxLength={15}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none uppercase"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Entity Type</label>
            <select
              value={form.entity_type}
              onChange={(e) => update('entity_type', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
            >
              {entityTypes.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Contact Person</label>
            <input
              type="text"
              value={form.contact_person}
              onChange={(e) => update('contact_person', e.target.value)}
              placeholder="Full Name"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => update('email', e.target.value)}
                placeholder="client@example.com"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Phone</label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => update('phone', e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 text-sm font-medium bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg flex items-center gap-2"
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
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const pageSize = 20;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['clients', { search, page, pageSize }],
    queryFn: () => clientsApi.list({ search, page, page_size: pageSize }),
  });

  const clients = data?.items || data?.clients || (Array.isArray(data) ? data : []);
  const total = data?.total || clients.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const entityLabel = (type) => {
    const map = {
      individual: 'Individual',
      huf: 'HUF',
      partnership: 'Partnership',
      llp: 'LLP',
      pvt_ltd: 'Pvt. Ltd.',
      public_ltd: 'Public Ltd.',
      trust: 'Trust',
      society: 'Society',
    };
    return map[type] || type || '--';
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Clients</h1>
          <p className="text-sm text-slate-500">Manage your client portfolio</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg shadow-sm"
        >
          <Plus className="w-4 h-4" /> Add Client
        </button>
      </div>

      {/* Search bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name, PAN, or GSTIN..."
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            <p className="text-sm text-slate-500 mt-2">Loading clients...</p>
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-sm text-red-500">Failed to load clients. Please try again.</div>
        ) : clients.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-600 font-medium">No clients found</p>
            <p className="text-sm text-slate-400 mt-1">
              {search ? 'Try a different search term' : 'Add your first client to get started'}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Firm Name</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:table-cell">PAN</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">Entity Type</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">Contact</th>
                    <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {clients.map((client) => (
                    <tr
                      key={client.id}
                      onClick={() => navigate(`/clients/${client.id}`)}
                      className="hover:bg-blue-50/50 cursor-pointer transition-colors"
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center text-xs font-bold shrink-0">
                            {(client.firm_name || client.name || '?')[0].toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-slate-800 truncate">{client.firm_name || client.name}</p>
                            <p className="text-xs text-slate-400 truncate sm:hidden">{client.pan || ''}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-sm text-slate-600 font-mono hidden sm:table-cell">
                        {client.pan || '--'}
                      </td>
                      <td className="px-5 py-3 text-sm text-slate-600 hidden md:table-cell">
                        {entityLabel(client.entity_type)}
                      </td>
                      <td className="px-5 py-3 hidden lg:table-cell">
                        <div className="text-sm text-slate-600">{client.contact_person || '--'}</div>
                        <div className="text-xs text-slate-400">{client.email || client.phone || ''}</div>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(client.status || 'active')}`}>
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
              <div className="flex items-center justify-between px-5 py-3 border-t border-slate-200">
                <p className="text-sm text-slate-500">
                  Showing {((page - 1) * pageSize) + 1}--{Math.min(page * pageSize, total)} of {total}
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-1.5 rounded text-slate-500 hover:bg-slate-100 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="px-3 py-1 text-sm text-slate-600">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-1.5 rounded text-slate-500 hover:bg-slate-100 disabled:opacity-40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Add client modal */}
      {showAddModal && <AddClientModal onClose={() => setShowAddModal(false)} />}
    </div>
  );
}
