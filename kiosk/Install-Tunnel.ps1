<#
===============================================================================
  Install-Tunnel.ps1 — Publica o PORTAL DO CLIENTE na internet (Cloudflare)
===============================================================================
  Baixa o cloudflared.exe e o coloca junto do app. A partir dai, ao abrir o
  dashboard, o proprio app sobe um tunel publico (https://...trycloudflare.com)
  e passa a gerar os links dos clientes com esse endereco — sem config manual.

  USO (PowerShell como Administrador):
    .\Install-Tunnel.ps1
    .\Install-Tunnel.ps1 -InstallDir "C:\AuraKiosk"
===============================================================================
#>
[CmdletBinding()]
param([string]$InstallDir = "C:\AuraKiosk")

$ErrorActionPreference = "Stop"
function Write-Step($m){ Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Write-Ok($m){ Write-Host "  OK: $m" -ForegroundColor Green }
function Write-Warn($m){ Write-Host "  ! $m" -ForegroundColor Yellow }

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Host "Execute como ADMINISTRADOR." -ForegroundColor Red; exit 1 }

if (-not (Test-Path "$InstallDir\requirements.txt")) {
    Write-Host "App nao encontrado em $InstallDir. Rode Install-Kiosk.ps1 antes." -ForegroundColor Red
    exit 1
}

# 1. Baixar o cloudflared.exe oficial (Windows 64 bits)
Write-Step "Baixando cloudflared (Cloudflare Tunnel)"
$dest = Join-Path $InstallDir "cloudflared.exe"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
Invoke-WebRequest $url -OutFile $dest
Write-Ok "cloudflared.exe salvo em $dest"

# 2. Tornar visivel tambem pelo PATH/variavel (para o servidor que roda como SYSTEM)
[Environment]::SetEnvironmentVariable("CLOUDFLARED_BIN", $dest, "Machine")
$env:CLOUDFLARED_BIN = $dest
Write-Ok "Variavel CLOUDFLARED_BIN definida."

# 3. Religar o servidor (tarefa AuraServer) para ele detectar o cloudflared
Write-Step "Reiniciando o servidor"
$task = Get-ScheduledTask -TaskName "AuraServer" -ErrorAction SilentlyContinue
if ($task) {
    Stop-ScheduledTask  -TaskName "AuraServer" -ErrorAction SilentlyContinue
    # Encerra qualquer streamlit/python do app que ainda esteja vivo
    Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='streamlit.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'streamlit' -or $_.CommandLine -match 'app\.py' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
    Start-ScheduledTask -TaskName "AuraServer"
    Write-Ok "Servidor reiniciado (tarefa AuraServer)."
} else {
    Write-Warn "Tarefa AuraServer nao encontrada. Rode Set-WindowsKiosk.ps1 antes,"
    Write-Warn "ou inicie o servidor manualmente com kiosk\Start-Server.ps1."
}

# Final
Write-Host ""
Write-Host "########################################################" -ForegroundColor Green
Write-Host "#   PORTAL DO CLIENTE: PUBLICACAO ATIVADA             #" -ForegroundColor Green
Write-Host "########################################################" -ForegroundColor Green
Write-Host ""
Write-Host "Agora abra o DASHBOARD (http://localhost:8501) e aguarde alguns"  -ForegroundColor Cyan
Write-Host "segundos: o app coloca o Portal do Cliente online automaticamente"  -ForegroundColor Cyan
Write-Host "e os links dos clientes passam a usar o endereco publico."          -ForegroundColor Cyan
Write-Host ""
Write-Warn "Tunel gratuito (trycloudflare): o endereco MUDA a cada reinicio do"
Write-Warn "servidor. Para um link FIXO, use um Cloudflare Tunnel nomeado (conta"
Write-Warn "Cloudflare + dominio) ou ngrok com dominio reservado — posso te ajudar."
