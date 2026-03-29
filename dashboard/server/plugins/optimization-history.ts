import { initializeOptimizationHistory } from '../utils/optimization-history'

export default defineNitroPlugin(async () => {
  try {
    await initializeOptimizationHistory()
  } catch (error) {
    console.warn('[optimization-history] Startup initialization failed:', error)
  }
})