@echo off
cd /d %~dp0
echo ================================================
echo   Agronil - Informe de Rendimento
echo ================================================
echo.

echo Encerrando instancias anteriores na porta 9000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr "0.0.0.0:9000\|127.0.0.1:9000" ^| findstr "LISTENING"') do (
    echo   Matando PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo Iniciando backend (API)...
start "Backend API" cmd /k "py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 9000 --reload"

timeout /t 3 /nobreak >nul

echo Iniciando frontend (Interface Web)...
start "Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 4 /nobreak >nul

echo.
echo Abrindo navegador...
start http://localhost:5173

echo.
echo Sistema iniciado!
echo   Interface: http://localhost:5173
echo   API docs:  http://localhost:9000/docs
echo.
pause
