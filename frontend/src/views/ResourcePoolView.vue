<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { resourcePoolApi, portRangeApi, publicIpApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import IpInput from '@/components/IpInput.vue'
import PortInput from '@/components/PortInput.vue'
import PortSearchInput from '@/components/PortSearchInput.vue'
import HighlightText from '@/components/HighlightText.vue'
import { formatDateTime } from '@/utils/date'

const authStore = useAuthStore()

const mappings = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const searchIp = ref('')
const searchPort = ref('')

const sortBy = ref('created_at')
const sortOrder = ref('desc')

const portRange = ref<{
  start_port: number
  end_port: number
  total_ports: number
  allocated_ports: number
  available_ports: number
} | null>(null)
const portRangeDialogVisible = ref(false)
const newStartPort = ref(10000)
const newEndPort = ref(20000)

const importDialogVisible = ref(false)
const importIpList = ref('')

const selectedIds = ref<number[]>([])

const hasSelection = computed(() => selectedIds.value.length > 0)

const publicIps = ref<any[]>([])
const importPubIpDialogVisible = ref(false)
const newPubIp = ref('')
const newPubIpDescription = ref('')
const newPubIpIsDefault = ref(false)
const ipInputRef = ref<InstanceType<typeof IpInput> | null>(null)

const changePubIpDialogVisible = ref(false)
const currentMapping = ref<any>(null)
const selectedPubIpId = ref<number | null>(null)

const fetchPublicIps = async () => {
  try {
    const response = await publicIpApi.list()
    publicIps.value = response.data.data
  } catch (error) {
    console.error('Failed to load public IPs')
  }
}

const fetchMappings = async () => {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    }
    if (searchIp.value) {
      params.internal_ip = searchIp.value
    }
    if (searchPort.value) {
      params.public_port = searchPort.value
    }
    
    const response = await resourcePoolApi.list(params)
    mappings.value = response.data.data.items
    total.value = response.data.data.total
    selectedIds.value = []
  } catch (error) {
    ElMessage.error('加载资源池失败')
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
  fetchMappings()
}

const handleSearch = () => {
  currentPage.value = 1
  fetchMappings()
}

const handleReset = () => {
  searchIp.value = ''
  searchPort.value = ''
  currentPage.value = 1
  fetchMappings()
}

const fetchPortRange = async () => {
  try {
    const response = await portRangeApi.get()
    portRange.value = response.data.data
  } catch (error) {
    console.error('Failed to load port range')
  }
}

const handleSetPortRange = async () => {
  if (newStartPort.value >= newEndPort.value) {
    ElMessage.warning('起始端口必须小于结束端口')
    return
  }
  
  try {
    await portRangeApi.set(newStartPort.value, newEndPort.value)
    ElMessage.success('端口范围已更新')
    portRangeDialogVisible.value = false
    fetchPortRange()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新端口范围失败')
  }
}

const handleImport = async () => {
  const inputs = importIpList.value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line)
  
  if (inputs.length === 0) {
    ElMessage.warning('请输入至少一个 IP 地址')
    return
  }
  
  try {
    const response = await resourcePoolApi.import(inputs)
    const count = response.data.data?.length || 0
    ElMessage.success(`成功导入 ${count} 个 IP 地址`)
    importDialogVisible.value = false
    importIpList.value = ''
    fetchMappings()
    fetchPortRange()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '导入失败')
  }
}

const handleImportPubIp = async () => {
  if (!newPubIp.value.trim()) {
    ElMessage.warning('请输入公网IP地址')
    return
  }
  
  if (!ipInputRef.value?.isValid) {
    ElMessage.warning('请输入有效的IP地址')
    return
  }
  
  try {
    await publicIpApi.import({
      ip_address: newPubIp.value.trim(),
      description: newPubIpDescription.value.trim() || undefined,
      is_default: newPubIpIsDefault.value,
    })
    ElMessage.success('公网IP导入成功')
    importPubIpDialogVisible.value = false
    newPubIp.value = ''
    newPubIpDescription.value = ''
    newPubIpIsDefault.value = false
    fetchPublicIps()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '导入失败')
  }
}

const handleSetDefaultPubIp = async (ipId: number) => {
  try {
    await publicIpApi.setDefault(ipId)
    ElMessage.success('已设为默认公网IP')
    fetchPublicIps()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '设置失败')
  }
}

