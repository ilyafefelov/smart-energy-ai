<template>
  <nav class="sticky top-0 z-50 bg-slate-950 border-b border-slate-800">
    <div class="max-w-full">
      <!-- Desktop Navigation -->
      <div class="hidden md:flex items-center justify-between h-16 px-8">
        <div class="flex items-center gap-1">
          <NuxtLink to="/" class="flex items-center gap-2 text-energy-400 font-bold text-xl hover:text-energy-300">
            ⚡ Smart Energy AI
          </NuxtLink>
        </div>

        <div class="flex items-center gap-1">
          <NuxtLink 
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            :class="[
              'px-4 py-2 rounded-lg font-semibold text-sm transition',
              isActive(link.path)
                ? 'bg-energy-400 text-slate-950'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            ]"
          >
            {{ link.icon }} {{ link.label }}
          </NuxtLink>
        </div>

        <div class="flex items-center gap-2">
          <button 
            @click="toggleTheme"
            class="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Toggle theme"
          >
            🌙
          </button>
        </div>
      </div>

      <!-- Mobile Navigation -->
      <div class="md:hidden flex items-center justify-between h-16 px-4">
        <NuxtLink to="/" class="flex items-center gap-2 text-energy-400 font-bold">
          ⚡ Energy
        </NuxtLink>

        <button 
          @click="mobileMenuOpen = !mobileMenuOpen"
          class="p-2 rounded-lg hover:bg-slate-800"
        >
          ☰
        </button>
      </div>

      <!-- Mobile Menu -->
      <div v-if="mobileMenuOpen" class="md:hidden border-t border-slate-800 bg-slate-900">
        <div class="px-4 py-2 space-y-1">
          <NuxtLink 
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            @click="mobileMenuOpen = false"
            :class="[
              'block px-4 py-2 rounded-lg font-semibold text-sm transition',
              isActive(link.path)
                ? 'bg-energy-400 text-slate-950'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            ]"
          >
            {{ link.icon }} {{ link.label }}
          </NuxtLink>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const mobileMenuOpen = ref(false)

const navLinks = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/analytics', label: 'Analytics', icon: '📈' },
  { path: '/settings', label: 'Settings', icon: '⚙️' }
]

const isActive = (path: string) => {
  return route.path === path
}

const toggleTheme = () => {
  // Theme toggle logic would go here
  console.log('Toggle theme')
}
</script>

<style scoped>
nav {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(15, 23, 42, 0.8) 100%);
}
</style>
