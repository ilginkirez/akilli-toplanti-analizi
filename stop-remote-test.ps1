param()

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot

function Get-RemoteTestProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -match 'ngrok\.exe' -or
        $_.CommandLine -match 'npm\.cmd.*run dev' -or
        $_.CommandLine -match 'vite' -and $_.CommandLine -match '5173' -or
        $_.CommandLine -match '127\.0\.0\.1:5173' -or
        $_.CommandLine -match [regex]::Escape($repoRoot)
    } | Where-Object {
        $_.ProcessId -ne $PID
    }
}

$matches = @(Get-RemoteTestProcesses)

if ($matches.Count -eq 0) {
    Write-Host "No remote-test frontend/ngrok processes found."
    exit 0
}

Write-Host "Stopping these processes:"
$matches | Select-Object ProcessId, Name, CommandLine | Format-Table -AutoSize | Out-Host

foreach ($proc in $matches) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
    } catch {
        Write-Warning "Could not stop PID $($proc.ProcessId) ($($proc.Name)): $($_.Exception.Message)"
    }
}

Write-Host "Remote-test processes stopped."
