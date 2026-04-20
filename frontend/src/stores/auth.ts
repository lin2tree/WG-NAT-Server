// Pinia store for authentication
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/services/api'

interface User {
  id: number
  username: string
  role: 'admin' | 'user'
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  const isAuthenticated = computed(() => !!token.value)
  const isRoot = computed(() => user.value?.role === 'admin')

  async function login(username: string, password: string) {
    const response = await authApi.login(username, password)
    token.value = response.data.access_token
    user.value = response.data.user
    localStorage.setItem('token', response.data.access_token)
    return response.data
  }

  async function logout() {
    await authApi.logout()
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  async function fetchUser() {
    if (!token.value) return null
    try {
      const response = await authApi.me()
      user.value = response.data
      return response.data
    } catch {
      logout()
      return null
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    isRoot,
    login,
    logout,
    fetchUser,
  }
})
