<#
  register_backup_task.ps1 — DB 일일 백업 작업 스케줄러 등록 (액션아이템 A1)
  ─────────────────────────────────────────────────────────────
  매일 14:00 backup_db.py 실행 (놓치면 다음 가능 시점에 실행).
  등록:   pwsh code/scripts/register_backup_task.ps1
  해제:   Unregister-ScheduledTask -TaskName "DRW2_DB_Backup" -Confirm:$false
  확인:   Get-ScheduledTask -TaskName "DRW2_DB_Backup" | Get-ScheduledTaskInfo
#>
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'backup_db.py'
$py = (Get-Command pythonw -ErrorAction SilentlyContinue)?.Source
if (-not $py) { $py = (Get-Command python).Source }

$action   = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $PSScriptRoot
$trigger  = New-ScheduledTaskTrigger -Daily -At 14:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName 'DRW2_DB_Backup' -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "등록 완료: DRW2_DB_Backup (매일 14:00, 미실행 시 가능 시점에 보충)" -ForegroundColor Green
