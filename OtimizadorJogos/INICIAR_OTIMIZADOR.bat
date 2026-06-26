@echo off
chcp 65001 >nul
title Otimizador de Jogos Aura - 24/7
cd /d "%~dp0"

:: ============================================================
::  Auto-eleva para Administrador (necessario p/ otimizacao max)
:: ============================================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Solicitando privilegios de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   OTIMIZADOR DE JOGOS AURA - inicializando...
echo ============================================================

:: Garante Python
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Python nao encontrado no PATH. Instale o Python 3 e tente de novo.
    pause
    exit /b 1
)

:: Instala dependencias (psutil) silenciosamente, se faltar
python -c "import psutil" >nul 2>&1
if %errorLevel% neq 0 (
    echo Instalando dependencia 'psutil'...
    python -m pip install -r "%~dp0requirements.txt"
)

:: Roda o otimizador 24/7
python "%~dp0otimizador.py"

pause
