import { existsSync, readFileSync, statSync } from 'fs'
import { join, resolve } from 'path'
import type { H3Event } from 'h3'
import { createError, getHeader, getQuery } from 'h3'

type TenantRecord = {
  id: string
  name: string | null
}

export type TenantDescriptor = {
  id: string
  name: string | null
}

type TenantRegistryCache = {
  path: string
  mtimeMs: number
  tenants: TenantRecord[]
}

export type TenantSource = 'body' | 'query' | 'header' | 'default'

export type TenantContext = {
  id: string
  name: string | null
  validated: true
  source: TenantSource
  defaultTenantId: string
  availableTenantIds: string[]
}

let tenantCache: TenantRegistryCache | null = null

const TENANT_OVERRIDE_TOKEN_HEADERS = [
  'x-smart-energy-tenant-token',
  'x-tenant-override-token',
  'x-internal-tenant-token',
] as const

function normalizeTenantId(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toLowerCase()
  return normalized.length > 0 ? normalized : null
}

function normalizeFieldValue(value: string): string {
  const trimmed = value.trim()
  const singleQuoted = trimmed.startsWith("'") && trimmed.endsWith("'")
  const doubleQuoted = trimmed.startsWith('"') && trimmed.endsWith('"')
  if ((singleQuoted || doubleQuoted) && trimmed.length >= 2) {
    return trimmed.slice(1, -1).trim()
  }
  return trimmed
}

function resolveCustomersFilePath(): string {
  const cwd = process.cwd()
  const candidates = [
    join(cwd, 'customers.yaml'),
    resolve(cwd, '..', 'customers.yaml'),
  ]

  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate
    }
  }

  throw createError({
    statusCode: 500,
    statusMessage: 'customers.yaml was not found for tenant validation',
    data: {
      success: false,
      error: {
        code: 'TENANT_CONFIG_MISSING',
        message: 'customers.yaml was not found for tenant validation',
      },
      tenant: {
        id: null,
        validated: false,
      },
    },
  })
}

function parseCustomersYamlTenantRecords(yamlContent: string): TenantRecord[] {
  const lines = yamlContent.split(/\r?\n/)
  const tenants: TenantRecord[] = []
  let current: TenantRecord | null = null

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue

    const idMatch = rawLine.match(/^\s*-\s*id\s*:\s*(.+?)\s*$/)
    if (idMatch) {
      const idValue = idMatch[1]
      if (typeof idValue !== 'string') continue

      const id = normalizeTenantId(normalizeFieldValue(idValue))
      if (!id) continue
      current = { id, name: null }
      tenants.push(current)
      continue
    }

    if (!current) continue

    const nameMatch = rawLine.match(/^\s*name\s*:\s*(.+?)\s*$/)
    if (nameMatch) {
      const rawNameValue = nameMatch[1]
      if (typeof rawNameValue !== 'string') continue

      const nameValue = normalizeFieldValue(rawNameValue)
      current.name = nameValue || null
    }
  }

  return tenants
}

function loadTenantRegistry(): TenantRecord[] {
  const customersPath = resolveCustomersFilePath()
  const stats = statSync(customersPath)

  if (tenantCache && tenantCache.path === customersPath && tenantCache.mtimeMs === stats.mtimeMs) {
    return tenantCache.tenants
  }

  const content = readFileSync(customersPath, 'utf-8')
  const tenants = parseCustomersYamlTenantRecords(content)

  if (tenants.length === 0) {
    throw createError({
      statusCode: 500,
      statusMessage: 'No customer tenants were found in customers.yaml',
      data: {
        success: false,
        error: {
          code: 'TENANT_CONFIG_EMPTY',
          message: 'No customer tenants were found in customers.yaml',
        },
        tenant: {
          id: null,
          validated: false,
        },
      },
    })
  }

  tenantCache = {
    path: customersPath,
    mtimeMs: stats.mtimeMs,
    tenants,
  }

  return tenants
}

export function listConfiguredTenants(): TenantDescriptor[] {
  return loadTenantRegistry().map((tenant) => ({
    id: tenant.id,
    name: tenant.name,
  }))
}

export function getDefaultTenantId(): string {
  const tenants = loadTenantRegistry()
  return tenants[0]?.id || ''
}

function getTrustedTenantOverrideToken(): string | null {
  const configuredToken = process.env.SMART_ENERGY_TENANT_OVERRIDE_TOKEN
    ?? process.env.TENANT_OVERRIDE_TOKEN
    ?? null

  if (typeof configuredToken !== 'string') {
    return null
  }

  const normalized = configuredToken.trim()
  return normalized || null
}

