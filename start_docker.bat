@echo off
echo Starting Docker services (PostgreSQL + Redis)...
cd /d "%~dp0infra"
docker-compose up -d
echo.
echo Services started:
echo   PostgreSQL: localhost:5432
echo   Redis:      localhost:6379
echo   pgAdmin:    http://localhost:5050
echo.
pause
