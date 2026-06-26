@echo off
chcp 65001 >nul
title Criar atalho do Otimizador na Area de Trabalho
cd /d "%~dp0"

echo ============================================================
echo   Criando atalho do Otimizador de Jogos na Area de Trabalho
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$lnk = Join-Path $desktop 'Otimizador de Jogos Aura.lnk';" ^
  "$s = $ws.CreateShortcut($lnk);" ^
  "$s.TargetPath = Join-Path '%~dp0' 'INICIAR_OTIMIZADOR.bat';" ^
  "$s.WorkingDirectory = '%~dp0'.TrimEnd('\');" ^
  "$s.IconLocation = '%SystemRoot%\System32\shell32.dll,18';" ^
  "$s.Description = 'Otimizacao maxima de jogos 24/7 - Aura';" ^
  "$s.WindowStyle = 1;" ^
  "$s.Save();" ^
  "Write-Host '[OK] Atalho criado:' $lnk -ForegroundColor Green"

echo.
echo Pronto! Procure o icone "Otimizador de Jogos Aura" na sua Area de Trabalho.
echo Basta dar duplo clique nele para iniciar a otimizacao 24/7.
echo.
pause
