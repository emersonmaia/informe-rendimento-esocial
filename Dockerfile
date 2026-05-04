# ── Estágio 1: build do frontend ─────────────────────────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ── Estágio 2: imagem final (Python + ODBC Driver) ────────────────────────────
FROM python:3.13-slim

# ODBC Driver 17 for SQL Server (necessário para pyodbc)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] \
        https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências Python
COPY requirements_backend.txt .
RUN pip install --no-cache-dir -r requirements_backend.txt

# Código da aplicação
COPY backend/     ./backend/
COPY *.py         ./

# Frontend buildado
COPY --from=frontend-build /frontend/dist ./frontend/dist/

# connections.json é montado como volume em runtime (contém senhas)
# Cria um arquivo vazio para evitar erro se o volume não for montado
RUN echo "[]" > connections.json

EXPOSE 9000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "9000"]
