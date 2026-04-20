<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { authApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/date'

const authStore = useAuthStore()

const users = ref<any[]>([])
const loading = ref(false)

const createUserDialogVisible = ref(false)
const changePasswordDialogVisible = ref(false)
const changeOwnPasswordDialogVisible = ref(false)

const newUser = ref({
  username: '',
  password: '',
  role: 'user',
})

const changePasswordForm = ref({
  userId: 0,
  newPassword: '',
  confirmPassword: '',
})

const changeOwnPasswordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const displayUsers = computed(() => {
  if (authStore.isRoot) {
    return users.value
  }
  return users.value.filter(u => u.id === authStore.user?.id)
})

const fetchUsers = async () => {
  loading.value = true
  try {
    const response = await authApi.listUsers()
    users.value = response.data.data
  } catch (error: any) {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleCreateUser = async () => {
  if (!newUser.value.username || !newUser.value.password) {
    ElMessage.warning('请填写完整的用户信息')
    return
  }
  
  try {
    await authApi.createUser(newUser.value)
    ElMessage.success('用户创建成功')
    createUserDialogVisible.value = false
    newUser.value = { username: '', password: '', role: 'user' }
    fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  }
}

const handleDeleteUser = async (user: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await authApi.deleteUser(user.id)
    ElMessage.success('用户删除成功')
    fetchUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const openChangePasswordDialog = (user: any) => {
  changePasswordForm.value = {
    userId: user.id,
    newPassword: '',
    confirmPassword: '',
  }
  changePasswordDialogVisible.value = true
}

const openChangeOwnPasswordDialog = () => {
  changeOwnPasswordForm.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  }
  changeOwnPasswordDialogVisible.value = true
}

const handleChangePassword = async () => {
  if (!changePasswordForm.value.newPassword || !changePasswordForm.value.confirmPassword) {
    ElMessage.warning('请填写新密码')
    return
  }
  
  if (changePasswordForm.value.newPassword !== changePasswordForm.value.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  
  if (changePasswordForm.value.newPassword.length < 6) {
    ElMessage.warning('密码长度至少6位')
    return
  }
  
  try {
    await authApi.changeUserPassword(changePasswordForm.value.userId, changePasswordForm.value.newPassword)
    ElMessage.success('密码修改成功')
    changePasswordDialogVisible.value = false
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  }
}

const handleChangeOwnPassword = async () => {
  if (!changeOwnPasswordForm.value.oldPassword || !changeOwnPasswordForm.value.newPassword || !changeOwnPasswordForm.value.confirmPassword) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  if (changeOwnPasswordForm.value.newPassword !== changeOwnPasswordForm.value.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  
  if (changeOwnPasswordForm.value.newPassword.length < 6) {
    ElMessage.warning('密码长度至少6位')
    return
  }
  
  try {
    await authApi.changeOwnPassword(changeOwnPasswordForm.value.oldPassword, changeOwnPasswordForm.value.newPassword)
    ElMessage.success('密码修改成功')
    changeOwnPasswordDialogVisible.value = false
    changeOwnPasswordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="user-management-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <div class="header-actions">
            <el-button v-if="authStore.isRoot" type="success" @click="createUserDialogVisible = true">
              创建用户
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="displayUsers" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="username" label="用户名" min-width="150" />
        <el-table-column prop="role" label="角色" min-width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">
              {{ row.role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="200">
          <template #default="{ row }">
            <template v-if="authStore.isRoot">
              <el-button
                size="small"
                @click="openChangePasswordDialog(row)"
              >
                修改密码
              </el-button>
              <el-button
                v-if="row.id !== authStore.user?.id"
                size="small"
                type="danger"
                @click="handleDeleteUser(row)"
              >
                删除
              </el-button>
            </template>
            <template v-else>
              <el-button
                size="small"
                type="primary"
                @click="openChangeOwnPasswordDialog"
              >
                修改我的密码
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog v-model="createUserDialogVisible" title="创建用户" width="400px">
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="newUser.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="newUser.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="newUser.role" style="width: 100%">
            <el-option label="Admin" value="admin" />
            <el-option label="User" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createUserDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateUser">创建</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="changePasswordDialogVisible" title="修改用户密码" width="400px">
      <el-form label-width="80px">
        <el-form-item label="新密码">
          <el-input v-model="changePasswordForm.newPassword" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="changePasswordForm.confirmPassword" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changePasswordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword">确定</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="changeOwnPasswordDialogVisible" title="修改我的密码" width="400px">
      <el-form label-width="80px">
        <el-form-item label="原密码">
          <el-input v-model="changeOwnPasswordForm.oldPassword" type="password" placeholder="请输入原密码" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="changeOwnPasswordForm.newPassword" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="changeOwnPasswordForm.confirmPassword" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changeOwnPasswordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleChangeOwnPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-management-view {
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
</style>
