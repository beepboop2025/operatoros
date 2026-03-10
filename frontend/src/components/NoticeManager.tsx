import { useState, useRef, ChangeEvent, ReactElement } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { noticesApi, documentsApi } from '../api/client';
import type {
  Notice,
  NoticeListResponse,
  DraftNoticeResponse,
} from '../api/client';
import {
  AlertTriangle,
  Upload,
  Loader2,
  Eye,
  FileText,
  X,
  Send,
  Clock,
  CheckCircle2,
  AlertCircle,
  Shield,
  Filter,
  LucideIcon,
} from 'lucide-react';
import { formatDate, formatDateTime, statusColor } from '../utils/format';

const URGENCY_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700 border-red-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-green-100 text-green-700 border-green-200',
};

export default function NoticeManager() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedNotice, setSelectedNotice] = useState<Notice | null>(null);
  const [showUpload, setShowUpload] = useState<boolean>(false);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [draftingId, setDraftingId] = useState<string | null>(null);

  const params: Record<string, string> = {};
  if (filterStatus) params.status = filterStatus;

  const { data: notices, isLoading } = useQuery<NoticeListResponse | Notice[]>({
    queryKey: ['notices', params],
    queryFn: () => noticesApi.list(params),
  });

  const normalizedNotices = notices as NoticeListResponse | undefined;
  const noticeList: Notice[] = normalizedNotices?.items || normalizedNotices?.notices || (Array.isArray(notices) ? notices : []);

  const processMutation = useMutation({
    mutationFn: (id: string) => noticesApi.process(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notices'] });
    },
  });

  const draftMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => noticesApi.draftResponse(id, data),
    onSuccess: (data: DraftNoticeResponse) => {
      setDraftingId(null);
      if (selectedNotice) {
        setSelectedNotice({ ...selectedNotice, draft_response: data.draft || data.response });
      }
      queryClient.invalidateQueries({ queryKey: ['notices'] });
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsApi.upload(file, undefined, 'notice'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notices'] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setShowUpload(false);
    },
  });

  const handleFileUpload = (files: FileList) => {
    Array.from(files).forEach((file) => uploadMutation.mutate(file));
  };

  const urgencyBadge = (urgency: string | undefined): ReactElement => {
    const colors = URGENCY_COLORS[urgency ?? ''] || URGENCY_COLORS.medium;
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${colors}`}>
        {urgency === 'high' && <AlertCircle className="w-3 h-3" />}
        {urgency ? urgency.charAt(0).toUpperCase() + urgency.slice(1) : 'Medium'}
      </span>
    );
  };

  const noticeTypeIcon = (type: string | undefined): LucideIcon => {
    switch (type) {
      case 'scrutiny': return Shield;
      case 'demand': return AlertTriangle;
      default: return FileText;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Notices</h1>
          <p className="text-sm text-stone-500">Track and respond to tax notices</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <select
              value={filterStatus}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterStatus(e.target.value)}
              className="pl-8 pr-3 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none appearance-none"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="draft_ready">Draft Ready</option>
              <option value="responded">Responded</option>
              <option value="closed">Closed</option>
            </select>
            <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-stone-400" />
          </div>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="inline-flex items-center gap-2 px-4 py-2.5 gradient-brand text-white text-sm font-medium rounded-xl shadow-sm hover:opacity-90 transition-all"
          >
            <Upload className="w-4 h-4" /> Upload Notice
          </button>
        </div>
      </div>

      {/* Upload panel */}
      {showUpload && (
        <div className="card p-6 text-center animate-fade-in">
          <Upload className="w-8 h-8 text-stone-400 mx-auto mb-2" />
          <p className="text-sm text-stone-600 mb-3">Upload a notice document for processing</p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-4 py-2.5 gradient-brand text-white text-sm font-medium rounded-xl shadow-sm"
          >
            Choose File
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={(e: ChangeEvent<HTMLInputElement>) => { if (e.target.files?.length) handleFileUpload(e.target.files); e.target.value = ''; }}
          />
          {uploadMutation.isPending && (
            <div className="flex items-center justify-center gap-2 mt-3 text-sm text-blue-600">
              <Loader2 className="w-4 h-4 animate-spin" /> Uploading and processing...
            </div>
          )}
          {uploadMutation.isError && (
            <p className="text-sm text-red-600 mt-3">
              {(uploadMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed'}
            </p>
          )}
        </div>
      )}

      {/* Notice list */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            <p className="text-sm text-stone-500 mt-2">Loading notices...</p>
          </div>
        ) : noticeList.length === 0 ? (
          <div className="p-12 text-center">
            <AlertTriangle className="w-10 h-10 text-stone-300 mx-auto mb-3" />
            <p className="text-stone-600 font-medium">No notices found</p>
            <p className="text-sm text-stone-400 mt-1">Upload a notice to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-stone-100">
            {noticeList.map((notice) => {
              const Icon = noticeTypeIcon(notice.notice_type || notice.type);
              return (
                <div
                  key={notice.id}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-stone-50 cursor-pointer transition-colors"
                  onClick={() => setSelectedNotice(notice)}
                >
                  <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5 text-red-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-stone-700 truncate">
                        {notice.title || notice.notice_type || 'Tax Notice'}
                      </p>
                      {notice.urgency && urgencyBadge(notice.urgency)}
                    </div>
                    <div className="flex gap-3 mt-0.5">
                      {notice.client_name && <span className="text-xs text-stone-400">{notice.client_name}</span>}
                      {notice.section && <span className="text-xs text-stone-400">Section {notice.section}</span>}
                      <span className="text-xs text-stone-400">{formatDate(notice.notice_date || notice.created_at)}</span>
                    </div>
                  </div>
                  {notice.response_due_date && (
                    <div className="hidden sm:block text-right shrink-0">
                      <p className="text-xs text-stone-400">Response Due</p>
                      <p className="text-xs font-medium text-stone-600">{formatDate(notice.response_due_date)}</p>
                    </div>
                  )}
                  <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full shrink-0 ${statusColor(notice.status || 'pending')}`}>
                    {notice.status || 'Pending'}
                  </span>
                  <Eye className="w-4 h-4 text-stone-400 shrink-0" />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Notice detail modal */}
      {selectedNotice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setSelectedNotice(null)}>
          <div
            className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-stone-200">
              <div>
                <h3 className="text-lg font-semibold text-stone-800">
                  {selectedNotice.title || selectedNotice.notice_type || 'Tax Notice'}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(selectedNotice.status || 'pending')}`}>
                    {selectedNotice.status || 'Pending'}
                  </span>
                  {selectedNotice.urgency && urgencyBadge(selectedNotice.urgency)}
                </div>
              </div>
              <button onClick={() => setSelectedNotice(null)} className="p-1 text-stone-400 hover:text-stone-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Info grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-xs text-stone-400">Client</p>
                  <p className="text-stone-700 font-medium">{selectedNotice.client_name || '--'}</p>
                </div>
                <div>
                  <p className="text-xs text-stone-400">Section</p>
                  <p className="text-stone-700 font-medium">{selectedNotice.section || '--'}</p>
                </div>
                <div>
                  <p className="text-xs text-stone-400">Assessment Year</p>
                  <p className="text-stone-700 font-medium">{selectedNotice.assessment_year || '--'}</p>
                </div>
                <div>
                  <p className="text-xs text-stone-400">Notice Date</p>
                  <p className="text-stone-700">{formatDate(selectedNotice.notice_date || selectedNotice.created_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-stone-400">Response Due</p>
                  <p className="text-stone-700 font-medium">{formatDate(selectedNotice.response_due_date)}</p>
                </div>
                <div>
                  <p className="text-xs text-stone-400">DIN</p>
                  <p className="text-stone-700 font-mono text-xs">{selectedNotice.din || '--'}</p>
                </div>
              </div>

              {selectedNotice.summary && (
                <div>
                  <p className="text-xs font-semibold text-stone-500 uppercase mb-1">Summary</p>
                  <div className="p-4 bg-stone-50 rounded-xl text-sm text-stone-700 leading-relaxed">
                    {selectedNotice.summary}
                  </div>
                </div>
              )}

              {selectedNotice.issues && selectedNotice.issues.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-stone-500 uppercase mb-2">Issues Raised</p>
                  <ul className="space-y-1.5">
                    {selectedNotice.issues.map((issue, idx) => {
                      const text = typeof issue === 'string' ? issue : issue.description || issue.issue || '';
                      return (
                        <li key={`${selectedNotice.id}-issue-${text.slice(0, 20)}-${idx}`} className="flex items-start gap-2 text-sm text-stone-600">
                          <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                          {text}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              {selectedNotice.draft_response && (
                <div>
                  <p className="text-xs font-semibold text-stone-500 uppercase mb-1">Draft Response</p>
                  <div className="p-4 bg-green-50 border border-green-200 rounded-xl text-sm text-stone-700 leading-relaxed whitespace-pre-wrap">
                    {selectedNotice.draft_response}
                  </div>
                </div>
              )}

              <div className="flex flex-wrap gap-3 pt-2 border-t border-stone-200">
                {selectedNotice.status === 'pending' && (
                  <button
                    onClick={() => processMutation.mutate(selectedNotice.id)}
                    disabled={processMutation.isPending}
                    className="px-4 py-2.5 bg-violet-500 hover:bg-violet-600 disabled:opacity-50 text-white text-sm font-medium rounded-xl flex items-center gap-2 transition-colors"
                  >
                    {processMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
                    Process Notice
                  </button>
                )}
                <button
                  onClick={() => {
                    setDraftingId(selectedNotice.id);
                    draftMutation.mutate({ id: selectedNotice.id, data: {} });
                  }}
                  disabled={draftMutation.isPending && draftingId === selectedNotice.id}
                  className="px-4 py-2.5 gradient-brand hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-xl flex items-center gap-2 shadow-sm transition-all"
                >
                  {draftMutation.isPending && draftingId === selectedNotice.id
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <Send className="w-4 h-4" />
                  }
                  Draft Response
                </button>
              </div>

              {draftMutation.isError && (
                <p className="text-sm text-red-600">
                  {(draftMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to draft response'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
