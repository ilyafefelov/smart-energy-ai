<template>
  <div>
    <!-- Top Navigation Menu -->
    <nav class="sticky top-0 z-50 bg-slate-900 border-b border-slate-800">
      <div class="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
        <!-- Logo / Brand -->
        <NuxtLink to="/" class="flex items-center gap-2 hover:text-energy-400 transition">
          <span class="text-2xl">⚡</span>
          <span class="text-xl font-bold text-white">Energy AI</span>
        </NuxtLink>

        <!-- Navigation Links -->
        <div class="hidden md:flex items-center gap-1">
          <NuxtLink to="/" 
                    class="px-4 py-2 rounded-lg hover:bg-slate-800 transition text-slate-300 hover:text-white"
                    :class="{ 'bg-slate-800 text-energy-400': $route.path === '/' }">
            📊 Dashboard
          </NuxtLink>
          <NuxtLink to="/analytics" 
                    class="px-4 py-2 rounded-lg hover:bg-slate-800 transition text-slate-300 hover:text-white"
                    :class="{ 'bg-slate-800 text-energy-400': $route.path === '/analytics' }">
            📈 Analytics
          </NuxtLink>
          <NuxtLink to="/control" 
                    class="px-4 py-2 rounded-lg hover:bg-slate-800 transition text-slate-300 hover:text-white"
                    :class="{ 'bg-slate-800 text-energy-400': $route.path === '/control' }">
            🔋 Control
          </NuxtLink>
          <NuxtLink to="/settings" 
                    class="px-4 py-2 rounded-lg hover:bg-slate-800 transition text-slate-300 hover:text-white"
                    :class="{ 'bg-slate-800 text-energy-400': $route.path === '/settings' }">
            ⚙️ Settings
          </NuxtLink>
        </div>

        <!-- Right side: Status & User Menu -->
        <div class="flex items-center gap-4">
          <!-- Model Status Badge -->
          <div class="hidden sm:flex items-center gap-2 px-3 py-1 bg-green-900 bg-opacity-30 border border-green-700 rounded-full">
            <span class="inline-block w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
            <span class="text-xs text-green-400 font-semibold">Model Ready</span>
          </div>

          <!-- Mobile menu button -->
          <button @click="mobileMenuOpen = !mobileMenuOpen" class="md:hidden text-white text-2xl">
            {{ mobileMenuOpen ? '✕' : '☰' }}
          </button>
        </div>
      </div>

      <!-- Mobile Menu -->
      <div v-if="mobileMenuOpen" class="md:hidden bg-slate-800 border-t border-slate-700 p-4 space-y-2">
        <NuxtLink to="/" class="block px-4 py-2 rounded-lg hover:bg-slate-700 text-slate-300 hover:text-white">
          📊 Dashboard
        </NuxtLink>
        <NuxtLink to="/analytics" class="block px-4 py-2 rounded-lg hover:bg-slate-700 text-slate-300 hover:text-white">
          📈 Analytics
        </NuxtLink>
        <NuxtLink to="/control" class="block px-4 py-2 rounded-lg hover:bg-slate-700 text-slate-300 hover:text-white">
          🔋 Control
        </NuxtLink>
        <NuxtLink to="/settings" class="block px-4 py-2 rounded-lg hover:bg-slate-700 text-slate-300 hover:text-white">
          ⚙️ Settings
        </NuxtLink>
      </div>
    </nav>

    <!-- Page Content -->
    <slot />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const mobileMenuOpen = ref(false)
</script>

<style scoped>
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
