@echo off
REM Script de deploy manual para Windows
REM Clona o repositório, instala dependências e inicia o sistema

REM 1. Clonar o repositório do GitHub
git clone https://github.com/emersonmaia/esocialconferenciairrfchatgpt.git
cd esocialconferenciairrfchatgpt

REM 2. Instalar dependências Python
pip install -r requirements_backend.txt

REM 3. Instalar dependências do frontend
cd frontend
npm ci
npm run build
cd ..

REM 4. Configurar connections.json
IF NOT EXIST connections.json (
    copy connections.json.example connections.json
    echo Edite o arquivo connections.json com os dados do banco e pastas!
    pause
)

REM 5. Criar tabelas no banco
python setup_tabelas.py

REM 6. Iniciar o backend
uvicorn backend.main:app --host 0.0.0.0 --port 9000
