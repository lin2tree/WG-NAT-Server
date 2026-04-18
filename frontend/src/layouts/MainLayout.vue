<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const activeMenu = ref('configs')

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
        <span>{{ authStore.user?.username }} ({{ authStore.user?.role }})</span>
        <el-button type="danger" size="small" @click="handleLogout">
          Logout
        </el-button>
      </div>
    </el-header>
    
    <el-container>
      <el-aside width="200px" class="sidebar">
        <el-menu
          :default-active="activeMenu"
          router
        >
          <el-menu-item index="configs">
            <el-icon><Document /></el-icon>
            <span>VPN Configs</span>
          </el-menu-item>
          <el-menu-item index="resource-pool" v-if="authStore.isRoot">
            <el-icon><Setting /></el-icon>
            <span>Resource Pool</span>
          </el-menu-item>
          <el-menu-item index="logs">
            <el-icon><List /></el-icon>
            <span>Logs</span>
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
}

.logo h1 {
  margin: 0;
  font-size: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.sidebar {
  background-color: #f5f7fa;
}

.main-content {
  padding: 20px;
  background-color: #fff;
}
</style>
