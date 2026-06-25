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

# 1. Limpar a configuracao Assigned Access (Configuration vazia)
$ns    = "root\cimv2\mdm\dmmap"
$obj   = Get-CimInstance -Namespace $ns -ClassName "MDM_AssignedAccess" -ErrorAction SilentlyContinue
if ($obj) {
    $obj.Configuration = ""
    try { Set-CimInstance -CimInstance $obj; Write-Ok "Assigned Access removido." }
    catch { Write-Host "  Nao foi possivel limpar Assigned Access automaticamente." -ForegroundColor Yellow }
}

# 2. Remover a tarefa do servidor
Unregister-ScheduledTask -TaskName "AuraServer" -Confirm:$false -ErrorAction SilentlyContinue
Write-Ok "Tarefa 'AuraServer' removida."

# 3. Parar o servidor que estiver rodando
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='streamlit.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'streamlit' -or $_.CommandLine -match 'app\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# 4. (Opcional) apagar a conta
if ($RemoveUser) {
    Remove-LocalUser -Name $KioskUser -ErrorAction SilentlyContinue
    Write-Ok "Conta '$KioskUser' removida."
}

Write-Host "Pronto. Pode ser necessario reiniciar para o Windows voltar ao normal." -ForegroundColor Cyan
