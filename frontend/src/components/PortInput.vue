<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = defineProps<{
  modelValue: number
  min?: number
  max?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>()

const localValue = ref<string>('')

const minValue = computed(() => props.min ?? 1024)
const maxValue = computed(() => props.max ?? 65535)

const isValid = computed(() => {
  if (!localValue.value) return true
  const num = parseInt(localValue.value, 10)
  return !isNaN(num) && num >= minValue.value && num <= maxValue.value
})

const errorMessage = computed(() => {
  if (!localValue.value) return ''
  const num = parseInt(localValue.value, 10)
  if (isNaN(num)) return '请输入数字'
  if (num < minValue.value) return `最小值为 ${minValue.value}`
  if (num > maxValue.value) return `最大值为 ${maxValue.value}`
  return ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal !== null && newVal !== undefined) {
    localValue.value = String(newVal)
  } else {
    localValue.value = String(minValue.value)
  }
}, { immediate: true })

watch(localValue, (newVal) => {
  if (newVal === '') {
    emit('update:modelValue', minValue.value)
  } else {
    const num = parseInt(newVal, 10)
    if (!isNaN(num)) {
      emit('update:modelValue', num)
    }
  }
})

const handleInput = (event: Event) => {
  const input = event.target as HTMLInputElement
  let value = input.value.replace(/[^0-9]/g, '')
  localValue.value = value
}

const handleBlur = () => {
  if (localValue.value) {
    let num = parseInt(localValue.value, 10)
    if (num < minValue.value) {
      localValue.value = String(minValue.value)
      emit('update:modelValue', minValue.value)
    } else if (num > maxValue.value) {
      localValue.value = String(maxValue.value)
      emit('update:modelValue', maxValue.value)
    }
  } else {
    localValue.value = String(minValue.value)
    emit('update:modelValue', minValue.value)
  }
}

const clearInput = () => {
  localValue.value = String(minValue.value)
}

defineExpose({
  isValid,
  clearInput,
  errorMessage
})
</script>

<template>
  <div class="port-input-wrapper" :class="{ 'is-invalid': !isValid && localValue }">
    <input
      :value="localValue"
      type="text"
      class="port-input"
      :placeholder="`${minValue}-${maxValue}`"
      @input="handleInput"
      @blur="handleBlur"
    />
    <span v-if="!isValid && localValue" class="error-hint">{{ errorMessage }}</span>
  </div>
</template>

<style scoped>
.port-input-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.port-input {
  width: 120px;
  height: 32px;
  text-align: center;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  font-family: monospace;
  outline: none;
  transition: border-color 0.2s;
  padding: 0 10px;
}

.port-input:focus {
  border-color: #409eff;
}

.port-input::placeholder {
  color: #c0c4cc;
}

.port-input-wrapper.is-invalid .port-input {
  border-color: #f56c6c;
}

.error-hint {
  color: #f56c6c;
  font-size: 12px;
  white-space: nowrap;
}
</style>
