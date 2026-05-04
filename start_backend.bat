@echo off
cd /d %~dp0
echo Iniciando backend Agronil Informe de Rendimento...
echo API disponivel em: http://localhost:9000
echo Documentacao:      http://localhost:9000/docs
echo.
py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 9000 --reload
pause
