<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  text: string
  keyword: string
  highlightClass?: string
}>()

const highlightClass = computed(() => props.highlightClass || 'highlight-text')

interface TextPart {
  text: string
  highlight: boolean
}

const highlightedText = computed((): TextPart[] => {
  if (!props.keyword || !props.text) {
    return [{ text: props.text, highlight: false }]
  }
  
  const regex = new RegExp(`(${escapeRegExp(props.keyword)})`, 'gi')
  const parts = props.text.split(regex)
  
  return parts.map((part): TextPart => {
    if (part.toLowerCase() === props.keyword.toLowerCase()) {
      return { text: part, highlight: true }
    }
    return { text: part, highlight: false }
  })
})

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
</script>

<template>
  <span>
    <template v-for="part in highlightedText" :key="part.text + part.highlight">
      <span v-if="part.highlight" :class="highlightClass">{{ part.text }}</span>
      <span v-else>{{ part.text }}</span>
    </template>
  </span>
</template>

<style scoped>
.highlight-text {
  background-color: #fef3cd;
  color: #856404;
  padding: 0 2px;
  border-radius: 2px;
  font-weight: 600;
}
</style>
