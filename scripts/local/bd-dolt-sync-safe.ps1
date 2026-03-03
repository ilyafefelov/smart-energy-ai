param(
  [switch]$RequireRemote
)

$ErrorActionPreference = 'Stop'

try {
  $remoteJson = bd dolt remote list --json
} catch {
  throw "Failed to query Beads Dolt remotes: $($_.Exception.Message)"
}

$remotes = $null
if ($remoteJson -and $remoteJson.Trim() -ne 'null') {
  try {
    $remotes = $remoteJson | ConvertFrom-Json
  } catch {
    throw "Failed to parse Dolt remote list JSON: $($_.Exception.Message)"
  }
}

$hasRemote = $false
if ($remotes -is [System.Array]) {
  $hasRemote = $remotes.Count -gt 0
} elseif ($null -ne $remotes) {
  $hasRemote = $true
}

if (-not $hasRemote) {
  if ($RequireRemote) {
    throw 'No Dolt remotes configured for this Beads board. Configure one with: bd dolt remote add <name> <url>'
  }

  Write-Host 'No Dolt remote configured; skipping bd dolt pull/push.' -ForegroundColor Yellow
  Write-Host 'Board issue operations remain available locally (bd ready/show/update/close).' -ForegroundColor Yellow
  exit 0
}

Write-Host 'Dolt remote detected; syncing Beads board...' -ForegroundColor Green
bd dolt pull
bd dolt push
Write-Host 'Beads Dolt sync complete.' -ForegroundColor Green
