@echo off
REM ====================================================================
REM FEAS 2.0 - Windows Command Prompt Universal Launcher
REM ====================================================================

setlocal
cd /d "%~dp0"

REM Check for virtual environment
if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
) else if exist "%~dp0venv\Scripts\activate.bat" (
    call "%~dp0venv\Scripts\activate.bat"
)

REM Check python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org and ensure "Add to PATH" is checked.
    pause
    exit /b 1
)

python "%~dp0run.py" %*
endlocal
