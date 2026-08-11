@echo off
chcp 65001 >nul
cd /d "%~dp0"
title УБРАТЬ КЛЮЧ
where py >nul 2>&1
if %errorlevel%==0 ( py -3 "ubrat_klyuch.py" & goto :konec )
where python >nul 2>&1
if %errorlevel%==0 ( python "ubrat_klyuch.py" & goto :konec )
echo.
echo   Питон не найден. Поставь его с python.org.
echo.
pause
:konec
