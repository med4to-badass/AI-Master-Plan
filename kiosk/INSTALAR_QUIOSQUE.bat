@echo off
REM ===========================================================================
REM  INSTALAR_QUIOSQUE.bat
REM  Da um duplo-clique aqui (ou "Executar como administrador") para instalar
REM  o quiosque. Ele apenas chama o Install-Kiosk.ps1 com permissao elevada.
REM ===========================================================================
setlocal

REM Garante que esta rodando como Administrador; se nao, relanca elevado.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando privilegios de administrador...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)

set "SCRIPT=%~dp0Install-Kiosk.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"

echo.
pause
