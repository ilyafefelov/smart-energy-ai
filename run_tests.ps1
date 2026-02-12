# run_tests.ps1 - Windows PowerShell Test Runner
<#
.SYNOPSIS
    Comprehensive Test Suite Runner for Smart Energy AI (Windows)

.DESCRIPTION
    Runs all test phases with proper Windows PowerShell support:
    - Unit Tests: Battery models, control system, optimization  
    - Integration Tests: API endpoints, system integration
    - E2E Tests: Dashboard workflows (if available)
    - Performance Tests: Load testing, response times

.PARAMETER TestType
    Type of tests to run: all, unit, integration, e2e, performance

.PARAMETER Coverage
    Run with coverage report

.PARAMETER InstallDeps  
    Install dependencies first

.EXAMPLE
    .\run_tests.ps1                     # Run all tests
    .\run_tests.ps1 -TestType unit      # Run only unit tests  
    .\run_tests.ps1 -Coverage           # Run with coverage
#>

param(
    [ValidateSet("all", "unit", "integration", "e2e", "performance")]
    [string]$TestType = "all",
    [switch]$Coverage,
    [switch]$InstallDeps,
    [switch]$SkipEnvCheck
)

$ErrorActionPreference = "Continue"

function Write-Header {
    param([string]$Title)
    Write-Host "`n🧪 $Title" -ForegroundColor Cyan
    Write-Host ("=" * 50) -ForegroundColor Cyan
}

function Write-SubHeader {
    param([string]$Title)
    Write-Host "`n$Title" -ForegroundColor Yellow
    Write-Host ("=" * 30) -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message) 
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Invoke-TestCommand {
    param(
        [string[]]$Command,
        [string]$Description,
        [int]$TimeoutSeconds = 300
    )
    
    Write-Host "🔄 $Description" -ForegroundColor Cyan
    Write-Host "Command: $($Command -join ' ')" -ForegroundColor Gray
    
    try {
        $process = Start-Process -FilePath $Command[0] -ArgumentList $Command[1..($Command.Length-1)] -NoNewWindow -Wait -PassThru -RedirectStandardOutput "temp_output.txt" -RedirectStandardError "temp_error.txt"
        
        $output = Get-Content "temp_output.txt" -ErrorAction SilentlyContinue
        $errors = Get-Content "temp_error.txt" -ErrorAction SilentlyContinue
        
        Remove-Item "temp_output.txt", "temp_error.txt" -ErrorAction SilentlyContinue
        
        if ($process.ExitCode -eq 0) {
            Write-Success "$Description - SUCCESS"
            if ($output) {
                Write-Host "Output: $($output[-10..-1] -join "`n")" -ForegroundColor Gray
            }
            return $true
        } else {
            Write-Error "$Description - FAILED"
            if ($errors) {
                Write-Host "Error: $($errors[-5..-1] -join "`n")" -ForegroundColor Red
            }
            return $false
        }
    } catch {
        Write-Error "$Description - ERROR: $_"
        return $false
    }
}

function Install-TestDependencies {
    Write-SubHeader "Installing Test Dependencies"
    
    $dependencies = @(
        "pytest",
        "pytest-asyncio",
        "pytest-cov", 
        "httpx",
        "pandas",
        "numpy"
    )
    
    $success = $true
    foreach ($dep in $dependencies) {
        $result = Invoke-TestCommand -Command @("python", "-m", "pip", "install", $dep) -Description "Installing $dep"
        if (-not $result) { $success = $false }
    }
    
    # Optional dependencies
    $optionalDeps = @("playwright")
    foreach ($dep in $optionalDeps) {
        Invoke-TestCommand -Command @("python", "-m", "pip", "install", $dep) -Description "Installing $dep (optional)"
    }
    
    # Install Playwright browsers
    try {
        Invoke-TestCommand -Command @("python", "-m", "playwright", "install", "chromium") -Description "Installing Playwright browsers (optional)"
    } catch {
        Write-Warning "Playwright browsers not installed (E2E tests will be skipped)"
    }
    
    return $success
}

function Test-Environment {
    Write-SubHeader "Checking Test Environment"
    
    # Check Python version
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                Write-Success "Python $major.$minor"
            } else {
                Write-Error "Python 3.8+ required, found Python $major.$minor"
                return $false
            }
        }
    } catch {
        Write-Error "Python not found in PATH"
        return $false
    }
    
    # Check project structure
    $requiredDirs = @("tests", "energy_ml")
    foreach ($dir in $requiredDirs) {
        if (Test-Path $dir) {
            Write-Success "$dir/ directory found"
        } else {
            Write-Error "$dir/ directory missing"
            return $false
        }
    }
    
    # Check test files
    $testFiles = @(
        "tests\unit\test_battery_physics.py",
        "tests\unit\test_control_system.py",
        "tests\integration\test_api_integration.py",
        "tests\e2e\test_dashboard_e2e.py"
    )
    
    foreach ($testFile in $testFiles) {
        if (Test-Path $testFile) {
            Write-Success $testFile
        } else {
            Write-Warning "$testFile missing"
        }
    }
    
    return $true
}

