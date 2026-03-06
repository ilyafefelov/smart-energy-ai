import { existsSync, readFileSync } from 'fs'
import path from 'path'
import { defineEventHandler } from 'h3'
import { readDagsterAssetChecks } from '../../utils/dagster-asset-checks'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const DEFAULT_MLFLOW_URI = process.env.MLFLOW_API_URL || 'http://localhost:5000'

type HealthStatus = 'healthy' | 'degraded' | 'down'

function deriveStatus(ok: boolean): HealthStatus {
  return ok ? 'healthy' : 'down'
}

function readFileSafe(filePath: string): string | null {
  try {
    if (!existsSync(filePath)) return null
    return readFileSync(filePath, 'utf-8')
  } catch {
    return null
  }
}

function inspectMlflowDocker(projectRoot: string) {
  const composePath = path.join(projectRoot, 'docker-compose.yml')
  const dockerfilePath = path.join(projectRoot, 'Dockerfile')

  const composeContent = readFileSafe(composePath) || ''
  const dockerfileContent = readFileSafe(dockerfilePath) || ''

  const composeHasMlflowService = /\n\s*mlflow\s*:\s*\n/i.test(`\n${composeContent}`)
  const composeHasMlflowPort = /"?5000:5000"?/i.test(composeContent)
  const composeHasPostgresDependency = /depends_on:[\s\S]*postgres/i.test(composeContent)
  const composeHasMlflowImage = /ghcr\.io\/mlflow\/mlflow/i.test(composeContent)

  const dockerfileHasMlflow = /pip\s+install[\s\S]*mlflow/i.test(dockerfileContent)
  const dockerfileExposesMlflowPort = /EXPOSE\s+[0-9\s]*5000/i.test(dockerfileContent)

  const health = composeHasMlflowService && composeHasMlflowPort && dockerfileHasMlflow

  return {
    status: deriveStatus(health),
    compose: {
      path: composePath,
      mlflow_service_defined: composeHasMlflowService,
      mlflow_port_exposed: composeHasMlflowPort,
      postgres_dependency_defined: composeHasPostgresDependency,
      mlflow_image_defined: composeHasMlflowImage,
    },
    dockerfile: {
      path: dockerfilePath,
      mlflow_installed: dockerfileHasMlflow,
      mlflow_port_exposed: dockerfileExposesMlflowPort,
    },
  }
}

async function checkMlflowReachability(mlflowUri: string) {
  try {
    const response = await fetch(`${mlflowUri}/`, {
      signal: AbortSignal.timeout(2500),
    })
    return {
      reachable: response.ok,
      status_code: response.status,
    }
  } catch (error: any) {
    return {
      reachable: false,
      status_code: null,
      error: error?.message || 'unreachable',
    }
  }
}

