<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = defineProps<{
  modelValue: string
  type?: 'public' | 'private' | 'any'
  searchMode?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const octets = ref<string[]>(['', '', '', ''])

const isValid = computed(() => {
  if (octets.value.every(o => o === '')) {
    return true
  }
  
  if (props.searchMode) {
    const filledOctets = octets.value.filter(o => o !== '')
    return filledOctets.every(o => {
      const num = parseInt(o, 10)
      return !isNaN(num) && num >= 0 && num <= 255
    })
  }
  
  if (!octets.value.every(o => {
    const num = parseInt(o, 10)
    return o !== '' && !isNaN(num) && num >= 0 && num <= 255
  })) {
    return false
  }
  
  const ip = getIpNumber()
  if (ip === null) return false
  
  return validateIpRange(ip)
})

const errorMessage = computed(() => {
  if (octets.value.every(o => o === '')) {
    return ''
  }
  
  if (props.searchMode) {
    const filledOctets = octets.value.filter(o => o !== '')
    if (!filledOctets.every(o => {
      const num = parseInt(o, 10)
      return !isNaN(num) && num >= 0 && num <= 255
    })) {
      return '每段必须在0-255之间'
    }
    return ''
  }
  
  const nums = octets.value.map(o => parseInt(o, 10))
  if (!nums.every(n => !isNaN(n) && n >= 0 && n <= 255)) {
    return '每段必须在0-255之间'
  }
  
  const ip = getIpNumber()
  if (ip === null) return ''
  
  return getIpValidationError(ip)
})

const fullIp = computed(() => {
  if (octets.value.every(o => o === '')) {
    return ''
  }
  return octets.value.join('.')
})

function getIpNumber(): number | null {
  const nums = octets.value.map(o => parseInt(o, 10))
  if (nums.some(n => isNaN(n))) return null
  return (nums[0] << 24) | (nums[1] << 16) | (nums[2] << 8) | nums[3]
}

function validateIpRange(ip: number): boolean {
  return getIpValidationError(ip) === ''
}

function getIpValidationError(ip: number): string {
  const firstOctet = (ip >> 24) & 0xFF
  
  if (firstOctet === 0) {
    return '0.x.x.x 是保留地址'
  }
  
  if (firstOctet === 127) {
    return '127.x.x.x 是回环地址'
  }
  
  if (firstOctet >= 224 && firstOctet <= 239) {
    return '224.x.x.x - 239.x.x.x 是组播地址'
  }
  
  if (firstOctet >= 240) {
    return '240.x.x.x - 255.x.x.x 是保留地址'
  }
  
  if (ip === 0xFFFFFFFF) {
    return '255.255.255.255 是广播地址'
  }
  
  if (firstOctet === 169 && ((ip >> 16) & 0xFF) === 254) {
    return '169.254.x.x 是链路本地地址'
  }
  
  if (props.type === 'public') {
    if (firstOctet === 10) {
      return '10.x.x.x 是私有地址，不能作为公网IP'
    }
    if (firstOctet === 172 && ((ip >> 16) & 0xFF) >= 16 && ((ip >> 16) & 0xFF) <= 31) {
      return '172.16.x.x - 172.31.x.x 是私有地址，不能作为公网IP'
    }
    if (firstOctet === 192 && ((ip >> 16) & 0xFF) === 168) {
      return '192.168.x.x 是私有地址，不能作为公网IP'
    }
  }
  
  if (props.type === 'private') {
    const isPrivate = 
      firstOctet === 10 ||
      (firstOctet === 172 && ((ip >> 16) & 0xFF) >= 16 && ((ip >> 16) & 0xFF) <= 31) ||
      (firstOctet === 192 && ((ip >> 16) & 0xFF) === 168)
    
    if (!isPrivate) {
      return '请输入私有IP地址 (10.x.x.x, 172.16-31.x.x, 或 192.168.x.x)'
    }
  }
  
  return ''
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    const parts = newVal.split('.')
    if (parts.length === 4) {
      octets.value = parts.map(p => p || '')
    } else if (props.searchMode && parts.length > 0 && parts.length <= 4) {
      const newOctets = ['', '', '', '']
      parts.forEach((p, i) => {
        newOctets[i] = p || ''
      })
      octets.value = newOctets
    }
  } else {
    octets.value = ['', '', '', '']
  }
}, { immediate: true })