export function hasTrustedTenantOverrideAccess(event: H3Event): boolean {
  const configuredToken = getTrustedTenantOverrideToken()
  if (!configuredToken) {
    return false
  }

  return TENANT_OVERRIDE_TOKEN_HEADERS.some((headerName) => getHeader(event, headerName) === configuredToken)
}

function firstQueryStringValue(queryValue: unknown): string | null {
  if (typeof queryValue === 'string') return queryValue
  if (Array.isArray(queryValue)) {
    const firstString = queryValue.find((item) => typeof item === 'string')
    return typeof firstString === 'string' ? firstString : null
  }
  return null
}

function extractTenantCandidate(event: H3Event, body?: Record<string, any> | null): { source: Exclude<TenantSource, 'default'> | null; value: string | null } {
  const bodyCandidate = normalizeTenantId(
    body?.tenantId ?? body?.tenant_id ?? body?.clientId ?? body?.client_id ?? null,
  )
  if (bodyCandidate) {
    return { source: 'body', value: bodyCandidate }
  }

  const query = getQuery(event)
  const queryCandidate = normalizeTenantId(
    firstQueryStringValue(query.tenantId)
      ?? firstQueryStringValue(query.tenant_id)
      ?? firstQueryStringValue(query.clientId)
      ?? firstQueryStringValue(query.client_id),
  )
  if (queryCandidate) {
    return { source: 'query', value: queryCandidate }
  }

  const headerCandidate = normalizeTenantId(
    getHeader(event, 'x-tenant-id')
      ?? getHeader(event, 'x-client-id')
      ?? getHeader(event, 'tenant-id')
      ?? getHeader(event, 'client-id')
      ?? null,
  )
  if (headerCandidate) {
    return { source: 'header', value: headerCandidate }
  }

  return { source: null, value: null }
}

export function buildTenantErrorResponse(tenantId: string | null, message: string, availableTenantIds: string[]) {
  return {
    success: false,
    error: {
      code: 'INVALID_TENANT',
      message,
    },
    tenant: {
      id: tenantId,
      validated: false,
    },
    available_tenants: availableTenantIds,
  }
}

export function buildTenantAuthorizationErrorResponse(tenantId: string, defaultTenantId: string) {
  return {
    success: false,
    error: {
      code: 'TENANT_AUTH_REQUIRED',
      message: `Tenant '${tenantId}' requires trusted server-side authorization. Public requests may only access the default tenant '${defaultTenantId}'.`,
    },
    tenant: {
      id: tenantId,
      validated: false,
    },
    default_tenant_id: defaultTenantId,
  }
}

export function getTenantResponseMetadata(tenant: TenantContext) {
  return {
    id: tenant.id,
    name: tenant.name,
    validated: tenant.validated,
    source: tenant.source,
  }
}

export function isRecordVisibleForTenant(recordTenantId: unknown, tenant: TenantContext): boolean {
  const normalizedRecordTenant = normalizeTenantId(recordTenantId)
  if (normalizedRecordTenant) {
    return normalizedRecordTenant === tenant.id
  }

  // Legacy records without tenant marker are treated as default-tenant records only.
  return tenant.id === tenant.defaultTenantId
}

export async function resolveTenantContext(
  event: H3Event,
  options?: {
    body?: Record<string, any> | null
    requireTrustedOverride?: boolean
  },
): Promise<TenantContext> {
  const tenants = loadTenantRegistry()
  const availableTenantIds = tenants.map((tenant) => tenant.id)
  const defaultTenant = tenants[0]
  if (!defaultTenant) {
    throw createError({
      statusCode: 500,
      statusMessage: 'No customer tenants were found in customers.yaml',
    })
  }

  const { source, value } = extractTenantCandidate(event, options?.body || null)
  const resolvedTenantId = value || defaultTenant.id
  const resolvedSource: TenantSource = source || 'default'

  const matchedTenant = tenants.find((tenant) => tenant.id === resolvedTenantId)
  if (!matchedTenant) {
    throw createError({
      statusCode: 400,
      statusMessage: `Unknown tenant_id '${resolvedTenantId}'`,
      data: buildTenantErrorResponse(
        resolvedTenantId,
        `Unknown tenant_id '${resolvedTenantId}'. Provide one of the configured tenant IDs.`,
        availableTenantIds,
      ),
    })
  }

  if (options?.requireTrustedOverride && matchedTenant.id !== defaultTenant.id && !hasTrustedTenantOverrideAccess(event)) {
    throw createError({
      statusCode: 403,
      statusMessage: `Tenant '${matchedTenant.id}' requires trusted authorization`,
      data: buildTenantAuthorizationErrorResponse(matchedTenant.id, defaultTenant.id),
    })
  }

  return {
    id: matchedTenant.id,
    name: matchedTenant.name,
    validated: true,
    source: resolvedSource,
    defaultTenantId: defaultTenant.id,
    availableTenantIds,
  }
}
