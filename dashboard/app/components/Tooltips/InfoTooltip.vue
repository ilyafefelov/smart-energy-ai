<template>
  <div class="group relative inline-block">
    <!-- Tooltip trigger slot -->
    <slot></slot>

    <!-- Tooltip content -->
    <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-gray-900 text-white text-xs rounded px-3 py-2 z-10 w-48 whitespace-normal border border-gray-700">
      <div class="font-semibold mb-1">{{ title }}</div>
      <div class="text-gray-300 mb-1">{{ description }}</div>
      <div v-if="formula" class="text-gray-500 text-xs italic">Formula: {{ formula }}</div>
      <!-- Tooltip arrow -->
      <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  },
  formula: {
    type: String,
    default: null
  }
})
</script>

<style scoped>
.group:hover > div {
  display: block;
}
</style>
