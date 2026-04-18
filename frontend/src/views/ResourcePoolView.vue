<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { resourcePoolApi, portRangeApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()

const mappings = ref<any[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const portRange = ref<{ start_port: number; end_port: number } | null>(null)
const portRangeDialogVisible = ref(false)
const newStartPort = ref(10000)
const newEndPort = ref(20000)

const importDialogVisible = ref(false)
const importIpList = ref('')

const fetchMappings = async () => {
  loading.value = true
  try {
    const response = await resourcePoolApi.list({
      page: currentPage.value,
      page_size: pageSize.value,
    })
    mappings.value = response.data.data.items
    total.value = response.data.data.total
  } catch (error) {
    ElMessage.error('Failed to load resource pool')
  } finally {
    loading.value = false
  }
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
  try {
    await portRangeApi.set(newStartPort.value, newEndPort.value)
    ElMessage.success('Port range updated')
    portRangeDialogVisible.value = false
    fetchPortRange()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to update port range')
  }
}

const handleImport = async () => {
  const ips = importIpList.value
    .split('\n')
    .map((ip) => ip.trim())
    .filter((ip) => ip)
  
  if (ips.length === 0) {
    ElMessage.warning('Please enter at least one IP address')
    return
  }
  
  try {
    const response = await resourcePoolApi.import(ips)
    ElMessage.success(`Imported ${response.data.message.match(/\d+/)[0]} IP addresses`)
    importDialogVisible.value = false
    importIpList.value = ''
    fetchMappings()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Import failed')
  }
}

const handleDelete = async (id: number) => {
  try {
    await resourcePoolApi.delete(id)
    ElMessage.success('Mapping deleted')
    fetchMappings()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Delete failed')
  }
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
  } catch (error) {
    ElMessage.error('Export failed')
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchMappings()
}

onMounted(() => {
  fetchMappings()
  fetchPortRange()
})
</script>

<template>
  <div class="resource-pool-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Resource Pool</span>
          <div class="header-actions">
            <el-button v-if="authStore.isRoot" type="primary" @click="portRangeDialogVisible = true">
              Configure Port Range
            </el-button>
            <el-button v-if="authStore.isRoot" type="success" @click="importDialogVisible = true">
              Import IPs
            </el-button>
            <el-button @click="handleExport">
              Export CSV
            </el-button>
          </div>
        </div>
      </template>
      
      <div v-if="portRange" class="port-range-info">
        <el-tag>Port Range: {{ portRange.start_port }} - {{ portRange.end_port }}</el-tag>
      </div>
      
      <el-table :data="mappings" v-loading="loading" stripe>
        <el-table-column prop="internal_ip" label="Internal IP" width="180" />
        <el-table-column prop="public_port" label="Public Port" width="120" />
        <el-table-column prop="created_at" label="Created" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="has_config" label="Has Config" width="100">
          <template #default="{ row }">
            <el-tag :type="row.has_config ? 'success' : 'info'">
              {{ row.has_config ? 'Yes' : 'No' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="100">
          <template #default="{ row }">
            <el-button
              v-if="authStore.isRoot && !row.has_config"
              type="danger"
              size="small"
              @click="handleDelete(row.id)"
            >
              Delete
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
    
    <el-dialog v-model="portRangeDialogVisible" title="Configure Port Range" width="400px">
      <el-form label-width="100px">
        <el-form-item label="Start Port">
          <el-input-number v-model="newStartPort" :min="1024" :max="65535" />
        </el-form-item>
        <el-form-item label="End Port">
          <el-input-number v-model="newEndPort" :min="1024" :max="65535" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="portRangeDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="handleSetPortRange">Save</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="importDialogVisible" title="Import IP Addresses" width="500px">
      <el-input
        v-model="importIpList"
        type="textarea"
        :rows="10"
        placeholder="Enter IP addresses, one per line&#10;Example:&#10;192.168.1.100&#10;192.168.1.101"
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="handleImport">Import</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.resource-pool-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.port-range-info {
  margin-bottom: 20px;
}
</style>
