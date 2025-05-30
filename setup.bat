@echo off
SETLOCAL EnableDelayedExpansion

echo Project Setup Script
echo ----------------------

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

:: Install Python dependencies
echo Installing Python dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

:: Install Playwright browsers
echo Installing Playwright browsers...
playwright install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Playwright browsers
    pause
    exit /b 1
)

:: Run Neo4j Docker setup
echo Starting Neo4j Docker environment...
call run-neo4j.bat

ENDLOCAL
