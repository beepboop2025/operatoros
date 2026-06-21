import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

// ── Shared Error Helpers ─────────────────────────────────────

export interface ApiError {
  response?: {
    data?: {
      detail?: string;
      message?: string;
    };
  };
  message?: string;
}

export function getErrorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (err && typeof err === 'object') {
    const ae = err as ApiError;
    if (ae.response?.data?.detail) return ae.response.data.detail;
    if (ae.response?.data?.message) return ae.response.data.message;
    if ('message' in err && typeof (err as Error).message === 'string') {
      return (err as Error).message;
    }
  }
  return fallback;
}

// ── Shared Entity Interfaces ─────────────────────────────────

export interface User {
  id: string;
  email: string;
  name?: string;
  firm_name?: string;
  role?: string;
  created_at?: string;
}

export interface Client {
  id: string;
  firm_name?: string;
  name?: string;
  pan?: string;
  gstin?: string;
  entity_type?: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ComplianceTask {
  id: string;
  task_name?: string;
  name?: string;
  task_type?: string;
  due_date: string;
  status: string;
  client_id?: string;
  client_name?: string;
  days_until_due?: number;
  created_at?: string;
}

export interface Document {
  id: string;
  filename?: string;
  name?: string;
  document_type?: string;
  type?: string;
  client_id?: string;
  client_name?: string;
  status?: string;
  summary?: string;
  parsed_data?: string | Record<string, unknown>;
  uploaded_at?: string;
  created_at?: string;
}

export interface QueryItem {
  id: string;
  question?: string;
  query?: string;
  answer?: string;
  response?: string;
  sources?: QuerySource[];
  citations?: QuerySource[];
  client_id?: string;
  created_at?: string;
}

export interface QuerySource {
  title?: string;
  section?: string;
  url?: string;
}

export interface Notice {
  id: string;
  title?: string;
  notice_type?: string;
  type?: string;
  section?: string;
  assessment_year?: string;
  notice_date?: string;
  response_due_date?: string;
  din?: string;
  client_id?: string;
  client_name?: string;
  status?: string;
  urgency?: 'high' | 'medium' | 'low';
  summary?: string;
  issues?: Array<string | { description?: string; issue?: string }>;
  draft_response?: string;
  created_at?: string;
}

// ── Request Types ────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
  firm_name?: string;
}

export interface ClientCreateRequest {
  firm_name: string;
  pan?: string;
  gstin?: string;
  entity_type?: string;
  contact_person?: string;
  email?: string;
  phone?: string;
}

export interface ClientUpdateRequest {
  firm_name?: string;
  pan?: string;
  gstin?: string;
  entity_type?: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  status?: string;
}

export interface IncomeTaxRequest {
  assessment_year: string;
  age_category: string;
  gross_salary: number;
  income_hp: number;
  business_income: number;
  capital_gains_lt: number;
  capital_gains_st: number;
  other_income: number;
  deductions: IncomeTaxDeductions;
}

export interface IncomeTaxDeductions {
  section_80c: number;
  section_80d: number;
  section_80g: number;
  section_80e: number;
  section_80ccd_1b: number;
  section_80tta: number;
  hra_exempt: number;
  lta_exempt: number;
  standard_deduction: number;
  nps_employer: number;
}

export interface TDSRequest {
  payment_type: string;
  amount: number;
  pan_available: boolean;
}

export interface GSTRequest {
  supply_type: string;
  hsn_sac: string;
  place_of_supply: string;
  place_of_origin: string;
  taxable_value: number;
  gst_rate: number;
}

export interface CapitalGainsRequest {
  asset_type: string;
  purchase_date: string;
  sale_date: string;
  purchase_price: number;
  sale_price: number;
  improvement_cost: number;
}

export interface InterestRequest {
  section: string;
  tax_liability: number;
  tax_paid: number;
  due_date: string;
  payment_date: string;
}

export interface HRARequest {
  basic_salary: number;
  da: number;
  hra_received: number;
  rent_paid: number;
  is_metro: boolean;
}

export interface QuerySubmitRequest {
  question: string;
  client_id?: string;
}

export interface ComplianceTaskUpdateRequest {
  status?: string;
  [key: string]: unknown;
}

export interface ComplianceTaskCreateRequest {
  task_name: string;
  task_type: string;
  due_date: string;
  client_id: string;
  [key: string]: unknown;
}

export interface GenerateCalendarRequest {
  client_id: string;
  financial_year: string;
}

