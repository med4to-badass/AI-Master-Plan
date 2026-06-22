# ============================================================================
#  Instalador 24/7 do Otimizador de Jogos Aura
#  Cria uma Tarefa Agendada que inicia o otimizador automaticamente no logon,
#  em segundo plano (oculto), com privilegios maximos e reinicio automatico.
#
#  Instalar:    powershell -ExecutionPolicy Bypass -File instalar_24-7.ps1
#  Desinstalar: powershell -ExecutionPolicy Bypass -File instalar_24-7.ps1 -Remover
# ============================================================================
param([switch]$Remover)

$ErrorActionPreference = "Stop"
$NomeTarefa = "OtimizadorJogosAura"
$Pasta      = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script     = Join-Path $Pasta "otimizador.py"

# --- Auto-eleva para administrador ---
$admin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Solicitando privilegios de administrador..."
    $argList = "-ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
    if ($Remover) { $argList += " -Remover" }
    Start-Process powershell -Verb RunAs -ArgumentList $argList
    exit
}

if ($Remover) {
    if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
        Write-Host "✔ Tarefa '$NomeTarefa' removida. O otimizador nao iniciara mais sozinho." -ForegroundColor Green
    } else {
        Write-Host "Tarefa '$NomeTarefa' nao estava instalada." -ForegroundColor Yellow
    }
    exit
}

# --- Localiza o Python (pythonw para rodar sem janela) ---
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) { $pythonw = (Get-Command python.exe -ErrorAction SilentlyContinue).Source }
if (-not $pythonw) {
    Write-Host "[ERRO] Python nao encontrado no PATH. Instale o Python 3 primeiro." -ForegroundColor Red
    exit 1
}

# --- Garante dependencias ---
Write-Host "Verificando dependencia 'psutil'..."
& python.exe -m pip install -r (Join-Path $Pasta "requirements.txt") | Out-Null

# --- Cria a tarefa agendada ---
$acao    = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$Script`"" -WorkingDirectory $Pasta
$gatilho = New-ScheduledTaskTrigger -AtLogOn
$config  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries -StartWhenAvailable `
            -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit ([TimeSpan]::Zero)
$config.MultipleInstances = "IgnoreNew"
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest -LogonType Interactive

Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho `
    -Settings $config -Principal $principal -Force | Out-Null

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ✔ Otimizador instalado para rodar 24/7!" -ForegroundColor Green
Write-Host "   - Inicia automaticamente sempre que voce fizer login" -ForegroundColor Gray
Write-Host "   - Roda oculto, em segundo plano, com prioridade maxima" -ForegroundColor Gray
Write-Host "   - Reinicia sozinho se for encerrado" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Inicia agora mesmo
Start-ScheduledTask -TaskName $NomeTarefa
Write-Host "Otimizador iniciado agora. Bons jogos! 🎮" -ForegroundColor Green
