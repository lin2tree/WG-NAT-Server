<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/archives')) return 'archives'
  if (path.startsWith('/resource-pool')) return 'resource-pool'
  if (path.startsWith('/users')) return 'users'
  if (path.startsWith('/logs')) return 'logs'
  return 'configs'
})

const menuKey = computed(() => route.path)

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="main-layout">
    <el-header class="header">
      <div class="logo">
        <h1>WireGuard VPN Manager</h1>
      </div>
      <div class="user-info">
        <span>用户：{{ authStore.user?.username }}（角色：{{ authStore.user?.role }}）</span>
        <el-button type="danger" size="small" @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </el-header>
    
    <el-container class="body-container">
      <el-aside width="200px" class="sidebar">
        <el-menu
          :key="menuKey"
          :default-active="activeMenu"
          router
        >
          <el-menu-item index="configs">
            <el-icon><Document /></el-icon>
            <span>VPN 配置</span>
          </el-menu-item>
          <el-menu-item index="archives">
            <el-icon><FolderOpened /></el-icon>
            <span>已归档数据</span>
          </el-menu-item>
          <el-menu-item index="resource-pool" v-if="authStore.isRoot">
            <el-icon><Setting /></el-icon>
            <span>资源池</span>
          </el-menu-item>
          <el-menu-item index="users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="logs">
            <el-icon><List /></el-icon>
            <span>操作日志</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.main-layout {
  height: 100vh;
  background: linear-gradient(135deg, var(--color-background) 0%, var(--color-background-alt) 100%);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  color: white;
  padding: 0 var(--spacing-lg);
  box-shadow: var(--shadow-lg);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  height: 60px;
}

.header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
}

.body-container {
  margin-top: 60px;
  height: calc(100vh - 60px);
}

.logo h1 {
  margin: 0;
  font-size: var(--font-size-title);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.5px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.1);
  font-family: 'Fira Code', monospace;
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
}

.user-info span {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: rgba(255,255,255,0.15);
  border-radius: var(--radius-md);
  backdrop-filter: blur(10px);
}

.sidebar {
  background: linear-gradient(180deg, #ffffff 0%, var(--color-background) 100%);
  box-shadow: var(--shadow-md);
  border-right: 1px solid var(--color-border);
  height: 100%;
  overflow-y: auto;
}

.sidebar :deep(.el-menu) {
  border-right: none;
  background: transparent;
}

.sidebar :deep(.el-menu-item) {
  margin: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.sidebar :deep(.el-menu-item::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--color-primary);
  transform: scaleY(0);
  transition: transform var(--transition-base);
}

.sidebar :deep(.el-menu-item:hover) {
  background: linear-gradient(90deg, rgba(3, 105, 161, 0.1), transparent);
  transform: translateX(4px);
}

.sidebar :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(3, 105, 161, 0.15), transparent);
  color: var(--color-primary);
  font-weight: var(--font-weight-bold);
}

.sidebar :deep(.el-menu-item.is-active::before) {
  transform: scaleY(1);
}

.main-content {
  padding: var(--spacing-lg);
  background-color: transparent;
  height: 100%;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .header {
    padding: 0 var(--spacing-md);
  }
  
  .logo h1 {
    font-size: var(--font-size-large);
  }
  
  .user-info {
    flex-direction: column;
    gap: var(--spacing-xs);
    align-items: flex-end;
  }
  
  .user-info span {
    font-size: var(--font-size-small);
  }
  
  .sidebar {
    width: 60px !important;
  }
  
  .sidebar :deep(.el-menu-item span) {
    display: none;
  }
  
  .main-content {
    padding: var(--spacing-md);
  }
}

@media (max-width: 480px) {
  .header {
    flex-direction: column;
    height: auto;
    padding: var(--spacing-sm);
  }
  
  .logo h1 {
    font-size: var(--font-size-base);
    margin-bottom: var(--spacing-xs);
  }
  
  .user-info {
    width: 100%;
    justify-content: space-between;
    flex-direction: row;
    align-items: center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar :deep(.el-menu-item:hover) {
    transform: none;
  }
}
</style>
