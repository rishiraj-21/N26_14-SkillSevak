@echo off
echo ============================================
echo    SkillSevak - Stopping All Services
echo ============================================
echo.

:: Kill Django
echo [1/3] Stopping Django...
taskkill /FI "WINDOWTITLE eq Django Server*" /F >nul 2>&1

:: Kill Celery
echo [2/3] Stopping Celery...
taskkill /FI "WINDOWTITLE eq Celery Worker*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Celery Beat*" /F >nul 2>&1

:: Optionally stop Redis (keep running for faster restart)
echo [3/3] Redis kept running (for faster restart)
echo      To stop Redis: docker stop skillsevak-redis

echo.
echo ============================================
echo    All services stopped!
echo ============================================
pause
