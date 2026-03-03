import { getDefaultTenantId, listConfiguredTenants } from '../utils/tenant-context'

export default defineEventHandler(async () => {
  try {
    const tenants = listConfiguredTenants()
    return {
      success: true,
      tenants,
      default_tenant_id: getDefaultTenantId(),
    }
  } catch (error: any) {
    return {
      success: false,
      error: error?.message || 'Failed to load tenant list',
      tenants: [],
      default_tenant_id: null,
    }
  }
})
