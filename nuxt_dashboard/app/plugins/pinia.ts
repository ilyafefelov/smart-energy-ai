import { createPinia } from 'pinia'

export default defineNuxtPlugin((nuxtApp) => {
  const pinia = createPinia()
  // Attach Pinia to the Vue application instance so it's available during SSR and CSR
  nuxtApp.vueApp.use(pinia)
})
