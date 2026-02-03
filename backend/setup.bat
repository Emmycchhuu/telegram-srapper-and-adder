@echo off
echo Installing Telegram Member Adder dependencies...
echo.

REM Check if Python is installed
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.7 or higher.
    pause
    exit /b 1
)

echo Installing required packages...
py -m pip install -r requirements.txt

echo.
echo Setup complete!
echo Copy .env.example to .env and configure your API credentials
pause