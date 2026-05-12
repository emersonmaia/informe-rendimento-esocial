#!/bin/bash
# Script de deploy manual para Linux
# Clona o repositório, instala dependências e inicia o sistema

set -e

# 1. Clonar o repositório do GitHub
git clone https://github.com/emersonmaia/esocialconferenciairrfchatgpt.git
cd esocialconferenciairrfchatgpt

# 2. Instalar dependências Python
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements_backend.txt

# 3. Instalar dependências do frontend
cd frontend
npm ci
npm run build
cd ..

# 4. Configurar connections.json
if [ ! -f connections.json ]; then
    cp connections.json.example connections.json
    echo "Edite o arquivo connections.json com os dados do banco e pastas!"
    read -p "Pressione Enter para continuar após editar..."
fi

# 5. Criar tabelas no banco
python3 setup_tabelas.py

# 6. Iniciar o backend
uvicorn backend.main:app --host 0.0.0.0 --port 9000
