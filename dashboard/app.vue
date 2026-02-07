<template>
  <div class="bg-slate-950 min-h-screen text-white">
    <!-- Global Navigation -->
    <NavigationPageMenu />

    <!-- Main Content -->
    <main>
      <NuxtPage />
    </main>

    <!-- Global Error Toast (optional) -->
    <div v-if="globalError" class="fixed bottom-4 right-4 bg-red-900 border border-red-700 rounded-lg p-4 text-red-200 max-w-sm">
      {{ globalError }}
      <button @click="globalError = ''" class="ml-2 text-red-400 hover:text-red-300">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'

const globalError = ref('')

const settingsStore = useSettingsStore()

// Initialize Pinia stores on app load
onMounted(async () => {
  try {
    // Load settings on app startup
    await settingsStore.loadSettings()
  } catch (e) {
    console.error('Failed to initialize app:', e)
    globalError.value = 'Failed to load application data'
  }
})
</script>

<style>
@import 'tailwindcss/base';
@import 'tailwindcss/components';
@import 'tailwindcss/utilities';

body {
  @apply bg-slate-950 text-white;
}

/* Energy color scheme */
:root {
  --color-energy-400: #22d3ee;
  --color-energy-500: #06b6d4;
}

.text-energy-400 {
  color: var(--color-energy-400);
}

.bg-energy-400 {
  background-color: var(--color-energy-400);
}

.border-energy-400 {
  border-color: var(--color-energy-400);
}

.hover\:text-energy-400:hover {
  color: var(--color-energy-400);
}
</style>
