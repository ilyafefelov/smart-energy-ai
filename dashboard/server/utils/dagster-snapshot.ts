import { normalizeClockHour } from './dagster-schedule-policy'
import { toFiniteNumber } from './recommendation-contract'

export type SnapshotFreshness = {
  isFresh: boolean
  ageMinutes: number | null
  materializedAtIso: string | null
  reason: string
}

export type ScheduleQualityAssessment = {
  isValid: boolean
  reason: string
  rowCount: number
}

export type DagsterSnapshotSourceDetail = 'dagster_postgres_snapshot' | 'dagster_asset_file'

type DagsterSnapshotScheduleRow = {
  hour?: unknown
  hour_offset?: unknown
  action_kw?: unknown
}

type DagsterSnapshotLike = {
  materialization_time?: string | null
  generated_at?: string | null
  schedule?: DagsterSnapshotScheduleRow[] | null
}

type DagsterSnapshotCandidate<TSnapshot extends DagsterSnapshotLike> = {
  snapshot: TSnapshot
  sourceDetail: DagsterSnapshotSourceDetail
  freshness: SnapshotFreshness
  quality: ScheduleQualityAssessment
}

export function resolveSnapshotTimestamp<TSnapshot extends DagsterSnapshotLike>(snapshot: TSnapshot | null): Date | null {
  if (!snapshot) return null

  const candidates = [snapshot.materialization_time, snapshot.generated_at]
  for (const candidate of candidates) {
    if (!candidate) continue
    const parsed = new Date(candidate)
    if (!Number.isNaN(parsed.getTime())) {
      return parsed
    }
  }

  return null
}

export function evaluateSnapshotFreshness<TSnapshot extends DagsterSnapshotLike>(
  snapshot: TSnapshot | null,
  maxSnapshotAgeMinutes: number,
): SnapshotFreshness {
  const materializedAt = resolveSnapshotTimestamp(snapshot)
  if (!materializedAt) {
    return {
      isFresh: false,
      ageMinutes: null,
      materializedAtIso: null,
      reason: 'missing_timestamp',
    }
  }

  const ageMs = Date.now() - materializedAt.getTime()
  const ageMinutes = ageMs / 60000
  return {
    isFresh: ageMinutes <= maxSnapshotAgeMinutes,
    ageMinutes: Number(ageMinutes.toFixed(2)),
    materializedAtIso: materializedAt.toISOString(),
    reason: ageMinutes <= maxSnapshotAgeMinutes ? 'fresh' : 'stale',
  }
}

export function evaluateScheduleQuality<TSnapshot extends DagsterSnapshotLike>(
  snapshot: TSnapshot | null,
): ScheduleQualityAssessment {
  if (!snapshot || !Array.isArray(snapshot.schedule)) {
    return {
      isValid: false,
      reason: 'missing_schedule',
      rowCount: 0,
    }
  }

  const rows = snapshot.schedule.slice(0, 24)
  if (rows.length < 24) {
    return {
      isValid: false,
      reason: 'insufficient_rows',
      rowCount: rows.length,
    }
  }

  const hourOffsets = new Set<number>()
  for (const row of rows) {
    const rawOffset = toFiniteNumber(row?.hour_offset ?? row?.hour)
    if (rawOffset == null) {
      return {
        isValid: false,
        reason: 'invalid_hour_offset',
        rowCount: rows.length,
      }
    }

    const offset = normalizeClockHour(rawOffset, 0)
    if (hourOffsets.has(offset)) {
      return {
        isValid: false,
        reason: 'duplicate_hour_offset',
        rowCount: rows.length,
      }
    }
    hourOffsets.add(offset)

    const actionKw = toFiniteNumber(row?.action_kw)
    if (actionKw == null) {
      return {
        isValid: false,
        reason: 'invalid_action_kw',
        rowCount: rows.length,
      }
    }
  }

  return {
    isValid: true,
    reason: 'valid',
    rowCount: rows.length,
  }
}

function compareDagsterSnapshotCandidates<TSnapshot extends DagsterSnapshotLike>(
  a: DagsterSnapshotCandidate<TSnapshot>,
  b: DagsterSnapshotCandidate<TSnapshot>,
) {
  const aTimestamp = resolveSnapshotTimestamp(a.snapshot)?.getTime() ?? 0
  const bTimestamp = resolveSnapshotTimestamp(b.snapshot)?.getTime() ?? 0
  if (aTimestamp !== bTimestamp) {
    return bTimestamp - aTimestamp
  }

  if (a.sourceDetail === b.sourceDetail) {
    return 0
  }

  return a.sourceDetail === 'dagster_postgres_snapshot' ? -1 : 1
}

function buildDagsterSnapshotCandidate<TSnapshot extends DagsterSnapshotLike>(
  snapshot: TSnapshot | null,
  sourceDetail: DagsterSnapshotSourceDetail,
  maxSnapshotAgeMinutes: number,
): DagsterSnapshotCandidate<TSnapshot> | null {
  if (!snapshot) {
    return null
  }

  return {
    snapshot,
    sourceDetail,
    freshness: evaluateSnapshotFreshness(snapshot, maxSnapshotAgeMinutes),
    quality: evaluateScheduleQuality(snapshot),
  }
}

export function selectDagsterSnapshotCandidate<TSnapshot extends DagsterSnapshotLike>(
  postgresDagster: TSnapshot | null,
  fileDagster: TSnapshot | null,
  maxSnapshotAgeMinutes: number,
) {
  const candidates = [
    buildDagsterSnapshotCandidate(postgresDagster, 'dagster_postgres_snapshot', maxSnapshotAgeMinutes),
    buildDagsterSnapshotCandidate(fileDagster, 'dagster_asset_file', maxSnapshotAgeMinutes),
  ]
    .filter((candidate): candidate is DagsterSnapshotCandidate<TSnapshot> => candidate != null)
    .sort((a, b) => compareDagsterSnapshotCandidates(a, b))

  return {
    selected: candidates.find((candidate) => candidate.freshness.isFresh && candidate.quality.isValid) || null,
    latest: candidates[0] || null,
  }
}