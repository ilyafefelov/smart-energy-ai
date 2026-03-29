function Test-Endpoint {
  param(
    [string]$Url,
    [int]$TimeoutSec = 3
  )

  try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
    return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
  } catch {
    return $false
  }
}

function Wait-Endpoint {
  param(
    [string]$Url,
    [int]$TimeoutSec = 90
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    if (Test-Endpoint -Url $Url -TimeoutSec 3) {
      return $true
    }
    Start-Sleep -Seconds 2
  }

  return $false
}

function Test-PythonModule {
  param(
    [string]$PythonPath,
    [string]$ModuleName
  )

  if (-not (Test-Path $PythonPath)) {
    return $false
  }

  $result = & $PythonPath -c "import importlib.util; print('1' if importlib.util.find_spec('$ModuleName') else '0')" 2>$null
  return (($result -join '').Trim() -eq '1')
}

function Resolve-DagsterPython {
  param(
    [string]$RepoRoot
  )

  $candidates = @()
  $candidates += (Join-Path $RepoRoot '.venv\Scripts\python.exe')
  $candidates += (Join-Path $env:APPDATA 'pypoetry\venv\Scripts\python.exe')

  $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCmd -and $pythonCmd.Source) {
    $candidates += $pythonCmd.Source
  }

  foreach ($candidate in ($candidates | Select-Object -Unique)) {
    $hasDagster = Test-PythonModule -PythonPath $candidate -ModuleName 'dagster'
    $hasWebserver = Test-PythonModule -PythonPath $candidate -ModuleName 'dagster_webserver'
    if ($hasDagster -and $hasWebserver) {
      return $candidate
    }
  }

  throw 'Unable to find a Python executable with both dagster and dagster_webserver installed.'
}

function Get-ListeningPortProcessId {
  param(
    [int]$Port
  )

  try {
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
      Select-Object -First 1
    if ($null -ne $connection) {
      return [int]$connection.OwningProcess
    }
  } catch {
    return $null
  }

  return $null
}