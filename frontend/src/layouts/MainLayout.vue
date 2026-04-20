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
    
    <el-container>
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
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #409eff;
  color: white;
  padding: 0 20px;
}

.logo h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  font-weight: 500;
}

.sidebar {
  background-color: #f5f7fa;
}

.main-content {
  padding: 20px;
  background-color: #fff;
}
</style>
