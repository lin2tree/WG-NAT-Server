<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { archiveApi, resourcePoolApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import PortSearchInput from '@/components/PortSearchInput.vue'
import HighlightText from '@/components/HighlightText.vue'
import { formatDateTime } from '@/utils/date'

const authStore = useAuthStore()

const archives = ref<any[]>([])
const loading = ref(false)
const searchIp = ref('')
const searchPort = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const stats = ref({
  total: 0,
})

const sortBy = ref('deleted_at')
const sortOrder = ref('desc')

const resourceIps = ref<Set<string>>(new Set())

const fetchResourceIps = async () => {
  try {
    const response = await resourcePoolApi.list({ page: 1, page_size: 10000 })
    const items = response.data.data.items
    resourceIps.value = new Set(items.map((item: any) => item.internal_ip))
  } catch (error) {
    console.error('Failed to fetch resource IPs')
  }
}

const validateSearch = (): boolean => {
  if (searchIp.value && !resourceIps.value.has(searchIp.value)) {
    ElMessage.warning('输入的 IP 不在资源池中')
    return false
  }
  return true
}

const fetchArchives = async () => {
  if (!validateSearch()) return
  
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    }
    if (searchIp.value) {
      params.vm_ip = searchIp.value
    }
    if (searchPort.value) {
      params.public_port = searchPort.value
    }
    
    const response = await archiveApi.list(params)
    archives.value = response.data.data.items
    total.value = response.data.data.total
    if (response.data.data.stats) {
      stats.value = response.data.data.stats
    }
  } catch (error: any) {
    ElMessage.error('加载归档数据失败')
  } finally {
    loading.value = false
  }
}

const handleSortChange = ({ prop, order }: { prop: string; order: string | null }) => {
  if (prop) {
    sortBy.value = prop
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    sortBy.value = 'deleted_at'
    sortOrder.value = 'desc'
  }
  fetchArchives()
}

const handleSearch = () => {
  currentPage.value = 1
  fetchArchives()
}

const handleReset = () => {
  searchIp.value = ''
  searchPort.value = ''
  currentPage.value = 1
  fetchArchives()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchArchives()
}

const handleExport = async () => {
  if (!validateSearch()) return
  
  try {
    const params: any = {}
    if (searchIp.value) {
      params.vm_ip = searchIp.value
    }
    if (searchPort.value) {
      params.public_port = searchPort.value
    }
    
    const response = await archiveApi.export(params)
    const blob = response.data
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'vpn_archives.csv'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchResourceIps()
  fetchArchives()
})
</script>

<template>
  <div class="archive-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>已归档数据</span>
          <div class="header-actions">
            <el-input
              v-model="searchIp"
              placeholder="搜索 VM IP"
              clearable
              @keyup.enter="handleSearch"
              style="width: 180px; margin-right: 10px"
            />
            <PortSearchInput
              v-model="searchPort"
              style="margin-right: 10px"
            />
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
            <el-button v-if="authStore.isRoot" type="success" @click="handleExport">
              导出 CSV
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="stats-bar">
        <el-tag type="info">已归档总数: {{ stats.total }}</el-tag>
      </div>
      
      <el-table
        :data="archives"
        v-loading="loading"
        stripe
        @sort-change="handleSortChange"
        :default-sort="{ prop: 'deleted_at', order: 'descending' }"
        style="width: 100%"
      >
        <el-table-column prop="vm_ip" label="VM IP" min-width="130" sortable="custom">
          <template #default="{ row }">
            <HighlightText :text="row.vm_ip" :keyword="searchIp" />
          </template>
        </el-table-column>
        <el-table-column prop="vm_port" label="VM Port" min-width="90" />
        <el-table-column prop="pub_ip" label="Pub IP" min-width="130" />
        <el-table-column prop="pub_port" label="Pub Port" min-width="90" />
        <el-table-column prop="status" label="状态" min-width="80">
          <template #default="{ row }">
            <el-tag type="info">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="初始化时间" min-width="170" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="启动时间" min-width="170" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="deleted_at" label="删除时间" min-width="170" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.deleted_at) }}
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
        @size-change="fetchArchives"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
  </div>
</template>

<style scoped>
.archive-view {
  padding: 20px;
}

:deep(.el-table .cell) {
  text-align: center;
}

:deep(.el-table) {
  width: 100% !important;
}

:deep(.el-table__body-wrapper),
:deep(.el-table__header-wrapper) {
  width: 100% !important;
}

:deep(.el-table__body),
:deep(.el-table__header) {
  width: 100% !important;
  table-layout: auto !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
}

.stats-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}
</style>
