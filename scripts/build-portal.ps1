<#
  build-portal.ps1 — 버전 포털(루트 index.html) 생성
  ─────────────────────────────────────────────────────────────
  code/public/versions.json 을 읽어 code/public/index.html(포털)을 만든다.
  포털 = 안정 버전 섹션(상단) + 개발 버전 섹션(하단)으로 분리.
    tagClass: beta|old → 안정 섹션 / dev → 개발 섹션

  새 버전 추가 흐름:
    1) scripts/new-version.ps1 -From v2.1.0 -To v2.2.0   # 폴더 동결 복제
    2) versions.json 맨 앞에 새 항목 추가 (tagClass 조정)
    3) scripts/build-portal.ps1                          # 포털 갱신
    4) firebase deploy --only hosting
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pub  = Join-Path $root 'code/public'
$meta = Get-Content (Join-Path $pub 'versions.json') -Raw -Encoding UTF8 | ConvertFrom-Json

function Row($x) {
@"
      <a class="row" href="$($x.v)/">
        <div class="left">
          <div class="vh"><span class="v">$($x.v)</span><span class="tag $($x.tagClass)">$($x.tag)</span></div>
          <div class="t">$($x.title)</div>
          <div class="d">$($x.desc)</div>
        </div>
        <span class="go">열기 →</span>
      </a>
"@
}

$stable = @($meta.versions | Where-Object { $_.tagClass -ne 'dev' })
$dev    = @($meta.versions | Where-Object { $_.tagClass -eq 'dev' })

$sections = ''
if ($stable.Count) {
  $rows = ($stable | ForEach-Object { Row $_ }) -join "`n"
  $sections += @"
    <div class="sec">
      <div class="sec-h"><span class="sec-t">🟢 안정 버전</span><span class="sec-s">실사용 권장</span></div>
      <div class="card">
$rows
      </div>
    </div>
"@
}
if ($dev.Count) {
  $rows = ($dev | ForEach-Object { Row $_ }) -join "`n"
  $sections += @"
    <div class="sec">
      <div class="sec-h"><span class="sec-t">🧪 개발 버전</span><span class="sec-s">새 기능 검증용 · 불안정할 수 있음</span></div>
      <div class="card dev">
$rows
      </div>
    </div>
"@
}

$html = @"
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0E1016">
<title>DailyReportWizard — 버전 선택</title>
<style>
  :root{--bg:#FAFAFB;--panel:#fff;--ink:#18181B;--sub:#5C6370;--muted:#9CA3AF;--line:#ECECEF;--soft:#F3F3F5;
    --indigo:#4F46E5;--indigo-ink:#4338CA;--indigo-l:#EEF0FF;--indigo-line:#DDE1FF;--green:#16A34A;--green-l:#ECFDF3}
  *{box-sizing:border-box;margin:0;padding:0;-webkit-font-smoothing:antialiased}
  body{font-family:'Pretendard','Malgun Gothic','맑은 고딕',-apple-system,sans-serif;background:var(--bg);color:var(--ink);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;letter-spacing:-.01em}
  .box{width:100%;max-width:480px}
  .brand{display:flex;align-items:center;gap:11px;margin-bottom:6px}
  .mark{width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,#6366F1,#4338CA);display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 2px 10px rgba(67,56,202,.4)}
  h1{font-size:17px;font-weight:800}h1 small{display:block;font-size:11.5px;font-weight:500;color:var(--muted);margin-top:1px}
  .lead{font-size:12px;color:var(--sub);margin:10px 2px 18px}
  .sec{margin-bottom:18px}
  .sec-h{display:flex;align-items:baseline;gap:8px;padding:0 4px 8px}
  .sec-t{font-size:12.5px;font-weight:800;letter-spacing:-.01em}
  .sec-s{font-size:10.5px;color:var(--muted);font-weight:500}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:0 1px 3px rgba(16,24,40,.07);overflow:hidden}
  .card.dev{border-style:dashed;border-color:var(--indigo-line);background:#FCFCFE;box-shadow:none}
  .row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 18px;border-bottom:1px solid var(--soft);text-decoration:none;color:var(--ink);transition:background .12s}
  .row:last-child{border-bottom:none}.row:hover{background:#F7F7F9}
  .vh{display:flex;align-items:center;gap:8px}
  .v{font-size:15px;font-weight:800}
  .tag{font-size:10px;font-weight:800;border-radius:7px;padding:2px 8px}
  .tag.dev{background:var(--indigo-l);color:var(--indigo-ink);border:1px solid var(--indigo-line)}
  .tag.beta{background:var(--green-l);color:var(--green);border:1px solid #C5F0D4}
  .tag.old{background:#F1F1F4;color:var(--muted);border:1px solid var(--line)}
  .t{font-size:12.5px;font-weight:600;color:var(--ink);margin-top:5px}
  .d{font-size:11px;color:var(--muted);margin-top:2px;line-height:1.4}
  .go{font-size:12px;font-weight:700;color:var(--indigo-ink);white-space:nowrap;flex-shrink:0}
  .note{font-size:11px;color:var(--muted);margin-top:6px;line-height:1.6;text-align:center}
</style>
</head>
<body>
  <div class="box">
    <div class="brand"><div class="mark">📝</div><h1>DailyReportWizard<small>버전 선택 · 테스트 빌드</small></h1></div>
    <p class="lead">사용할 버전을 선택하세요. 각 버전은 독립 동결 빌드이며, 설정·데이터(로컬·Firebase)는 버전 간 공유됩니다.</p>
$sections
    <div class="note">평소 사용은 <b>안정 버전</b>을 권장합니다.<br>개발 버전의 온보딩 테스트는 시크릿창 또는 설정의 “위저드 다시 실행”을 이용하세요.</div>
  </div>
</body>
</html>
"@
Set-Content -Path (Join-Path $pub 'index.html') -Value $html -Encoding UTF8
Write-Host "포털 생성: 안정 $($stable.Count) · 개발 $($dev.Count)" -ForegroundColor Green
