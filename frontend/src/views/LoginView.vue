<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

const handleLogin = async () => {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入完整的用户名和密码')
    return
  }
  
  loading.value = true
  try {
    await authStore.login(username.value, password.value)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error: any) {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-box">
      <h1>WireGuard VPN Manager</h1>
      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input
            v-model="username"
            placeholder="Username"
            size="large"
            prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="Password"
            size="large"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            style="width: 100%"
          >
            Login
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 50%, var(--color-secondary) 100%);
  position: relative;
  overflow: hidden;
}

.login-container::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
  animation: rotate 30s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.login-box {
  width: 420px;
  max-width: 90%;
  padding: var(--spacing-2xl);
  background: rgba(255, 255, 255, 0.98);
  border-radius: var(--radius-xl);
  box-shadow: 0 20px 60px rgba(3, 105, 161, 0.3);
  backdrop-filter: blur(20px);
  position: relative;
  z-index: 1;
  animation: fadeIn var(--transition-slow);
}

.login-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light), var(--color-cta));
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.login-box h1 {
  text-align: center;
  margin-bottom: var(--spacing-xl);
  color: var(--color-text);
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.5px;
  font-family: 'Fira Code', monospace;
}

.login-box :deep(.el-form-item) {
  margin-bottom: var(--spacing-lg);
}

.login-box :deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
  box-shadow: 0 2px 8px rgba(3, 105, 161, 0.08);
  transition: all var(--transition-base);
  padding: var(--spacing-sm) var(--spacing-md);
}

.login-box :deep(.el-input__wrapper:hover) {
  box-shadow: 0 4px 12px rgba(3, 105, 161, 0.12);
}

.login-box :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.2);
  border-color: var(--color-primary);
}

.login-box :deep(.el-button--primary) {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
  border: none;
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.5px;
  transition: all var(--transition-base);
  box-shadow: 0 4px 15px rgba(3, 105, 161, 0.3);
}

.login-box :deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
  box-shadow: 0 6px 20px rgba(3, 105, 161, 0.4);
  transform: translateY(-2px);
}

.login-box :deep(.el-button--primary:active) {
  transform: translateY(0);
  box-shadow: 0 2px 10px rgba(3, 105, 161, 0.3);
}

@media (max-width: 768px) {
  .login-box {
    width: 90%;
    padding: var(--spacing-xl);
  }
  
  .login-box h1 {
    font-size: 20px;
    margin-bottom: var(--spacing-lg);
  }
}

@media (max-width: 480px) {
  .login-box {
    width: 95%;
    padding: var(--spacing-lg);
  }
  
  .login-box h1 {
    font-size: 18px;
  }
  
  .login-box :deep(.el-input__inner) {
    font-size: var(--font-size-small);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-container::before {
    animation: none;
  }
  
  .login-box {
    animation: none;
  }
  
  .login-box :deep(.el-button--primary:hover) {
    transform: none;
  }
}
</style>
