<#
===============================================================================
  Install-Kiosk.ps1 — Instalador do Quiosque Windows (Aura Dashboard)
===============================================================================
  Prepara TUDO o que e necessario para rodar o app em modo quiosque:
    1. Garante Python 3.9+ (instala silenciosamente se faltar)
    2. Garante Git (usa download ZIP como fallback)
    3. Baixa/atualiza o projeto
    4. Cria o ambiente virtual e instala as dependencias
    5. Registra a inicializacao automatica (Tarefa Agendada no logon)
    6. Cria atalhos no Desktop e no Menu Iniciar
    7. (Opcional) Configura login automatico do Windows -AutoLogin

  USO (PowerShell como Administrador):
    Set-ExecutionPolicy -Scope Process Bypass -Force
    .\Install-Kiosk.ps1

  PARAMETROS:
    -InstallDir  Pasta de instalacao (padrao: C:\AuraKiosk)
    -Branch      Branch do git      (padrao: main)
    -Port        Porta do Streamlit (padrao: 8501)
    -AutoLogin   Liga login automatico do Windows (pede usuario/senha)
    -AutoStart   Registra start automatico no logon (padrao: ligado)
===============================================================================
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "C:\AuraKiosk",
    [string]$Branch     = "main",
    [int]   $Port       = 8501,
    [string]$Repo       = "https://github.com/med4to-badass/AI-Master-Plan.git",
    [switch]$AutoLogin,
    [bool]  $AutoStart  = $true
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  OK: $msg"   -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ! $msg"     -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
# 0. Exigir privilegios de Administrador
# ---------------------------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Este script precisa ser executado como ADMINISTRADOR." -ForegroundColor Red
    Write-Host "Clique com o botao direito no PowerShell e escolha 'Executar como administrador'." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "########################################################" -ForegroundColor Magenta
Write-Host "#   INSTALADOR DO QUIOSQUE - AURA DASHBOARD            #" -ForegroundColor Magenta
Write-Host "########################################################" -ForegroundColor Magenta

# ---------------------------------------------------------------------------
# 1. Garantir Python 3.9+
# ---------------------------------------------------------------------------
Write-Step "Verificando Python"
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            if ([int]$Matches[1] -ge 9) { $python = $cmd; Write-Ok "$ver"; break }
        }
    } catch {}
}
if (-not $python) {
    Write-Warn "Python 3.9+ nao encontrado. Baixando Python 3.12..."
    $pyInstaller = "$env:TEMP\python-installer.exe"
    Invoke-WebRequest "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe" -OutFile $pyInstaller
    Start-Process $pyInstaller -ArgumentList "/quiet","InstallAllUsers=1","PrependPath=1" -Wait
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + `
                [Environment]::GetEnvironmentVariable("Path","User")
    $python = "python"
    Write-Ok "Python instalado."
}

# ---------------------------------------------------------------------------
# 2. Verificar Git
# ---------------------------------------------------------------------------
Write-Step "Verificando Git"
$temGit = $false
try { git --version | Out-Null; $temGit = $true; Write-Ok "Git disponivel" }
catch { Write-Warn "Git nao encontrado. Usarei download ZIP." }

# ---------------------------------------------------------------------------
# 3. Baixar / atualizar o projeto
# ---------------------------------------------------------------------------
Write-Step "Obtendo o projeto em $InstallDir"
if (Test-Path "$InstallDir\.git" -PathType Container) {
    Push-Location $InstallDir
    git fetch origin $Branch 2>&1 | Out-Null
    git checkout $Branch 2>&1 | Out-Null
    git pull origin $Branch 2>&1 | Out-Null
    Pop-Location
    Write-Ok "Projeto atualizado."
}
elseif (Test-Path $InstallDir) {
    Write-Warn "Pasta ja existe (sem .git). Mantendo conteudo atual."
}
else {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    if ($temGit) {
        git clone --branch $Branch $Repo $InstallDir 2>&1
        Write-Ok "Repositorio clonado."
    } else {
        # Branch com barra (ex.: claude/x) -> a pasta extraida troca / por -
        $safe = $Branch -replace '[/\\]','-'
        $zip = "$env:TEMP\aura.zip"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest "https://github.com/med4to-badass/AI-Master-Plan/archive/refs/heads/$Branch.zip" -OutFile $zip
        Expand-Archive $zip -DestinationPath $env:TEMP -Force
        Copy-Item "$env:TEMP\AI-Master-Plan-$safe\*" $InstallDir -Recurse -Force
        Write-Ok "Projeto baixado e extraido."
    }
}

# ---------------------------------------------------------------------------
# 4. Ambiente virtual + dependencias
# ---------------------------------------------------------------------------
Write-Step "Configurando ambiente virtual e dependencias"
$venv = "$InstallDir\venv_win"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    & $python -m venv $venv
    Write-Ok "Ambiente virtual criado."
}
& "$venv\Scripts\python.exe" -m pip install --upgrade pip -q
& "$venv\Scripts\python.exe" -m pip install -r "$InstallDir\requirements.txt" -q
Write-Ok "Dependencias instaladas."

# ---------------------------------------------------------------------------
# 5. Inicializacao automatica (Tarefa Agendada no logon)
# ---------------------------------------------------------------------------
$startScript = "$InstallDir\kiosk\Start-Kiosk.ps1"
if (-not (Test-Path $startScript)) {
    Write-Warn "Start-Kiosk.ps1 nao encontrado em $startScript (sera necessario para o quiosque)."
}

if ($AutoStart) {
    Write-Step "Registrando inicializacao automatica (logon)"
    $taskName = "AuraKiosk"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`" -Port $Port"
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Settings $settings -RunLevel Highest -Force | Out-Null
    Write-Ok "Tarefa '$taskName' criada (inicia no logon)."
}