const handleDeletePubIp = async (ip: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除公网IP "${ip.ip_address}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await publicIpApi.delete(ip.id)
    ElMessage.success('删除成功')
    fetchPublicIps()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const handleChangePubIp = (row: any) => {
  currentMapping.value = row
  selectedPubIpId.value = row.public_ip_id
  changePubIpDialogVisible.value = true
}

const handleConfirmChangePubIp = async () => {
  if (!currentMapping.value || !selectedPubIpId.value) {
    return
  }
  
  try {
    await resourcePoolApi.updatePublicIp(currentMapping.value.id, selectedPubIpId.value)
    ElMessage.success('公网IP更换成功')
    changePubIpDialogVisible.value = false
    fetchMappings()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更换失败')
  }
}

const handleDelete = async (row: any) => {
  if (row.has_config) {
    ElMessage.warning('该 IP 存在活跃配置，无法删除')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除 IP "${row.internal_ip}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await resourcePoolApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchMappings()
    fetchPortRange()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const handleBatchDelete = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的记录')
    return
  }
  
  const selectedRows = mappings.value.filter(m => selectedIds.value.includes(m.id))
  const withConfig = selectedRows.filter(r => r.has_config)
  
  if (withConfig.length > 0) {
    ElMessage.warning(`选中的 ${withConfig.length} 条记录存在活跃配置，无法删除`)
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.length} 条记录吗？`,
      '批量删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    const response = await resourcePoolApi.batchDelete(selectedIds.value)
    const result = response.data.data
    
    if (result.failed.length > 0) {
      ElMessage.warning(`成功删除 ${result.deleted.length} 条，失败 ${result.failed.length} 条`)
    } else {
      ElMessage.success(`成功删除 ${result.deleted.length} 条记录`)
    }
    
    fetchMappings()
    fetchPortRange()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedIds.value = selection.map(item => item.id)
}

const handleExport = async () => {
  try {
    const response = await fetch('/api/admin/resource-pool/export', {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
      },
    })
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'resource_pool.csv'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchMappings()
}

onMounted(() => {
  fetchMappings()
  fetchPortRange()
  fetchPublicIps()
})
</script>

<template>
  <div class="resource-pool-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>资源池管理</span>
          <div class="header-actions">
            <el-button v-if="authStore.isRoot" type="primary" @click="portRangeDialogVisible = true">
              配置端口范围
            </el-button>
            <el-button v-if="authStore.isRoot" type="success" @click="importDialogVisible = true">
              导入VM IP
            </el-button>
            <el-button v-if="authStore.isRoot" type="warning" @click="importPubIpDialogVisible = true">
              导入Pub IP
            </el-button>
            <el-button @click="handleExport">
              导出 CSV
            </el-button>
            <el-button
              v-if="authStore.isRoot"
              type="danger"
              :disabled="!hasSelection"
              @click="handleBatchDelete"
            >
              批量删除 ({{ selectedIds.length }})
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="search-bar">
        <el-input
          v-model="searchIp"
          placeholder="搜索内网 IP"
          clearable
          @keyup.enter="handleSearch"
          style="width: 200px; margin-right: 10px"
        />
        <PortSearchInput
          v-model="searchPort"
          style="margin-right: 10px"
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
      
      <div v-if="portRange" class="port-stats">
        <el-tag type="primary">端口范围: {{ portRange.start_port }} - {{ portRange.end_port }}</el-tag>
        <el-tag type="info">总端口数: {{ portRange.total_ports }}</el-tag>
        <el-tag type="success">已映射: {{ portRange.allocated_ports }}</el-tag>
        <el-tag type="warning">可用: {{ portRange.available_ports }}</el-tag>
      </div>
      
      <el-table
        :data="mappings"
        v-loading="loading"
        stripe
        @selection-change="handleSelectionChange"
        @sort-change="handleSortChange"
        :default-sort="{ prop: 'created_at', order: 'descending' }"
        style="width: 100%"
      >
        <el-table-column type="selection" min-width="55" />
        <el-table-column prop="internal_ip" label="内网 IP" min-width="150" sortable="custom">
          <template #default="{ row }">
            <HighlightText :text="row.internal_ip" :keyword="searchIp" />
          </template>
        </el-table-column>
        <el-table-column prop="public_ip_address" label="Pub IP" min-width="140">
          <template #default="{ row }">
            <el-button
              v-if="authStore.isRoot"
              type="primary"
              link
              @click="handleChangePubIp(row)"
            >
              {{ row.public_ip_address || '未设置' }}
            </el-button>
            <span v-else>{{ row.public_ip_address || '未设置' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="public_port" label="公网端口" min-width="100" sortable="custom" />
        <el-table-column prop="created_at" label="IP地址导入时间" min-width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="has_config" label="有配置" min-width="90">
          <template #default="{ row }">
            <el-tag :type="row.has_config ? 'success' : 'info'">
              {{ row.has_config ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="100">
          <template #default="{ row }">
            <el-button
              v-if="authStore.isRoot"
              type="danger"
              size="small"
              :disabled="row.has_config"
              @click="handleDelete(row)"
            >
              删除
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
        @size-change="fetchMappings"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
    
    <el-dialog v-model="portRangeDialogVisible" title="配置端口范围" width="400px">
      <el-form label-width="100px">
        <el-form-item label="起始端口">
          <PortInput v-model="newStartPort" :min="1024" :max="65535" />
        </el-form-item>
        <el-form-item label="结束端口">
          <PortInput v-model="newEndPort" :min="1024" :max="65535" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="portRangeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSetPortRange">保存</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="importDialogVisible" title="导入 VM IP 地址" width="600px">
      <div class="import-tips">
        <p>支持的输入格式：</p>
        <ul>
          <li><strong>单个 IP</strong>：192.168.1.100</li>
          <li><strong>IP 范围</strong>：192.168.1.100-192.168.1.110</li>
          <li><strong>CIDR 格式</strong>：192.168.1.0/24</li>
        </ul>
        <p>每行一个输入项，重复的 IP 会自动去重</p>
      </div>
      <el-input
        v-model="importIpList"
        type="textarea"
        :rows="10"
        placeholder="示例：&#10;192.168.1.100&#10;192.168.1.101-192.168.1.110&#10;192.168.2.0/28"
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="importPubIpDialogVisible" title="导入公网 IP" width="600px">
      <div class="pub-ip-list" v-if="publicIps.length > 0">
        <p style="margin-bottom: 10px; font-weight: 600;">已导入的公网IP：</p>
        <el-table :data="publicIps" size="small" max-height="200">
          <el-table-column prop="ip_address" label="IP地址" min-width="140" />
          <el-table-column prop="description" label="描述" min-width="120">
            <template #default="{ row }">
              {{ row.description || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="is_default" label="默认" min-width="70">
            <template #default="{ row }">
              <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
              <el-button
                v-else
                type="primary"
                link
                size="small"
                @click="handleSetDefaultPubIp(row.id)"
              >
                设为默认
              </el-button>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="70">
            <template #default="{ row }">
              <el-button
                type="danger"
                link
                size="small"
                @click="handleDeletePubIp(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-divider v-if="publicIps.length > 0" />
      <div class="import-form">
        <p style="margin-bottom: 10px; font-weight: 600;">导入新的公网IP：</p>
        <el-form label-width="100px">
          <el-form-item label="IP地址" required>
            <IpInput ref="ipInputRef" v-model="newPubIp" type="public" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="newPubIpDescription" placeholder="可选描述" />
          </el-form-item>
          <el-form-item label="设为默认">
            <el-switch v-model="newPubIpIsDefault" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="importPubIpDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleImportPubIp">导入</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="changePubIpDialogVisible" title="更换公网IP" width="400px">
      <p style="margin-bottom: 15px;">
        当前内网IP: <strong>{{ currentMapping?.internal_ip }}</strong>
      </p>
      <el-form label-width="100px">
        <el-form-item label="选择公网IP">
          <el-select v-model="selectedPubIpId" placeholder="请选择公网IP" style="width: 100%">
            <el-option
              v-for="ip in publicIps"
              :key="ip.id"
              :label="ip.ip_address + (ip.is_default ? ' (默认)' : '')"
              :value="ip.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changePubIpDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmChangePubIp">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.resource-pool-view {
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
  gap: 10px;
}

.search-bar {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.port-stats {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.import-tips {
  margin-bottom: 15px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
}

.import-tips p {
  margin: 5px 0;
}

.import-tips ul {
  margin: 5px 0;
  padding-left: 20px;
}

.import-tips li {
  margin: 3px 0;
}

.pub-ip-list {
  margin-bottom: 15px;
}

.import-form {
  margin-top: 15px;
}
</style>
