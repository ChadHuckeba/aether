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
    $proc = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' AND CommandLine LIKE '%server.py%'"
    return $proc.ProcessId
}

switch ($Action) {
    "start" {
        $APID = Get-AetherPID
        if ($APID) {
            Write-Host "Aether is already running (PID: $APID)" -ForegroundColor Cyan
        } else {
            Write-Host "Starting Aether Context Engine..." -ForegroundColor Yellow
            Start-Process uv -ArgumentList "run python server.py" -WindowStyle Hidden
            Start-Sleep -Seconds 2
            Write-Host "Aether is live at http://localhost:$Port" -ForegroundColor Green
        }
        # Optional: Open the dashboard automatically
        # Start-Process "http://localhost:$Port"
    }

    "stop" {
        $APID = Get-AetherPID
        if ($APID) {
            Write-Host "Stopping Aether (PID: $APID)..." -ForegroundColor Yellow
            Stop-Process -Id $APID -Force
            Write-Host "Aether session ended. Workstation clean." -ForegroundColor Green
        } else {
            Write-Host "Aether is not running." -ForegroundColor Gray
        }
    }

    "status" {
        $APID = Get-AetherPID
        if ($APID) {
            $mem = (Get-Process -Id $APID).WorkingSet / 1MB
            Write-Host "Aether Status: ACTIVE" -ForegroundColor Green
            Write-Host "PID: $APID"
            Write-Host "RAM: $([Math]::Round($mem, 2)) MB"
        } else {
            Write-Host "Aether Status: INACTIVE" -ForegroundColor Red
        }
    }
}