watch(fullIp, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleInput = (index: number, event: Event) => {
  const input = event.target as HTMLInputElement
  let value = input.value.replace(/[^0-9]/g, '')
  
  if (value.length > 0) {
    let num = parseInt(value, 10)
    if (num > 255) {
      value = '255'
    } else if (num < 0) {
      value = '0'
    }
  }
  
  octets.value[index] = value
  
  if (value.length === 3 && index < 3) {
    const nextInput = input.parentElement?.parentElement?.querySelectorAll('.ip-octet')[index + 1] as HTMLInputElement
    if (nextInput) {
      nextInput.focus()
      nextInput.select()
    }
  }
}

const handleKeydown = (index: number, event: KeyboardEvent) => {
  const input = event.target as HTMLInputElement
  
  if (event.key === 'Backspace' && input.value === '' && index > 0) {
    const prevInput = input.parentElement?.parentElement?.querySelectorAll('.ip-octet')[index - 1] as HTMLInputElement
    if (prevInput) {
      prevInput.focus()
      prevInput.select()
    }
  }
  
  if (event.key === 'ArrowLeft' && input.selectionStart === 0 && index > 0) {
    const prevInput = input.parentElement?.parentElement?.querySelectorAll('.ip-octet')[index - 1] as HTMLInputElement
    if (prevInput) {
      prevInput.focus()
      prevInput.select()
      event.preventDefault()
    }
  }
  
  if (event.key === 'ArrowRight' && input.selectionStart === input.value.length && index < 3) {
    const nextInput = input.parentElement?.parentElement?.querySelectorAll('.ip-octet')[index + 1] as HTMLInputElement
    if (nextInput) {
      nextInput.focus()
      nextInput.select()
      event.preventDefault()
    }
  }
}

const handlePaste = (event: ClipboardEvent) => {
  event.preventDefault()
  const text = event.clipboardData?.getData('text') || ''
  const parts = text.split('.').map(p => p.trim())
  
  if (parts.length >= 1 && parts.length <= 4) {
    const validParts = parts.map(p => {
      const num = parseInt(p, 10)
      if (isNaN(num) || num < 0) return ''
      if (num > 255) return '255'
      return String(num)
    })
    while (validParts.length < 4) {
      validParts.push('')
    }
    octets.value = validParts.slice(0, 4) as string[]
  }
}

const clearInput = () => {
  octets.value = ['', '', '', '']
}

defineExpose({
  isValid,
  clearInput,
  errorMessage
})
</script>

<template>
  <div class="ip-input-wrapper" :class="{ 'is-invalid': !isValid && fullIp, 'search-mode': searchMode }">
    <input
      v-for="(_, index) in 4"
      :key="index"
      :value="octets[index]"
      type="text"
      class="ip-octet"
      :class="{ 'search-octet': searchMode }"
      maxlength="3"
      :placeholder="searchMode ? '' : '0'"
      @input="handleInput(index, $event)"
      @keydown="handleKeydown(index, $event)"
      @paste="index === 0 ? handlePaste($event) : null"
    />
    <span v-if="!isValid && fullIp" class="error-hint">{{ errorMessage }}</span>
  </div>
</template>

<style scoped>
.ip-input-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ip-octet {
  width: 60px;
  height: 32px;
  text-align: center;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  font-family: monospace;
  outline: none;
  transition: border-color 0.2s;
}

.ip-octet:focus {
  border-color: #409eff;
}

.ip-octet::placeholder {
  color: #c0c4cc;
}

.search-mode .ip-octet {
  width: 50px;
  height: 28px;
  font-size: 13px;
}

.search-mode .search-octet {
  background-color: #f5f7fa;
}

.ip-input-wrapper.is-invalid .ip-octet {
  border-color: #f56c6c;
}

.error-hint {
  color: #f56c6c;
  font-size: 12px;
  margin-left: 8px;
  white-space: nowrap;
}
</style>
