@echo off
cd /d %~dp0
echo ================================================
echo   Agronil - Informe de Rendimento (SERVIDOR)
echo ================================================
echo.

echo [1/3] Encerrando instancias anteriores na porta 9000...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":9000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo [2/3] Gerando build do frontend...
cd frontend
call npm run build
if errorlevel 1 (
    echo ERRO ao gerar build do frontend!
    pause
    exit /b 1
)
cd ..

echo [3/3] Iniciando servidor (porta 9000, acessivel na rede)...
echo.
echo  Acesse pelo navegador:
echo    Neste computador : http://localhost:9000
echo    Outros na rede   : http://%COMPUTERNAME%:9000
echo    ou pelo IP       : http://SEU_IP:9000
echo.
py -3 -m uvicorn backend.main:app --host 0.0.0.0 --port 9000
pause
