import fs from 'fs'
import path from 'path'

export type BillingFeature =
  | 'optimization_control'
  | 'scheduled_control'
  | 'model_retraining'

export type BillingUsageUnit = 'command' | 'job'

export type BillingUsageEvent = {
  event_id: string
  tenant_id: string
  feature: BillingFeature
  quantity: number
  unit: BillingUsageUnit
  occurred_at: string
  metadata: Record<string, any>
  created_at: string
}

export type BillingLineItem = {
  feature: BillingFeature
  unit: BillingUsageUnit
  quantity: number
  unit_price_uah: number
  total_uah: number
  billable: boolean
  reason: string | null
}

export type BillingPlan = {
  id: string
  name: string
  base_monthly_fee_uah: number
  entitlements: BillingFeature[]
  rates_uah: Partial<Record<BillingFeature, number>>
}

export type BillingDraftInvoice = {
  provider_id: string
  tenant_id: string
  period: {
    from: string
    to: string
  }
  currency: 'UAH'
  plan: {
    id: string
    name: string
    entitlements: BillingFeature[]
  }
  summary: {
    event_count: number
    billable_event_count: number
    base_fee_uah: number
    usage_total_uah: number
    subtotal_uah: number
  }
  line_items: BillingLineItem[]
  events: BillingUsageEvent[]
  generated_at: string
}

export type RecordBillingUsageInput = {
  tenantId: string
  feature: BillingFeature
  quantity?: number
  unit?: BillingUsageUnit
  occurredAt?: string
  metadata?: Record<string, any>
}

export type BuildDraftInvoiceInput = {
  tenantId: string
  from: string
  to: string
  includeEvents?: boolean
}

export interface BillingProvider {
  readonly providerId: string
  buildDraftInvoice(input: BuildDraftInvoiceInput): BillingDraftInvoice
}

const PLAN_CATALOG: Record<string, BillingPlan> = {
  starter: {
    id: 'starter',
    name: 'Starter',
    base_monthly_fee_uah: 299,
    entitlements: ['optimization_control', 'scheduled_control'],
    rates_uah: {
      optimization_control: 1.2,
      scheduled_control: 0.4,
    },
  },
  growth: {
    id: 'growth',
    name: 'Growth',
    base_monthly_fee_uah: 799,
    entitlements: ['optimization_control', 'scheduled_control', 'model_retraining'],
    rates_uah: {
      optimization_control: 1.0,
      scheduled_control: 0.3,
      model_retraining: 25,
    },
  },
  enterprise: {
    id: 'enterprise',
    name: 'Enterprise',
    base_monthly_fee_uah: 1999,
    entitlements: ['optimization_control', 'scheduled_control', 'model_retraining'],
    rates_uah: {
      optimization_control: 0.8,
      scheduled_control: 0.2,
      model_retraining: 20,
    },
  },
}

const STATIC_PLAN_OVERRIDES: Record<string, keyof typeof PLAN_CATALOG> = {
  client_001_kyiv_mall: 'growth',
  client_002_lviv_office: 'starter',
  client_003_dnipro_factory: 'enterprise',
  client_004_kharkiv_hospital: 'enterprise',
  client_005_odesa_hotel: 'growth',
}

let eventCounter = 0
let activeProvider: BillingProvider | null = null

function normalizeTenantSegment(tenantId: string): string {
  return tenantId.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_')
}

function resolveBillingEventsFilePath(tenantId: string): string {
  const normalizedTenant = normalizeTenantSegment(tenantId)
  return path.join(process.cwd(), 'data', 'tenants', normalizedTenant, 'billing', 'usage-events.jsonl')
}

function ensureParentDir(filePath: string): void {
  const dirPath = path.dirname(filePath)
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true })
  }
}

function toIsoOrNow(value?: string): string {
  if (typeof value === 'string') {
    const parsed = new Date(value)
    if (Number.isFinite(parsed.getTime())) {
      return parsed.toISOString()
    }
  }
  return new Date().toISOString()
}

function sanitizeQuantity(value: unknown): number {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return 1
  }
  return Number(numeric.toFixed(6))
}

function resolvePlanForTenant(tenantId: string): BillingPlan {
  const envMapRaw = process.env.TENANT_BILLING_PLAN_MAP
  if (envMapRaw) {
    try {
      const envMap = JSON.parse(envMapRaw) as Record<string, string>
      const envPlanId = envMap?.[tenantId]
      if (envPlanId && PLAN_CATALOG[envPlanId]) {
        return PLAN_CATALOG[envPlanId]
      }
    } catch {
      // Ignore malformed overrides and continue with defaults.
    }
  }

  const overridePlanId = STATIC_PLAN_OVERRIDES[tenantId]
  if (overridePlanId && PLAN_CATALOG[overridePlanId]) {
    return PLAN_CATALOG[overridePlanId]
  }

  const starterPlan = PLAN_CATALOG.starter
  if (starterPlan) {
    return starterPlan
  }

  throw new Error('Starter billing plan is not configured')
}

