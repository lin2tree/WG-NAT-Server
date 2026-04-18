<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { vpnConfigApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()

const configs = ref<any[]>([])
const loading = ref(false)
const statusFilter = ref('')
const searchIp = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const fetchConfigs = async () => {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    if (searchIp.value) {
      params.vm_ip = searchIp.value
    }
    
    const response = await vpnConfigApi.list(params)
    configs.value = response.data.data.items
    total.value = response.data.data.total
  } catch (error: any) {
    ElMessage.error('Failed to load configs')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchConfigs()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchConfigs()
}

const getStatusType = (status: string) => {
  return status === 'started' ? 'success' : 'warning'
}

const downloadConfig = async (vmIp: string, type: 'server' | 'client', clientName?: string) => {
  try {
    let url = `/api/admin/configs/${vmIp}/download/`
    if (type === 'server') {
      url += 'server'
    } else {
      url += `client/${clientName}`
    }
    
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
      },
    })
    
    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = type === 'server' ? `wg0_${vmIp}.conf` : `${clientName}.conf`
    a.click()
    window.URL.revokeObjectURL(downloadUrl)
  } catch (error) {
    ElMessage.error('Download failed')
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>

<template>
  <div class="vpn-config-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VPN Configurations</span>
          <div class="header-actions">
            <el-select
              v-model="statusFilter"
              placeholder="Status"
              clearable
              @change="handleSearch"
              style="width: 120px; margin-right: 10px"
            >
              <el-option label="Init" value="init" />
              <el-option label="Started" value="started" />
            </el-select>
            <el-input
              v-model="searchIp"
              placeholder="Search by IP"
              clearable
              @keyup.enter="handleSearch"
              style="width: 200px; margin-right: 10px"
            />
            <el-button type="primary" @click="handleSearch">Search</el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="configs" v-loading="loading" stripe>
        <el-table-column prop="vm_ip" label="VM IP" width="150" />
        <el-table-column prop="status" label="Status" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="Created" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="Started" width="180">
          <template #default="{ row }">
            {{ row.started_at ? new Date(row.started_at).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="200">
          <template #default="{ row }">
            <el-button
              v-if="authStore.isRoot"
              size="small"
              @click="downloadConfig(row.vm_ip, 'server')"
            >
              Download Server
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="fetchConfigs"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
  </div>
</template>

<style scoped>
.vpn-config-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}
</style>
