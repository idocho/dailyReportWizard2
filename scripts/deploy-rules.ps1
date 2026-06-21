<#
.SYNOPSIS
  Firebase Security Rules 전환 — deny-by-default 룰 배포 (1차 봉인, #15).
  SECURITY_RULES_PLAN.md "전환 창 절차"를 한 번에·순서대로·검증까지 자동 수행.

.DESCRIPTION
  실행 순서(중단 시 그 단계까지만 적용):
    1) 사전점검: firebase CLI·database.rules.json·firebase.json 확인
    2) 백업 1회 (code/scripts/backup_db.py)
    3) [확인 게이트] 모든 클라이언트(웹·PC·CM·Analyzer)에 시크릿 무장 완료했는가?
       — 룰 배포 전에 클라가 시크릿을 가져야 다운타임 0. 미무장이면 전 클라 차단됨.
    4) schema_version 노드 = 14 설정
    5) firebase.json 에 database 룰 배선(이미 있으면 건너뜀)
    6) firebase deploy --only database
    7) 검증: 무인증 차단 + 유인증 통과 확인

  ⚠️ 라이브 DB 를 잠그는 되돌리기 어려운 작업이다. -DryRun 으로 먼저 점검 권장.
  롤백: Firebase 콘솔 → Realtime Database → 규칙에서 .read/.write:true 임시 복원.

.PARAMETER Secret
  Firebase DB Secret(레거시 admin 토큰). schema_version 설정·검증에 사용.
.PARAMETER DbUrl
  RTDB 베이스 URL. 기본: https://dailyreportwizard-default-rtdb.firebaseio.com
.PARAMETER DbPath
  데이터 루트 경로. 기본: drw2_cbt
.PARAMETER DryRun
  실제 변경 없이 수행할 단계만 출력.

.EXAMPLE
  ./scripts/deploy-rules.ps1 -Secret "AbCd..." -DryRun
  ./scripts/deploy-rules.ps1 -Secret "AbCd..."
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Secret,
  [string]$DbUrl  = "https://dailyreportwizard-default-rtdb.firebaseio.com",
  [string]$DbPath = "drw2_cbt",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RulesFile    = Join-Path $RepoRoot "database.rules.json"
$FirebaseJson = Join-Path $RepoRoot "firebase.json"
$BackupScript = Join-Path $RepoRoot "code/scripts/backup_db.py"
$SCHEMA_VERSION = 14

