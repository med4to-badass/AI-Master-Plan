<#
===============================================================================
  Remove-WindowsKiosk.ps1 — Desfaz o kiosk nativo (Assigned Access)
===============================================================================
  Limpa a configuracao de quiosque, remove a tarefa do servidor e (opcional)
  apaga a conta de quiosque.

  USO (Administrador):
    .\Remove-WindowsKiosk.ps1
    .\Remove-WindowsKiosk.ps1 -RemoveUser     # tambem apaga a conta
    .\Remove-WindowsKiosk.ps1 -KioskUser "QuiosqueAura" -RemoveUser
===============================================================================
#>
[CmdletBinding()]
param(
    [string]$KioskUser = "QuiosqueAura",
    [switch]$RemoveUser
)

$ErrorActionPreference = "SilentlyContinue"
function Write-Ok($m){ Write-Host "  OK: $m" -ForegroundColor Green }

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Host "Execute como ADMINISTRADOR." -ForegroundColor Red; exit 1 }

Write-Host "Removendo quiosque nativo..." -ForegroundColor Yellow

# 1. Limpar a configuracao Assigned Access (precisa rodar como SYSTEM)
$work = Join-Path $env:ProgramData "AuraKiosk"
New-Item -ItemType Directory -Path $work -Force | Out-Null
$clearPath = Join-Path $work "clear-assignedaccess.ps1"
@'
try {
    $obj = Get-CimInstance -Namespace "root\cimv2\mdm\dmmap" -ClassName "MDM_AssignedAccess"
    if ($obj) { $obj.Configuration = ""; Set-CimInstance -CimInstance $obj }
} catch {}
'@ | Set-Content -Path $clearPath -Encoding UTF8

$act  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$clearPath`""
$prin = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "AuraClearKiosk" -Action $act -Principal $prin -Force | Out-Null
Start-ScheduledTask -TaskName "AuraClearKiosk"
Start-Sleep -Seconds 5
Unregister-ScheduledTask -TaskName "AuraClearKiosk" -Confirm:$false -ErrorAction SilentlyContinue
Write-Ok "Assigned Access limpo."

# 2. Remover a tarefa do servidor
Unregister-ScheduledTask -TaskName "AuraServer" -Confirm:$false -ErrorAction SilentlyContinue
Write-Ok "Tarefa 'AuraServer' removida."

# 3. Parar o servidor que estiver rodando
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='streamlit.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'streamlit' -or $_.CommandLine -match 'app\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# 4. Reverter otimizacoes (politicas do Edge + tela de bloqueio)
Remove-Item "HKLM:\SOFTWARE\Policies\Microsoft\Edge" -Recurse -Force -ErrorAction SilentlyContinue
Remove-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization" `
    -Name "NoLockScreen" -ErrorAction SilentlyContinue
Write-Ok "Politicas do Edge e tela de bloqueio revertidas."
Write-Host "  (As configuracoes de energia foram mantidas; ajuste em Configuracoes se quiser.)" -ForegroundColor Gray

# 5. (Opcional) apagar a conta
if ($RemoveUser) {
    Remove-LocalUser -Name $KioskUser -ErrorAction SilentlyContinue
    Write-Ok "Conta '$KioskUser' removida."
}

Write-Host "Pronto. Pode ser necessario reiniciar para o Windows voltar ao normal." -ForegroundColor Cyan
