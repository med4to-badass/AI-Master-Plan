<#
===============================================================================
  Stop-Kiosk.ps1 — Encerra o quiosque (navegador + servidor) e (opcional) remove
===============================================================================
  USO:
    powershell -ExecutionPolicy Bypass -File Stop-Kiosk.ps1            # so para
    powershell -ExecutionPolicy Bypass -File Stop-Kiosk.ps1 -Uninstall # remove autostart/atalhos
===============================================================================
#>
[CmdletBinding()]
param([switch]$Uninstall)

$ErrorActionPreference = "SilentlyContinue"

Write-Host "Encerrando quiosque..." -ForegroundColor Yellow

# Sinaliza saida ao Start-Kiosk (caso esteja rodando o loop)
New-Item -ItemType File -Path (Join-Path $env:TEMP "aura_kiosk_exit.flag") -Force | Out-Null
Start-Sleep -Seconds 1

# Mata o navegador do perfil de quiosque
Get-Process msedge,chrome -ErrorAction SilentlyContinue |
    Where-Object { $_.Path } |
    Stop-Process -Force -ErrorAction SilentlyContinue

# Mata o Streamlit / processos python rodando app.py
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='streamlit.exe'" |
    Where-Object { $_.CommandLine -match 'streamlit' -or $_.CommandLine -match 'app\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Write-Host "  Processos encerrados." -ForegroundColor Green

if ($Uninstall) {
    Write-Host "Removendo inicializacao automatica e atalhos..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName "AuraKiosk" -Confirm:$false -ErrorAction SilentlyContinue
    Remove-Item "$env:PUBLIC\Desktop\Aura Quiosque.lnk" -ErrorAction SilentlyContinue
    Remove-Item "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Aura Quiosque.lnk" -ErrorAction SilentlyContinue

    # Desliga login automatico se estiver ativo
    $reg = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
    Set-ItemProperty $reg "AutoAdminLogon" "0" -ErrorAction SilentlyContinue
    Remove-ItemProperty $reg "DefaultPassword" -ErrorAction SilentlyContinue

    Write-Host "  Quiosque desinstalado (a pasta do app foi mantida)." -ForegroundColor Green
}
