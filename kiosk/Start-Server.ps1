<#
===============================================================================
  Start-Server.ps1 — Sobe APENAS o servidor Streamlit (sem navegador)
===============================================================================
  Usado pelo kiosk NATIVO do Windows (Assigned Access): quem mostra a tela e o
  Microsoft Edge em modo kiosk; aqui so garantimos o servidor no ar.

  Roda em PRIMEIRO PLANO (bloqueante) de proposito: assim a Tarefa Agendada
  "AuraServer" (gatilho: ao iniciar o sistema, conta SYSTEM) mantem o processo
  vivo enquanto o PC estiver ligado.

  USO:
    powershell -ExecutionPolicy Bypass -File Start-Server.ps1 [-Port 8501]
===============================================================================
#>
[CmdletBinding()]
param(
    [int]   $Port    = 8501,
    [string]$AppFile = "app.py"
)

$ErrorActionPreference = "Stop"

# Raiz do projeto = pasta-pai da pasta deste script (kiosk\..)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root      = Split-Path -Parent $ScriptDir
Set-Location $Root

$python = Join-Path $Root "venv_win\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

# Se o cloudflared.exe estiver junto do app, o portal do cliente fica online
# automaticamente (o app usa CLOUDFLARED_BIN para abrir o tunel publico).
$cloudflared = Join-Path $Root "cloudflared.exe"
if (Test-Path $cloudflared) { $env:CLOUDFLARED_BIN = $cloudflared }

# --- Experiencia nativa: esconde "cara de web" e reduz consumo ---------------
# Barra/menu do Streamlit em modo minimo (sem botoes de deploy/rerun/etc).
$env:STREAMLIT_CLIENT_TOOLBAR_MODE        = "minimal"
$env:STREAMLIT_CLIENT_SHOW_ERROR_DETAILS  = "false"
# Sem file-watcher (menos CPU; o app nao muda em producao).
$env:STREAMLIT_SERVER_FILE_WATCHER_TYPE   = "none"
$env:STREAMLIT_SERVER_RUN_ON_SAVE         = "false"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
$env:STREAMLIT_GLOBAL_DEVELOPMENT_MODE    = "false"

# Bloqueante: mantem a tarefa viva. Aceita conexoes locais do Edge em localhost.
& $python -m streamlit run $AppFile `
    --server.port $Port `
    --server.address 0.0.0.0 `
    --server.headless true `
    --browser.gatherUsageStats false
