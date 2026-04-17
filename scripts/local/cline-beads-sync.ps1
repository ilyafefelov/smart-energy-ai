# Cline Kanban ↔ Beads Sync Script
# This script bridges Cline's task tracking with Beads (bd)
#
# Usage:
#   .\scripts\local\cline-beads-sync.ps1 -Action Export    # Export Beads tasks for Cline
#   .\scripts\local\cline-beads-sync.ps1 -Action Import    # Import tasks from Cline to Beads
#   .\scripts\local\cline-beads-sync.ps1 -Action Status    # Show current sync status

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Export', 'Import', 'Status', 'Create', 'Claim', 'Close')]
    [string]$Action,
    
    [string]$TaskId,
    [string]$Title,
    [string]$Description,
    [string]$Reason
)

$ErrorActionPreference = "Stop"
# Navigate to project root (scripts/local -> scripts -> project root)
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$SyncDir = Join-Path $ProjectRoot ".cline"
$BeadsExportPath = Join-Path $SyncDir "beads-tasks.json"
$ClineTasksPath = Join-Path $SyncDir "cline-tasks.json"

# Ensure sync directory exists
if (-not (Test-Path $SyncDir)) {
    New-Item -ItemType Directory -Path $SyncDir -Force | Out-Null
    Write-Host "Created sync directory: $SyncDir" -ForegroundColor Green
}

function Export-BeadsTasks {
    Write-Host "📥 Exporting Beads tasks for Cline..." -ForegroundColor Cyan
    
    Set-Location $ProjectRoot
    $beadsJson = bd ready --json 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to run 'bd ready --json'. Is Beads installed?"
        return $false
    }
    
    # Parse and transform for Cline compatibility
    $beadsTasks = $beadsJson | ConvertFrom-Json
    
    $clineFormat = $beadsTasks | ForEach-Object {
        @{
            id = $_.id
            title = $_.title
            description = $_.description
            status = if ($_.status -eq 'open') { 'todo' } elseif ($_.status -eq 'closed') { 'done' } else { 'in-progress' }
            priority = $_.priority
            issue_type = $_.issue_type
            owner = $_.owner
            created_at = $_.created_at
            updated_at = $_.updated_at
            labels = $_.labels
            beads_id = $_.id  # Keep reference to Beads ID
        }
    }
    
    $clineFormat | ConvertTo-Json -Depth 10 | Out-File -FilePath $BeadsExportPath -Encoding utf8
    
    Write-Host "✅ Exported $($clineFormat.Count) tasks to $BeadsExportPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Tasks by status:" -ForegroundColor Yellow
    $clineFormat | Group-Object status | ForEach-Object {
        Write-Host "   $($_.Name): $($_.Count)"
    }
    
    return $true
}

function Import-ClineTasks {
    Write-Host "📤 Importing tasks from Cline to Beads..." -ForegroundColor Cyan
    
    if (-not (Test-Path $ClineTasksPath)) {
        Write-Warning "No Cline tasks file found at $ClineTasksPath"
        Write-Host "Create tasks in Cline first, then export them."
        return $false
    }
    
    $clineTasks = Get-Content $ClineTasksPath -Raw | ConvertFrom-Json
    
    Set-Location $ProjectRoot
    
    $imported = 0
    $skipped = 0
    
    foreach ($task in $clineTasks) {
        # Skip if already has a beads_id (already synced)
        if ($task.beads_id) {
            $skipped++
            continue
        }
        
        # Create in Beads
        Write-Host "  Creating: $($task.title)" -ForegroundColor Gray
        
        $result = bd create $task.title --description $task.description --json 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            $newTask = $result | ConvertFrom-Json
            $task.beads_id = $newTask.id
            $imported++
            Write-Host "    ✅ Created Beads task: $($newTask.id)" -ForegroundColor Green
        } else {
            Write-Host "    ❌ Failed to create" -ForegroundColor Red
        }
    }
    
    # Save updated tasks with beads_id
    $clineTasks | ConvertTo-Json -Depth 10 | Out-File -FilePath $ClineTasksPath -Encoding utf8
    
    Write-Host ""
    Write-Host "✅ Imported $imported tasks, skipped $skipped (already synced)" -ForegroundColor Green
    
    return $true
}

