<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { logApi } from '@/services/api'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/date'

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

const dialogVisible = ref(false)
const selectedLog = ref<any>(null)

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

const getStatusType = (row: any) => {
  const status = row.response_status
  if (status >= 200 && status < 300) {
    if (row.error_message) {
      return 'warning'
    }
    return 'success'
  }
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

const showLogDetails = (row: any) => {
  selectedLog.value = row
  dialogVisible.value = true
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
            {{ formatDateTime(row.request_time) }}
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
        <el-table-column prop="response_status" label="Status" width="100">
          <template #default="{ row }">
            <el-tag 
              :type="getStatusType(row)" 
              size="small"
              class="clickable-tag"
              @click="showLogDetails(row)"
            >
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
    
    <el-dialog
      v-model="dialogVisible"
      title="Log Details"
      width="500px"
    >
      <div v-if="selectedLog" class="log-details">
        <div class="detail-row">
          <span class="detail-label">Time:</span>
          <span class="detail-value">{{ formatDateTime(selectedLog.request_time) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Source IP:</span>
          <span class="detail-value">{{ selectedLog.source_ip }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Method:</span>
          <span class="detail-value">{{ selectedLog.request_method }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Path:</span>
          <span class="detail-value">{{ selectedLog.request_path }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Status:</span>
          <el-tag :type="getStatusType(selectedLog)" size="small">
            {{ selectedLog.response_status }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">Response Time:</span>
          <span class="detail-value">{{ selectedLog.response_time_ms }} ms</span>
        </div>
        <div v-if="selectedLog.error_message" class="detail-row error-row">
          <span class="detail-label">Error Message:</span>
          <div class="error-message-box">
            {{ selectedLog.error_message }}
          </div>
        </div>
        <div v-if="selectedLog.request_params" class="detail-row">
          <span class="detail-label">Request Params:</span>
          <pre class="params-box">{{ JSON.stringify(selectedLog.request_params, null, 2) }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">Close</el-button>
      </template>
    </el-dialog>
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

.clickable-tag {
  cursor: pointer;
}

.clickable-tag:hover {
  opacity: 0.8;
}

.log-details {
  font-size: 14px;
}

.detail-row {
  display: flex;
  margin-bottom: 12px;
  align-items: flex-start;
}

.detail-label {
  width: 120px;
  color: #909399;
  flex-shrink: 0;
}

.detail-value {
  color: #303133;
  word-break: break-all;
}

.error-row {
  flex-direction: column;
}

.error-row .detail-label {
  margin-bottom: 8px;
}

.error-message-box {
  background-color: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 4px;
  padding: 12px;
  color: #f56c6c;
  word-break: break-word;
  white-space: pre-wrap;
  width: 100%;
}

.params-box {
  background-color: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  margin: 0;
  font-size: 12px;
  overflow-x: auto;
  width: 100%;
}
</style>
