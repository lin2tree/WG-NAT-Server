<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { logApi } from '@/services/api'
import { ElMessage } from 'element-plus'

const logs = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

const filters = ref({
  source_ip: '',
  request_path: '',
  start_time: '',
  end_time: '',
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    
    if (filters.value.source_ip) {
      params.source_ip = filters.value.source_ip
    }
    if (filters.value.request_path) {
      params.request_path = filters.value.request_path
    }
    if (filters.value.start_time) {
      params.start_time = filters.value.start_time
    }
    if (filters.value.end_time) {
      params.end_time = filters.value.end_time
    }
    
    const response = await logApi.list(params)
    logs.value = response.data.data.items
    total.value = response.data.data.total
  } catch (error) {
    ElMessage.error('Failed to load logs')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchLogs()
}

const handleReset = () => {
  filters.value = {
    source_ip: '',
    request_path: '',
    start_time: '',
    end_time: '',
  }
  handleSearch()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchLogs()
}

const getStatusType = (status: number) => {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'warning'
  if (status >= 500) return 'danger'
  return 'info'
}

const getMethodColor = (method: string) => {
  const colors: Record<string, string> = {
    GET: '#67c23a',
    POST: '#409eff',
    PUT: '#e6a23c',
    DELETE: '#f56c6c',
  }
  return colors[method] || '#909399'
}

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="log-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Operation Logs</span>
        </div>
      </template>
      
      <div class="filters">
        <el-input
          v-model="filters.source_ip"
          placeholder="Source IP"
          clearable
          style="width: 150px; margin-right: 10px"
        />
        <el-input
          v-model="filters.request_path"
          placeholder="Request Path"
          clearable
          style="width: 200px; margin-right: 10px"
        />
        <el-date-picker
          v-model="filters.start_time"
          type="datetime"
          placeholder="Start Time"
          style="margin-right: 10px"
        />
        <el-date-picker
          v-model="filters.end_time"
          type="datetime"
          placeholder="End Time"
          style="margin-right: 10px"
        />
        <el-button type="primary" @click="handleSearch">Search</el-button>
        <el-button @click="handleReset">Reset</el-button>
      </div>
      
      <el-table :data="logs" v-loading="loading" stripe style="margin-top: 20px">
        <el-table-column prop="request_time" label="Time" width="180">
          <template #default="{ row }">
            {{ new Date(row.request_time).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="source_ip" label="Source IP" width="140" />
        <el-table-column prop="request_method" label="Method" width="80">
          <template #default="{ row }">
            <span :style="{ color: getMethodColor(row.request_method), fontWeight: 'bold' }">
              {{ row.request_method }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="request_path" label="Path" min-width="200" />
        <el-table-column prop="response_status" label="Status" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.response_status)" size="small">
              {{ row.response_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time_ms" label="Time (ms)" width="100" />
      </el-table>
      
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="fetchLogs"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
  </div>
</template>

<style scoped>
.log-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
