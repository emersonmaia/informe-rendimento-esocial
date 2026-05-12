@echo off
REM Script para subir o projeto para o GitHub (Windows)
REM Certifique-se de já ter git instalado e configurado

REM 1. Inicializa o repositório (caso não esteja inicializado)
git init

REM 2. Adiciona o repositório remoto
git remote add origin https://github.com/emersonmaia/esocialconferenciairrfchatgpt.git

REM 3. Adiciona todos os arquivos, exceto connections.json
git add .
git reset connections.json

REM 4. Commit inicial
git commit -m "Primeiro commit do projeto"

REM 5. Define branch principal
git branch -M main

REM 6. Sobe para o GitHub
git push -u origin main

echo Projeto enviado para o GitHub!
pause
