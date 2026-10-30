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

$pyExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pyExe)) {
    $pyExe = "python"
}

if (-not $ScriptArgs -or $ScriptArgs.Count -eq 0) {
    & $pyExe run.py all
} else {
    & $pyExe run.py @ScriptArgs
}