function Show-SyncStatus {
    Write-Host "📊 Cline ↔ Beads Sync Status" -ForegroundColor Cyan
    Write-Host "=" * 50
    
    Set-Location $ProjectRoot
    
    # Get Beads tasks count
    $beadsCount = (bd ready --json 2>$null | ConvertFrom-Json).Count
    
    # Get Cline tasks count
    $clineCount = 0
    $syncedCount = 0
    if (Test-Path $ClineTasksPath) {
        $clineTasks = Get-Content $ClineTasksPath -Raw | ConvertFrom-Json
        $clineCount = $clineTasks.Count
        $syncedCount = ($clineTasks | Where-Object { $_.beads_id }).Count
    }
    
    Write-Host ""
    Write-Host "Beads tasks:     $beadsCount" -ForegroundColor Blue
    Write-Host "Cline tasks:     $clineCount" -ForegroundColor Green
    Write-Host "Synced tasks:    $syncedCount" -ForegroundColor Yellow
    Write-Host "Unsynced Cline:  $($clineCount - $syncedCount)" -ForegroundColor $(if ($clineCount - $syncedCount -gt 0) { 'Red' } else { 'Green' })
    
    Write-Host ""
    Write-Host "Sync files:" -ForegroundColor Cyan
    Write-Host "  Beads export: $BeadsExportPath" -ForegroundColor Gray
    Write-Host "  Cline tasks:  $ClineTasksPath" -ForegroundColor Gray
    
    if (Test-Path $BeadsExportPath) {
        $lastExport = (Get-Item $BeadsExportPath).LastWriteTime
        Write-Host "  Last export:   $lastExport" -ForegroundColor Gray
    }
}

function Create-BeadsTask {
    if (-not $Title) {
        Write-Error "Title is required for creating a task"
        return $false
    }
    
    Set-Location $ProjectRoot
    
    $cmd = "bd create `"$Title`""
    if ($Description) {
        $cmd += " --description `"$Description`""
    }
    $cmd += " --json"
    
    Write-Host "Creating Beads task: $Title" -ForegroundColor Cyan
    $result = Invoke-Expression $cmd
    
    if ($LASTEXITCODE -eq 0) {
        $task = $result | ConvertFrom-Json
        Write-Host "✅ Created task: $($task.id)" -ForegroundColor Green
        return $task.id
    } else {
        Write-Error "Failed to create task"
        return $false
    }
}

function Claim-BeadsTask {
    if (-not $TaskId) {
        Write-Error "TaskId is required for claiming a task"
        return $false
    }
    
    Set-Location $ProjectRoot
    
    Write-Host "Claiming task: $TaskId" -ForegroundColor Cyan
    $result = bd update $TaskId --claim --json 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        $task = $result | ConvertFrom-Json
        Write-Host "✅ Claimed task: $($task.id) (Owner: $($task.owner))" -ForegroundColor Green
        return $true
    } else {
        Write-Error "Failed to claim task"
        return $false
    }
}

function Close-BeadsTask {
    if (-not $TaskId) {
        Write-Error "TaskId is required for closing a task"
        return $false
    }
    
    if (-not $Reason) {
        $Reason = "Completed"
    }
    
    Set-Location $ProjectRoot
    
    Write-Host "Closing task: $TaskId" -ForegroundColor Cyan
    $result = bd close $TaskId --reason "`"$Reason`"" --json 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Closed task: $TaskId" -ForegroundColor Green
        return $true
    } else {
        Write-Error "Failed to close task"
        return $false
    }
}

# Main execution
switch ($Action) {
    'Export' { Export-BeadsTasks }
    'Import' { Import-ClineTasks }
    'Status' { Show-SyncStatus }
    'Create' { Create-BeadsTask }
    'Claim' { Claim-BeadsTask }
    'Close' { Close-BeadsTask }
}