export interface DraftResponseRequest {
  [key: string]: unknown;
}

// ── Response Types ───────────────────────────────────────────

export interface LoginResponse {
  access_token?: string;
  token?: string;
  user?: User;
}

export interface PaginatedResponse<T> {
  items?: T[];
  total?: number;
  page?: number;
  page_size?: number;
}

export interface TaxRegimeResult {
  gross_total_income: number;
  total_deductions: number;
  taxable_income: number;
  tax_on_income: number;
  surcharge: number;
  education_cess: number;
  total_tax_liability: number;
  slab_breakdown?: Array<{ slab?: string; range?: string; tax: number }>;
}

export interface IncomeTaxResponse {
  old_regime?: TaxRegimeResult;
  new_regime?: TaxRegimeResult;
  recommended_regime?: 'old_regime' | 'new_regime';
}

export interface TDSResponse {
  section?: string;
  rate?: number;
  amount?: number;
  tds_amount: number;
  notes?: string;
}

export interface GSTResponse {
  taxable_value?: number;
  is_interstate?: boolean;
  cgst?: number;
  sgst?: number;
  igst?: number;
  cgst_rate?: number;
  sgst_rate?: number;
  igst_rate?: number;
  total_gst?: number;
  total_amount?: number;
}

export interface CapitalGainsResponse {
  gain_type: 'ltcg' | 'stcg';
  holding_period?: string;
  sale_price?: number;
  purchase_price?: number;
  indexed_cost?: number;
  improvement_cost?: number;
  capital_gain: number;
  tax_rate?: number;
  tax_amount: number;
  exemptions?: string[];
}

export interface InterestResponse {
  tax_liability?: number;
  tax_paid?: number;
  shortfall?: number;
  months?: number;
  rate?: number;
  interest_amount: number;
  month_wise_breakdown?: Array<{ month?: string; period?: string; interest: number }>;
}

export interface HRAResponse {
  actual_hra?: number;
  percent_of_salary?: number;
  rent_minus_10_percent?: number;
  exemption_amount: number;
  taxable_hra?: number;
}

export interface DashboardStats {
  total_clients?: number;
  active_tasks?: number;
  overdue_tasks?: number;
  queries_today?: number;
  documents_processed?: number;
}

export interface TeamMemberWorkload {
  user_id: string;
  name: string;
  total_tasks: number;
  completed: number;
  pending: number;
  in_progress: number;
  overdue: number;
  completion_rate: number;
}

export interface WorkloadResponse {
  team: TeamMemberWorkload[];
}

export interface ComplianceCalendarEvent {
  task_type: string;
  description: string;
  due_date: string;
  form_name: string;
  statute: string;
  notes?: string;
}

export interface ComplianceCalendarDashboard {
  statutory_calendar: ComplianceCalendarEvent[];
  client_tasks: Array<{
    id: string;
    client_name: string;
    task_type: string;
    due_date: string;
    status: string;
    description: string;
  }>;
}

export interface ComplianceOverview {
  [key: string]: unknown;
}

export interface ActivityItem {
  id?: string;
  type?: string;
  description?: string;
  title?: string;
  client_name?: string;
  time_ago?: string;
  created_at?: string;
}

export interface RecentActivityResponse {
  items?: ActivityItem[];
}

export interface UpcomingTasksResponse {
  tasks?: ComplianceTask[];
}

export interface QueryResponse {
  answer?: string;
  response?: string;
  sources?: QuerySource[];
  citations?: QuerySource[];
}

export interface NoticeProcessResponse {
  [key: string]: unknown;
}

export interface DraftNoticeResponse {
  draft?: string;
  response?: string;
  draft_text?: string;
  legal_references?: string[];
  recommended_actions?: string[];
}

export interface SubmitNoticeResponseRequest {
  response: string;
}

// ── List response helpers (APIs return varying shapes) ───────

export interface ClientListResponse {
  items?: Client[];
  clients?: Client[];
  total?: number;
}

export interface ComplianceTaskListResponse {
  items?: ComplianceTask[];
  tasks?: ComplianceTask[];
  total?: number;
}

export interface DocumentListResponse {
  items?: Document[];
  documents?: Document[];
  total?: number;
}

export interface QueryListResponse {
  items?: QueryItem[];
  queries?: QueryItem[];
  total?: number;
}

export interface NoticeListResponse {
  items?: Notice[];
  notices?: Notice[];
  total?: number;
}

// ── Axios Instance ───────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Token-refresh bookkeeping (shared across all requests)
let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null) => void> = [];

