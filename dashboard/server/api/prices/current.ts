import { exec } from 'child_process'
import { resolve } from 'path'
import { promisify } from 'util'

type Trend = 'up' | 'down' | 'stable'

function resolveTariffWindow(hour: number): 'peak' | 'offpeak' | 'shoulder' | 'unknown' {
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    return 'unknown'
  }
  if (hour >= 8 && hour <= 20) {
    return 'peak'
  }
  if (hour === 7 || hour === 21) {
    return 'shoulder'
  }
  return 'offpeak'
}

let PRICE_CACHE: { ts: number; data: any } | null = null
const CACHE_TTL_MS = 5 * 60 * 1000
const OREE_DATA_VIEW_URL = 'https://www.oree.com.ua/index.php/pricectr/data_view'
const execAsync = promisify(exec)

function formatDateLabel(date: Date): string {
  const dd = String(date.getDate()).padStart(2, '0')
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const yyyy = String(date.getFullYear())
  return `${dd}.${mm}.${yyyy}`
}

function formatMonthLabel(date: Date): string {
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const yyyy = String(date.getFullYear())
  return `${mm}.${yyyy}`
}

function stripHtml(value: string): string {
  return value
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function parseDecimal(text: string): number | null {
  const normalized = text.replace(/\s/g, '').replace(',', '.')
  const number = Number(normalized)
  if (!Number.isFinite(number)) return null
  return number
}

function toKwhPriceFromUahMwh(value: number): number {
  return value / 1000
}

async function fetchOreeDayPrices(targetDate: Date): Promise<Map<number, number>> {
  try {
    const params = new URLSearchParams({
      date: formatMonthLabel(targetDate),
      market: 'DAM',
      zone: 'IPS',
    })

    const response = await fetch(OREE_DATA_VIEW_URL, {
      method: 'POST',
      body: params,
      headers: {
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'x-requested-with': 'XMLHttpRequest',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'origin': 'https://www.oree.com.ua',
        'referer': 'https://www.oree.com.ua/index.php/pricectr?lang=english',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
      },
    })

    if (!response.ok) {
      throw new Error(`OREE data_view request failed (${response.status})`)
    }

    const payload = (await response.json()) as { content?: string }
    const html = payload?.content || ''
    if (!html) {
      return new Map()
    }

    const targetLabel = formatDateLabel(targetDate)
    const rows = html.match(/<tr[\s\S]*?<\/tr>/gi) || []

    for (const row of rows) {
      const cells = Array.from(row.matchAll(/<(td|th)[^>]*>([\s\S]*?)<\/(td|th)>/gi)).map((m) => stripHtml(m[2] || ''))
      if (cells.length < 25) continue
      if (cells[0] !== targetLabel) continue

      const result = new Map<number, number>()
      for (let hour = 0; hour < 24; hour += 1) {
        const value = parseDecimal(cells[hour + 1] || '')
        if (value == null || value <= 0) continue
        result.set(hour, toKwhPriceFromUahMwh(value))
      }
      return result
    }

    return new Map()
  } catch (error) {
    console.warn('[prices/current] JS parser failed, trying Python fallback:', error)
    return fetchOreeDayPricesViaPython(targetDate)
  }
}

async function fetchOreeDayPricesViaPython(targetDate: Date): Promise<Map<number, number>> {
  const projectRoot = resolve(process.cwd(), '..')
  const scriptPath = resolve(projectRoot, 'scripts/fetch_oree_data_view.py')
  const dateLabel = formatDateLabel(targetDate)

  const command = `python "${scriptPath}" --date "${dateLabel}"`
  const { stdout } = await execAsync(command, {
    cwd: projectRoot,
    timeout: 45000,
    maxBuffer: 5 * 1024 * 1024,
  })

  const payload = JSON.parse(stdout.trim() || '{}') as { success?: boolean; hours?: Record<string, number> }
  const hours = payload?.hours || {}
  const result = new Map<number, number>()

  for (const [hourStr, price] of Object.entries(hours)) {
    const hour = Number(hourStr)
    if (!Number.isInteger(hour) || hour < 0 || hour > 23) continue
    if (!Number.isFinite(price) || price <= 0) continue
    result.set(hour, Number(price))
  }

  return result
}

function buildFallbackPrices(now: Date) {
  const hour = now.getHours()
  const basePrice = 9.85

  const forecast = Array.from({ length: 24 }, (_, i) => {
    const h = (hour + i) % 24
    const multiplier = h >= 8 && h <= 20 ? 1.35 : 0.75
    const variation = Math.sin((h % 12) * 0.5) * 2
    const price = Math.max(5, Math.min(18, basePrice * multiplier + variation))
    return {
      hour: h,
      timestamp: new Date(now.getTime() + i * 3600000).toISOString(),
      price: Number(price.toFixed(2)),
      confidence: 0.75,
      trend: (variation > 0.5 ? 'up' : variation < -0.5 ? 'down' : 'stable') as Trend,
    }
  })

  return {
    forecast,
    source: 'fallback',
  }
}

function summarizePrices(now: Date, series: Array<{ hour: number; timestamp: string; price: number; confidence: number; trend: Trend }>, source: string) {
  const minPrice = Math.min(...series.map((p) => p.price))
  const maxPrice = Math.max(...series.map((p) => p.price))
  const avgPrice = series.reduce((sum, p) => sum + p.price, 0) / series.length
  const weightedSum = series.reduce((sum, p) => sum + p.price * p.confidence, 0)
  const confidenceSum = series.reduce((sum, p) => sum + p.confidence, 0)
  const weightedPrice = confidenceSum > 0 ? weightedSum / confidenceSum : avgPrice
  const currentPrice = series[0]?.price ?? avgPrice

  const peakRows = series.filter((p) => p.hour >= 8 && p.hour <= 20)
  const offPeakRows = series.filter((p) => p.hour < 8 || p.hour > 20)

  const peakPrice = peakRows.length
    ? peakRows.reduce((sum, p) => sum + p.price, 0) / peakRows.length
    : avgPrice
  const offPeakPrice = offPeakRows.length
    ? offPeakRows.reduce((sum, p) => sum + p.price, 0) / offPeakRows.length
    : avgPrice

  const currentIntervalStart = series[0]?.timestamp ? new Date(series[0].timestamp) : now
  const currentIntervalEnd = new Date(currentIntervalStart.getTime() + 3600000)
  const currentWindow = resolveTariffWindow(currentIntervalStart.getHours())

  return {
    success: true,
    prices: {
      current: {
        price: Number(currentPrice.toFixed(2)),
        timestamp: now.toISOString(),
        trend: currentPrice > avgPrice * 1.05 ? 'up' : currentPrice < avgPrice * 0.95 ? 'down' : 'stable',
        interval_start: currentIntervalStart.toISOString(),
        interval_end: currentIntervalEnd.toISOString(),
        tariff_window: currentWindow,
      },
      today: {
        min: Number(minPrice.toFixed(2)),
        max: Number(maxPrice.toFixed(2)),
        avg: Number(avgPrice.toFixed(2)),
        current: Number(currentPrice.toFixed(2)),
        weighted: Number(weightedPrice.toFixed(2)),
      },
      forecast: {
        next24h: series,
        peak: Number(peakPrice.toFixed(2)),
        offPeak: Number(offPeakPrice.toFixed(2)),
      },
      tariffs: {
        peak: Number(peakPrice.toFixed(2)),
        offPeak: Number(offPeakPrice.toFixed(2)),
      },
      source,
    },
  }
}

export default defineEventHandler(async () => {
  try {
    const nowTs = Date.now()
    if (PRICE_CACHE && nowTs - PRICE_CACHE.ts < CACHE_TTL_MS) {
      return PRICE_CACHE.data
    }

    const now = new Date()
    const tomorrow = new Date(now)
    tomorrow.setDate(tomorrow.getDate() + 1)

    let todayMap = new Map<number, number>()
    let tomorrowMap = new Map<number, number>()
    let source = 'OREE_DATA_VIEW'

    try {
      ;[todayMap, tomorrowMap] = await Promise.all([
        fetchOreeDayPrices(now),
        fetchOreeDayPrices(tomorrow),
      ])
    } catch (e) {
      console.warn('[prices/current] OREE fetch failed:', e)
    }

    const hasRealData = todayMap.size > 0 || tomorrowMap.size > 0
    let forecast: Array<{ hour: number; timestamp: string; price: number; confidence: number; trend: Trend }> = []

    if (hasRealData) {
      for (let i = 0; i < 24; i += 1) {
        const ts = new Date(now.getTime() + i * 3600000)
        const hour = ts.getHours()
        const sameDay = formatDateLabel(ts) === formatDateLabel(now)
        const map = sameDay ? todayMap : tomorrowMap
        const price = map.get(hour)

        if (price == null) {
          source = 'PARTIAL_OREE_WITH_FALLBACK'
          const fallback = buildFallbackPrices(now).forecast[i]
          forecast.push({ ...fallback, hour, timestamp: ts.toISOString() })
          continue
        }

        const prev = forecast[forecast.length - 1]?.price
        const trend: Trend = prev == null ? 'stable' : price > prev ? 'up' : price < prev ? 'down' : 'stable'
        forecast.push({
          hour,
          timestamp: ts.toISOString(),
          price: Number(price.toFixed(2)),
          confidence: 0.95,
          trend,
        })
      }
    } else {
      const fallback = buildFallbackPrices(now)
      forecast = fallback.forecast
      source = fallback.source
    }

    const result = summarizePrices(now, forecast, source)
    PRICE_CACHE = { ts: nowTs, data: result }
    return result
  } catch (error: any) {
    console.error('Failed to fetch prices:', error)
    return {
      success: false,
      error: error.message || 'Failed to fetch prices',
      prices: null,
    }
  }
})
