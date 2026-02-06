export default defineNuxtConfig({
  devtools: { enabled: true },
  
  // UI Configuration - Simplified
  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
  ],

  // Build config
  nitro: {
    prerender: {
      crawlLinks: false,
      routes: [],
    }
  },

  // Runtime config
  runtimeConfig: {
    // Server-side env variables
    apiBase: process.env.API_BASE || 'http://localhost:8000',
    
    public: {
      // Client-side env variables
      siteName: 'Smart Energy Dashboard',
      siteDescription: 'AI-powered battery optimization for Ukraine energy market',
    }
  },

  // App config
  app: {
    head: {
      title: 'Smart Energy Dashboard',
      meta: [
        { name: 'description', content: 'Premium energy management dashboard' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }
      ]
    }
  },

  // Compatibility config
  compatibilityDate: '2024-01-01'
})
