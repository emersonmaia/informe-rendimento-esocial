@echo off
cd /d %~dp0
echo ================================================
echo   Setup - Informe de Rendimento
echo ================================================
echo.

:: Verifica Python
py -3 --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado.
    echo Baixe em https://www.python.org/downloads/ e marque "Add to PATH"
    pause & exit /b 1
)

:: Verifica Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Node.js nao encontrado.
    echo Baixe em https://nodejs.org/
    pause & exit /b 1
)

echo [1/4] Instalando dependencias Python...
py -3 -m pip install --upgrade pip --quiet
py -3 -m pip install -r requirements_backend.txt
if errorlevel 1 ( echo ERRO ao instalar Python! & pause & exit /b 1 )

echo [2/4] Instalando dependencias do frontend...
cd frontend
call npm install --silent
if errorlevel 1 ( echo ERRO ao instalar Node! & pause & exit /b 1 )
cd ..

echo [3/4] Gerando build do frontend...
cd frontend
call npm run build
if errorlevel 1 ( echo ERRO no build! & pause & exit /b 1 )
cd ..

echo [4/4] Configurando connections.json...
if not exist connections.json (
    copy connections.json.example connections.json
    echo.
    echo  ATENCAO: Edite o arquivo connections.json com os dados do seu banco
    echo  antes de iniciar o sistema.
    echo.
    notepad connections.json
)

echo.
echo ================================================
echo   Setup concluido!
echo   Para iniciar: start_servidor.bat
echo ================================================
pause
