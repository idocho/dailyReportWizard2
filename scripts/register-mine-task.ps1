<#
  register-mine-task.ps1 — 노트 태그 마이닝 알림을 화·금 09:00 작업 스케줄러에 등록

  실행: pwsh -File scripts/register-mine-task.ps1
  해제: Unregister-ScheduledTask -TaskName 'DRW Note Tag Mining' -Confirm:$false
  확인: Get-ScheduledTask -TaskName 'DRW Note Tag Mining'

  현재 로그인 사용자 세션에서 실행(알림은 대화형 세션 필요).
  시간/요일을 바꾸려면 아래 -DaysOfWeek / -At 수정 후 재실행.
#>
$ErrorActionPreference = 'Stop'
$wrapper = Join-Path $PSScriptRoot 'mine_notify.ps1'
$ps      = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$name    = 'DRW Note Tag Mining'

$action  = New-ScheduledTaskAction -Execute $ps `
  -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$wrapper`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday, Friday -At 2:25pm
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
  -Settings $settings -Description '강사 노트 history build + 알림 (화·금 14:25). 분석은 Claude Code /mine-tags' -Force | Out-Null

Write-Host "등록 완료: '$name' (화·금 14:25)" -ForegroundColor Green
Get-ScheduledTask -TaskName $name | Select-Object TaskName, State |
  Format-Table -AutoSize
