<template>
  <div class="relative group inline-block">
    <slot />
    
    <!-- Tooltip -->
    <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-50">
      <div class="bg-slate-800 text-white px-4 py-3 rounded-lg shadow-lg border border-slate-700 w-max max-w-xs">
        <p class="font-semibold text-sm mb-1">{{ title }}</p>
        <p class="text-xs text-slate-300 mb-2">{{ description }}</p>
        <p v-if="formula" class="text-xs text-slate-400 italic">
          <span class="font-semibold">Formula:</span> {{ formula }}
        </p>

        <!-- Arrow pointing down -->
        <div class="absolute top-full left-1/2 transform -translate-x-1/2 -translate-y-1 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-slate-800"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string
  description: string
  formula?: string
}

withDefaults(defineProps<Props>(), {
  formula: undefined
})
</script>

<style scoped>
.group:hover > :last-child {
  display: block;
}
</style>
