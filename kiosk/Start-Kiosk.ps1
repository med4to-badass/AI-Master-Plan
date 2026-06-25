<#
===============================================================================
  Start-Kiosk.ps1 — Inicia o app e abre o navegador em modo QUIOSQUE
===============================================================================
  O que faz:
    1. Sobe o servidor Streamlit (headless) usando o venv local
    2. Espera o app ficar saudavel (/_stcore/health)
    3. Abre Edge ou Chrome em --kiosk (tela cheia, sem barras)
    4. Vigia o navegador: se fechar, reabre (impede "escapar" do quiosque)
    5. Atalho de saida: Ctrl+Alt+K encerra tudo de forma limpa

  USO:
    powershell -ExecutionPolicy Bypass -File Start-Kiosk.ps1 [-Port 8501] [-NoRelaunch]
===============================================================================
#>
[CmdletBinding()]
param(
    [int]   $Port = 8501,
    [string]$AppFile = "app.py",
    [switch]$NoRelaunch   # se presente, NAO reabre o navegador ao fechar
)

$ErrorActionPreference = "Stop"

# Raiz do projeto = pasta-pai da pasta deste script (kiosk\..)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root      = Split-Path -Parent $ScriptDir
Set-Location $Root

$Url      = "http://localhost:$Port/?view=cliente"
$HealthUrl= "http://127.0.0.1:$Port/_stcore/health"
$Streamlit= Join-Path $Root "venv_win\Scripts\streamlit.exe"
$Profile  = Join-Path $env:LOCALAPPDATA "AuraKiosk\browser-profile"
New-Item -ItemType Directory -Path $Profile -Force | Out-Null

# Tela de carregamento -> redireciona para o app quando ficar pronto.
$LoadingPath = Join-Path $ScriptDir "loading.html"
$StartUrl    = if (Test-Path $LoadingPath) {
    "file:///" + ($LoadingPath -replace '\\','/') + "#" + $Url
} else { $Url }

# Experiencia nativa: esconde barra/menu do Streamlit e reduz consumo.
$env:STREAMLIT_CLIENT_TOOLBAR_MODE        = "minimal"
$env:STREAMLIT_CLIENT_SHOW_ERROR_DETAILS  = "false"
$env:STREAMLIT_SERVER_FILE_WATCHER_TYPE   = "none"
$env:STREAMLIT_SERVER_RUN_ON_SAVE         = "false"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

function Log($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) -ForegroundColor Cyan }

# ---------------------------------------------------------------------------
# 1. Subir o Streamlit (se ainda nao estiver no ar)
# ---------------------------------------------------------------------------
function Test-Health {
    try { (Invoke-WebRequest $HealthUrl -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 }
    catch { $false }
}

$stProc = $null
if (Test-Health) {
    Log "Streamlit ja esta no ar na porta $Port."
} else {
    if (-not (Test-Path $Streamlit)) {
        # fallback: usar python -m streamlit do venv (ou global)
        $py = Join-Path $Root "venv_win\Scripts\python.exe"
        if (-not (Test-Path $py)) { $py = "python" }
        Log "streamlit.exe nao encontrado, usando '$py -m streamlit'."
        $stProc = Start-Process -FilePath $py -PassThru -WindowStyle Hidden `
            -ArgumentList "-m","streamlit","run",$AppFile,
                          "--server.port",$Port,"--server.address","0.0.0.0",
                          "--server.headless","true"
    } else {
        Log "Iniciando Streamlit..."
        $stProc = Start-Process -FilePath $Streamlit -PassThru -WindowStyle Hidden `
            -ArgumentList "run",$AppFile,
                          "--server.port",$Port,"--server.address","0.0.0.0",
                          "--server.headless","true"
    }

    Log "Aguardando o app ficar pronto..."
    $ok = $false
    foreach ($i in 1..60) {
        if (Test-Health) { $ok = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ok) { Log "ERRO: o app nao respondeu a tempo."; exit 1 }
    Log "App pronto."
}

# ---------------------------------------------------------------------------
# 2. Localizar o navegador (Edge primeiro, depois Chrome)
# ---------------------------------------------------------------------------
function Find-Browser {
    $candidatos = @(
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
    )
    foreach ($c in $candidatos) { if (Test-Path $c) { return $c } }
    return $null
}
$Browser = Find-Browser
if (-not $Browser) { Log "ERRO: Edge/Chrome nao encontrado."; exit 1 }
Log "Navegador: $Browser"

$BrowserArgs = @(
    "--kiosk", $StartUrl,
    "--user-data-dir=$Profile",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-pinch",
    "--overscroll-history-navigation=0",
    "--disable-features=TranslateUI,Translate,AutofillServerCommunication",
    "--disable-session-crashed-bubble",
    "--disable-infobars",
    "--noerrdialogs",
    "--check-for-update-interval=31536000",
    "--password-store=basic",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-component-update",
    "--hide-scrollbars",
    "--start-fullscreen"
)

# ---------------------------------------------------------------------------
# 3. Hotkey de saida (Ctrl+Alt+K) -> cria um arquivo "flag" que encerra o loop
# ---------------------------------------------------------------------------
$ExitFlag = Join-Path $env:TEMP "aura_kiosk_exit.flag"
Remove-Item $ExitFlag -ErrorAction SilentlyContinue

$hotkeyJob = Start-Job -ScriptBlock {
    param($flag)
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Keys {
    [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int k);
}
"@
    while ($true) {
        $ctrl = ([Keys]::GetAsyncKeyState(0x11) -band 0x8000)
        $alt  = ([Keys]::GetAsyncKeyState(0x12) -band 0x8000)
        $k    = ([Keys]::GetAsyncKeyState(0x4B) -band 0x8000)   # tecla K
        if ($ctrl -and $alt -and $k) { New-Item -ItemType File -Path $flag -Force | Out-Null; break }
        Start-Sleep -Milliseconds 200
    }
} -ArgumentList $ExitFlag

# ---------------------------------------------------------------------------
# 4. Loop do quiosque: abrir navegador e reabrir se fechar
# ---------------------------------------------------------------------------
Log "Abrindo navegador em modo quiosque. Saida: Ctrl+Alt+K"
try {
    do {
        $b = Start-Process -FilePath $Browser -ArgumentList $BrowserArgs -PassThru
        while (-not $b.HasExited) {
            if (Test-Path $ExitFlag) { break }
            Start-Sleep -Milliseconds 500
        }
        if (Test-Path $ExitFlag) {
            if (-not $b.HasExited) { $b.CloseMainWindow() | Out-Null; Start-Sleep 1; $b | Stop-Process -Force -ErrorAction SilentlyContinue }
            break
        }
        if ($NoRelaunch) { break }
        Log "Navegador fechou. Reabrindo o quiosque..."
        Start-Sleep -Seconds 1
    } while ($true)
}
finally {
    # ---------------------------------------------------------------------
    # 5. Encerramento limpo
    # ---------------------------------------------------------------------
    Log "Encerrando quiosque..."
    Stop-Job   $hotkeyJob -ErrorAction SilentlyContinue
    Remove-Job $hotkeyJob -ErrorAction SilentlyContinue -Force
    Remove-Item $ExitFlag -ErrorAction SilentlyContinue
    if ($stProc -and -not $stProc.HasExited) {
        $stProc | Stop-Process -Force -ErrorAction SilentlyContinue
        Log "Streamlit encerrado."
    }
    Log "Quiosque finalizado."
}