function Step($n, $msg) { Write-Host "`n[$n] $msg" -ForegroundColor Cyan }
function Ok($msg)       { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Warn($msg)     { Write-Host "  ! $msg" -ForegroundColor Yellow }

# ── 1. 사전 점검 ──────────────────────────────────────────────────────
Step 1 "사전 점검"
if (-not (Get-Command firebase -ErrorAction SilentlyContinue)) {
  throw "firebase CLI 없음. 'npm i -g firebase-tools' 후 'firebase login'."
}
if (-not (Test-Path $RulesFile))    { throw "database.rules.json 없음: $RulesFile" }
if (-not (Test-Path $FirebaseJson)) { throw "firebase.json 없음: $FirebaseJson" }
Ok "firebase CLI·룰 파일·firebase.json 확인"
$base = $DbUrl.TrimEnd('/'); $path = $DbPath.Trim('/')
Write-Host "  대상: $base/$path  (schema_version=$SCHEMA_VERSION)"

if ($DryRun) { Warn "DryRun — 이후 단계는 출력만, 실제 변경 없음" }

# ── 2. 백업 ───────────────────────────────────────────────────────────
Step 2 "DB 전체 백업"
if ($DryRun) {
  Write-Host "  (dry) python `"$BackupScript`""
} else {
  python "$BackupScript"
  if ($LASTEXITCODE -ne 0) { throw "백업 실패(exit $LASTEXITCODE) — 중단. DB 상태 확인 후 재시도." }
  Ok "백업 완료"
}

# ── 3. 확인 게이트 (주요 의사결정) ────────────────────────────────────
Step 3 "클라이언트 무장 확인 (주요 결정)"
Write-Host "  룰 배포 전, 아래 모두에 DB 시크릿이 설정·동작 확인되어야 합니다:" -ForegroundColor Yellow
Write-Host "    • PC DRW / ClassManager  → config.json (또는 설정창)"
Write-Host "    • 운영 태블릿 웹앱        → 설정 > Firebase 연결 > DB 시크릿"
Write-Host "    • Analyzer                → 접속 폼 DB 시크릿"
Write-Host "  미무장 클라이언트는 배포 즉시 전부 차단됩니다." -ForegroundColor Yellow
if (-not $DryRun) {
  $ans = Read-Host "  모두 무장·로드 확인됐으면 'DEPLOY' 입력 (그 외 입력 시 중단)"
  if ($ans -ne "DEPLOY") { Warn "확인 미입력 — 안전 중단."; exit 0 }
}

# ── 4. schema_version 설정 ────────────────────────────────────────────
Step 4 "schema_version = $SCHEMA_VERSION 설정"
$schemaUrl = "$base/$path/schema_version.json?auth=$([uri]::EscapeDataString($Secret))"
if ($DryRun) {
  Write-Host "  (dry) PUT $base/$path/schema_version.json  body=$SCHEMA_VERSION"
} else {
  Invoke-RestMethod -Uri $schemaUrl -Method Put -Body "$SCHEMA_VERSION" | Out-Null
  Ok "schema_version 기록"
}

# ── 5. firebase.json 에 database 룰 배선 ──────────────────────────────
Step 5 "firebase.json database 룰 배선"
$fjText = Get-Content $FirebaseJson -Raw
if ($fjText -match '"database"\s*:') {
  Ok "이미 배선됨 — 건너뜀"
} else {
  # 최상위 여는 중괄호 직후에 database 블록 삽입(들여쓰기 보존, 포맷 비파괴)
  $inject = "`n  `"database`": {`n    `"rules`": `"database.rules.json`"`n  },"
  $newText = [regex]::Replace($fjText, '^\s*{', { param($m) $m.Value + $inject }, 1)
  if ($DryRun) {
    Write-Host "  (dry) firebase.json 에 database 블록 추가 예정:"
    Write-Host $inject
  } else {
    Set-Content -Path $FirebaseJson -Value $newText -NoNewline -Encoding UTF8
    Ok "database 블록 추가"
  }
}

# ── 6. 룰 배포 ────────────────────────────────────────────────────────
Step 6 "firebase deploy --only database"
if ($DryRun) {
  Write-Host "  (dry) firebase deploy --only database"
} else {
  firebase deploy --only database
  if ($LASTEXITCODE -ne 0) { throw "배포 실패(exit $LASTEXITCODE). 콘솔에서 룰 상태 확인." }
  Ok "룰 배포 완료"
}

# ── 7. 검증 ───────────────────────────────────────────────────────────
Step 7 "검증 (무인증 차단 + 유인증 통과)"
if ($DryRun) {
  Write-Host "  (dry) GET $base/$path/students.json        → 차단(401) 기대"
  Write-Host "  (dry) GET $base/$path/students.json?auth=… → 통과 기대"
  Write-Host "`nDryRun 종료 — 실제 전환은 -DryRun 없이 재실행." -ForegroundColor Yellow
  exit 0
}
$blocked = $false
try { Invoke-RestMethod -Uri "$base/$path/students.json" -Method Get -ErrorAction Stop | Out-Null }
catch { $blocked = $true }
if ($blocked) { Ok "무인증 접근 차단 확인" } else { Warn "무인증 접근이 여전히 열려 있음! 룰 배포 상태 즉시 확인 필요." }

try {
  Invoke-RestMethod -Uri "$base/$path/students.json?auth=$([uri]::EscapeDataString($Secret))" -Method Get -ErrorAction Stop | Out-Null
  Ok "유인증 접근 통과 확인"
} catch {
  Warn "유인증 접근 실패 — 시크릿/네트워크 확인. (운영 클라가 못 붙을 수 있음)"
}

Write-Host "`n전환 완료. 각 클라이언트 1회 스모크(웹 입력→전송·CM 명단·Analyzer·backup) 권장." -ForegroundColor Green
