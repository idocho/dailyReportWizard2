<#
  new-version.ps1 — 기존 버전 폴더를 복제해 새 버전 동결본 시작
  ─────────────────────────────────────────────────────────────
  사용:
    pwsh scripts/new-version.ps1 -From v2.1.0 -To v2.2.0
  동작:
    code/public/<From>/  →  code/public/<To>/  복제
    <To>/index.html 의 인라인 APP_VERSION 을 <To> 로 갱신
  이후:
    1) code/public/<To>/ 안에서 개발 진행
    2) versions.json 맨 앞에 <To> 항목 추가
    3) pwsh scripts/build-portal.ps1
#>
param(
  [Parameter(Mandatory=$true)][string]$From,
  [Parameter(Mandatory=$true)][string]$To
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pub  = Join-Path $root 'code/public'
$src  = Join-Path $pub $From
$dst  = Join-Path $pub $To
if (-not (Test-Path $src)) { throw "원본 폴더 없음: $src" }
if (Test-Path $dst) { throw "대상 폴더가 이미 있음: $dst (먼저 정리하세요)" }

Copy-Item $src $dst -Recurse
# 인라인 APP_VERSION 갱신
$idx = Join-Path $dst 'index.html'
if (Test-Path $idx) {
  (Get-Content $idx -Raw -Encoding UTF8) `
    -replace "APP_VERSION='[^']*'", "APP_VERSION='$To'" |
    Set-Content $idx -Encoding UTF8 -NoNewline
}
Write-Host "복제 완료: $From → $To" -ForegroundColor Green
Write-Host "다음: $To/ 에서 개발 → versions.json 편집 → build-portal.ps1" -ForegroundColor Yellow
