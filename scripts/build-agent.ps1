# build-agent.ps1 — DRW 강사 에이전트 단일 exe 빌드 (PC 앱 빌드 폐기 후 유일 빌드 타깃).
# 에이전트 = AI 생성(genJobs) + 카톡 전송(sendJobs) 로컬 워커. 진입점 agent_gui.py.
# 키·카톡은 강사 PC 로컬(DPAPI). 웹(v2.5.0)이 입력·검토·전송요청 담당.
#
# 사전: pip install pyinstaller pyautogui pyperclip pillow
# 산출물: code/dist/DRW-Agent.exe  (build/·dist/·*.spec 은 gitignore)
param([switch]$Clean)

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\code')

if ($Clean) { Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue }

# 에이전트는 키 입력·클립보드만 사용(이미지 인식·스크린샷 미사용) → pyautogui가 끌어오는
# cv2/numpy/pandas 등 무거운 의존성 제외(67MB→20MB). PIL/pyscreeze는 pyautogui import 안정성 위해 유지.
pyinstaller --noconfirm --onefile --windowed `
  --name DRW-Agent `
  --hidden-import pyautogui --hidden-import pyperclip --hidden-import PIL `
  --hidden-import kakao_send --hidden-import secret_codec `
  --hidden-import ai_engine --hidden-import ai_style --hidden-import constants --hidden-import agent_worker `
  --exclude-module cv2 --exclude-module numpy --exclude-module pandas `
  --exclude-module scipy --exclude-module matplotlib --exclude-module IPython --exclude-module pytest `
  agent_gui.py

Write-Host "`n[완료] code/dist/DRW-Agent.exe" -ForegroundColor Green
Write-Host "강사 PC 최초 1회: DRW-Agent 실행 → 캠퍼스·이름·엔진·개인키 입력 → 저장하고 시작." -ForegroundColor Cyan
