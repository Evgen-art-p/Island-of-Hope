@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ОСТРОВ НАДЕЖДЫ

rem ищем питон: сперва лаунчер py, потом обычный python
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 "остров.py"
    goto :konec
)
where python >nul 2>&1
if %errorlevel%==0 (
    python "остров.py"
    goto :konec
)

echo.
echo   Питон не найден.
echo   Поставь его с python.org и при установке поставь галочку
echo   "Add Python to PATH". Потом запусти этот файл снова.
echo.
pause

:konec
