@echo off
SETLOCAL EnableDelayedExpansion

:: Title
echo Neo4j Docker Setup
echo ------------------

:: Check if Docker is running
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

:: Check for existing .env
if exist .env (
    echo WARNING: .env file already exists.
    choice /c yn /m "Do you want to overwrite it? (y/n)"
    if !errorlevel! equ 2 (
        echo Using existing .env file
        goto start_container
    )
)

:: Get credentials from user
:get_username
set /p "neo4j_user=Enter Neo4j username (default: neo4j): "
if "!neo4j_user!"=="" set "neo4j_user=neo4j"

:get_password
set /p "neo4j_pass=Enter Neo4j password (min 8 chars): "
if "!neo4j_pass!"=="" (
    echo Password cannot be empty
    goto get_password
)
if "!neo4j_pass:~0,8!"=="!neo4j_pass!" (
    echo Password must be at least 8 characters
    goto get_password
)

:: Create .env file
(
    echo NEO4J_URI=bolt://localhost:7687
    echo NEO4J_USER=!neo4j_user!
    echo NEO4J_PASSWORD=!neo4j_pass!
) > .env

echo Created .env file with your credentials

:: Remove old containers and volumes to apply new credentials
echo Resetting Neo4j containers and volumes to apply new credentials...
docker-compose down -v

:start_container
:: Start Neo4j
echo Starting Neo4j with Docker Compose...
docker-compose up -d

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: Neo4j container started
    echo Browser URL: http://localhost:7474
    echo Username: !neo4j_user!
    echo Password: ******** (hidden for security)
    echo.
    echo You can now close this window.
    timeout /t 15 >nul
) else (
    echo.
    echo ERROR: Failed to start Neo4j
    echo Possible reasons:
    echo - Ports 7474 or 7687 are already in use
    echo - Docker has insufficient resources
    echo - Network configuration issues
    pause
    exit /b 1
)

ENDLOCAL
