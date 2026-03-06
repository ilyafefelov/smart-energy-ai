<template>
  <div class="relative group inline-block">
    <slot />
    
    <!-- Tooltip - positioned top-right with better spacing -->
    <div class="absolute bottom-full left-0 hidden group-hover:block z-50 mb-2 pointer-events-none">
      <div class="bg-slate-900 text-white px-4 py-3 rounded-lg shadow-xl border border-slate-600 w-max max-w-sm whitespace-normal">
        <!-- Title -->
        <p class="font-semibold text-sm text-energy-400 mb-2">{{ title }}</p>
        
        <!-- Description -->
        <p class="text-xs text-slate-300 mb-3 leading-relaxed">{{ description }}</p>
        
        <!-- Formula -->
        <div v-if="formula" class="border-t border-slate-700 pt-2 mt-2">
          <p class="text-xs text-slate-400">
            <span class="font-semibold text-slate-300">Formula:</span>
          </p>
          <p class="text-xs text-slate-400 italic mt-1">{{ formula }}</p>
        </div>

        <!-- Arrow pointing down -->
        <div class="absolute left-4 top-full transform -translate-y-2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-slate-900"></div>
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
/* Ensure tooltip stays visible */
.group:hover > :last-child {
  display: block;
  pointer-events: auto;
}
</style>
