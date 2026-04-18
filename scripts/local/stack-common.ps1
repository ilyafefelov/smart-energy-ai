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

function Resolve-OptimizationDbConfig {
  $dbHost = if ($env:APP_DB_HOST) { $env:APP_DB_HOST } elseif ($env:DB_HOST) { $env:DB_HOST } else { 'localhost' }
  $dbPort = if ($env:APP_DB_PORT) { $env:APP_DB_PORT } elseif ($env:DB_PORT) { $env:DB_PORT } else { '5432' }
  $dbUser = if ($env:APP_DB_USER) { $env:APP_DB_USER } elseif ($env:DB_USER) { $env:DB_USER } else { 'dagster' }
  $dbPassword = if ($env:APP_DB_PASSWORD) { $env:APP_DB_PASSWORD } elseif ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { 'dagster' }
  $dbName = if ($env:APP_DB_NAME) { $env:APP_DB_NAME } elseif ($env:OPTIMIZATION_DB_NAME) { $env:OPTIMIZATION_DB_NAME } else { 'smart_energy_ai' }
  $bootstrapDb = if ($env:APP_DB_BOOTSTRAP_DB) { $env:APP_DB_BOOTSTRAP_DB } elseif ($env:DB_NAME) { $env:DB_NAME } else { 'dagster' }

  return [pscustomobject]@{
    Host = [string]$dbHost
    Port = [int]$dbPort
    User = [string]$dbUser
    Password = [string]$dbPassword
    Database = [string]$dbName
    BootstrapDatabase = [string]$bootstrapDb
  }
}

function Set-OptimizationDbEnvironment {
  param(
    [pscustomobject]$Config
  )

  $env:APP_DB_HOST = [string]$Config.Host
  $env:APP_DB_PORT = [string]$Config.Port
  $env:APP_DB_USER = [string]$Config.User
  $env:APP_DB_PASSWORD = [string]$Config.Password
  $env:APP_DB_NAME = [string]$Config.Database
  $env:OPTIMIZATION_DB_NAME = [string]$Config.Database
  $env:APP_DB_BOOTSTRAP_DB = [string]$Config.BootstrapDatabase
}

function Ensure-OptimizationDatabase {
  param(
    [string]$PythonPath,
    [pscustomobject]$Config
  )

  if (-not (Test-Path $PythonPath)) {
    Write-Host 'Optimization DB bootstrap skipped: Python executable not found.' -ForegroundColor Yellow
    return $false
  }

  Set-OptimizationDbEnvironment -Config $Config

  $bootstrapCode = @'
import json
import os
import sys

try:
    import psycopg2
    from psycopg2 import sql
except Exception as exc:
    print(json.dumps({"ok": False, "reason": f"psycopg2 unavailable: {exc}"}))
    raise SystemExit(1)

host = os.environ.get("APP_DB_HOST") or "localhost"
port = int(os.environ.get("APP_DB_PORT") or "5432")
user = os.environ.get("APP_DB_USER") or "dagster"
password = os.environ.get("APP_DB_PASSWORD") or "dagster"
target_db = os.environ.get("APP_DB_NAME") or os.environ.get("OPTIMIZATION_DB_NAME") or "smart_energy_ai"

bootstrap_candidates = []
for candidate in [os.environ.get("APP_DB_BOOTSTRAP_DB"), os.environ.get("DB_NAME"), "dagster", "postgres"]:
    if candidate and candidate not in bootstrap_candidates:
        bootstrap_candidates.append(candidate)

connection = None
selected = None
last_error = None
for candidate in bootstrap_candidates:
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=candidate,
        )
        selected = candidate
        break
    except Exception as exc:
        last_error = str(exc)

if connection is None:
    print(json.dumps({"ok": False, "reason": last_error or "no bootstrap database reachable"}))
    raise SystemExit(1)

connection.autocommit = True
created = False
try:
    with connection.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute(sql.SQL("CREATE DATABASE {}"
            ).format(sql.Identifier(target_db)))
            created = True
finally:
    connection.close()

print(json.dumps({
    "ok": True,
    "bootstrap_database": selected,
    "target_database": target_db,
    "created": created,
}))
'@

  $rawResult = & $PythonPath -c $bootstrapCode 2>&1
  $resultText = (($rawResult | Out-String) -replace '\r', '').Trim()
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Optimization DB bootstrap skipped: $resultText" -ForegroundColor Yellow
    return $false
  }

  try {
    $payload = $resultText | ConvertFrom-Json
  } catch {
    Write-Host "Optimization DB bootstrap returned non-JSON output: $resultText" -ForegroundColor Yellow
    return $false
  }

  if (-not $payload.ok) {
    Write-Host "Optimization DB bootstrap skipped: $($payload.reason)" -ForegroundColor Yellow
    return $false
  }

  $status = if ($payload.created) { 'created' } else { 'already present' }
  Write-Host "Optimization history DB ${status}: $($payload.target_database) (bootstrap DB: $($payload.bootstrap_database))" -ForegroundColor DarkGray
  return $true
}