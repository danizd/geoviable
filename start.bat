@echo off
setlocal enabledelayedexpansion

:: ==============================================================================
:: GeoViable — Start Script (Windows)
:: ==============================================================================
:: This script automates the local startup process for the GeoViable project.
:: It checks prerequisites, initializes the environment, and starts all services.
:: ==============================================================================

echo.
echo ========================================
echo    GeoViable - Local Development
echo ========================================
echo.

:: ──────────────────────────────────────────────────────────────────────────────
:: Step 1: Check if Docker is running
:: ──────────────────────────────────────────────────────────────────────────────
echo [1/6] Checking Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo [OK] Docker is running.

:: ──────────────────────────────────────────────────────────────────────────────
:: Step 2: Check if Docker Compose is available
:: ──────────────────────────────────────────────────────────────────────────────
echo [2/6] Checking Docker Compose...
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose not found. Please install Docker Compose V2.
    pause
    exit /b 1
)
echo [OK] Docker Compose is available.

:: ──────────────────────────────────────────────────────────────────────────────
:: Step 3: Verify .env file exists
:: ──────────────────────────────────────────────────────────────────────────────
echo [3/6] Checking environment configuration...
if not exist ".env" (
    echo [WARNING] .env file not found.
    echo Creating .env from .env.example...
    copy ".env.example" ".env" >nul
    echo [OK] .env file created. Please edit it with your configuration.
    echo.
    echo Press any key to continue after editing .env, or Ctrl+C to cancel.
    pause >nul
) else (
    echo [OK] .env file found.
)

:: ──────────────────────────────────────────────────────────────────────────────
:: Step 4: Check if frontend build exists
:: ──────────────────────────────────────────────────────────────────────────────
echo [4/6] Checking frontend build...
if not exist "frontend\build\index.html" (
    echo [WARNING] Frontend build not found at frontend\build\.
    echo The web server expects a built frontend in this directory.
    echo.
    echo To build the frontend, run:
    echo   cd frontend
    echo   npm run build
    echo.
    set /p "continue=Continue anyway? (y/n): "
    if /i not "!continue!"=="y" (
        echo Aborted. Please build the frontend first.
        pause
        exit /b 1
    )
) else (
    echo [OK] Frontend build found.
)

:: ──────────────────────────────────────────────────────────────────────────────
:: Step 5: Pull latest images (optional)
:: ──────────────────────────────────────────────────────────────────────────────
echo [5/6] Checking Docker images...
echo Pulling latest images (this may take a moment)...
docker compose pull
if %errorlevel% neq 0 (
    echo [WARNING] Failed to pull some images. Continuing with local images if available.
)

:: ──────────────────────────────────────────────────────────────────────────────
:: Step 6: Start all services
:: ──────────────────────────────────────────────────────────────────────────────
echo [6/6] Starting GeoViable services...
echo.
echo ========================================
echo    Starting services...
echo ========================================
echo.

docker compose up -d

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start services. Check the output above for details.
    pause
    exit /b 1
)

:: ──────────────────────────────────────────────────────────────────────────────
:: Wait for services to be ready
:: ──────────────────────────────────────────────────────────────────────────────
echo.
echo Waiting for services to initialize...
timeout /t 5 /nobreak >nul

:: Show service status
echo.
echo ========================================
echo    Service Status
echo ========================================
docker compose ps

echo.
echo ========================================
echo    GeoViable is starting!
echo ========================================
echo.
echo Services:
echo   - Frontend:  http://localhost:3000
echo   - Backend:   http://localhost:8000
echo   - Database:  Internal (not exposed)
echo.
echo Useful commands:
echo   View logs:        docker compose logs -f
echo   Stop services:    docker compose down
echo   Reset database:   docker compose down -v ^&^& docker compose up -d
echo.
echo Opening browser...
timeout /t 3 /nobreak >nul
start http://localhost:3000

pause
