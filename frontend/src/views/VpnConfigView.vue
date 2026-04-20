<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { vpnConfigApi, resourcePoolApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'
import PortSearchInput from '@/components/PortSearchInput.vue'
import HighlightText from '@/components/HighlightText.vue'
import { formatDateTime } from '@/utils/date'

const authStore = useAuthStore()

const configs = ref<any[]>([])
const loading = ref(false)
const statusFilter = ref('')
const searchIp = ref('')
const searchPort = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const stats = ref({
  total: 0,
  init: 0,
  started: 0,
})

const sortBy = ref('created_at')
const sortOrder = ref('desc')

const resourceIps = ref<Set<string>>(new Set())

const clientConfigDialogVisible = ref(false)
const clientConfigLoading = ref(false)
const clientConfigData = ref<any>(null)
const currentVmIp = ref('')

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

const fetchConfigs = async () => {
  if (!validateSearch()) return
  
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    if (searchIp.value) {
      params.vm_ip = searchIp.value
    }
    if (searchPort.value) {
      params.public_port = searchPort.value
    }
    
    const response = await vpnConfigApi.list(params)
    configs.value = response.data.data.items
    total.value = response.data.data.total
    if (response.data.data.stats) {
      stats.value = response.data.data.stats
    }
  } catch (error: any) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

const handleSortChange = ({ prop, order }: { prop: string; order: string | null }) => {
  if (prop) {
    sortBy.value = prop
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    sortBy.value = 'created_at'
    sortOrder.value = 'desc'
  }
  fetchConfigs()
}

const handleSearch = () => {
  currentPage.value = 1
  fetchConfigs()
}

const handleReset = () => {
  statusFilter.value = ''
  searchIp.value = ''
  searchPort.value = ''
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

const downloadServerConfig = async (vmIp: string) => {
  try {
    const response = await vpnConfigApi.downloadServer(vmIp)
    const blob = response.data
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `wg0_${vmIp}.conf`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const downloadAllClients = async (vmIp: string) => {
  try {
    const response = await vpnConfigApi.downloadAllClients(vmIp)
    const blob = response.data
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `clients_${vmIp}.zip`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const viewClientConfigs = async (vmIp: string) => {
  currentVmIp.value = vmIp
  clientConfigDialogVisible.value = true
  clientConfigLoading.value = true
  
  try {
    const response = await vpnConfigApi.getClientConfigs(vmIp)
    clientConfigData.value = response.data.data
  } catch (error) {
    ElMessage.error('获取客户端配置失败')
    clientConfigDialogVisible.value = false
  } finally {
    clientConfigLoading.value = false
  }
}

const copyConfig = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const handleExport = async () => {
  if (!validateSearch()) return
  
  try {
    const params: any = {}
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    if (searchIp.value) {
      params.vm_ip = searchIp.value
    }
    if (searchPort.value) {
      params.public_port = searchPort.value
    }
    
    const response = await vpnConfigApi.export(params)
    const blob = response.data
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'vpn_configs.csv'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchResourceIps()
  fetchConfigs()
})
</script>

<template>
  <div class="vpn-config-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VPN 配置管理</span>
          <div class="header-actions">
            <el-select
              v-model="statusFilter"
              placeholder="状态"
              clearable
              @change="handleSearch"
              style="width: 120px; margin-right: 10px"
            >
              <el-option label="Init" value="init" />
              <el-option label="Started" value="started" />
            </el-select>
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
        <el-tag type="info">总配置数: {{ stats.total }}</el-tag>
        <el-tag type="warning">待启动: {{ stats.init }}</el-tag>
        <el-tag type="success">已启动: {{ stats.started }}</el-tag>
      </div>
      
      <el-table
        :data="configs"
        v-loading="loading"
        stripe
        @sort-change="handleSortChange"
        :default-sort="{ prop: 'created_at', order: 'descending' }"
        style="width: 100%"
      >
        <el-table-column prop="vm_ip" label="VM IP" min-width="140" sortable="custom">
          <template #default="{ row }">
            <HighlightText :text="row.vm_ip" :keyword="searchIp" />
          </template>
        </el-table-column>
        <el-table-column prop="vm_port" label="VM Port" min-width="100" />
        <el-table-column prop="pub_ip" label="Pub IP" min-width="140" />
        <el-table-column prop="pub_port" label="Pub Port" min-width="100" />
        <el-table-column prop="status" label="状态" min-width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="初始化时间" min-width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="启动时间" min-width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="280">
          <template #default="{ row }">
            <el-button
              v-if="authStore.isRoot"
              size="small"
              type="primary"
              @click="downloadServerConfig(row.vm_ip)"
            >
              下载服务端配置
            </el-button>
            <el-button
              v-if="authStore.isRoot"
              size="small"
              type="success"
              @click="downloadAllClients(row.vm_ip)"
            >
              下载客户端配置
            </el-button>
            <el-button
              v-if="!authStore.isRoot"
              size="small"
              @click="viewClientConfigs(row.vm_ip)"
            >
              查看客户端配置
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
    
    <el-dialog
      v-model="clientConfigDialogVisible"
      :title="`客户端配置 - ${currentVmIp}`"
      width="90%"
      class="client-config-dialog"
    >
      <div v-loading="clientConfigLoading">
        <div v-if="clientConfigData" class="client-configs">
          <p class="server-info">
            VM公钥: <code>{{ clientConfigData.server_public_key }}</code>
          </p>
          <el-divider style="margin: 12px 0" />
          <div class="client-cards">
            <el-card
              v-for="client in clientConfigData.clients"
              :key="client.name"
              class="client-card"
              shadow="hover"
            >
              <template #header>
                <div class="client-header">
                  <span class="client-name">{{ client.name }}</span>
                  <el-tag size="small">{{ client.vpn_ip }}</el-tag>
                </div>
              </template>
              <div class="client-info">
                <p><strong>客户端私钥:</strong> <code>{{ client.private_key_masked }}</code></p>
                <p><strong>客户端公钥:</strong> <code>{{ client.public_key }}</code></p>
              </div>
              <el-collapse>
                <el-collapse-item name="config">
                  <template #title>
                    <span class="collapse-title">查看完整配置</span>
                  </template>
                  <div class="config-wrapper">
                    <el-tooltip content="复制" placement="top">
                      <el-button
                        class="copy-btn"
                        size="small"
                        :icon="DocumentCopy"
                        circle
                        @click="copyConfig(client.config_file_masked)"
                      />
                    </el-tooltip>
                    <pre class="config-text">{{ client.config_file_masked }}</pre>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </el-card>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="clientConfigDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.vpn-config-view {
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

.client-configs {
  padding: 5px 0;
}

.server-info {
  margin-bottom: 8px;
  font-size: 14px;
}

.server-info code {
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.client-cards {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.client-card {
  flex: 0 0 calc(50% - 6px);
  min-width: 300px;
}

.client-card :deep(.el-card__header) {
  padding: 10px 15px;
}

.client-card :deep(.el-card__body) {
  padding: 12px 15px;
}

.client-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.client-name {
  font-weight: 600;
  font-size: 18px;
}

.client-info {
  font-size: 13px;
  margin-bottom: 8px;
}

.client-info p {
  margin: 4px 0;
}

.client-info code {
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
}

.collapse-title {
  font-size: 18px;
  font-weight: 600;
}

.config-wrapper {
  position: relative;
}

.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
}

.config-text {
  background-color: #f5f7fa;
  padding: 10px;
  padding-right: 40px;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  max-height: 150px;
  overflow-y: auto;
}

.client-config-dialog :deep(.el-dialog__body) {
  padding: 15px 20px;
}

.client-config-dialog :deep(.el-dialog__title) {
  font-size: 20px;
  font-weight: 600;
}

.client-config-dialog :deep(.el-dialog__header) {
  display: flex;
  align-items: center;
  height: 54px;
}

.client-config-dialog :deep(.el-divider) {
  margin: 10px 0;
}

.client-config-dialog :deep(.el-collapse-item__header) {
  height: 36px;
  line-height: 36px;
}

.client-config-dialog :deep(.el-collapse-item__content) {
  padding-bottom: 8px;
}

.client-config-dialog :deep(.el-tag) {
  font-size: 22px;
}
</style>
