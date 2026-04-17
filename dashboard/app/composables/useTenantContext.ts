import { computed, watch } from 'vue'

type TenantOption = {
  id: string
  name: string | null
}

export type TenantRequestOptions = {
  query: {
    tenantId: string
  }
  headers: {
    'x-tenant-id': string
  }
}

const STORAGE_KEY = 'selected_tenant_id_v1'
let initialized = false
let loadPromise: Promise<void> | null = null

export function useTenantContext() {
  const tenants = useState<TenantOption[]>('tenant-options', () => [])
  const selectedTenantId = useState<string>('selected-tenant-id', () => '')
  const defaultTenantId = useState<string>('default-tenant-id', () => '')
  const isLoaded = useState<boolean>('tenant-context-loaded', () => false)

  const setTenant = (tenantId: string) => {
    const normalized = typeof tenantId === 'string' ? tenantId.trim().toLowerCase() : ''
    if (!normalized) return
    selectedTenantId.value = normalized
  }

  const loadTenants = async (force = false) => {
    if (!force && isLoaded.value && tenants.value.length > 0) {
      return
    }

    if (!force && loadPromise) {
      await loadPromise
      return
    }

    loadPromise = (async () => {
      const response = await $fetch<any>('/api/tenants').catch(() => null)
      if (!response?.success) {
        return
      }

      tenants.value = Array.isArray(response.tenants) ? response.tenants : []
      defaultTenantId.value = String(response.default_tenant_id || tenants.value[0]?.id || '')

      const validTenantIds = new Set(tenants.value.map((tenant) => tenant.id))
      if (!validTenantIds.has(selectedTenantId.value)) {
        selectedTenantId.value = defaultTenantId.value
      }

      isLoaded.value = true
    })()

    try {
      await loadPromise
    } finally {
      loadPromise = null
    }
  }

  if (!initialized) {
    initialized = true

    if (import.meta.client) {
      const savedTenantId = window.localStorage.getItem(STORAGE_KEY)
      if (savedTenantId && typeof savedTenantId === 'string') {
        selectedTenantId.value = savedTenantId.trim().toLowerCase()
      }
    }

    watch(
      selectedTenantId,
      (nextTenantId) => {
        if (!import.meta.client) return
        if (!nextTenantId) return
        window.localStorage.setItem(STORAGE_KEY, nextTenantId)
      },
      { immediate: true },
    )
  }

  const currentTenantId = computed(() => selectedTenantId.value || defaultTenantId.value || '')

  const currentTenant = computed(() => {
    return tenants.value.find((tenant) => tenant.id === currentTenantId.value) || null
  })

  const tenantRequest = computed<TenantRequestOptions | undefined>(() => {
    const tenantId = currentTenantId.value || defaultTenantId.value || ''
    if (!tenantId) {
      return undefined
    }

    return {
      query: { tenantId },
      headers: { 'x-tenant-id': tenantId },
    }
  })

  const getTenantRequest = (): TenantRequestOptions => {
    const request = tenantRequest.value
    if (!request) {
      throw new Error('Tenant request unavailable')
    }
    return request
  }

  return {
    tenants,
    selectedTenantId,
    defaultTenantId,
    currentTenantId,
    currentTenant,
    isLoaded,
    tenantRequest,
    getTenantRequest,
    loadTenants,
    setTenant,
  }
}
