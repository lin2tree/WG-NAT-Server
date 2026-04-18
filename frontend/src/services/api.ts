"""Frontend API client service"""
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
}

export const resourcePoolApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get('/admin/resource-pool', { params }),
  import: (ipList: string[]) =>
    api.post('/admin/resource-pool', { ip_list: ipList }),
  delete: (id: number) => api.delete(`/admin/resource-pool/${id}`),
  export: () => api.get('/admin/resource-pool/export'),
}

export const portRangeApi = {
  get: () => api.get('/admin/port-range'),
  set: (startPort: number, endPort: number) =>
    api.post('/admin/port-range', { start_port: startPort, end_port: endPort }),
}

export const vpnConfigApi = {
  list: (params?: { status?: string; vm_ip?: string; page?: number }) =>
    api.get('/admin/configs', { params }),
  download: (vmIp: string, type: 'server' | 'client', clientIndex?: number) =>
    api.get(`/admin/configs/${vmIp}/download`, {
      params: { type, client_index: clientIndex },
    }),
  history: (vmIp: string) => api.get(`/admin/configs/${vmIp}/history`),
}

export const logApi = {
  list: (params?: { start_time?: string; end_time?: string; source_ip?: string }) =>
    api.get('/admin/logs', { params }),
}
