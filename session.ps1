# SurvivalStack | Aether Session Manager
# Usage: ./session.ps1 [start|stop|status]

param (
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "status")]
    $Action = "start"
)

$Port = 8000
$ProcessName = "python" # We filter by command line to be precise

function Get-AetherPID {
    $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' AND CommandLine LIKE '%server.py%'"
    if ($procs) {
        if ($procs.Count -gt 1) {
            return $procs[0].ProcessId
        }
        return $procs.ProcessId
    }
    return $null
}

switch ($Action) {
    "start" {
        $APID = Get-AetherPID
        if ($APID) {
            Write-Host "Aether is already running (PID: $APID)" -ForegroundColor Cyan
        } else {
            Write-Host "Starting Aether Context Engine..." -ForegroundColor Yellow
            # Use 'uv run' to ensure the correct venv is used
            Start-Process uv -ArgumentList "run python server.py" -WindowStyle Hidden
            Start-Sleep -Seconds 2
            $NewPID = Get-AetherPID
            if ($NewPID) {
                Write-Host "Aether is live at http://localhost:$Port (PID: $NewPID)" -ForegroundColor Green
            } else {
                Write-Host "Aether started but PID not found immediately. Check http://localhost:$Port" -ForegroundColor Gray
            }
        }
    }

    "stop" {
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' AND CommandLine LIKE '%server.py%'"
        if ($procs) {
            Write-Host "Stopping Aether process(es)..." -ForegroundColor Yellow
            foreach ($p in $procs) {
                Stop-Process -Id $p.ProcessId -Force
            }
            Write-Host "Aether session ended. Workstation clean." -ForegroundColor Green
        } else {
            Write-Host "Aether is not running." -ForegroundColor Gray
        }
    }

    "status" {
        $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' AND CommandLine LIKE '%server.py%'"
        if ($procs) {
            $totalMem = 0
            foreach ($p in $procs) {
                $totalMem += (Get-Process -Id $p.ProcessId).WorkingSet
            }
            Write-Host "Aether Status: ACTIVE" -ForegroundColor Green
            Write-Host "PIDs: $(($procs | ForEach-Object { $_.ProcessId }) -join ', ')"
            Write-Host "Total RAM: $([Math]::Round($totalMem / 1MB, 2)) MB"
        } else {
            Write-Host "Aether Status: INACTIVE" -ForegroundColor Red
        }
    }
}
