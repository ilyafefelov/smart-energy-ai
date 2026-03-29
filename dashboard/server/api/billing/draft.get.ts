import { createError, defineEventHandler, getQuery } from 'h3'
import { buildTenantDraftInvoice } from '../../utils/billing'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

function resolvePeriodStart(rawFrom: unknown): string {
  if (typeof rawFrom === 'string') {
    const parsed = new Date(rawFrom)
    if (Number.isFinite(parsed.getTime())) {
      return parsed.toISOString()
    }
  }

  const now = new Date()
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1, 0, 0, 0, 0)).toISOString()
}

function resolvePeriodEnd(rawTo: unknown): string {
  if (typeof rawTo === 'string') {
    const parsed = new Date(rawTo)
    if (Number.isFinite(parsed.getTime())) {
      return parsed.toISOString()
    }
  }

  return new Date().toISOString()
}

function asBoolean(value: unknown): boolean {
  if (typeof value === 'boolean') {
    return value
  }
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    return normalized === '1' || normalized === 'true' || normalized === 'yes'
  }
  return false
}

export default defineEventHandler(async (event: any) => {
  try {
    const tenant = await resolveTenantContext(event, { requireTrustedOverride: true })
    const query = getQuery(event)

    const from = resolvePeriodStart(query.from)
    const to = resolvePeriodEnd(query.to)

    if (new Date(from) > new Date(to)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid period. `from` must be <= `to`.',
      })
    }

    const includeEvents = asBoolean(query.includeEvents)

    const invoice = buildTenantDraftInvoice({
      tenantId: tenant.id,
      from,
      to,
      includeEvents,
    })

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      draft_invoice: invoice,
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT' || errorData?.error?.code === 'TENANT_AUTH_REQUIRED') {
      return errorData
    }

    if (error?.statusCode) {
      throw error
    }

    throw createError({
      statusCode: 500,
      statusMessage: error?.message || 'Failed to build billing draft invoice',
    })
  }
})
