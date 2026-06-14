<#
  mine_notify.ps1 — 노트 태그 마이닝 주기 트리거 (스케줄러용)
  ───────────────────────────────────────────────────────────
  1) mine_note_tags.py build 실행 → history 취합 + PROMPT.md 갱신 (증분)
  2) 결과를 Windows 알림(풍선/토스트)으로 표시
       → 사용자는 Claude Code 세션에서 /mine-tags 로 분석·ingest

  카운트는 documents/tag-mining/.pending.json(build 산출) 에서 읽는다
  (콘솔 인코딩 의존 제거). 파일은 UTF-8 BOM 으로 저장해야 powershell.exe(5.1)가
  한글을 올바로 파싱한다.

  작업 스케줄러 등록(화·금 09:00): scripts/register-mine-task.ps1
  실행 로그: scripts/mine_notify.log
#>
$ErrorActionPreference = 'Stop'
$repo    = Split-Path -Parent $PSScriptRoot
$python  = 'C:\Python314\python.exe'
$log     = Join-Path $PSScriptRoot 'mine_notify.log'
$pending = Join-Path $repo 'documents\tag-mining\.pending.json'
$stamp   = Get-Date -Format 'yyyy-MM-dd HH:mm'
$today   = Get-Date -Format 'yyyy-MM-dd'

function Notify($title, $body) {
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  $ni = New-Object System.Windows.Forms.NotifyIcon
  $ni.Icon    = [System.Drawing.SystemIcons]::Information
  $ni.Visible = $true
  $ni.BalloonTipTitle = $title
  $ni.BalloonTipText  = $body
  $ni.ShowBalloonTip(12000)
  Start-Sleep -Seconds 12
  $ni.Dispose()
}

try {
  Set-Location $repo
  $out = & $python 'scripts/mine_note_tags.py' 'build' 2>&1 | Out-String
  Add-Content $log "[$stamp] build`n$out"

  $count = 0
  if (Test-Path $pending) {
    $meta = Get-Content $pending -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($meta.build_date -eq $today) { $count = [int]$meta.note_count }
  }

  if ($count -gt 0) {
    Notify '노트 태그 마이닝' "노트 $count 건 준비됨 · Claude Code에서 /mine-tags 실행"
  } else {
    Notify '노트 태그 마이닝' '이번 기간 새 노트 없음 · 분석 생략'
  }
} catch {
  Add-Content $log "[$stamp] 오류: $_"
  Notify '노트 태그 마이닝 — 오류' "build 실패: $($_.Exception.Message)"
}
