<#
===============================================================================
  Set-WindowsKiosk.ps1 — Configura o KIOSK NATIVO do Windows (Assigned Access)
===============================================================================
  Trava uma conta local no Microsoft Edge em modo kiosk, apontando para o app
  rodando localmente (http://localhost:<porta>). E o recurso oficial de
  "Quiosque" do Windows — sem watchdog, o proprio sistema impede sair do app.

  REQUISITOS:
    - Windows 10/11 PRO, ENTERPRISE ou EDUCATION (NAO funciona no Home)
    - Microsoft Edge instalado (vem com o Windows)
    - App ja instalado: rode antes  Install-Kiosk.ps1  (Python + deps + venv)

  O QUE ESTE SCRIPT FAZ:
    1. Cria uma conta local dedicada e sem senha para o quiosque
    2. Cria a Tarefa Agendada "AuraServer" (SYSTEM, ao iniciar o PC) que sobe
       o servidor Streamlit via Start-Server.ps1
    3. Remove a tarefa "AuraKiosk" (navegador-watchdog) se existir, para nao
       conflitar com o kiosk nativo
    4. Aplica a configuracao Assigned Access (Edge kiosk -> localhost) via WMI
       bridge (MDM_AssignedAccess)

  USO (PowerShell como Administrador):
    .\Set-WindowsKiosk.ps1
    .\Set-WindowsKiosk.ps1 -Port 8501 -KioskUser "QuiosqueAura"
    .\Set-WindowsKiosk.ps1 -Url "http://localhost:8501/?view=cliente"
===============================================================================
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "C:\AuraKiosk",
    [int]   $Port       = 8501,
    [string]$KioskUser  = "QuiosqueAura",
    [string]$Url        = "",
    [switch]$UseSplash   # usa loading.html antes do app (file://). Padrao: URL direta.
)

$ErrorActionPreference = "Stop"
function Write-Step($m){ Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Write-Ok($m){ Write-Host "  OK: $m" -ForegroundColor Green }
function Write-Warn($m){ Write-Host "  ! $m" -ForegroundColor Yellow }

if (-not $Url) { $Url = "http://localhost:$Port/?view=cliente" }

# ---------------------------------------------------------------------------
# 0. Pre-checagens: admin + edicao do Windows + Edge
# ---------------------------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Execute como ADMINISTRADOR." -ForegroundColor Red; exit 1
}