# ---------------------------------------------------------------------------
# 6. Atalhos no Desktop e Menu Iniciar
# ---------------------------------------------------------------------------
Write-Step "Criando atalhos"
$ws = New-Object -ComObject WScript.Shell
foreach ($dest in @(
    "$env:PUBLIC\Desktop\Aura Quiosque.lnk",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Aura Quiosque.lnk"
)) {
    try {
        $lnk = $ws.CreateShortcut($dest)
        $lnk.TargetPath = "powershell.exe"
        $lnk.Arguments  = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`" -Port $Port"
        $lnk.WorkingDirectory = $InstallDir
        $lnk.IconLocation = "shell32.dll,220"
        $lnk.Description = "Inicia o Aura Dashboard em modo quiosque"
        $lnk.Save()
    } catch { Write-Warn "Nao foi possivel criar atalho em $dest" }
}
Write-Ok "Atalhos criados."

# ---------------------------------------------------------------------------
# 7. (Opcional) Login automatico do Windows
# ---------------------------------------------------------------------------
if ($AutoLogin) {
    Write-Step "Configurando login automatico do Windows"
    $user = Read-Host "Usuario do Windows para login automatico (ex: kiosk)"
    $pass = Read-Host "Senha desse usuario" -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass))
    $reg = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
    Set-ItemProperty $reg "AutoAdminLogon" "1"
    Set-ItemProperty $reg "DefaultUserName" $user
    Set-ItemProperty $reg "DefaultPassword" $plain
    Write-Ok "Login automatico configurado para '$user'."
    Write-Warn "A senha fica em texto no registro. Use uma conta dedicada de quiosque."
}

# ---------------------------------------------------------------------------
# Final
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "########################################################" -ForegroundColor Green
Write-Host "#   INSTALACAO CONCLUIDA                               #" -ForegroundColor Green
Write-Host "########################################################" -ForegroundColor Green
Write-Host ""
Write-Host "Pasta:  $InstallDir"           -ForegroundColor Gray
Write-Host "Porta:  $Port"                 -ForegroundColor Gray
Write-Host ""
Write-Host "Para iniciar agora:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$startScript`" -Port $Port" -ForegroundColor White
Write-Host ""
Write-Host "Para SAIR do quiosque a qualquer momento: Ctrl+Alt+K" -ForegroundColor Yellow
Write-Host ""
$go = Read-Host "Deseja iniciar o quiosque agora? (S/N)"
if ($go -match '^[SsYy]') {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $startScript -Port $Port
}
