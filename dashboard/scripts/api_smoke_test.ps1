param(
  [string]$BaseUrl = 'http://127.0.0.1:3600',
  [bool]$RequireCanonicalEconomics = $true,
  [string[]]$TenantIds = @('client_001_kyiv_mall', 'client_002_lviv_office')
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$results = New-Object System.Collections.Generic.List[object]

try {
  Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
} catch {
  # Assembly may already be loaded or unavailable in constrained environments.
}

function Add-Result {
  param(
    [string]$Method,
    [string]$Path,
    [int]$Status,
    [object]$Parsed,
    [string]$Raw,
    [string]$Note = ''
  )

  $appSuccess = $null
  $message = ''

  if ($null -ne $Parsed) {
    if ($Parsed.PSObject.Properties.Name -contains 'success') {
      $appSuccess = [bool]$Parsed.success
    }

    if ($Parsed.PSObject.Properties.Name -contains 'error' -and $Parsed.error) {
      $message = [string]$Parsed.error
    } elseif ($Parsed.PSObject.Properties.Name -contains 'message' -and $Parsed.message) {
      $message = [string]$Parsed.message
    } elseif ($Parsed.PSObject.Properties.Name -contains 'status' -and $Parsed.status) {
      $message = [string]$Parsed.status
    }
  }

  if (-not $message -and $Raw) {
    $message = if ($Raw.Length -gt 180) { $Raw.Substring(0, 180) + '...' } else { $Raw }
  }

  $results.Add([pscustomobject]@{
      method = $Method
      path = $Path
      status = $Status
      http_ok = ($Status -ge 200 -and $Status -lt 300)
      app_success = $appSuccess
      note = $Note
      message = $message
    }) | Out-Null
}

function Add-Assertion {
  param(
    [string]$Name,
    [bool]$Passed,
    [string]$Message
  )

  $status = if ($Passed) { 200 } else { 500 }
  $payload = [pscustomobject]@{
    success = $Passed
    message = $Message
  }

  Add-Result -Method 'ASSERT' -Path "/assertions/$Name" -Status $status -Parsed $payload -Raw $Message -Note 'assertion'
}

function Get-EconomicsSource {
  param(
    [object]$Payload
  )

  if ($null -eq $Payload) {
    return ''
  }

  if (-not ($Payload.PSObject.Properties.Name -contains 'source')) {
    return ''
  }

  $source = $Payload.source
  if ($null -eq $source) {
    return ''
  }

  if ($source -is [hashtable]) {
    return [string]($source['economics_source'])
  }

  if ($source.PSObject.Properties.Name -contains 'economics_source') {
    return [string]$source.economics_source
  }

  return ''
}

function Get-ErrorCode {
  param(
    [object]$Payload
  )

  if ($null -eq $Payload) {
    return ''
  }

  if ($Payload.PSObject.Properties.Name -contains 'error') {
    $errorValue = $Payload.error
    if ($errorValue -is [hashtable]) {
      return [string]($errorValue['code'])
    }

    if ($errorValue -and ($errorValue.PSObject.Properties.Name -contains 'code')) {
      return [string]$errorValue.code
    }
  }

  return ''
}

function Invoke-Api {
  param(
    [string]$Method,
    [string]$Path,
    [object]$Body = $null,
    [hashtable]$Form = $null,
    [string]$Note = ''
  )

  $url = "$BaseUrl$Path"
  $status = 0
  $raw = ''
  $parsed = $null

  try {
    if ($null -ne $Form) {
      $resp = Invoke-WebRequest -Uri $url -Method $Method -Form $Form -TimeoutSec 120 -UseBasicParsing -ErrorAction Stop
      $status = [int]$resp.StatusCode
      $raw = [string]$resp.Content
    } elseif ($null -ne $Body) {
      $json = $Body | ConvertTo-Json -Depth 20
      $resp = Invoke-WebRequest -Uri $url -Method $Method -Body $json -ContentType 'application/json' -TimeoutSec 120 -UseBasicParsing -ErrorAction Stop
      $status = [int]$resp.StatusCode
      $raw = [string]$resp.Content
    } else {
      $resp = Invoke-WebRequest -Uri $url -Method $Method -TimeoutSec 120 -UseBasicParsing -ErrorAction Stop
      $status = [int]$resp.StatusCode
      $raw = [string]$resp.Content
    }
  } catch [System.Net.WebException] {
    $ex = $_.Exception
    if ($ex.Response) {
      $status = [int]$ex.Response.StatusCode
      try {
        $reader = New-Object System.IO.StreamReader($ex.Response.GetResponseStream())
        $raw = $reader.ReadToEnd()
      } catch {
        $raw = $ex.Message
      }
    } else {
      $status = 0
      $raw = $ex.Message
    }
  } catch {
    if ($_.Exception.Response) {
      $status = [int]$_.Exception.Response.StatusCode
      if ($_.ErrorDetails.Message) {
        $raw = $_.ErrorDetails.Message
      } else {
        $raw = $_.Exception.Message
      }
    } else {
      $status = 0
      $raw = $_.Exception.Message
    }
  }

  try {
    if ($raw) {
      try {
        $parsed = $raw | ConvertFrom-Json -Depth 50
      } catch {
        $parsed = $raw | ConvertFrom-Json
      }
    }
  } catch {
    $parsed = $null
  }

  Add-Result -Method $Method -Path $Path -Status $status -Parsed $parsed -Raw $raw -Note $Note
  return $parsed
}

function Invoke-ApiJsonImport {
  param(
    [string]$Path,
    [string]$FilePath,
    [string]$Note = ''
  )

  $url = "$BaseUrl$Path"
  $status = 0
  $raw = ''
  $parsed = $null

  try {
    $env:SMOKE_IMPORT_URL = $url
    $env:SMOKE_IMPORT_FILE_PATH = $FilePath
    $nodeResult = @'
import { readFile } from 'node:fs/promises'

const url = process.env.SMOKE_IMPORT_URL
const filePath = process.env.SMOKE_IMPORT_FILE_PATH
const fileContent = await readFile(filePath, 'utf8')
const form = new FormData()
form.append('file', new Blob([fileContent], { type: 'application/json' }), 'settings-smoke-import.json')

const response = await fetch(url, {
  method: 'POST',
  body: form,
})

console.log(JSON.stringify({
  status: response.status,
  raw: await response.text(),
}))
'@ | node --input-type=module

    $nodePayload = (($nodeResult -join [Environment]::NewLine) | ConvertFrom-Json)
    $status = [int]$nodePayload.status
    $raw = [string]$nodePayload.raw
  } catch {
    $status = 0
    $raw = $_.Exception.Message
  } finally {
    if (Test-Path Env:SMOKE_IMPORT_URL) {
      Remove-Item Env:SMOKE_IMPORT_URL -ErrorAction SilentlyContinue
    }
    if (Test-Path Env:SMOKE_IMPORT_FILE_PATH) {
      Remove-Item Env:SMOKE_IMPORT_FILE_PATH -ErrorAction SilentlyContinue
    }
  }

  try {
    if ($raw) {
      try {
        $parsed = $raw | ConvertFrom-Json -Depth 50
      } catch {
        $parsed = $raw | ConvertFrom-Json
      }
    }
  } catch {
    $parsed = $null
  }

  Add-Result -Method 'POST' -Path $Path -Status $status -Parsed $parsed -Raw $raw -Note $Note
  return $parsed
}

# GET endpoints
$null = Invoke-Api -Method 'GET' -Path '/api/battery'
$historyResp = Invoke-Api -Method 'GET' -Path '/api/history'
$metricsResp = Invoke-Api -Method 'GET' -Path '/api/metrics'
$null = Invoke-Api -Method 'GET' -Path '/api/prices'
$null = Invoke-Api -Method 'GET' -Path '/api/battery/status'
$null = Invoke-Api -Method 'GET' -Path '/api/battery/simulate'
$null = Invoke-Api -Method 'GET' -Path '/api/config/current'
$null = Invoke-Api -Method 'GET' -Path '/api/config/templates'
$null = Invoke-Api -Method 'GET' -Path '/api/control/history'
$null = Invoke-Api -Method 'GET' -Path '/api/control/physics'
$null = Invoke-Api -Method 'GET' -Path '/api/control/scheduled'
$null = Invoke-Api -Method 'GET' -Path '/api/control/status'
$null = Invoke-Api -Method 'GET' -Path '/api/dagster/assets'
$null = Invoke-Api -Method 'GET' -Path '/api/dagster/recommendation'
$null = Invoke-Api -Method 'GET' -Path '/api/dagster/schedule-24h'
$null = Invoke-Api -Method 'GET' -Path '/api/metrics/dashboard'
$null = Invoke-Api -Method 'GET' -Path '/api/ml/monitoring'
$null = Invoke-Api -Method 'GET' -Path '/api/ml/predict'
$null = Invoke-Api -Method 'GET' -Path '/api/ml/recommendation'
$null = Invoke-Api -Method 'GET' -Path '/api/mlflow/status'
$null = Invoke-Api -Method 'GET' -Path '/api/optimization/strategy'
$null = Invoke-Api -Method 'GET' -Path '/api/physics/battery'
$null = Invoke-Api -Method 'GET' -Path '/api/prices/current'
$null = Invoke-Api -Method 'GET' -Path '/api/renewable/forecast?type=forecast&forecast_hours=24&solar_capacity=5&wind_capacity=2'
$null = Invoke-Api -Method 'GET' -Path '/api/retraining/progress?jobId=missing-job' -Note 'expected-negative'
$null = Invoke-Api -Method 'GET' -Path '/api/settings/export'
$null = Invoke-Api -Method 'GET' -Path '/api/settings/load'

# POST endpoints
$null = Invoke-Api -Method 'POST' -Path '/api/battery/simulate' -Body @{ action = 'setPower'; power = 0 }
$null = Invoke-Api -Method 'POST' -Path '/api/config/save' -Body @{
  battery_type = 'LFP'
  battery_capacity_kwh = 150
  battery_efficiency = 0.95
  load_profile_type = 'standard'
  load_peak_kw = 50
  tariff_peak_hours_start = 8
  tariff_peak_hours_end = 22
  tariff_peak_rate_uah_kwh = 12
  tariff_off_peak_rate_uah_kwh = 6
}
$executeResp = Invoke-Api -Method 'POST' -Path '/api/control/execute' -Body @{ command = 'hold'; power_kw = 0; reason = 'api smoke test' }

$historyAfterExecute = Invoke-Api -Method 'GET' -Path '/api/history' -Note 'post-execute-canonical-check'
$metricsAfterExecute = Invoke-Api -Method 'GET' -Path '/api/metrics' -Note 'post-execute-canonical-check'

if ($RequireCanonicalEconomics) {
  $allowedHistorySources = @('optimization_history_db', 'dagster_asset_results', 'ppo_validation_artifact')
  $historySource = Get-EconomicsSource -Payload $historyAfterExecute
  if (-not $historySource) {
    $historyRetry = Invoke-Api -Method 'GET' -Path '/api/history' -Note 'canonical-assertion-retry'
    $historySource = Get-EconomicsSource -Payload $historyRetry
    if ($historyRetry) {
      $historyAfterExecute = $historyRetry
    }
  }
  $historyCanonical = $allowedHistorySources -contains $historySource
  Add-Assertion -Name 'history_economics_source' -Passed $historyCanonical -Message "Expected economics_source to be one of [$($allowedHistorySources -join ', ')], got '$historySource'"

  $metricsSource = Get-EconomicsSource -Payload $metricsAfterExecute
  if (-not $metricsSource) {
    $metricsRetry = Invoke-Api -Method 'GET' -Path '/api/metrics' -Note 'canonical-assertion-retry'
    $metricsSource = Get-EconomicsSource -Payload $metricsRetry
    if ($metricsRetry) {
      $metricsAfterExecute = $metricsRetry
    }
  }
  $metricsAligned = $metricsSource -eq $historySource
  Add-Assertion -Name 'metrics_economics_source_alignment' -Passed $metricsAligned -Message "Expected metrics economics_source to match history ('$historySource'), got '$metricsSource'"
}

$historyRows = @()
if ($historyAfterExecute -and ($historyAfterExecute.PSObject.Properties.Name -contains 'data')) {
  $historyRows = @($historyAfterExecute.data)
}
if ($historyRows.Count -gt 0) {
  $row = $historyRows[0]
  $baseline = [double]($row.cost_baseline)
  $optimized = [double]($row.cost_optimized)
  $savings = [double]($row.savings)

  Add-Assertion -Name 'history_value_sanity' -Passed ($baseline -ge 0 -and $optimized -ge 0) -Message "Expected non-negative costs, got baseline=$baseline optimized=$optimized"
  Add-Assertion -Name 'history_savings_consistency' -Passed ([math]::Abs(($baseline - $optimized) - $savings) -lt 0.2) -Message "Expected savings≈baseline-optimized within tolerance, got baseline=$baseline optimized=$optimized savings=$savings"
}

$scheduledTime = (Get-Date).ToUniversalTime().AddHours(1).ToString('o')
$scheduleResp = Invoke-Api -Method 'POST' -Path '/api/control/schedule' -Body @{ command = 'charge'; power_kw = 1; scheduled_time = $scheduledTime; reason = 'api smoke test' }
if ($scheduleResp -and $scheduleResp.schedule_id) {
  $sid = [string]$scheduleResp.schedule_id
  $null = Invoke-Api -Method 'DELETE' -Path "/api/control/schedule/$sid" -Note 'delete-created-schedule'
} else {
  Add-Result -Method 'DELETE' -Path '/api/control/schedule/[id]' -Status 0 -Parsed $null -Raw '' -Note 'skipped: no schedule_id from create'
}

$null = Invoke-Api -Method 'POST' -Path '/api/dagster/trigger' -Body @{ asset = 'weather_asset' }
$null = Invoke-Api -Method 'POST' -Path '/api/ml/predict' -Body @{ strategy = 'balanced'; battery_soc = 50; price = 14.26 }
$recalcResp = Invoke-Api -Method 'POST' -Path '/api/ml/recalculate' -Body @{ force = $false }
if ($recalcResp -and $recalcResp.jobId) {
  $null = Invoke-Api -Method 'GET' -Path ("/api/ml/recalculate-status?jobId=" + [string]$recalcResp.jobId)
} else {
  $null = Invoke-Api -Method 'GET' -Path '/api/ml/recalculate-status?jobId=missing-job'
}

$null = Invoke-Api -Method 'POST' -Path '/api/mlflow/log-metrics' -Body @{ step = 1; metrics = @{ smoke_metric = 1.0 } }
$null = Invoke-Api -Method 'POST' -Path '/api/optimization/strategy' -Body @{ strategy = 'balanced' }

$startResp = Invoke-Api -Method 'POST' -Path '/api/retraining/start' -Body @{ model = 'smoke-test' }
$jobId = if ($startResp -and $startResp.jobId) { [string]$startResp.jobId } else { 'missing-job' }
$null = Invoke-Api -Method 'GET' -Path "/api/retraining/progress?jobId=$jobId"
$null = Invoke-Api -Method 'POST' -Path "/api/retraining/cancel?jobId=$jobId"

$null = Invoke-Api -Method 'POST' -Path '/api/settings/battery' -Body @{ battery_type = 'LFP'; battery_capacity_kwh = 150; battery_efficiency = 0.95 }
$null = Invoke-Api -Method 'POST' -Path '/api/settings/load-profile' -Body @{ load_profile_type = 'standard'; load_peak_kw = 50 }
$null = Invoke-Api -Method 'POST' -Path '/api/settings/save' -Body @{
  general = @{ siteName = 'Smoke Test Site'; timezone = 'Europe/Kiev (GMT+2)'; currency = 'UAH'; notificationsEnabled = $true }
  battery = @{ capacity = 150; minSOC = 15; maxChargeRate = 50; maxDischargeRate = 50 }
  notifications = @{ highPrice = $true; highPriceThreshold = 13.0; lowPrice = $true; lowPriceThreshold = 7.0; modelComplete = $true; systemAlerts = $true }
  model = @{ learningRate = 0.0003; batchSize = 64; epochs = 20 }
}

# Tenant-scoped smoke checks
foreach ($tenantId in $TenantIds) {
  $tenantMetrics = Invoke-Api -Method 'GET' -Path "/api/metrics/dashboard?tenantId=$tenantId" -Note "tenant-check:$tenantId"
  $settingsNote = if ($tenantId -eq $TenantIds[0]) { "tenant-check:$tenantId" } else { 'expected-negative' }
  $tenantSettings = Invoke-Api -Method 'GET' -Path "/api/settings/load?tenantId=$tenantId" -Note $settingsNote

  $metricsTenantEcho = if ($tenantMetrics -and $tenantMetrics.tenant) { [string]$tenantMetrics.tenant.id } else { '' }
  $settingsTenantEcho = if ($tenantSettings -and $tenantSettings.tenant) { [string]$tenantSettings.tenant.id } else { '' }
  $settingsErrorCode = Get-ErrorCode -Payload $tenantSettings

  Add-Assertion -Name ("tenant_echo_metrics_{0}" -f $tenantId) -Passed ($metricsTenantEcho -eq $tenantId) -Message "Expected /api/metrics/dashboard tenant.id='$tenantId', got '$metricsTenantEcho'"

  if ($tenantId -eq $TenantIds[0]) {
    Add-Assertion -Name ("tenant_echo_settings_{0}" -f $tenantId) -Passed ($settingsTenantEcho -eq $tenantId) -Message "Expected /api/settings/load tenant.id='$tenantId', got '$settingsTenantEcho'"
  } else {
    $tenantGuardPassed = $settingsErrorCode -eq 'TENANT_AUTH_REQUIRED'
    Add-Assertion -Name ("tenant_settings_guard_{0}" -f $tenantId) -Passed $tenantGuardPassed -Message "Expected /api/settings/load to require trusted override for tenant '$tenantId', got error code '$settingsErrorCode'"
  }
}

if ($TenantIds.Count -ge 2) {
  $tenantA = $TenantIds[0]
  $tenantB = $TenantIds[1]

  $null = Invoke-Api -Method 'POST' -Path "/api/control/execute?tenantId=$tenantA" -Body @{ tenantId = $tenantA; command = 'hold'; power_kw = 0; reason = 'tenant smoke A' }
  $null = Invoke-Api -Method 'POST' -Path "/api/control/execute?tenantId=$tenantB" -Body @{ tenantId = $tenantB; command = 'hold'; power_kw = 0; reason = 'tenant smoke B' }

  $historyA = Invoke-Api -Method 'GET' -Path "/api/control/history?tenantId=$tenantA&limit=25" -Note 'tenant-leak-check'
  $historyB = Invoke-Api -Method 'GET' -Path "/api/control/history?tenantId=$tenantB&limit=25" -Note 'tenant-leak-check'

  $rowsA = if ($historyA -and $historyA.history) { @($historyA.history) } else { @() }
  $rowsB = if ($historyB -and $historyB.history) { @($historyB.history) } else { @() }

  $crossInA = @($rowsA | Where-Object { $_.tenant_id -eq $tenantB }).Count
  $crossInB = @($rowsB | Where-Object { $_.tenant_id -eq $tenantA }).Count

  Add-Assertion -Name 'tenant_history_no_cross_A' -Passed ($crossInA -eq 0) -Message "Expected no tenant '$tenantB' rows in tenant '$tenantA' history, found $crossInA"
  Add-Assertion -Name 'tenant_history_no_cross_B' -Passed ($crossInB -eq 0) -Message "Expected no tenant '$tenantA' rows in tenant '$tenantB' history, found $crossInB"
}

# Multipart import endpoint. Keep this near the end because it mutates tenant-local
# settings files that can trigger a transient dev-server restart under Nuxt watch mode.
$smokeArtifactDir = Join-Path (Join-Path $PSScriptRoot '..') '..\artifacts\local-smoke'
if (-not (Test-Path $smokeArtifactDir)) {
  New-Item -Path $smokeArtifactDir -ItemType Directory -Force | Out-Null
}

$tmpImport = Join-Path $smokeArtifactDir 'settings-smoke-import.json'
$importPayload = @{
  metadata = @{ exported = (Get-Date).ToString('o'); version = '1.0'; siteName = 'Smoke Import' }
  settings = @{
    general = @{ siteName = 'Smoke Import'; timezone = 'Europe/Kiev (GMT+2)'; currency = 'UAH'; notificationsEnabled = $true }
    battery = @{ capacity = 155; minSOC = 15; maxChargeRate = 50; maxDischargeRate = 50 }
    notifications = @{ highPrice = $true; highPriceThreshold = 13.0; lowPrice = $true; lowPriceThreshold = 7.0; modelComplete = $true; systemAlerts = $true }
    model = @{ learningRate = 0.0003; batchSize = 64; epochs = 20 }
  }
}
$importPayload | ConvertTo-Json -Depth 20 | Set-Content -Path $tmpImport -Encoding UTF8
$null = Invoke-ApiJsonImport -Path '/api/settings/import' -FilePath $tmpImport

$reportDir = Join-Path (Join-Path $PSScriptRoot '..') 'data'
if (-not (Test-Path $reportDir)) {
  New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
}
$reportPath = Join-Path $reportDir 'api_smoke_test_report.json'
$results | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding UTF8

$appSuccessFalse = @($results | Where-Object { $_.app_success -eq $false -and $_.note -ne 'expected-negative' }).Count
$appSuccessExpectedFalse = @($results | Where-Object { $_.app_success -eq $false -and $_.note -eq 'expected-negative' }).Count

$summary = [pscustomobject]@{
  total = $results.Count
  http_ok = @($results | Where-Object { $_.http_ok }).Count
  http_fail = @($results | Where-Object { -not $_.http_ok }).Count
  app_success_true = @($results | Where-Object { $_.app_success -eq $true }).Count
  app_success_false = $appSuccessFalse
  app_success_expected_false = $appSuccessExpectedFalse
  report = $reportPath
}

$summary | ConvertTo-Json -Depth 4
