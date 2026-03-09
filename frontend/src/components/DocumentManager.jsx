import { useState, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi, clientsApi } from '../api/client';
import {
  Upload,
  FileText,
  Search,
  Filter,
  Loader2,
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
  Eye,
  ChevronDown,
  File,
  FileSpreadsheet,
  Image,
} from 'lucide-react';
import { formatDate, formatDateTime, statusColor } from '../utils/format';

function fileIcon(name) {
  if (!name) return File;
  const ext = name.split('.').pop()?.toLowerCase();
  if (['pdf'].includes(ext)) return FileText;
  if (['xls', 'xlsx', 'csv'].includes(ext)) return FileSpreadsheet;
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return Image;
  return File;
}

export default function DocumentManager() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterClient, setFilterClient] = useState('');
  const [filterType, setFilterType] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [uploadClient, setUploadClient] = useState('');
  const [uploadDocType, setUploadDocType] = useState('');
  const [selectedDoc, setSelectedDoc] = useState(null);

  const params = {};
  if (filterClient) params.client_id = filterClient;
  if (filterType) params.document_type = filterType;

  const { data: docs, isLoading } = useQuery({
    queryKey: ['documents', params],
    queryFn: () => documentsApi.list(params),
  });

  const { data: searchResults, isFetching: searching } = useQuery({
    queryKey: ['documents', 'search', searchQuery],
    queryFn: () => documentsApi.search(searchQuery),
    enabled: searchQuery.length >= 3,
  });

  const { data: clients } = useQuery({
    queryKey: ['clients', 'list-all'],
    queryFn: () => clientsApi.list({ page_size: 200 }),
  });

  const clientList = clients?.items || clients?.clients || (Array.isArray(clients) ? clients : []);

  const uploadMutation = useMutation({
    mutationFn: (file) => documentsApi.upload(file, uploadClient || undefined, uploadDocType || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleFiles = useCallback((files) => {
    Array.from(files).forEach((file) => {
      uploadMutation.mutate(file);
    });
  }, [uploadMutation]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const docList = searchQuery.length >= 3
    ? (searchResults?.items || searchResults?.documents || (Array.isArray(searchResults) ? searchResults : []))
    : (docs?.items || docs?.documents || (Array.isArray(docs) ? docs : []));

  const docTypes = ['form_16', 'form_26as', 'bank_statement', 'balance_sheet', 'gst_return', 'itr', 'notice', 'invoice', 'other'];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Documents</h1>
          <p className="text-sm text-slate-500">Upload, search, and manage client documents</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="inline-flex items-center gap-2 px-3 py-2 border border-slate-300 text-sm font-medium text-slate-600 rounded-lg hover:bg-slate-50"
        >
          <Filter className="w-4 h-4" /> Filters <ChevronDown className="w-3 h-3" />
        </button>
      </div>

      {/* Upload area */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={() => setDragging(false)}
        className={`bg-white rounded-xl border-2 border-dashed p-8 text-center transition-colors
          ${dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'}`}
      >
        <Upload className={`w-10 h-10 mx-auto mb-3 ${dragging ? 'text-blue-500' : 'text-slate-400'}`} />
        <p className="text-sm font-medium text-slate-700">
          {dragging ? 'Drop files here' : 'Drag & drop files here, or click to browse'}
        </p>
        <p className="text-xs text-slate-400 mt-1">PDF, Excel, Images, and more</p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-4">
          <select
            value={uploadClient}
            onChange={(e) => setUploadClient(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          >
            <option value="">No Client (General)</option>
            {clientList.map((c) => (
              <option key={c.id} value={c.id}>{c.firm_name || c.name}</option>
            ))}
          </select>
          <select
            value={uploadDocType}
            onChange={(e) => setUploadDocType(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          >
            <option value="">Auto-detect Type</option>
            {docTypes.map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
            ))}
          </select>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg"
          >
            Browse Files
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => { if (e.target.files?.length) handleFiles(e.target.files); e.target.value = ''; }}
          />
        </div>

        {uploadMutation.isPending && (
          <div className="flex items-center justify-center gap-2 mt-4 text-sm text-blue-600">
            <Loader2 className="w-4 h-4 animate-spin" /> Uploading...
          </div>
        )}
        {uploadMutation.isSuccess && (
          <div className="flex items-center justify-center gap-2 mt-4 text-sm text-green-600">
            <CheckCircle2 className="w-4 h-4" /> Upload successful!
          </div>
        )}
        {uploadMutation.isError && (
          <div className="flex items-center justify-center gap-2 mt-4 text-sm text-red-600">
            <AlertCircle className="w-4 h-4" /> {uploadMutation.error?.response?.data?.detail || 'Upload failed'}
          </div>
        )}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1">Client</label>
            <select
              value={filterClient}
              onChange={(e) => setFilterClient(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            >
              <option value="">All Clients</option>
              {clientList.map((c) => (
                <option key={c.id} value={c.id}>{c.firm_name || c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Type</label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            >
              <option value="">All Types</option>
              {docTypes.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="relative max-w-lg">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents (semantic search, min 3 characters)..."
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          {searching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-blue-500" />}
        </div>
      </div>

      {/* Document list */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            <p className="text-sm text-slate-500 mt-2">Loading documents...</p>
          </div>
        ) : docList.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-600 font-medium">No documents found</p>
            <p className="text-sm text-slate-400 mt-1">Upload documents to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {docList.map((doc, i) => {
              const Icon = fileIcon(doc.filename || doc.name);
              return (
                <div
                  key={doc.id || i}
                  className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50 cursor-pointer transition-colors"
                  onClick={() => setSelectedDoc(doc)}
                >
                  <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-700 truncate">{doc.filename || doc.name}</p>
                    <div className="flex gap-3 mt-0.5">
                      {doc.client_name && <span className="text-xs text-slate-400">{doc.client_name}</span>}
                      <span className="text-xs text-slate-400">{doc.document_type?.replace(/_/g, ' ') || ''}</span>
                      <span className="text-xs text-slate-400">{formatDate(doc.uploaded_at || doc.created_at)}</span>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full shrink-0 ${statusColor(doc.status || 'uploaded')}`}>
                    {doc.status || 'Uploaded'}
                  </span>
                  <Eye className="w-4 h-4 text-slate-400 shrink-0" />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Document detail modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setSelectedDoc(null)}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-800 truncate">{selectedDoc.filename || selectedDoc.name}</h3>
              <button onClick={() => setSelectedDoc(null)} className="p-1 text-slate-400 hover:text-slate-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-400 text-xs mb-0.5">Type</p>
                  <p className="text-slate-700 font-medium">{selectedDoc.document_type?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || '--'}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs mb-0.5">Status</p>
                  <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(selectedDoc.status || 'uploaded')}`}>
                    {selectedDoc.status || 'Uploaded'}
                  </span>
                </div>
                <div>
                  <p className="text-slate-400 text-xs mb-0.5">Client</p>
                  <p className="text-slate-700">{selectedDoc.client_name || '--'}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs mb-0.5">Uploaded</p>
                  <p className="text-slate-700">{formatDateTime(selectedDoc.uploaded_at || selectedDoc.created_at)}</p>
                </div>
              </div>

              {selectedDoc.summary && (
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-1">Summary</p>
                  <div className="p-3 bg-slate-50 rounded-lg text-sm text-slate-700">{selectedDoc.summary}</div>
                </div>
              )}

              {selectedDoc.parsed_data && (
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-1">Parsed Data</p>
                  <pre className="p-3 bg-slate-50 rounded-lg text-xs text-slate-600 overflow-x-auto">
                    {typeof selectedDoc.parsed_data === 'string'
                      ? selectedDoc.parsed_data
                      : JSON.stringify(selectedDoc.parsed_data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
