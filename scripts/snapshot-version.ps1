<#
  snapshot-version.ps1 — 현재 웹 앱을 버전 하위폴더로 스냅샷
  ─────────────────────────────────────────────────────────────
  code/public/{index.html,guide.html,css,js,data} 를
  code/public/v<VERSION>/ 로 복사하여 버전별 동결 사본을 만든다.
  versions.html(버전 목록 랜딩)도 자동 재생성한다.

  사용:
    pwsh scripts/snapshot-version.ps1            # constants.py의 APP_VERSION 사용
    pwsh scripts/snapshot-version.ps1 -Version v2.1.0
  스냅샷 후 배포:
    firebase deploy --only hosting
  접속:
    https://dailyreportwizard.web.app/v2.1.0/
#>
param([string]$Version)

$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $PSScriptRoot          # 저장소 루트
$pub    = Join-Path $root 'code/public'
$consts = Join-Path $root 'code/constants.py'

# 버전 미지정 시 constants.py에서 APP_VERSION 추출
if (-not $Version) {
  $m = Select-String -Path $consts -Pattern 'APP_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
  if (-not $m) { throw "constants.py에서 APP_VERSION을 찾지 못했습니다." }
  $Version = $m.Matches[0].Groups[1].Value
}
if ($Version -notmatch '^v\d') { $Version = "v$Version" }   # 'v' 접두 보정

$dest = Join-Path $pub $Version
Write-Host "→ 스냅샷: $Version" -ForegroundColor Cyan

if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Force -Path $dest | Out-Null

foreach ($f in @('index.html','guide.html')) {
  $p = Join-Path $pub $f
  if (Test-Path $p) { Copy-Item $p $dest }
}
foreach ($d in @('css','js','data')) {
  $p = Join-Path $pub $d
  if (Test-Path $p) { Copy-Item $p (Join-Path $dest $d) -Recurse }
}
Write-Host "  복사 완료 → $dest" -ForegroundColor Green

# ── versions.html 재생성 (v* 폴더 스캔) ──
$versions = Get-ChildItem -Path $pub -Directory |
  Where-Object { $_.Name -match '^v\d' } |
  Sort-Object Name -Descending
$rows = ($versions | ForEach-Object {
  "      <a class=""row"" href=""$($_.Name)/""><span class=""v"">$($_.Name)</span><span class=""go"">열기 →</span></a>"
}) -join "`n"

$html = @"
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DailyReportWizard — 버전 목록</title>
<style>
  :root{--bg:#FAFAFB;--panel:#fff;--ink:#18181B;--sub:#5C6370;--muted:#9CA3AF;--line:#ECECEF;--indigo:#4F46E5;--indigo-ink:#4338CA}
  *{box-sizing:border-box;margin:0;padding:0;-webkit-font-smoothing:antialiased}
  body{font-family:'Pretendard','Malgun Gothic',sans-serif;background:var(--bg);color:var(--ink);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;letter-spacing:-.01em}
  .box{width:100%;max-width:440px}
  .brand{display:flex;align-items:center;gap:10px;margin-bottom:18px}
  .mark{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#6366F1,#4338CA);display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 2px 8px rgba(67,56,202,.4)}
  h1{font-size:16px;font-weight:800}h1 small{display:block;font-size:11px;font-weight:500;color:var(--muted);margin-top:1px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:0 1px 3px rgba(16,24,40,.07);overflow:hidden}
  .row{display:flex;align-items:center;justify-content:space-between;padding:15px 18px;border-bottom:1px solid #F3F3F5;text-decoration:none;color:var(--ink);transition:background .12s}
  .row:last-child{border-bottom:none}.row:hover{background:#F7F7F9}
  .v{font-size:14px;font-weight:700}.go{font-size:12px;font-weight:600;color:var(--indigo-ink)}
  .prod{padding:15px 18px;border-bottom:1px solid #F3F3F5;text-decoration:none;display:flex;align-items:center;justify-content:space-between;color:var(--ink);transition:background .12s}
  .prod:hover{background:#F7F7F9}.prod .v{color:var(--indigo-ink)}.tag{font-size:10px;font-weight:700;background:#EEF0FF;color:var(--indigo-ink);border:1px solid #DDE1FF;border-radius:7px;padding:2px 8px}
  .note{font-size:11px;color:var(--muted);margin-top:14px;line-height:1.5;text-align:center}
</style>
</head>
<body>
  <div class="box">
    <div class="brand"><div class="mark">📝</div><h1>DailyReportWizard<small>버전별 테스트 빌드</small></h1></div>
    <div class="card">
      <a class="prod" href="./"><span class="v">최신 (프로덕션)</span><span class="tag">/</span></a>
$rows
    </div>
    <div class="note">각 버전은 동결된 스냅샷입니다. 루트(/)는 최신 안정판.</div>
  </div>
</body>
</html>
"@
Set-Content -Path (Join-Path $pub 'versions.html') -Value $html -Encoding UTF8
Write-Host "  versions.html 갱신 ($($versions.Count)개 버전)" -ForegroundColor Green
Write-Host "`n배포: firebase deploy --only hosting" -ForegroundColor Yellow