function subscribeTokenRefresh(cb: (token: string | null) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string | null) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

function clearAuthAndRedirect() {
  localStorage.removeItem('auditmind_token');
  localStorage.removeItem('auditmind_user');
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

// Request interceptor: attach JWT
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('auditmind_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 (silent refresh), then transient failures
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { __skipRefresh?: boolean; __retryCount?: number })
      | undefined;

    if (error.response?.status === 401 && originalRequest) {
      const url = originalRequest.url || '';
      const isAuthRequest =
        url === '/auth/refresh' ||
        url === '/auth/login' ||
        url === '/auth/register' ||
        originalRequest.__skipRefresh;

      if (isAuthRequest) {
        clearAuthAndRedirect();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((token) => {
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(api(originalRequest));
            } else {
              reject(error);
            }
          });
        });
      }

      isRefreshing = true;
      try {
        const rs = await authApi.refresh();
        const newToken = rs.access_token || rs.token || '';
        if (!newToken) {
          throw new Error('Refresh endpoint did not return a token');
        }
        localStorage.setItem('auditmind_token', newToken);
        onRefreshed(newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        onRefreshed(null);
        clearAuthAndRedirect();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Automatic retry for transient failures (5xx / network errors)
    const config = error.config;
    if (!config) return Promise.reject(error);

    // Only retry GET requests automatically (mutations are retried by TanStack Query)
    const isRetryable =
      config.method === 'get' &&
      (!error.response || error.response.status >= 500) &&
      !config.__retryCount;

    if (isRetryable) {
      config.__retryCount = (config.__retryCount || 0) + 1;
      const MAX_RETRIES = 2;

      if (config.__retryCount <= MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** (config.__retryCount - 1), 4000);
        await new Promise((resolve) => setTimeout(resolve, delay));
        return api(config);
      }
    }

    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string): Promise<LoginResponse> =>
    api.post('/auth/login', { email, password }).then((r) => r.data),
  register: (data: RegisterRequest): Promise<User> =>
    api.post('/auth/register', data).then((r) => r.data),
  getMe: (): Promise<User> =>
    api.get('/auth/me').then((r) => r.data),
  refresh: (): Promise<LoginResponse> =>
    api.post('/auth/refresh', {}, { __skipRefresh: true } as unknown as InternalAxiosRequestConfig).then((r) => r.data),
};

// ── Clients ───────────────────────────────────────────────
export const clientsApi = {
  list: (params?: Record<string, unknown>): Promise<ClientListResponse | Client[]> =>
    api.get('/clients', { params }).then((r) => r.data),
  get: (id: string): Promise<Client> =>
    api.get(`/clients/${id}`).then((r) => r.data),
  create: (data: ClientCreateRequest): Promise<Client> =>
    api.post('/clients', data).then((r) => r.data),
  update: (id: string, data: ClientUpdateRequest): Promise<Client> =>
    api.put(`/clients/${id}`, data).then((r) => r.data),
  delete: (id: string): Promise<void> =>
    api.delete(`/clients/${id}`).then((r) => r.data),
};

// ── Compliance ────────────────────────────────────────────
export const complianceApi = {
  listTasks: (params?: Record<string, unknown>): Promise<ComplianceTaskListResponse | ComplianceTask[]> =>
    api.get('/compliance/tasks', { params }).then((r) => r.data),
  createTask: (data: ComplianceTaskCreateRequest): Promise<ComplianceTask> =>
    api.post('/compliance/tasks', data).then((r) => r.data),
  updateTask: (id: string, data: ComplianceTaskUpdateRequest): Promise<ComplianceTask> =>
    api.put(`/compliance/tasks/${id}`, data).then((r) => r.data),
  getOverdue: (): Promise<ComplianceTask[]> =>
    api.get('/compliance/overdue').then((r) => r.data),
  getUpcoming: (days: number = 7): Promise<UpcomingTasksResponse | ComplianceTask[]> =>
    api.get('/compliance/upcoming', { params: { days } }).then((r) => r.data),
  generateCalendar: (clientId: string, financialYear: string): Promise<unknown> =>
    api.post('/compliance/generate', null, { params: { client_id: clientId, fy: financialYear } }).then((r) => r.data),
};

