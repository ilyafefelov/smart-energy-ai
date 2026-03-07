export default defineEventHandler(() => {
  return {
    success: true,
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'dashboard',
  }
})