export default defineEventHandler(async (event: any) => {
  const startedAt = Date.now()

  try {
    const tenant = await resolveTenantContext(event)
    const tenantRequest = {
      query: { tenantId: tenant.id },
      headers: { 'x-tenant-id': tenant.id },
    }

    const projectRoot = path.resolve(process.cwd(), '..')
    const bridgeScriptPath = path.join(projectRoot, 'ml_integration_api.py')

    const [mlflowStatus, recommendation, monitoring, dagsterRecommendation, mlflowReachability, dagsterAssetChecks] = await Promise.all([
      $fetch<any>('/api/mlflow/status', tenantRequest).catch(() => null),
      $fetch<any>('/api/ml/recommendation', tenantRequest).catch(() => null),
      $fetch<any>('/api/ml/monitoring', tenantRequest).catch(() => null),
      $fetch<any>('/api/dagster/recommendation', tenantRequest).catch(() => null),
      checkMlflowReachability(DEFAULT_MLFLOW_URI),
      readDagsterAssetChecks(projectRoot),
    ])

    const mlflowDocker = inspectMlflowDocker(projectRoot)

    const bridgeScriptExists = existsSync(bridgeScriptPath)
    const recommendationOk = recommendation?.success === true
    const monitoringOk = Boolean(monitoring?.system_health)
    const dagsterOk = dagsterRecommendation?.status === 'success'

    const driftStatus = recommendation?.data?.drift_diagnostics?.status || 'unknown'
    const driftScore = recommendation?.data?.drift_diagnostics?.score ?? null
    const dagsterSourceMetadata = dagsterRecommendation?.source_metadata || {}
    const dagsterCheckStatus = dagsterAssetChecks.summary?.overall_status || 'unknown'
    const dagsterCheckHealth: HealthStatus = dagsterAssetChecks.success
      ? dagsterCheckStatus === 'healthy'
        ? 'healthy'
        : 'degraded'
      : 'degraded'

    const components = {
      recommendation_api: {
        status: deriveStatus(recommendationOk),
        success: recommendationOk,
        action: recommendation?.data?.action || null,
      },
      monitoring_api: {
        status: deriveStatus(monitoringOk),
        available: monitoringOk,
      },
      dagster_recommendation_api: {
        status: deriveStatus(dagsterOk),
        available: dagsterOk,
        source: dagsterRecommendation?.source_metadata?.recommendation_source || null,
        snapshot_age_minutes: dagsterSourceMetadata?.dagster_snapshot_age_minutes ?? null,
        snapshot_is_fresh: dagsterSourceMetadata?.dagster_snapshot_is_fresh ?? null,
      },
      dagster_schedule_checks: {
        status: dagsterCheckHealth,
        available: dagsterAssetChecks.success,
        overall_status: dagsterCheckStatus,
        total_checks: dagsterAssetChecks.summary?.total_checks || 0,
        failed_checks: dagsterAssetChecks.summary?.failed_checks || 0,
        warning_checks: dagsterAssetChecks.summary?.warning_checks || 0,
        not_run_checks: dagsterAssetChecks.summary?.not_run_checks || 0,
        latest_evaluated_at: dagsterAssetChecks.summary?.latest_evaluated_at || null,
        failing_check_names: dagsterAssetChecks.summary?.failing_check_names || [],
        unevaluated_check_names: dagsterAssetChecks.summary?.unevaluated_check_names || [],
      },
      ml_bridge: {
        status: deriveStatus(bridgeScriptExists),
        script_path: bridgeScriptPath,
        script_exists: bridgeScriptExists,
      },
      mlflow: {
        status: mlflowStatus?.mlflow_connected === true || mlflowReachability.reachable ? 'healthy' : 'degraded',
        configured_uri: DEFAULT_MLFLOW_URI,
        connected_via_status_api: mlflowStatus?.mlflow_connected === true,
        reachable_over_http: mlflowReachability.reachable,
        reachability: mlflowReachability,
      },
      mlflow_docker: mlflowDocker,
      inference_drift: {
        status: driftStatus,
        score: driftScore,
      },
    }

    const downCount = Object.values(components).filter((component: any) => component?.status === 'down').length
    const degradedCount = Object.values(components).filter((component: any) => component?.status === 'degraded').length

    const overallStatus: HealthStatus = downCount > 0 ? 'down' : degradedCount > 0 ? 'degraded' : 'healthy'

    return {
      success: true,
      status: overallStatus,
      timestamp: new Date().toISOString(),
      latency_ms: Date.now() - startedAt,
      tenant: getTenantResponseMetadata(tenant),
      summary: {
        healthy_components: Object.values(components).filter((component: any) => component?.status === 'healthy').length,
        degraded_components: degradedCount,
        down_components: downCount,
      },
      components,
      dagster_asset_checks: dagsterAssetChecks,
      recommendations: [
        mlflowDocker.status !== 'healthy' ? 'Check Docker MLflow service definitions in docker-compose.yml and Dockerfile.' : null,
        components.mlflow.status !== 'healthy' ? `Start/recover MLflow at ${DEFAULT_MLFLOW_URI} or update MLFLOW_API_URL.` : null,
        driftStatus === 'drifted' ? 'Trigger accelerated retraining due to inference drift.' : null,
        dagsterCheckStatus === 'degraded' ? 'Investigate Dagster optimization schedule asset-check failures before trusting live recommendations.' : null,
        dagsterCheckStatus === 'unknown' ? 'Run the optimization schedule contract checks job to populate Dagster asset-check history.' : null,
      ].filter(Boolean),
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    return {
      success: false,
      status: 'down',
      timestamp: new Date().toISOString(),
      error: error?.message || 'ML pipeline health check failed',
    }
  }
})