function Invoke-UnitTests {
    Write-SubHeader "Running Unit Tests"
    return Invoke-TestCommand -Command @("python", "-m", "pytest", "tests/unit/", "-v", "--tb=short", "-m", "not slow") -Description "Unit Tests"
}

function Invoke-IntegrationTests {
    Write-SubHeader "Running Integration Tests"
    return Invoke-TestCommand -Command @("python", "-m", "pytest", "tests/integration/", "-v", "--tb=short", "--timeout=60") -Description "Integration Tests"
}

function Invoke-E2ETests {
    Write-SubHeader "Running E2E Tests"
    return Invoke-TestCommand -Command @("python", "-m", "pytest", "tests/e2e/", "-v", "--tb=short", "--timeout=120") -Description "E2E Tests" -TimeoutSeconds 600
}

function Invoke-PerformanceTests {
    Write-SubHeader "Running Performance Tests"
    return Invoke-TestCommand -Command @("python", "-m", "pytest", "tests/performance/", "-v", "--tb=short", "--timeout=30") -Description "Performance Tests"
}

function Invoke-CoverageTests {
    Write-SubHeader "Running Tests with Coverage"
    $success = Invoke-TestCommand -Command @("python", "-m", "pytest", "tests/", "--cov=energy_ml", "--cov-report=html", "--cov-report=term", "--cov-report=xml", "-v") -Description "Coverage Tests" -TimeoutSeconds 600
    
    if ($success) {
        Write-Host "`n📈 Coverage Report Generated:" -ForegroundColor Green
        Write-Host "  - HTML: htmlcov/index.html" -ForegroundColor Green
        Write-Host "  - XML: coverage.xml" -ForegroundColor Green
    }
    
    return $success
}

# Main execution
$startTime = Get-Date

Write-Header "Smart Energy AI - Comprehensive Test Suite"

# Install dependencies if requested
if ($InstallDeps) {
    if (-not (Install-TestDependencies)) {
        Write-Error "Failed to install dependencies"
        exit 1
    }
}

# Check environment unless skipped
if (-not $SkipEnvCheck) {
    if (-not (Test-Environment)) {
        Write-Error "Environment check failed"
        exit 1
    }
}

# Run requested tests
$results = @{}

switch ($TestType) {
    "unit" {
        $results['unit'] = Invoke-UnitTests
    }
    "integration" {
        $results['integration'] = Invoke-IntegrationTests
    }
    "e2e" {
        $results['e2e'] = Invoke-E2ETests
    }
    "performance" {
        $results['performance'] = Invoke-PerformanceTests
    }
    "all" {
        Write-Host "`n🚀 Running Full Test Suite" -ForegroundColor Cyan
        $results['unit'] = Invoke-UnitTests
        $results['integration'] = Invoke-IntegrationTests 
        $results['e2e'] = Invoke-E2ETests
        $results['performance'] = Invoke-PerformanceTests
    }
}

# Run coverage if requested
if ($Coverage) {
    $results['coverage'] = Invoke-CoverageTests
}

# Summary
$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

Write-Host "`n$("=" * 50)" -ForegroundColor Cyan
Write-Host "📊 TEST SUITE SUMMARY" -ForegroundColor Cyan  
Write-Host ("=" * 50) -ForegroundColor Cyan

$totalTests = $results.Count
$passedTests = ($results.Values | Where-Object { $_ }).Count

foreach ($testType in $results.Keys) {
    $success = $results[$testType]
    $status = if ($success) { "✅ PASSED" } else { "❌ FAILED" }
    Write-Host ("{0,-15} {1}" -f $testType.ToUpper(), $status) -ForegroundColor $(if ($success) { "Green" } else { "Red" })
}

Write-Host "`nTotal: $passedTests/$totalTests test suites passed" -ForegroundColor Cyan
Write-Host "Duration: $([math]::Round($duration, 1)) seconds" -ForegroundColor Cyan

# Exit with appropriate code
if ($passedTests -eq $totalTests) {
    Write-Host "`n🎉 ALL TESTS PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n⚠️  $($totalTests - $passedTests) test suite(s) failed" -ForegroundColor Yellow
    exit 1
}