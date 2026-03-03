export default defineNuxtConfig({
  devtools: { enabled: true },
  
  // Source directory configuration (Nuxt 4)
  srcDir: 'app',
  
  dir: {
    pages: 'pages'
  },

  modules: [
    '@nuxtjs/tailwindcss'
  ],

  pinia: {
    storesDirs: ['./app/stores/**']
  },

  // Dev server defaults to 3600 to avoid collisions with Dagster on 3000.
  devServer: {
    port: 3600,
    host: '0.0.0.0'
  },
  
  // Nitro runtime defaults also use 3600 for consistency.
  nitro: {
    prerender: {
      crawlLinks: false,
      routes: [],
    },
    port: 3600,
    host: '0.0.0.0'
  },

  runtimeConfig: {
    apiBase: process.env.API_BASE || 'http://localhost:8000',
    public: {
      siteName: 'Smart Energy Dashboard',
      siteDescription: 'AI-powered battery optimization for Ukraine energy market',
    }
  },

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

  compatibilityDate: '2024-04-01'
})
