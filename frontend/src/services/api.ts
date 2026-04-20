// Frontend API client service
import axios from 'axios'
import JSEncrypt from 'jsencrypt'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
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

async function getPublicKey(): Promise<string> {
  const response = await api.get('/auth/public-key')
  return response.data.public_key
}

function encryptPassword(password: string, publicKey: string): string {
  const encrypt = new JSEncrypt()
  encrypt.setPublicKey(publicKey)
  const encrypted = encrypt.encryptOAEP(password)
  return encrypted || ''
}

export const authApi = {
  login: async (username: string, password: string) => {
    const publicKey = await getPublicKey()
    const encryptedPassword = encryptPassword(password, publicKey)
    const params = new URLSearchParams()
    params.append('username', username)
    params.append('encrypted_password', encryptedPassword)
    return api.post('/auth/login/encrypted', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  listUsers: () => api.get('/auth/users'),
  createUser: (data: { username: string; password: string; role: string }) =>
    api.post('/auth/users', data),
  deleteUser: (userId: number) => api.delete(`/auth/users/${userId}`),
  changeUserPassword: (userId: number, newPassword: string) =>
    api.put(`/auth/users/${userId}/password`, { new_password: newPassword }),
  changeOwnPassword: (oldPassword: string, newPassword: string) =>
    api.put('/auth/me/password', { old_password: oldPassword, new_password: newPassword }),
}

export const publicIpApi = {
  list: () => api.get('/admin/public-ips'),
  import: (data: { ip_address: string; description?: string; is_default?: boolean }) =>
    api.post('/admin/public-ips', data),
  setDefault: (ipId: number) => api.put(`/admin/public-ips/${ipId}/default`),
  delete: (ipId: number) => api.delete(`/admin/public-ips/${ipId}`),
}

export const resourcePoolApi = {
  list: (params?: { page?: number; page_size?: number; internal_ip?: string; public_port?: string; sort_by?: string; sort_order?: string }) =>
    api.get('/admin/resource-pool', { params }),
  import: (ipList: string[]) =>
    api.post('/admin/resource-pool/import', ipList),
  delete: (id: number) => api.delete(`/admin/resource-pool/${id}`),
  batchDelete: (ids: number[]) => api.post('/admin/resource-pool/batch-delete', { ids }),
  export: () => api.get('/admin/resource-pool/export', { responseType: 'blob' }),
  updatePublicIp: (mappingId: number, publicIpId: number) =>
    api.put(`/admin/resource-pool/${mappingId}/public-ip`, null, { params: { public_ip_id: publicIpId } }),
}

export const portRangeApi = {
  get: () => api.get('/admin/port-range'),
  set: (startPort: number, endPort: number) =>
    api.post('/admin/port-range', null, { params: { start_port: startPort, end_port: endPort } }),
}

export const vpnConfigApi = {
  list: (params?: { status?: string; vm_ip?: string; public_port?: string; page?: number; page_size?: number; sort_by?: string; sort_order?: string }) =>
    api.get('/admin/configs', { params }),
  export: (params?: { status?: string; vm_ip?: string; public_port?: string }) =>
    api.get('/admin/configs/export', { params, responseType: 'blob' }),
  downloadServer: (vmIp: string) =>
    api.get(`/admin/configs/${vmIp}/download/server`, { responseType: 'blob' }),
  downloadClient: (vmIp: string, clientName: string) =>
    api.get(`/admin/configs/${vmIp}/download/client/${clientName}`, { responseType: 'blob' }),
  downloadAllClients: (vmIp: string) =>
    api.get(`/admin/configs/${vmIp}/download/clients`, { responseType: 'blob' }),
  getClientConfigs: (vmIp: string) =>
    api.get(`/admin/configs/${vmIp}/clients`),
  history: (vmIp: string) => api.get(`/admin/configs/${vmIp}/history`),
}

export const archiveApi = {
  list: (params?: { vm_ip?: string; public_port?: string; page?: number; page_size?: number; sort_by?: string; sort_order?: string }) =>
    api.get('/admin/archives', { params }),
  export: (params?: { vm_ip?: string; public_port?: string }) =>
    api.get('/admin/archives/export', { params, responseType: 'blob' }),
}

export const logApi = {
  list: (params?: { start_time?: string; end_time?: string; source_ip?: string }) =>
    api.get('/admin/logs', { params }),
}
