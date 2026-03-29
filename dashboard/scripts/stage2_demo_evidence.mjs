import { assessDagsterScheduleRowPolicy } from '../server/utils/dagster-schedule-policy.ts'

const baseUrl = process.env.DASHBOARD_BASE_URL || 'http://127.0.0.1:3600'
const tenantId = process.env.STAGE2_TENANT_ID || 'client_001_kyiv_mall'

function buildUrl(path) {
  const url = new URL(path, baseUrl)
  if (!url.searchParams.has('tenantId')) {
    url.searchParams.set('tenantId', tenantId)
  }
  return url
}

async function requestJson(path, options = {}) {
  const response = await fetch(buildUrl(path), {
    method: options.method || 'GET',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Tenant-Id': tenantId,
      ...(options.headers || {}),
    },
    body: options.body == null ? undefined : JSON.stringify(options.body),
  })

  const text = await response.text()
  const payload = text ? JSON.parse(text) : null
  if (!response.ok) {
    throw new Error(`Request failed for ${path}: ${response.status} ${response.statusText} ${text}`)
  }
  return payload
}

function toNumber(value, fallback = null) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}

function findScheduleRow(schedule, hour) {
  return schedule.find((row) => Number(row?.hour) === Number(hour)) || null
}

function buildMarketPremiumConfig(currentConfig) {
  return {
    battery_capacity_kwh: toNumber(currentConfig?.battery_capacity_kwh, 100),
    battery_soc_min: toNumber(currentConfig?.battery_soc_min, 0.15),
    battery_efficiency: toNumber(currentConfig?.battery_efficiency, 0.95),
    connected_power_kw: 75,
    market_regime_override: 'market_premium',
    timezone: String(currentConfig?.timezone || 'Europe/Kiev'),
  }
}

function buildScenarioAssessment(hourOffset, socBeforeKwh, currentConfig, schedule, label) {
  const config = buildMarketPremiumConfig(currentConfig)
  const liveRow = findScheduleRow(schedule, hourOffset)
  const assessment = assessDagsterScheduleRowPolicy(
    {
      hour_offset: hourOffset,
      action: 'SELL',
      action_kw: 18,
      soc_before_kwh: socBeforeKwh,
    },
    {
      config,
      batteryCapacityKwh: config.battery_capacity_kwh,
      scheduleStartUtc: `${new Date().toISOString().slice(0, 10)}T00:00:00.000Z`,
    },
  )

  return {
    label,
    live_schedule_price_uah_kwh: liveRow ? toNumber(liveRow.price_uah_kwh) : null,
    hour: hourOffset,
    requested_action: assessment.requestedAction,
    adjusted_action: assessment.policyCompliance.adjusted_action,
    veto_applied: assessment.policyCompliance.veto_applied,
    rule_hits: assessment.policyCompliance.rule_hits,
    explanations: assessment.policyCompliance.explanations,
    battery_soc_percent: assessment.batterySocPercent,
    market_regime: assessment.policyCompliance.market_regime,
  }
}

async function saveConfig(partialConfig) {
  return requestJson('/api/config/save', {
    method: 'POST',
    body: partialConfig,
  })
}

const currentConfigPayload = await requestJson('/api/config/current')
const originalConfig = currentConfigPayload?.data || {}
const originalPowerKw = toNumber(originalConfig.connected_power_kw, 10)
const originalRegimeOverride = String(originalConfig.market_regime_override || 'auto')

let result

try {
  const recommendationPayload = await requestJson('/api/dagster/recommendation')
  const historyPayload = await requestJson('/api/history')
  const schedule = recommendationPayload?.schedule_24h?.schedule || []

  const silenceWindowScenario = buildScenarioAssessment(10, 80, originalConfig, schedule, 'silence_window_export_veto')
  const eveningDischargeScenario = buildScenarioAssessment(18, 80, originalConfig, schedule, 'evening_high_price_discharge')
  const lowSocScenario = buildScenarioAssessment(18, 12, originalConfig, schedule, 'low_soc_remit_block')

  await saveConfig({ connected_power_kw: 20, market_regime_override: 'auto' })
  const netBillingHistory = await requestJson('/api/history')

  await saveConfig({ connected_power_kw: 75, market_regime_override: 'auto' })
  const marketPremiumHistory = await requestJson('/api/history')

  result = {
    generated_at: new Date().toISOString(),
    tenant_id: tenantId,
    base_url: baseUrl,
    live_runtime: {
      recommendation: {
        action: recommendationPayload?.recommendation?.action || null,
        battery_soc_percent: toNumber(recommendationPayload?.current_state?.battery_soc_percent),
        current_price_uah_kwh: toNumber(recommendationPayload?.current_state?.price_uah_kwh),
        market_regime: recommendationPayload?.recommendation?.policy_compliance?.market_regime || null,
        rule_hits: recommendationPayload?.recommendation?.policy_compliance?.rule_hits || [],
        rationale: recommendationPayload?.recommendation?.rationale || null,
      },
      schedule_summary: {
        total_rows: schedule.length,
        sell_rows: schedule.filter((row) => row?.recommended_action === 'SELL').length,
        veto_rows: schedule.filter((row) => Boolean(row?.policy_compliance?.veto_applied)).length,
      },
      history: historyPayload?.stage2_financials || null,
    },
    scenarios: {
      silence_window_export_veto: {
        ...silenceWindowScenario,
        passed:
          silenceWindowScenario.veto_applied === true
          && silenceWindowScenario.adjusted_action === 'HOLD'
          && silenceWindowScenario.rule_hits.includes('window_of_silence_export_veto'),
        evidence_source: 'runtime_utility_with_live_schedule_price',
      },
      evening_high_price_discharge: {
        ...eveningDischargeScenario,
        passed:
          eveningDischargeScenario.veto_applied === false
          && eveningDischargeScenario.adjusted_action === 'SELL',
        evidence_source: 'runtime_utility_with_live_schedule_price',
      },
      low_soc_remit_block: {
        ...lowSocScenario,
        passed:
          lowSocScenario.veto_applied === true
          && lowSocScenario.adjusted_action === 'HOLD'
          && lowSocScenario.rule_hits.includes('remit_insufficient_deliverable_energy'),
        evidence_source: 'runtime_utility_with_live_schedule_price',
      },
      comparative_regime_analytics: {
        net_billing: netBillingHistory?.stage2_financials || null,
        market_premium: marketPremiumHistory?.stage2_financials || null,
        passed:
          netBillingHistory?.stage2_financials?.market_regime === 'net_billing'
          && marketPremiumHistory?.stage2_financials?.market_regime === 'market_premium',
        evidence_source: 'live_history_api',
      },
    },
  }
} finally {
  try {
    await saveConfig({
      connected_power_kw: originalPowerKw,
      market_regime_override: originalRegimeOverride,
    })
  } catch (error) {
    console.error('Failed to restore original Stage 2 config snapshot:', error)
  }
}

console.log(JSON.stringify(result, null, 2))