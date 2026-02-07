<template>
  <nav class="bg-slate-900 border-b border-slate-700 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo/Brand -->
        <div class="flex items-center space-x-2">
          <span class="text-2xl">⚡</span>
          <span class="text-xl font-bold text-white">Energy Dashboard</span>
        </div>

        <!-- Navigation Links -->
        <div class="hidden md:flex items-center space-x-8">
          <NuxtLink
            to="/"
            :class="[
              'px-3 py-2 rounded-md text-sm font-medium transition-colors',
              isActive('/') 
                ? 'text-energy-400 bg-slate-800 border-b-2 border-energy-400'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            📊 Dashboard
          </NuxtLink>

          <NuxtLink
            to="/settings"
            :class="[
              'px-3 py-2 rounded-md text-sm font-medium transition-colors',
              isActive('/settings')
                ? 'text-energy-400 bg-slate-800 border-b-2 border-energy-400'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            ⚙️ Settings
          </NuxtLink>

          <NuxtLink
            to="/control"
            :class="[
              'px-3 py-2 rounded-md text-sm font-medium transition-colors',
              isActive('/control')
                ? 'text-energy-400 bg-slate-800 border-b-2 border-energy-400'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            🎮 Control
          </NuxtLink>

          <NuxtLink
            to="/analytics"
            :class="[
              'px-3 py-2 rounded-md text-sm font-medium transition-colors',
              isActive('/analytics')
                ? 'text-energy-400 bg-slate-800 border-b-2 border-energy-400'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            ]"
          >
            📈 Analytics
          </NuxtLink>
        </div>

        <!-- Status Indicator -->
        <div class="flex items-center space-x-3">
          <div class="hidden sm:flex items-center space-x-2">
            <span class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
            <span class="text-sm text-slate-300">
              {{ currentTime }}
            </span>
          </div>
          <span class="text-xs font-semibold text-energy-400 bg-slate-800 px-3 py-1 rounded-full">
            TRADING HOURS
          </span>
        </div>

        <!-- Mobile Menu Button -->
        <button
          @click="mobileMenuOpen = !mobileMenuOpen"
          class="md:hidden text-slate-300 hover:text-white transition"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      <!-- Mobile Menu -->
      <div v-if="mobileMenuOpen" class="md:hidden border-t border-slate-700 py-3 space-y-2">
        <NuxtLink
          to="/"
          class="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800"
          @click="mobileMenuOpen = false"
        >
          📊 Dashboard
        </NuxtLink>
        <NuxtLink
          to="/settings"
          class="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800"
          @click="mobileMenuOpen = false"
        >
          ⚙️ Settings
        </NuxtLink>
        <NuxtLink
          to="/control"
          class="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800"
          @click="mobileMenuOpen = false"
        >
          🎮 Control
        </NuxtLink>
        <NuxtLink
          to="/analytics"
          class="block px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:text-white hover:bg-slate-800"
          @click="mobileMenuOpen = false"
        >
          📈 Analytics
        </NuxtLink>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const mobileMenuOpen = ref(false)
const currentTime = ref('00:00')

const isActive = (path: string) => {
  return route.path === path || (path === '/' && route.path === '/')
}

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

onMounted(() => {
  updateTime()
  const interval = setInterval(updateTime, 1000)
  onUnmounted(() => clearInterval(interval))
})
</script>

<style scoped>
nav {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
