import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Request interceptor: attach JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auditmind_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auditmind_token');
      localStorage.removeItem('auditmind_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────
export const authApi = {
  login: (email, password) =>
    api.post('/auth/login', { email, password }).then((r) => r.data),
  register: (data) =>
    api.post('/auth/register', data).then((r) => r.data),
  getMe: () =>
    api.get('/auth/me').then((r) => r.data),
};

// ── Clients ───────────────────────────────────────────────
export const clientsApi = {
  list: (params) =>
    api.get('/clients', { params }).then((r) => r.data),
  get: (id) =>
    api.get(`/clients/${id}`).then((r) => r.data),
  create: (data) =>
    api.post('/clients', data).then((r) => r.data),
  update: (id, data) =>
    api.put(`/clients/${id}`, data).then((r) => r.data),
  delete: (id) =>
    api.delete(`/clients/${id}`).then((r) => r.data),
};

// ── Compliance ────────────────────────────────────────────
export const complianceApi = {
  listTasks: (params) =>
    api.get('/compliance/tasks', { params }).then((r) => r.data),
  createTask: (data) =>
    api.post('/compliance/tasks', data).then((r) => r.data),
  updateTask: (id, data) =>
    api.put(`/compliance/tasks/${id}`, data).then((r) => r.data),
  getOverdue: () =>
    api.get('/compliance/overdue').then((r) => r.data),
  getUpcoming: (days = 7) =>
    api.get('/compliance/upcoming', { params: { days } }).then((r) => r.data),
  generateCalendar: (clientId, financialYear) =>
    api.post('/compliance/generate-calendar', { client_id: clientId, financial_year: financialYear }).then((r) => r.data),
};

// ── Compute ───────────────────────────────────────────────
export const computeApi = {
  tax: (data) =>
    api.post('/compute/tax', data).then((r) => r.data),
  tds: (data) =>
    api.post('/compute/tds', data).then((r) => r.data),
  gst: (data) =>
    api.post('/compute/gst', data).then((r) => r.data),
  capitalGains: (data) =>
    api.post('/compute/capital-gains', data).then((r) => r.data),
  interest: (data) =>
    api.post('/compute/interest', data).then((r) => r.data),
  hra: (data) =>
    api.post('/compute/hra', data).then((r) => r.data),
};

// ── Documents ─────────────────────────────────────────────
export const documentsApi = {
  upload: (file, clientId, docType) => {
    const formData = new FormData();
    formData.append('file', file);
    if (clientId) formData.append('client_id', clientId);
    if (docType) formData.append('document_type', docType);
    return api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    }).then((r) => r.data);
  },
  get: (id) =>
    api.get(`/documents/${id}`).then((r) => r.data),
  search: (query, params) =>
    api.get('/documents/search', { params: { q: query, ...params } }).then((r) => r.data),
  list: (params) =>
    api.get('/documents', { params }).then((r) => r.data),
};

// ── Queries ───────────────────────────────────────────────
export const queriesApi = {
  submit: (data) =>
    api.post('/queries', data).then((r) => r.data),
  list: (params) =>
    api.get('/queries', { params }).then((r) => r.data),
  get: (id) =>
    api.get(`/queries/${id}`).then((r) => r.data),
};

// ── Notices ───────────────────────────────────────────────
export const noticesApi = {
  list: (params) =>
    api.get('/notices', { params }).then((r) => r.data),
  get: (id) =>
    api.get(`/notices/${id}`).then((r) => r.data),
  process: (id) =>
    api.post(`/notices/${id}/process`).then((r) => r.data),
  draftResponse: (id, data) =>
    api.post(`/notices/${id}/draft-response`, data).then((r) => r.data),
};

// ── Dashboard ─────────────────────────────────────────────
export const dashboardApi = {
  stats: () =>
    api.get('/dashboard/stats').then((r) => r.data),
  complianceOverview: () =>
    api.get('/dashboard/compliance-overview').then((r) => r.data),
  recentActivity: () =>
    api.get('/dashboard/recent-activity').then((r) => r.data),
};

export default api;