$edition = (Get-CimInstance Win32_OperatingSystem).Caption
if ($edition -match "Home") {
    Write-Host "Edicao detectada: $edition" -ForegroundColor Red
    Write-Host "O kiosk nativo (Assigned Access) NAO funciona no Windows Home." -ForegroundColor Red
    Write-Host "Use o kiosk de navegador: kiosk\Start-Kiosk.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Ok "Edicao compativel: $edition"

$edge = @(
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { Write-Host "Microsoft Edge nao encontrado." -ForegroundColor Red; exit 1 }
Write-Ok "Edge: $edge"

$startServer = Join-Path $InstallDir "kiosk\Start-Server.ps1"
if (-not (Test-Path $startServer)) {
    Write-Host "Nao achei $startServer. Rode Install-Kiosk.ps1 primeiro." -ForegroundColor Red; exit 1
}

# ---------------------------------------------------------------------------
# 1. Conta local dedicada do quiosque (sem senha, padrao/limitada)
# ---------------------------------------------------------------------------
Write-Step "Conta de quiosque '$KioskUser'"
$u = Get-LocalUser -Name $KioskUser -ErrorAction SilentlyContinue
if (-not $u) {
    New-LocalUser -Name $KioskUser -NoPassword -AccountNeverExpires `
        -FullName "Quiosque Aura" -Description "Conta dedicada do quiosque" | Out-Null
    Set-LocalUser  -Name $KioskUser -PasswordNeverExpires $true
    Add-LocalGroupMember -Group "Users" -Member $KioskUser -ErrorAction SilentlyContinue
    Write-Ok "Conta criada."
} else {
    Write-Ok "Conta ja existe."
}

# ---------------------------------------------------------------------------
# 2. Tarefa "AuraServer" — sobe o servidor no boot, como SYSTEM
# ---------------------------------------------------------------------------
Write-Step "Tarefa de inicializacao do servidor (boot, SYSTEM)"
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startServer`" -Port $Port"
$trigger = New-ScheduledTaskTrigger -AtStartup
$princ   = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$set     = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName "AuraServer" -Action $action -Trigger $trigger `
    -Principal $princ -Settings $set -Force | Out-Null
Write-Ok "Tarefa 'AuraServer' registrada (inicia o servidor no boot)."

# Inicia o servidor agora tambem, para o teste imediato funcionar
Start-ScheduledTask -TaskName "AuraServer" -ErrorAction SilentlyContinue

# Remove a tarefa do kiosk de navegador (se foi instalada antes) p/ nao conflitar
Unregister-ScheduledTask -TaskName "AuraKiosk" -Confirm:$false -ErrorAction SilentlyContinue

# ---------------------------------------------------------------------------
# 3. Otimizacoes nativas: politicas do Edge + energia + sem bloqueio de tela
# ---------------------------------------------------------------------------
Write-Step "Aplicando otimizacoes (Edge, energia, tela)"

# 3a. Politicas do Edge (maquina toda) — remove autofill/senhas/sync/nags,
#     que sao justamente os popups que atrapalham num quiosque.
$pol = "HKLM:\SOFTWARE\Policies\Microsoft\Edge"
New-Item -Path $pol -Force | Out-Null
$edgePolicies = @{
    HideFirstRunExperience               = 1
    AutofillAddressEnabled               = 0
    AutofillCreditCardEnabled            = 0
    PasswordManagerEnabled               = 0
    BrowserSignin                        = 0   # 0 = sign-in desabilitado
    SyncDisabled                         = 1
    TranslateEnabled                     = 0
    DefaultBrowserSettingEnabled         = 0
    ShowRecommendationsEnabled           = 0
    EdgeShoppingAssistantEnabled         = 0
    HubsSidebarEnabled                   = 0
    BackgroundModeEnabled                = 0
    StartupBoostEnabled                  = 0
    PromotionalTabsEnabled               = 0
    EdgeCollectionsEnabled               = 0
    PersonalizationReportingEnabled      = 0
    SpotlightExperiencesAndRecommendationsEnabled = 0
    ConfigureDoNotTrack                  = 1
    AutoImportAtFirstRun                 = 4   # 4 = nao importar nada
}
foreach ($k in $edgePolicies.Keys) {
    New-ItemProperty -Path $pol -Name $k -Value $edgePolicies[$k] -PropertyType DWord -Force | Out-Null
}
Write-Ok "Politicas do Edge aplicadas (sem autofill/senha/sync/nags)."

# 3b. Energia: tela e PC NUNCA dormem (AC e bateria).
foreach ($p in @("monitor-timeout-ac","monitor-timeout-dc",
                 "standby-timeout-ac","standby-timeout-dc",
                 "hibernate-timeout-ac","hibernate-timeout-dc",
                 "disk-timeout-ac","disk-timeout-dc")) {
    & powercfg /change $p 0 2>$null
}
Write-Ok "Energia configurada (sem suspensao/desligar tela)."

# 3c. Sem tela de bloqueio (vai direto pro app).
$perso = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization"
New-Item -Path $perso -Force | Out-Null
New-ItemProperty -Path $perso -Name "NoLockScreen" -Value 1 -PropertyType DWord -Force | Out-Null
Write-Ok "Tela de bloqueio desativada."

# ---------------------------------------------------------------------------
# 4. XML do Assigned Access (Edge kiosk -> tela de carregamento -> app)
# ---------------------------------------------------------------------------
Write-Step "Aplicando configuracao de quiosque (Assigned Access)"
$profileId = [guid]::NewGuid().ToString("B")  # {xxxx-...}

# Por padrao abre o app direto (mais robusto no kiosk nativo). Com -UseSplash,
# abre a tela de carregamento (file://) que redireciona quando o app sobe.
# Como o servidor inicia no BOOT (antes do logon), ele costuma ja estar pronto.
$loadingPath = Join-Path $InstallDir "kiosk\loading.html"
$startUrl = if ($UseSplash -and (Test-Path $loadingPath)) {
    "file:///" + ($loadingPath -replace '\\','/') + "#" + $Url
} else { $Url }

$edgeArgs = "--kiosk `"$startUrl`" --edge-kiosk-type=fullscreen --no-first-run " +
            "--kiosk-idle-timeout-minutes=0 --disable-sync --disable-features=Translate,TranslateUI " +
            "--no-default-browser-check --disable-background-networking --hide-scrollbars"

# Escapa para uso seguro em atributos XML (& < > " ')
$edgeAttr = [System.Security.SecurityElement]::Escape($edgeArgs)
$pathAttr = [System.Security.SecurityElement]::Escape($edge)

# Schema v5 (2021) permite KioskModeApp com app classico (Win32 Edge)
$xml = @"
<?xml version="1.0" encoding="utf-8" ?>
<AssignedAccessConfiguration
  xmlns="http://schemas.microsoft.com/AssignedAccess/2017/config"
  xmlns:v5="http://schemas.microsoft.com/AssignedAccess/2021/config">
  <Profiles>
    <Profile Id="$profileId">
      <KioskModeApp v5:ClassicAppPath="$pathAttr"
                    v5:ClassicAppArguments="$edgeAttr" />
    </Profile>
  </Profiles>
  <Configs>
    <Config>
      <Account>$KioskUser</Account>
      <DefaultProfile Id="$profileId" />
    </Config>
  </Configs>
</AssignedAccessConfiguration>
"@

# A ponte WMI (MDM_AssignedAccess) SO existe na conta SYSTEM. Como admin comum
# o Get-CimInstance volta nulo. Por isso aplicamos via uma tarefa agendada
# de uso unico que roda como SYSTEM.
$work = Join-Path $env:ProgramData "AuraKiosk"
New-Item -ItemType Directory -Path $work -Force | Out-Null
$xmlPath    = Join-Path $work "assignedaccess.xml"
$applyPath  = Join-Path $work "apply-assignedaccess.ps1"
$resultPath = Join-Path $work "apply-result.txt"
Remove-Item $resultPath -ErrorAction SilentlyContinue
Set-Content -Path $xmlPath -Value $xml -Encoding UTF8

# Script que roda como SYSTEM e aplica a configuracao.
$applyBody = @'
param([string]$XmlPath,[string]$ResultPath)
try {
    $xml = Get-Content -Raw -Path $XmlPath
    $obj = Get-CimInstance -Namespace "root\cimv2\mdm\dmmap" -ClassName "MDM_AssignedAccess"
    if (-not $obj) { throw "MDM_AssignedAccess indisponivel (edicao do Windows nao suporta?)" }
    $obj.Configuration = [System.Net.WebUtility]::HtmlEncode($xml)
    Set-CimInstance -CimInstance $obj -ErrorAction Stop
    "OK" | Set-Content -Path $ResultPath -Encoding UTF8
} catch {
    "ERRO: $($_.Exception.Message)" | Set-Content -Path $ResultPath -Encoding UTF8
}
'@
Set-Content -Path $applyPath -Value $applyBody -Encoding UTF8

$act  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$applyPath`" -XmlPath `"$xmlPath`" -ResultPath `"$resultPath`""
$prin = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "AuraApplyKiosk" -Action $act -Principal $prin -Force | Out-Null
Start-ScheduledTask -TaskName "AuraApplyKiosk"

# Espera o resultado (ate ~30s)
$result = $null
foreach ($i in 1..30) {
    Start-Sleep -Seconds 1
    if (Test-Path $resultPath) { $result = (Get-Content -Raw $resultPath).Trim(); break }
}
Unregister-ScheduledTask -TaskName "AuraApplyKiosk" -Confirm:$false -ErrorAction SilentlyContinue

if ($result -eq "OK") {
    Write-Ok "Quiosque nativo aplicado para a conta '$KioskUser'."
} else {
    Write-Host "Falha ao aplicar Assigned Access: $result" -ForegroundColor Red
    Write-Warn "Alternativa manual (funciona sempre):"
    Write-Warn "Configuracoes > Contas > Outros usuarios > Configurar um quiosque >"
    Write-Warn "conta '$KioskUser' > Microsoft Edge > URL: $Url"
    exit 1
}

# ---------------------------------------------------------------------------
# Final
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "########################################################" -ForegroundColor Green
Write-Host "#   QUIOSQUE NATIVO CONFIGURADO                        #" -ForegroundColor Green
Write-Host "########################################################" -ForegroundColor Green
Write-Host ""
Write-Host "Conta de quiosque : $KioskUser (sem senha)"      -ForegroundColor Gray
Write-Host "URL do app        : $Url"                         -ForegroundColor Gray
Write-Host "Servidor          : Tarefa 'AuraServer' (boot)"   -ForegroundColor Gray
Write-Host ""
Write-Host "Faca logoff e entre como '$KioskUser' (ou reinicie):" -ForegroundColor Cyan
Write-Host "o Windows abre o Edge travado no app automaticamente." -ForegroundColor Cyan
Write-Host ""
Write-Host "Para REMOVER o quiosque depois: kiosk\Remove-WindowsKiosk.ps1" -ForegroundColor Yellow
