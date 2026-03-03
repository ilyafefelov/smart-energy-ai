# Start Nuxt Dashboard with Real Data (PowerShell)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "🚀 Starting Smart Energy AI Dashboard" -ForegroundColor Green
Write-Host "════════════════════════════════════" -ForegroundColor Green
Write-Host ""

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install --legacy-peer-deps
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ npm install failed" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🔄 Starting Nuxt dev server..." -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Dashboard will be available at:" -ForegroundColor Cyan
Write-Host "   → http://localhost:3600" -ForegroundColor White
Write-Host ""
Write-Host "📚 Pages:" -ForegroundColor Cyan
Write-Host "   → http://localhost:3600/ (Dashboard)" -ForegroundColor White
Write-Host "   → http://localhost:3600/analytics (Analytics)" -ForegroundColor White
Write-Host "   → http://localhost:3600/control (Control)" -ForegroundColor White
Write-Host "   → http://localhost:3600/settings (Settings)" -ForegroundColor White
Write-Host ""
Write-Host "📈 Real Data Sources:" -ForegroundColor Cyan
Write-Host "   → OREE Feb 2026 prices (5₴ - 15₴/kWh)" -ForegroundColor White
Write-Host "   → PPO ML validation (57.9% savings)" -ForegroundColor White
Write-Host "   → Battery status (150 kWh capacity)" -ForegroundColor White
Write-Host "   → 7-day history (55,316₴ saved)" -ForegroundColor White
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""

npm run dev
