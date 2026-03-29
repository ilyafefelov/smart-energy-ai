param(
  [int]$DagsterPort = 3000,
  [int]$DashboardPort = 3600,
  [int]$StartupTimeoutSec = 180,
  [switch]$InstallDashboardDeps,
  [switch]$SkipStart,
  [switch]$SkipDagsterJob,
  [switch]$SkipDashboardSmoke
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

. (Join-Path $PSScriptRoot 'stack-common.ps1')

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$startScript = Join-Path $PSScriptRoot 'start-local-stack.ps1'
$dashboardSmokeScript = Join-Path $repoRoot 'dashboard\scripts\api_smoke_test.ps1'
$stage2SmokeScript = Join-Path $repoRoot 'dashboard\scripts\stage2_demo_evidence.mjs'
$reportDir = Join-Path $repoRoot 'artifacts\local-smoke'
$reportPath = Join-Path $reportDir 'local_mvp_smoke_report.json'
$stage2EvidenceReportPath = Join-Path $reportDir 'stage2_demo_evidence_report.json'

if (-not (Test-Path $reportDir)) {
  New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
}

$dagsterUrl = "http://127.0.0.1:$DagsterPort/server_info"
$dashboardHealthUrl = "http://127.0.0.1:$DashboardPort/api/health"
$dashboardBaseUrl = "http://127.0.0.1:$DashboardPort"

$summary = [ordered]@{
  generated_at = (Get-Date).ToString('o')
  repo_root = [string]$repoRoot
  dagster_url = $dagsterUrl
  dashboard_base_url = $dashboardBaseUrl
  steps = @()
}

function Add-Step {
  param(
    [string]$Name,
    [bool]$Passed,
    [string]$Detail,
    [object]$Extra = $null
  )

  $step = [ordered]@{
    name = $Name
    passed = $Passed
    detail = $Detail
  }

  if ($null -ne $Extra) {
    $step.extra = $Extra
  }

  $summary.steps += [pscustomobject]$step
  $color = if ($Passed) { 'Green' } else { 'Red' }
  $prefix = if ($Passed) { '[PASS]' } else { '[FAIL]' }
  Write-Host ("$prefix $Name - $Detail") -ForegroundColor $color
}

try {
  if (-not $SkipStart) {
    $startArgs = @{
      DagsterPort = $DagsterPort
      DashboardPort = $DashboardPort
      StartupTimeoutSec = $StartupTimeoutSec
      Start = 'both'
    }
    if ($InstallDashboardDeps) {
      $startArgs.InstallDashboardDeps = $true
    }

    & $startScript @startArgs
    Add-Step -Name 'start_local_stack' -Passed $true -Detail 'Launcher completed successfully.'
  } else {
    Add-Step -Name 'start_local_stack' -Passed $true -Detail 'Skipped by request.'
  }

  $dagsterHealthy = Wait-Endpoint -Url $dagsterUrl -TimeoutSec $StartupTimeoutSec
  if (-not $dagsterHealthy) {
    throw "Dagster health check failed at $dagsterUrl"
  }
  Add-Step -Name 'dagster_health' -Passed $true -Detail "Dagster reachable at $dagsterUrl"

  $dashboardHealthy = Wait-Endpoint -Url $dashboardHealthUrl -TimeoutSec $StartupTimeoutSec
  if (-not $dashboardHealthy) {
    throw "Dashboard health check failed at $dashboardHealthUrl"
  }
  Add-Step -Name 'dashboard_health' -Passed $true -Detail "Dashboard reachable at $dashboardHealthUrl"

  if (-not $SkipDagsterJob) {
    $dagsterPython = Resolve-DagsterPython -RepoRoot $repoRoot
    Push-Location $repoRoot
    try {
      $jobOutput = & $dagsterPython -m dagster job execute -m src.definitions -j optimization_schedule_contract_checks 2>&1
    } finally {
      Pop-Location
    }
    if ($LASTEXITCODE -ne 0) {
      throw "Dagster contract-check job failed.`n$($jobOutput -join [Environment]::NewLine)"
    }

    Add-Step -Name 'dagster_contract_checks' -Passed $true -Detail 'optimization_schedule_contract_checks completed successfully.' -Extra @{
      python = $dagsterPython
    }
  } else {
    Add-Step -Name 'dagster_contract_checks' -Passed $true -Detail 'Skipped by request.'
  }

  if (-not $SkipDashboardSmoke) {
    Push-Location $repoRoot
    try {
      $dashboardSmokeRaw = & $dashboardSmokeScript -BaseUrl $dashboardBaseUrl 2>&1
    } finally {
      Pop-Location
    }
    if ($LASTEXITCODE -ne 0) {
      throw "Dashboard API smoke test failed.`n$($dashboardSmokeRaw -join [Environment]::NewLine)"
    }

    $dashboardSmokeText = ($dashboardSmokeRaw -join [Environment]::NewLine).Trim()
    $dashboardSmokeSummary = $null
    if ($dashboardSmokeText) {
      try {
        $dashboardSmokeSummary = $dashboardSmokeText | ConvertFrom-Json -Depth 20
      } catch {
        $dashboardSmokeSummary = $null
      }
    }

    if ($null -eq $dashboardSmokeSummary) {
      throw 'Dashboard API smoke test did not return a parseable JSON summary.'
    }

    $dashboardSmokePassed = ($dashboardSmokeSummary.http_fail -eq 0 -and $dashboardSmokeSummary.app_success_false -eq 0)
    if (-not $dashboardSmokePassed) {
      throw "Dashboard API smoke test reported failures: http_fail=$($dashboardSmokeSummary.http_fail), app_success_false=$($dashboardSmokeSummary.app_success_false)"
    }

    Add-Step -Name 'dashboard_api_smoke' -Passed $true -Detail 'Dashboard API smoke test completed successfully.' -Extra $dashboardSmokeSummary

    Push-Location $repoRoot
    try {
      $env:STAGE2_EVIDENCE_REPORT_PATH = $stage2EvidenceReportPath
      $stage2SmokeRaw = & node $stage2SmokeScript 2>&1
    } finally {
      if (Test-Path Env:STAGE2_EVIDENCE_REPORT_PATH) {
        Remove-Item Env:STAGE2_EVIDENCE_REPORT_PATH -ErrorAction SilentlyContinue
      }
      Pop-Location
    }
    if ($LASTEXITCODE -ne 0) {
      throw "Stage 2 evidence smoke test failed.`n$($stage2SmokeRaw -join [Environment]::NewLine)"
    }

    $stage2SmokeText = ($stage2SmokeRaw -join [Environment]::NewLine).Trim()
    $stage2SmokeSummary = $null
    if ($stage2SmokeText) {
      try {
        $stage2SmokeSummary = $stage2SmokeText | ConvertFrom-Json -Depth 20
      } catch {
        $stage2SmokeSummary = $null
      }
    }

    if ($null -eq $stage2SmokeSummary) {
      throw 'Stage 2 evidence smoke test did not return a parseable JSON summary.'
    }

    $stage2SmokePassed = ($stage2SmokeSummary.validation.passed -eq $true)
    if (-not $stage2SmokePassed) {
      throw "Stage 2 evidence smoke test reported validation failures."
    }

    Add-Step -Name 'stage2_evidence_smoke' -Passed $true -Detail 'Stage 2 evidence smoke test completed successfully.' -Extra $stage2SmokeSummary.validation
  } else {
    Add-Step -Name 'dashboard_api_smoke' -Passed $true -Detail 'Skipped by request.'
    Add-Step -Name 'stage2_evidence_smoke' -Passed $true -Detail 'Skipped by request.'
  }

  $summary.success = $true
  $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding UTF8
  Write-Host "Local MVP smoke report: $reportPath" -ForegroundColor Cyan
} catch {
  $summary.success = $false
  $summary.error = $_.Exception.Message
  $summary | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding UTF8
  Write-Host "Local MVP smoke report: $reportPath" -ForegroundColor Yellow
  throw
}