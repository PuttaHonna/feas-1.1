@echo off
REM ====================================================================
REM FEAS 2.0 - Windows Command Prompt Universal Launcher
REM ====================================================================

setlocal
cd /d "%~dp0"

REM Prefer virtualenv python if available
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

if "%~1"=="" (
    "%PY_EXE%" run.py all
) else (
    "%PY_EXE%" run.py %*
)
endlocal
