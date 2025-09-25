@echo off
REM Simple startup script for Atlassian MCP Server on Windows

echo Starting Atlassian MCP Server...
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: Please create .env file with your Atlassian OAuth credentials
    echo Copy .env.example to .env and fill in your details
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Install dependencies
pip install -r requirements.txt

REM Get local IP for team access
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address" ^| findstr 192.168') do set LOCAL_IP=%%a
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo ================================
echo Server will be available at:
echo - Local: http://localhost:8080
echo - Team:  http://%LOCAL_IP%:8080
echo ================================
echo.

python main.py
