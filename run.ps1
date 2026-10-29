# ====================================================================
# FEAS 2.0 - Windows PowerShell Universal Launcher
# ====================================================================
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
Set-Location -Path $PSScriptRoot

# Auto-activate venv if available
$venvActivate = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
}

# Find python
$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pythonCmd) {
    Write-Error "Python was not found on your system PATH. Please install Python 3.10+ from python.org."
    exit 1
}

$runPy = Join-Path $PSScriptRoot "run.py"
& python $runPy $ScriptArgs
