$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDirectory = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$logFile = Join-Path $logDirectory ("update-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

Push-Location $root
try {
    & cmd.exe /c (Join-Path $root 'auto_update.bat') 2>&1 | Tee-Object -FilePath $logFile
    if ($LASTEXITCODE -ne 0) {
        throw "auto_update.bat exited with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
