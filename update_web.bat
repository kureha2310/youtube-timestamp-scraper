@echo off
chcp 65001 > nul
echo ========================================
echo   ワンクリックWeb更新
echo ========================================
echo.

python update_web.py
if %errorlevel% neq 0 (
    echo.
    echo [!] エラーが発生しました
    pause
    exit /b %errorlevel%
)

echo.
pause
