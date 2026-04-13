param()

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"
$ngrokExe = Join-Path $repoRoot "ngrok.exe"
$logRoot = Join-Path $env:TEMP "meeting-analyzer-remote-test"

function Start-DetachedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Name
    )

    New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
    $stdout = Join-Path $logRoot "$Name.out.log"
    $stderr = Join-Path $logRoot "$Name.err.log"

    return Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru
}

function Wait-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Timed out waiting for $Url"
}

function Get-NgrokPublicUrl {
    param(
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod "http://127.0.0.1:4040/api/tunnels"
            $tunnel = $response.tunnels | Where-Object { $_.public_url -match '^https://' } | Select-Object -First 1
            if ($null -ne $tunnel) {
                return $tunnel.public_url
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "ngrok did not publish a public URL"
}

function Test-DockerEngine {
    try {
        & docker info *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Start-DockerDesktopIfAvailable {
    $candidates = @(
        if ($env:ProgramFiles) {
            Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
        }
        if (${env:ProgramFiles(x86)}) {
            Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\Docker Desktop.exe"
        }
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($candidate in $candidates) {
        Start-Process -FilePath $candidate | Out-Null
        return $true
    }

    return $false
}

function Wait-DockerEngine {
    param(
        [int]$TimeoutSeconds = 180
    )

    if (Test-DockerEngine) {
        return
    }

    $startedDesktop = Start-DockerDesktopIfAvailable
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        if (Test-DockerEngine) {
            return
        }
        Start-Sleep -Seconds 2
    }

    if ($startedDesktop) {
        throw "Docker Desktop opened but the engine was not ready in time. Wait until Docker says it is running, then rerun the script."
    }

    throw "Docker is not available. Start Docker Desktop, wait until the engine is running, then rerun the script."
}

if (-not (Test-Path $ngrokExe)) {
    throw "ngrok.exe not found at $ngrokExe"
}

if (Get-Process ngrok -ErrorAction SilentlyContinue) {
    throw "An ngrok process is already running. Stop it first and rerun this script."
}

Wait-DockerEngine

if (-not $env:OPENVIDU_SECRET) {
    $env:OPENVIDU_SECRET = "MY_SECRET"
}

if (-not $env:SSL_VERIFY) {
    $env:SSL_VERIFY = "false"
}

$frontendProc = $null
$ngrokProc = $null
$frontendPublicUrl = $null
$success = $false

try {
    Write-Host "Starting frontend dev server..."
    $frontendProc = Start-DetachedProcess `
        -FilePath "npm.cmd" `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort") `
        -WorkingDirectory $frontendDir `
        -Name "frontend"

    Wait-HttpEndpoint -Url "http://127.0.0.1:5173" -TimeoutSeconds 60

    Write-Host "Starting ngrok tunnel..."
    $ngrokProc = Start-DetachedProcess `
        -FilePath $ngrokExe `
        -ArgumentList @("http", "5173") `
        -WorkingDirectory $repoRoot `
        -Name "ngrok-frontend"

    $frontendPublicUrl = Get-NgrokPublicUrl -TimeoutSeconds 60
    $frontendHost = ([Uri]$frontendPublicUrl).Host
    $env:DOMAIN_OR_PUBLIC_IP = $frontendHost
    $env:HTTPS_PORT = "443"
    $env:FORCE_PLAIN_HTTP = "false"
    $env:OPENVIDU_URL = "http://openvidu:$($env:HTTPS_PORT)"

    Write-Host "Starting backend and OpenVidu..."
    Push-Location $repoRoot
    try {
        $dockerProc = Start-Process `
            -FilePath "docker" `
            -ArgumentList @("compose", "up", "-d", "redis", "openvidu", "backend") `
            -WorkingDirectory $repoRoot `
            -PassThru `
            -Wait `
            -NoNewWindow `
            -RedirectStandardOutput (Join-Path $logRoot "docker.out.log") `
            -RedirectStandardError (Join-Path $logRoot "docker.err.log")
        if ($dockerProc.ExitCode -ne 0) {
            throw "docker compose up failed with exit code $($dockerProc.ExitCode)"
        }
    } finally {
        Pop-Location
    }

    Wait-HttpEndpoint -Url "http://127.0.0.1:8000/api/health" -TimeoutSeconds 120
    $success = $true

    Write-Host ""
    Write-Host "Share this URL with your friends:"
    Write-Host $frontendPublicUrl
    Write-Host ""
    Write-Host "OpenVidu public path:"
    Write-Host "$frontendPublicUrl/openvidu"
    Write-Host ""
    Write-Host "Logs:"
    Write-Host "  $logRoot"
} finally {
    if (-not $success) {
        if ($ngrokProc) {
            Stop-Process -Id $ngrokProc.Id -Force -ErrorAction SilentlyContinue
        }
        if ($frontendProc) {
            Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
