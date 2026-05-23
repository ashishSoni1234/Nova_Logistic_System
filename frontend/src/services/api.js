import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('nova_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 → clear token only, React Router handles the redirect
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('nova_token')
      localStorage.removeItem('nova_user')
      // Dispatch event so ProtectedLayout re-checks token
      window.dispatchEvent(new Event('nova_logout'))
    }
    return Promise.reject(error)
  }
)

// ─── Auth ───────────────────────────────────────────────────────────────────
export const authAPI = {
  login: (email, password) => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    return api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
}

// ─── Dashboard ─────────────────────────────────────────────────────────────
export const dashboardAPI = {
  getSummary: () => api.get('/dashboard/summary'),
  getShipmentsOverTime: (days = 30) => api.get(`/dashboard/shipments-over-time?days=${days}`),
  getApprovalStatus: () => api.get('/dashboard/approval-status'),
  getExceptionTrend: (days = 14) => api.get(`/dashboard/exception-trend?days=${days}`),
  getCategoryBreakdown: () => api.get('/dashboard/category-breakdown'),
  getRecentActivity: () => api.get('/dashboard/recent-activity'),
}

// ─── Workflows ──────────────────────────────────────────────────────────────
export const workflowsAPI = {
  list: (skip = 0, limit = 20) => api.get(`/workflows?skip=${skip}&limit=${limit}`),
  get: (id) => api.get(`/workflows/${id}`),
  create: (data) => api.post('/workflows', data),
  update: (id, data) => api.put(`/workflows/${id}`, data),
  delete: (id) => api.delete(`/workflows/${id}`),
  run: (id, inputData = {}) => api.post(`/workflows/${id}/run`, { input_data: inputData }),
  getRuns: (id) => api.get(`/workflows/${id}/runs`),
  validate: (yamlConfig) => api.post('/workflows/validate', { yaml_config: yamlConfig }),
}

// ─── Documents ──────────────────────────────────────────────────────────────
export const documentsAPI = {
  list: (skip = 0, limit = 20, status = '') => {
    const params = new URLSearchParams({ skip, limit })
    if (status) params.append('status', status)
    return api.get(`/documents?${params}`)
  },
  get: (id) => api.get(`/documents/${id}`),
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  reprocess: (id) => api.post(`/documents/${id}/reprocess`),
  delete: (id) => api.delete(`/documents/${id}`),
}

// ─── Approvals ──────────────────────────────────────────────────────────────
export const approvalsAPI = {
  list: (skip = 0, limit = 20, status = '') => {
    const params = new URLSearchParams({ skip, limit })
    if (status) params.append('status', status)
    return api.get(`/approvals?${params}`)
  },
  get: (id) => api.get(`/approvals/${id}`),
  action: (id, action, comment = '') => api.post(`/approvals/${id}/action`, { action, comment }),
  pendingCount: () => api.get('/approvals/pending-count'),
}

// ─── Exceptions ─────────────────────────────────────────────────────────────
export const exceptionsAPI = {
  list: (skip = 0, limit = 20, resolved = null) => {
    const params = new URLSearchParams({ skip, limit })
    if (resolved !== null) params.append('resolved', resolved)
    return api.get(`/exceptions?${params}`)
  },
  get: (id) => api.get(`/exceptions/${id}`),
  stats: () => api.get('/exceptions/stats'),
  resolve: (id) => api.post(`/exceptions/${id}/resolve`, {}),
  create: (data) => api.post('/exceptions', data),
}

// ─── Agents ─────────────────────────────────────────────────────────────────
export const agentsAPI = {
  status: () => api.get('/agents/status'),
  ragQuery: (query, collections = ['supply_chain', 'business_rules']) =>
    api.post('/agents/rag-query', { query, collections }),
  extract: (filePath, rawText = '') => api.post('/agents/extract', { file_path: filePath, raw_text: rawText }),
  validate: (extractedData) => api.post('/agents/validate', { extracted_data: extractedData }),
  detectException: (data) => api.post('/agents/detect-exception', { transaction_data: data }),
}

export default api
