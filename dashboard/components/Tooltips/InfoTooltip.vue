<template>
  <div class="relative group inline-block">
    <slot />
    
    <!-- Tooltip - positioned top-right -->
    <div class="absolute top-0 right-0 transform translate-x-full -translate-y-1/4 hidden group-hover:block z-50 ml-2">
      <div class="bg-slate-800 text-white px-4 py-3 rounded-lg shadow-lg border border-slate-700 w-max max-w-xs whitespace-normal">
        <p class="font-semibold text-sm mb-1">{{ title }}</p>
        <p class="text-xs text-slate-300 mb-2 max-w-xs">{{ description }}</p>
        <p v-if="formula" class="text-xs text-slate-400 italic">
          <span class="font-semibold">Formula:</span> {{ formula }}
        </p>

        <!-- Arrow pointing left -->
        <div class="absolute left-0 top-1/4 transform translate-x-full -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-t-transparent border-b-transparent border-r-slate-800"></div>
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