// ── Compute ───────────────────────────────────────────────
export const computeApi = {
  tax: (data: IncomeTaxRequest, clientId?: string): Promise<IncomeTaxResponse> =>
    api.post('/compute/tax', { client_id: clientId, data }).then((r) => r.data),
  tds: (data: TDSRequest, clientId?: string): Promise<TDSResponse> =>
    api.post('/compute/tds', { client_id: clientId, data }).then((r) => r.data),
  gst: (data: GSTRequest, clientId?: string): Promise<GSTResponse> =>
    api.post('/compute/gst', { client_id: clientId, data }).then((r) => r.data),
  capitalGains: (data: CapitalGainsRequest, clientId?: string): Promise<CapitalGainsResponse> =>
    api.post('/compute/capital-gains', { client_id: clientId, data }).then((r) => r.data),
  interest: (data: InterestRequest, clientId?: string): Promise<InterestResponse> =>
    api.post('/compute/interest', { client_id: clientId, data }).then((r) => r.data),
  hra: (data: HRARequest, clientId?: string): Promise<HRAResponse> =>
    api.post('/compute/hra', { client_id: clientId, data }).then((r) => r.data),
};

// ── Documents ─────────────────────────────────────────────
export const documentsApi = {
  upload: (file: File, clientId?: string, docType?: string): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    if (clientId) formData.append('client_id', clientId);
    if (docType) formData.append('doc_type', docType);
    return api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    }).then((r) => r.data);
  },
  get: (id: string): Promise<Document> =>
    api.get(`/documents/${id}`).then((r) => r.data),
  search: (query: string, params?: Record<string, unknown>): Promise<DocumentListResponse | Document[]> =>
    api.post('/documents/search', { query, ...params }).then((r) => r.data),
  list: (params?: Record<string, unknown>): Promise<DocumentListResponse | Document[]> =>
    api.get('/documents', { params }).then((r) => r.data),
  download: (id: string): Promise<Blob> =>
    api.get(`/documents/${id}/download`, { responseType: 'blob' }).then((r) => r.data),
};

// ── Queries ───────────────────────────────────────────────
export const queriesApi = {
  submit: (data: QuerySubmitRequest): Promise<QueryResponse> =>
    api.post('/queries', data).then((r) => r.data),
  list: (params?: Record<string, unknown>): Promise<QueryListResponse | QueryItem[]> =>
    api.get('/queries', { params }).then((r) => r.data),
  get: (id: string): Promise<QueryItem> =>
    api.get(`/queries/${id}`).then((r) => r.data),
};

// ── Notices ───────────────────────────────────────────────
export const noticesApi = {
  list: (params?: Record<string, unknown>): Promise<NoticeListResponse | Notice[]> =>
    api.get('/notices', { params }).then((r) => r.data),
  get: (id: string): Promise<Notice> =>
    api.get(`/notices/${id}`).then((r) => r.data),
  process: (id: string): Promise<NoticeProcessResponse> =>
    api.post(`/notices/${id}/process`).then((r) => r.data),
  draftResponse: (id: string, data: DraftResponseRequest): Promise<DraftNoticeResponse> =>
    api.post(`/notices/${id}/draft-response`, data).then((r) => r.data),
  submitResponse: (id: string, data: SubmitNoticeResponseRequest): Promise<Notice> =>
    api.post(`/notices/${id}/submit-response`, data).then((r) => r.data),
};

// ── Dashboard ─────────────────────────────────────────────
export const dashboardApi = {
  stats: (): Promise<DashboardStats> =>
    api.get('/dashboard/stats').then((r) => r.data),
  complianceOverview: (): Promise<ComplianceOverview> =>
    api.get('/dashboard/compliance-overview').then((r) => r.data),
  recentActivity: (): Promise<RecentActivityResponse | ActivityItem[]> =>
    api.get('/dashboard/recent-activity').then((r) => r.data),
  complianceCalendar: (months?: number): Promise<ComplianceCalendarDashboard> =>
    api.get('/dashboard/compliance-calendar', { params: { months: months || 3 } }).then((r) => r.data),
  workload: (): Promise<WorkloadResponse> =>
    api.get('/dashboard/workload').then((r) => r.data),
};

// ── Tasks Status ─────────────────────────────────────────
export const tasksApi = {
  getStatus: (taskId: string): Promise<{ task_id: string; status: string; ready: boolean; result?: unknown; error?: string }> =>
    api.get(`/tasks/${taskId}/status`).then((r) => r.data),
};

// ── Audit Logs ───────────────────────────────────────────
export const auditApi = {
  list: (params?: Record<string, unknown>): Promise<PaginatedResponse<unknown>> =>
    api.get('/audit', { params }).then((r) => r.data),
};

export default api;
