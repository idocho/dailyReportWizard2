@echo off
title DRW Local Test Launcher
cd /d "%~dp0"

echo ==================================================
echo   DRW Local Integration Test  (web v2.5.0 + agent)
echo ==================================================
echo.

echo [1/3] Starting web server at localhost:7788 ...
start "DRW Web 7788" cmd /k "pushd %~dp0code\public && python -m http.server 7788"

REM wait for server to come up
ping -n 3 127.0.0.1 >nul

echo [2/3] Opening browser (v2.5.0 report app) ...
start "" "http://localhost:7788/v2.5.0/index.html"

echo [3/3] Starting agent GUI ...
start "DRW Agent" cmd /k "pushd %~dp0code && python agent_gui.py"

echo.
echo Done. Next:
echo   - Web : login (campus=dongsuwon / your name / pw) then Report tab
echo   - Agent : save setup, uncheck real-send (dry), click Start
echo   - NOTE : web login name MUST equal agent setup name (queue key)
echo.
echo You may close THIS window. (web/agent windows stay open)
pause
