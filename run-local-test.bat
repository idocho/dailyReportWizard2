@echo off
chcp 65001 >nul
title DRW 로컬 통합 테스트 런처
cd /d "%~dp0"

echo ===============================================
echo   DRW 로컬 통합 테스트 (웹 v2.5.0 + 에이전트)
echo ===============================================
echo.

REM [1] 웹 정적 서버 (code\public -> localhost:7788)
echo [1/3] 웹 서버 시작 ... localhost:7788
start "DRW Web 7788" cmd /k "pushd %~dp0code\public && python -m http.server 7788"

REM 서버 기동 대기
ping -n 3 127.0.0.1 >nul

REM [2] 브라우저로 v2.5.0 리포트 앱 열기
echo [2/3] 브라우저 열기 ... /v2.5.0/index.html
start "" "http://localhost:7788/v2.5.0/index.html"

REM [3] 강사 에이전트 GUI (설정 폼/상태창)
echo [3/3] 에이전트 GUI 시작 ...
start "DRW Agent" cmd /k "pushd %~dp0code && python agent_gui.py"

echo.
echo 완료.
echo  - 웹: 로그인(캠퍼스 동수원 / 본인 이름 / 비번) - 리포트 전송 탭
echo  - 에이전트: 설정 저장 후 [실발송 해제=dry] - [시작]
echo  - 주의: 웹 로그인 이름 == 에이전트 설정 이름 (큐 연결 키)
echo.
echo 이 창은 닫아도 됩니다. (웹/에이전트 창은 유지)
pause
