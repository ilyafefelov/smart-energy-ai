import {
  getDefaultTenantId,
  hasTrustedTenantOverrideAccess,
  listConfiguredTenants,
} from '../utils/tenant-context'

export default defineEventHandler(async (event) => {
  try {
    const defaultTenantId = getDefaultTenantId()
    const configuredTenants = listConfiguredTenants()
    const trustedOverride = hasTrustedTenantOverrideAccess(event)
    const tenants = trustedOverride
      ? configuredTenants
      : configuredTenants.filter((tenant) => tenant.id === defaultTenantId)

    return {
      success: true,
      tenants,
      default_tenant_id: defaultTenantId,
      tenant_override_requires_auth: true,
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
