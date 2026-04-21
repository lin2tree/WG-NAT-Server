import { ref, onMounted, onUnmounted } from 'vue'

const REFRESH_INTERVAL = parseInt(import.meta.env.VITE_REFRESH_INTERVAL || '5000', 10)

export function useAutoRefresh(fetchFn: () => Promise<void>, interval: number = REFRESH_INTERVAL) {
  const refreshTimer = ref<number | null>(null)
  const isAutoRefreshEnabled = ref(interval > 0)

  const startAutoRefresh = () => {
    if (interval <= 0) return
    
    stopAutoRefresh()
    refreshTimer.value = window.setInterval(() => {
      fetchFn()
    }, interval)
  }

  const stopAutoRefresh = () => {
    if (refreshTimer.value) {
      clearInterval(refreshTimer.value)
      refreshTimer.value = null
    }
  }

  onMounted(() => {
    if (isAutoRefreshEnabled.value) {
      startAutoRefresh()
    }
  })

  onUnmounted(() => {
    stopAutoRefresh()
  })

  return {
    isAutoRefreshEnabled,
    startAutoRefresh,
    stopAutoRefresh,
  }
}
