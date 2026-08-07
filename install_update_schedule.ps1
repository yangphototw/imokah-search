param(
    [string]$Time = '04:00',
    [string]$TaskName = 'AIOK Channel Update'
)

$ErrorActionPreference = 'Stop'
if ($Time -notmatch '^(?:[01]\d|2[0-3]):[0-5]\d$') {
    throw 'Time must be in HH:mm format, for example 04:00.'
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $root 'run_scheduled_update.ps1'
$start = "$(Get-Date -Format 'yyyy-MM-dd')T$Time`:00"
$userId = "$env:USERDOMAIN\$env:USERNAME"
$escapedRunner = [Security.SecurityElement]::Escape($runner)
$escapedRoot = [Security.SecurityElement]::Escape($root)
$escapedUser = [Security.SecurityElement]::Escape($userId)

# StartWhenAvailable covers a powered-off laptop: the task runs after the next
# sign-in. WakeToRun covers the more common sleeping-laptop case.  Interactive
# Token intentionally avoids storing the Windows password in the task.
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers><CalendarTrigger><StartBoundary>$start</StartBoundary><Enabled>true</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>$escapedUser</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><StartWhenAvailable>true</StartWhenAvailable><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate><RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable><WakeToRun>true</WakeToRun><ExecutionTimeLimit>PT6H</ExecutionTimeLimit><Enabled>true</Enabled></Settings>
  <Actions Context="Author"><Exec><Command>powershell.exe</Command><Arguments>-NoProfile -ExecutionPolicy Bypass -File &quot;$escapedRunner&quot;</Arguments><WorkingDirectory>$escapedRoot</WorkingDirectory></Exec></Actions>
</Task>
"@

$temp = Join-Path $env:TEMP 'aiok-channel-update-task.xml'
[IO.File]::WriteAllText($temp, $xml, [Text.Encoding]::Unicode)
try {
    schtasks.exe /Create /TN $TaskName /XML $temp /F
    if ($LASTEXITCODE -ne 0) { throw "schtasks failed with code $LASTEXITCODE" }
    Write-Host "Installed '$TaskName' for $Time."
    Write-Host 'If the computer is off, Windows will run it after the next sign-in; if asleep, it may wake it.'
}
finally {
    Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
}
