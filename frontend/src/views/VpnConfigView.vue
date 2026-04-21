<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { vpnConfigApi, resourcePoolApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'
import PortSearchInput from '@/components/PortSearchInput.vue'
import HighlightText from '@/components/HighlightText.vue'
import { formatDateTime } from '@/utils/date'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

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

useAutoRefresh(fetchConfigs)
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
  padding: var(--spacing-lg);
  animation: fadeIn var(--transition-base);
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
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  font-family: 'Fira Code', monospace;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.stats-bar {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
  padding: var(--spacing-sm);
  background: linear-gradient(135deg, var(--color-background) 0%, var(--color-background-alt) 100%);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.stats-bar :deep(.el-tag) {
  font-weight: var(--font-weight-bold);
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
}

.client-configs {
  padding: var(--spacing-sm) 0;
}

.server-info {
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
}

.server-info code {
  background: linear-gradient(135deg, var(--color-background) 0%, var(--color-background-alt) 100%);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-md);
  font-family: 'Fira Code', monospace;
  border: 1px solid var(--color-border);
}

.client-cards {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.client-card {
  flex: 0 0 calc(50% - var(--spacing-sm));
  min-width: 300px;
  transition: all var(--transition-base);
  border: 1px solid var(--color-border);
  cursor: pointer;
}

.client-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-xl);
  border-color: var(--color-primary);
}

.client-card :deep(.el-card__header) {
  padding: var(--spacing-sm) var(--spacing-md);
  background: linear-gradient(135deg, var(--color-background) 0%, #ffffff 100%);
  border-bottom: 2px solid var(--color-primary);
}

.client-card :deep(.el-card__body) {
  padding: var(--spacing-md);
}

.client-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.client-name {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-large);
  color: var(--color-text);
  font-family: 'Fira Code', monospace;
}

.client-info {
  font-size: var(--font-size-small);
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-muted);
}

.client-info p {
  margin: var(--spacing-xs) 0;
  line-height: 1.6;
}

.client-info code {
  background: linear-gradient(135deg, var(--color-background) 0%, var(--color-background-alt) 100%);
  padding: 2px var(--spacing-xs);
  border-radius: var(--radius-sm);
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  border: 1px solid var(--color-border);
}

.collapse-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.config-wrapper {
  position: relative;
  background: linear-gradient(135deg, var(--color-background) 0%, #ffffff 100%);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border);
}

.copy-btn {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
  z-index: 10;
  transition: all var(--transition-fast);
  cursor: pointer;
}

.copy-btn:hover {
  transform: scale(1.1);
}

.config-text {
  background-color: #0C4A6E;
  color: #E0F2FE;
  padding: var(--spacing-md);
  padding-right: 48px;
  border-radius: var(--radius-md);
  font-size: 11px;
  font-family: 'Fira Code', monospace;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  max-height: 200px;
  overflow-y: auto;
  line-height: 1.6;
  box-shadow: inset 0 2px 8px rgba(12, 74, 110, 0.2);
}

.client-config-dialog :deep(.el-dialog__body) {
  padding: var(--spacing-md) var(--spacing-lg);
}

.client-config-dialog :deep(.el-dialog__title) {
  font-size: var(--font-size-title);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  font-family: 'Fira Code', monospace;
}

.client-config-dialog :deep(.el-dialog__header) {
  display: flex;
  align-items: center;
  height: 60px;
  background: linear-gradient(135deg, var(--color-background) 0%, #ffffff 100%);
  border-bottom: 2px solid var(--color-primary);
}

.client-config-dialog :deep(.el-divider) {
  margin: var(--spacing-sm) 0;
}

.client-config-dialog :deep(.el-collapse-item__header) {
  height: 40px;
  line-height: 40px;
  background: linear-gradient(135deg, var(--color-background) 0%, #ffffff 100%);
  border-radius: var(--radius-md);
  padding: 0 var(--spacing-md);
  transition: all var(--transition-fast);
  cursor: pointer;
}

.client-config-dialog :deep(.el-collapse-item__header:hover) {
  background: linear-gradient(135deg, var(--color-background-alt) 0%, var(--color-background) 100%);
}

.client-config-dialog :deep(.el-collapse-item__content) {
  padding-bottom: var(--spacing-sm);
}

.client-config-dialog :deep(.el-tag) {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
}

@media (max-width: 1024px) {
  .client-card {
    flex: 0 0 100%;
  }
}

@media (max-width: 768px) {
  .vpn-config-view {
    padding: var(--spacing-md);
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
  
  .header-actions :deep(.el-input),
  .header-actions :deep(.el-select) {
    width: 100% !important;
    margin-right: 0 !important;
    margin-bottom: var(--spacing-xs);
  }
  
  .stats-bar {
    justify-content: center;
  }
  
  .client-card {
    min-width: 100%;
  }
  
  :deep(.el-table__body-wrapper) {
    overflow-x: auto;
  }
}

@media (max-width: 480px) {
  .vpn-config-view {
    padding: var(--spacing-sm);
  }
  
  .stats-bar :deep(.el-tag) {
    font-size: 11px;
    padding: var(--spacing-xs) var(--spacing-sm);
  }
  
  .config-text {
    font-size: 10px;
    padding: var(--spacing-sm);
  }
}

@media (prefers-reduced-motion: reduce) {
  .vpn-config-view {
    animation: none;
  }
  
  .client-card:hover {
    transform: none;
  }
  
  .copy-btn:hover {
    transform: none;
  }
}
</style>
