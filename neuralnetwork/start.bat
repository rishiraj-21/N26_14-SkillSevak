@echo off
echo ============================================
echo    SkillSevak - Starting All Services
echo ============================================
echo.

:: Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop first.
    pause
    exit /b 1
)

:: Start Redis if not running
docker ps --filter "name=skillsevak-redis" --format "{{.Names}}" | findstr "skillsevak-redis" >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/4] Starting Redis...
    docker start skillsevak-redis 2>nul || docker run -d --name skillsevak-redis -p 6379:6379 --restart unless-stopped redis
) else (
    echo [1/4] Redis already running
)

:: Wait for Redis
timeout /t 2 /nobreak >nul

:: Start Celery Worker
echo [2/4] Starting Celery Worker...
start "Celery Worker" cmd /k "cd /d %~dp0 && celery -A neuralnetwork worker -l info -P solo"

:: Start Celery Beat (scheduler)
echo [3/4] Starting Celery Beat...
start "Celery Beat" cmd /k "cd /d %~dp0 && celery -A neuralnetwork beat -l info"

:: Wait a moment
timeout /t 2 /nobreak >nul

:: Start Django
echo [4/4] Starting Django Server...
start "Django Server" cmd /k "cd /d %~dp0 && python manage.py runserver"

echo.
echo ============================================
echo    All services started!
echo    Open: http://127.0.0.1:8000/
echo ============================================
echo.
echo Windows opened:
echo   - Celery Worker (background tasks)
echo   - Celery Beat (scheduled tasks)
echo   - Django Server (web app)
echo.
echo Press any key to open browser...
pause >nul
start http://127.0.0.1:8000/
