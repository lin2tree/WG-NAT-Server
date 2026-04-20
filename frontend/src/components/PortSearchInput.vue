<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = defineProps<{
  modelValue: string
  min?: number
  max?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const localValue = ref<string>('')

const minValue = computed(() => props.min ?? 1024)
const maxValue = computed(() => props.max ?? 65535)

const isValid = computed(() => {
  if (!localValue.value) return true
  const num = parseInt(localValue.value, 10)
  if (isNaN(num)) return false
  return num >= minValue.value && num <= maxValue.value
})

watch(() => props.modelValue, (newVal) => {
  localValue.value = newVal || ''
}, { immediate: true })

watch(localValue, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleInput = (event: Event) => {
  const input = event.target as HTMLInputElement
  let value = input.value.replace(/[^0-9]/g, '')
  localValue.value = value
}

const handleBlur = () => {
  if (localValue.value) {
    const num = parseInt(localValue.value, 10)
    if (isNaN(num) || num < minValue.value) {
      localValue.value = String(minValue.value)
    } else if (num > maxValue.value) {
      localValue.value = String(maxValue.value)
    }
  }
}

defineExpose({
  isValid
})
</script>

<template>
  <div class="port-search-wrapper" :class="{ 'is-invalid': !isValid }">
    <input
      :value="localValue"
      type="text"
      class="port-search-input"
      :placeholder="`端口 (${minValue}-${maxValue})`"
      @input="handleInput"
      @blur="handleBlur"
    />
  </div>
</template>

<style scoped>
.port-search-wrapper {
  display: inline-block;
}

.port-search-input {
  width: 150px;
  height: 32px;
  text-align: center;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  font-family: monospace;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  padding: 0 10px;
  background-color: #fff;
}

.port-search-input:focus {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.port-search-input::placeholder {
  color: #a8abb2;
  font-size: 13px;
}

.port-search-wrapper.is-invalid .port-search-input {
  border-color: #f56c6c;
}
</style>
