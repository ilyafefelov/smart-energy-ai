<template>
  <div class="min-h-screen bg-slate-950 text-white">
    <!-- Navigation -->
    <div class="border-b border-slate-800">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <div class="flex justify-between items-center">
          <div class="flex items-center space-x-2">
            <div class="text-3xl">⚡</div>
            <div>
              <h1 class="text-2xl font-bold text-energy-400">Smart Energy</h1>
              <p class="text-xs text-slate-400">AI-Powered Optimization</p>
            </div>
          </div>
          <nav class="flex space-x-8">
            <NuxtLink to="/" class="hover:text-energy-400 transition">Dashboard</NuxtLink>
            <NuxtLink to="/analytics" class="hover:text-energy-400 transition">Analytics</NuxtLink>
            <NuxtLink to="/control" class="hover:text-energy-400 transition">Control</NuxtLink>
            <NuxtLink to="/settings" class="hover:text-energy-400 transition">Settings</NuxtLink>
          </nav>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-8">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800 mt-16 py-8 text-center text-slate-400 text-sm">
      <p>Smart Energy AI • Feb 2026 • Ukraine Energy Market</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
// Global layout for all pages
</script>
