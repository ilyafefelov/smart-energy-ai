param(
  [string]$BaseUrl = 'http://127.0.0.1:3600',
  [bool]$RequireCanonicalEconomics = $true
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
      $tempBodyFile = [System.IO.Path]::GetTempFileName()
      $curlArgs = @('-s', '-o', $tempBodyFile, '-w', '%{http_code}', '-X', $Method)
      foreach ($k in $Form.Keys) {
        $v = $Form[$k]
        if ($v -is [System.IO.FileInfo]) {
          $curlArgs += @('-F', "${k}=@$($v.FullName);type=application/json")
        } else {
          $curlArgs += @('-F', "${k}=$v")
        }
      }
      $curlArgs += $url
      $statusText = ((& curl.exe @curlArgs) -join '').Trim()
      $raw = if (Test-Path $tempBodyFile) { Get-Content -Path $tempBodyFile -Raw -ErrorAction SilentlyContinue } else { '' }
      $status = if ($statusText -match '^\d{3}$') { [int]$statusText } else { 0 }
      if (Test-Path $tempBodyFile) {
        Remove-Item -Path $tempBodyFile -Force -ErrorAction SilentlyContinue
      }
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
    $status = 0
    $raw = $_.Exception.Message
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
$null = Invoke-Api -Method 'GET' -Path '/api/retraining/progress?jobId=missing-job'
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
  $historySource = Get-EconomicsSource -Payload $historyAfterExecute
  if (-not $historySource) {
    $historyRetry = Invoke-Api -Method 'GET' -Path '/api/history' -Note 'canonical-assertion-retry'
    $historySource = Get-EconomicsSource -Payload $historyRetry
    if ($historyRetry) {
      $historyAfterExecute = $historyRetry
    }
  }
  $historyCanonical = $historySource -eq 'optimization_history_db'
  Add-Assertion -Name 'history_economics_source' -Passed $historyCanonical -Message "Expected economics_source=optimization_history_db after execute, got '$historySource'"

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

# Multipart import endpoint
$tmpImport = Join-Path $env:TEMP 'settings-smoke-import.json'
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
$null = Invoke-Api -Method 'POST' -Path '/api/settings/import' -Form @{ file = Get-Item $tmpImport }

$reportDir = Join-Path (Join-Path $PSScriptRoot '..') 'data'
if (-not (Test-Path $reportDir)) {
  New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
}
$reportPath = Join-Path $reportDir 'api_smoke_test_report.json'
$results | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding UTF8

$summary = [pscustomobject]@{
  total = $results.Count
  http_ok = @($results | Where-Object { $_.http_ok }).Count
  http_fail = @($results | Where-Object { -not $_.http_ok }).Count
  app_success_true = @($results | Where-Object { $_.app_success -eq $true }).Count
  app_success_false = @($results | Where-Object { $_.app_success -eq $false }).Count
  report = $reportPath
}

$summary | ConvertTo-Json -Depth 4
