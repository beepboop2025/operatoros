import { useState, useRef, useCallback, ChangeEvent, DragEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi, clientsApi } from '../api/client';
import type {
  Client,
  Document as DocType,
  ClientListResponse,
  DocumentListResponse,
} from '../api/client';
import {
  Upload,
  FileText,
  Search,
  Filter,
  Loader2,
  X,
  CheckCircle2,
  AlertCircle,
  Eye,
  ChevronDown,
  File,
  FileSpreadsheet,
  Image,
  LucideIcon,
} from 'lucide-react';
import { formatDate, formatDateTime, statusColor } from '../utils/format';

function fileIcon(name: string | undefined): LucideIcon {
  if (!name) return File;
  const ext = name.split('.').pop()?.toLowerCase();
  if (ext && ['pdf'].includes(ext)) return FileText;
  if (ext && ['xls', 'xlsx', 'csv'].includes(ext)) return FileSpreadsheet;
  if (ext && ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return Image;
  return File;
}

export default function DocumentManager() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterClient, setFilterClient] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [uploadClient, setUploadClient] = useState<string>('');
  const [uploadDocType, setUploadDocType] = useState<string>('');
  const [selectedDoc, setSelectedDoc] = useState<DocType | null>(null);

  const params: Record<string, string> = {};
  if (filterClient) params.client_id = filterClient;
  if (filterType) params.document_type = filterType;

  const { data: docs, isLoading } = useQuery<DocumentListResponse | DocType[]>({
    queryKey: ['documents', params],
    queryFn: () => documentsApi.list(params),
  });

  const { data: searchResults, isFetching: searching } = useQuery<DocumentListResponse | DocType[]>({
    queryKey: ['documents', 'search', searchQuery],
    queryFn: () => documentsApi.search(searchQuery),
    enabled: searchQuery.length >= 3,
  });

  const { data: clients } = useQuery<ClientListResponse | Client[]>({
    queryKey: ['clients', 'list-all'],
    queryFn: () => clientsApi.list({ page_size: 200 }),
  });

  const normalizedClients = clients as ClientListResponse | undefined;
  const clientList: Client[] = normalizedClients?.items || normalizedClients?.clients || (Array.isArray(clients) ? clients : []);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsApi.upload(file, uploadClient || undefined, uploadDocType || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleFiles = useCallback((files: FileList) => {
    Array.from(files).forEach((file) => {
      uploadMutation.mutate(file);
    });
  }, [uploadMutation]);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const normalizeDocList = (data: DocumentListResponse | DocType[] | undefined): DocType[] => {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    return data.items || data.documents || [];
  };

  const docList: DocType[] = searchQuery.length >= 3
    ? normalizeDocList(searchResults)
    : normalizeDocList(docs);

  const docTypes: string[] = ['form_16', 'form_26as', 'bank_statement', 'balance_sheet', 'gst_return', 'itr', 'notice', 'invoice', 'other'];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Documents</h1>
          <p className="text-sm text-stone-500">Upload, search, and manage client documents</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="inline-flex items-center gap-2 px-3 py-2.5 border border-stone-200 text-sm font-medium text-stone-600 rounded-xl hover:bg-stone-50 transition-colors"
        >
          <Filter className="w-4 h-4" /> Filters <ChevronDown className="w-3 h-3" />
        </button>
      </div>

      {/* Upload area */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={() => setDragging(false)}
        className={`card border-2 border-dashed p-8 text-center transition-all
          ${dragging ? 'border-blue-500 bg-blue-50/50' : 'border-stone-300 hover:border-stone-400'}`}
      >
        <Upload className={`w-10 h-10 mx-auto mb-3 ${dragging ? 'text-blue-500' : 'text-stone-400'}`} />
        <p className="text-sm font-medium text-stone-700">
          {dragging ? 'Drop files here' : 'Drag & drop files here, or click to browse'}
        </p>
        <p className="text-xs text-stone-400 mt-1">PDF, Excel, Images, and more</p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-4">
          <select
            value={uploadClient}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setUploadClient(e.target.value)}
            className="px-3 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
          >
            <option value="">No Client (General)</option>
            {clientList.map((c) => (
              <option key={c.id} value={c.id}>{c.firm_name || c.name}</option>
            ))}
          </select>
          <select
            value={uploadDocType}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setUploadDocType(e.target.value)}
            className="px-3 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
          >
            <option value="">Auto-detect Type</option>
            {docTypes.map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
            ))}
          </select>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2.5 gradient-brand text-white text-sm font-medium rounded-xl shadow-sm hover:opacity-90 transition-all"
          >
            Browse Files
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e: ChangeEvent<HTMLInputElement>) => { if (e.target.files?.length) handleFiles(e.target.files); e.target.value = ''; }}
          />
        </div>

        {uploadMutation.isPending && (
          <div className="flex items-center justify-center gap-2 mt-4 text-sm text-blue-600">
            <Loader2 className="w-4 h-4 animate-spin" /> Uploading...
          </div>
        )}
        {uploadMutation.isSuccess && (
          <div className="flex items-center justify-center gap-2 mt-4 text-sm text-emerald-600">
            <CheckCircle2 className="w-4 h-4" /> Upload successful!
          </div>
        )}
        {uploadMutation.isError && (
          <div className="flex items-center justify-center gap-2 mt-4 text-sm text-red-600">
            <AlertCircle className="w-4 h-4" /> {(uploadMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed'}
          </div>
        )}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="card p-4 flex flex-col sm:flex-row gap-3 animate-fade-in">
          <div className="flex-1">
            <label className="block text-xs font-medium text-stone-500 mb-1.5">Client</label>
            <select
              value={filterClient}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterClient(e.target.value)}
              className="w-full px-3 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
            >
              <option value="">All Clients</option>
              {clientList.map((c) => (
                <option key={c.id} value={c.id}>{c.firm_name || c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-stone-500 mb-1.5">Type</label>
            <select
              value={filterType}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterType(e.target.value)}
              className="w-full px-3 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
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
      <div className="card p-4">
        <div className="relative max-w-lg">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
            placeholder="Search documents (semantic search, min 3 characters)..."
            className="w-full pl-10 pr-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
          />
          {searching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-blue-500" />}
        </div>
      </div>

      {/* Document list */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            <p className="text-sm text-stone-500 mt-2">Loading documents...</p>
          </div>
        ) : docList.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-stone-300 mx-auto mb-3" />
            <p className="text-stone-600 font-medium">No documents found</p>
            <p className="text-sm text-stone-400 mt-1">Upload documents to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-stone-100">
            {docList.map((doc) => {
              const Icon = fileIcon(doc.filename || doc.name);
              return (
                <div
                  key={doc.id}
                  className="flex items-center gap-4 px-5 py-3 hover:bg-stone-50 cursor-pointer transition-colors"
                  onClick={() => setSelectedDoc(doc)}
                >
                  <div className="w-10 h-10 bg-stone-100 rounded-xl flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-stone-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-stone-700 truncate">{doc.filename || doc.name}</p>
                    <div className="flex gap-3 mt-0.5">
                      {doc.client_name && <span className="text-xs text-stone-400">{doc.client_name}</span>}
                      <span className="text-xs text-stone-400">{doc.document_type?.replace(/_/g, ' ') || ''}</span>
                      <span className="text-xs text-stone-400">{formatDate(doc.uploaded_at || doc.created_at)}</span>
                    </div>
                  </div>
                  <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full shrink-0 ${statusColor(doc.status || 'uploaded')}`}>
                    {doc.status || 'Uploaded'}
                  </span>
                  <Eye className="w-4 h-4 text-stone-400 shrink-0" />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Document detail modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setSelectedDoc(null)}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-stone-200">
              <h3 className="text-lg font-semibold text-stone-800 truncate">{selectedDoc.filename || selectedDoc.name}</h3>
              <button onClick={() => setSelectedDoc(null)} className="p-1 text-stone-400 hover:text-stone-600 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-stone-400 text-xs mb-0.5">Type</p>
                  <p className="text-stone-700 font-medium">{selectedDoc.document_type?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || '--'}</p>
                </div>
                <div>
                  <p className="text-stone-400 text-xs mb-0.5">Status</p>
                  <span className={`inline-block px-2.5 py-0.5 text-xs font-medium rounded-full ${statusColor(selectedDoc.status || 'uploaded')}`}>
                    {selectedDoc.status || 'Uploaded'}
                  </span>
                </div>
                <div>
                  <p className="text-stone-400 text-xs mb-0.5">Client</p>
                  <p className="text-stone-700">{selectedDoc.client_name || '--'}</p>
                </div>
                <div>
                  <p className="text-stone-400 text-xs mb-0.5">Uploaded</p>
                  <p className="text-stone-700">{formatDateTime(selectedDoc.uploaded_at || selectedDoc.created_at)}</p>
                </div>
              </div>

              {selectedDoc.summary && (
                <div>
                  <p className="text-xs font-medium text-stone-500 mb-1">Summary</p>
                  <div className="p-3 bg-stone-50 rounded-xl text-sm text-stone-700">{selectedDoc.summary}</div>
                </div>
              )}

              {selectedDoc.parsed_data && (
                <div>
                  <p className="text-xs font-medium text-stone-500 mb-1">Parsed Data</p>
                  <pre className="p-3 bg-stone-50 rounded-xl text-xs text-stone-600 overflow-x-auto">
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