function readTenantUsageEvents(tenantId: string): BillingUsageEvent[] {
  const filePath = resolveBillingEventsFilePath(tenantId)
  if (!fs.existsSync(filePath)) {
    return []
  }

  try {
    const raw = fs.readFileSync(filePath, 'utf8')
    if (!raw.trim()) {
      return []
    }

    return raw
      .split(/\r?\n/)
      .filter((line) => line.trim().length > 0)
      .map((line) => JSON.parse(line) as BillingUsageEvent)
      .filter((event) => event.tenant_id === tenantId)
  } catch (error) {
    console.warn('[billing] Failed to read usage events:', error)
    return []
  }
}

function filterEventsByPeriod(events: BillingUsageEvent[], from: string, to: string): BillingUsageEvent[] {
  const fromTs = new Date(from).getTime()
  const toTs = new Date(to).getTime()

  if (!Number.isFinite(fromTs) || !Number.isFinite(toTs)) {
    return events
  }

  return events.filter((event) => {
    const occurredTs = new Date(event.occurred_at).getTime()
    if (!Number.isFinite(occurredTs)) {
      return false
    }
    return occurredTs >= fromTs && occurredTs <= toTs
  })
}

class LocalRateCardBillingProvider implements BillingProvider {
  readonly providerId = 'local-rate-card-v1'

  buildDraftInvoice(input: BuildDraftInvoiceInput): BillingDraftInvoice {
    const tenantPlan = resolvePlanForTenant(input.tenantId)
    const allEvents = readTenantUsageEvents(input.tenantId)
    const scopedEvents = filterEventsByPeriod(allEvents, input.from, input.to)

    const lineItems: BillingLineItem[] = scopedEvents.map((event) => {
      const entitled = tenantPlan.entitlements.includes(event.feature)
      const unitPrice = entitled ? Number(tenantPlan.rates_uah[event.feature] || 0) : 0
      const total = Number((event.quantity * unitPrice).toFixed(4))

      return {
        feature: event.feature,
        unit: event.unit,
        quantity: event.quantity,
        unit_price_uah: unitPrice,
        total_uah: total,
        billable: entitled && unitPrice > 0,
        reason: entitled ? null : 'feature_not_entitled',
      }
    })

    const billableItems = lineItems.filter((item) => item.billable)
    const usageTotal = Number(
      billableItems.reduce((sum, item) => sum + item.total_uah, 0).toFixed(4),
    )
    const subtotal = Number((tenantPlan.base_monthly_fee_uah + usageTotal).toFixed(4))

    return {
      provider_id: this.providerId,
      tenant_id: input.tenantId,
      period: {
        from: input.from,
        to: input.to,
      },
      currency: 'UAH',
      plan: {
        id: tenantPlan.id,
        name: tenantPlan.name,
        entitlements: [...tenantPlan.entitlements],
      },
      summary: {
        event_count: scopedEvents.length,
        billable_event_count: billableItems.length,
        base_fee_uah: tenantPlan.base_monthly_fee_uah,
        usage_total_uah: usageTotal,
        subtotal_uah: subtotal,
      },
      line_items: lineItems,
      events: input.includeEvents ? scopedEvents : [],
      generated_at: new Date().toISOString(),
    }
  }
}

function getProvider(): BillingProvider {
  if (!activeProvider) {
    activeProvider = new LocalRateCardBillingProvider()
  }
  return activeProvider
}

export function setBillingProviderForTesting(provider: BillingProvider | null): void {
  activeProvider = provider
}

export function recordBillingUsageEvent(input: RecordBillingUsageInput): BillingUsageEvent {
  const tenantId = normalizeTenantSegment(input.tenantId)
  const occurredAt = toIsoOrNow(input.occurredAt)
  const quantity = sanitizeQuantity(input.quantity)

  eventCounter += 1
  const eventId = `bill_evt_${Date.now()}_${eventCounter}`

  const eventRecord: BillingUsageEvent = {
    event_id: eventId,
    tenant_id: tenantId,
    feature: input.feature,
    quantity,
    unit: input.unit || 'command',
    occurred_at: occurredAt,
    metadata: input.metadata || {},
    created_at: new Date().toISOString(),
  }

  const filePath = resolveBillingEventsFilePath(tenantId)
  ensureParentDir(filePath)
  fs.appendFileSync(filePath, `${JSON.stringify(eventRecord)}\n`, 'utf8')

  return eventRecord
}

export function buildTenantDraftInvoice(input: BuildDraftInvoiceInput): BillingDraftInvoice {
  return getProvider().buildDraftInvoice(input)
}
