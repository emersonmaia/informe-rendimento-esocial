# Informe de Rendimento eSocial

Sistema web para importação de XMLs do eSocial (S-1210, S-1200) e geração de
Informes de Rendimento em PDF (IN RFB nº 2.060/2021), com suporte a múltiplas empresas.

---

# esocialconferenciairrfchatgpt

Este repositório permite importar XMLs do eSocial e gerar Informes de Rendimento em PDF.

## Como rodar

Veja os scripts `deploy_manual_windows.bat` e `deploy_manual_linux.sh` para deploy manual.

## Deploy via Docker

Consulte as instruções abaixo ou o arquivo original para detalhes completos.

## Instalação com Docker (recomendado)

> Não precisa instalar Python, Node.js nem ODBC Driver. Só precisa do Docker.

### 1. Instale o Docker Desktop

- Windows: https://www.docker.com/products/docker-desktop/
- Linux: `curl -fsSL https://get.docker.com | sh`

### 2. Clone o repositório

```bat
git clone https://github.com/emersonmaia/informe-rendimento-esocial.git
cd informe-rendimento-esocial
```

### 3. Configure as conexões

```bat
copy connections.json.example connections.json
notepad connections.json
```

Preencha com os dados de cada empresa:

```json
[
  {
    "id": "empresa1",
    "nome": "Nome da Empresa",
    "server": "IP_DO_SQL_SERVER",
    "database": "nome_do_banco",
    "uid": "sa",
    "pwd": "senha",
    "pasta_xml_s1210": "C:\\caminho\\para\\xmls\\s1210",
    "pasta_xml_s1200": "C:\\caminho\\para\\xmls\\s1200",
    "pasta_informes": "C:\\caminho\\para\\pdfs"
  }
]
```

### 4. Ajuste os volumes no docker-compose.yml

Edite `docker-compose.yml` e aponte os caminhos das pastas de XML/PDF do servidor:

```yaml
volumes:
  - ./connections.json:/app/connections.json
  - C:\brven:/brven # ajuste para o caminho real no servidor
  - D:\dados:/agronil # ajuste para o caminho real no servidor
```

### 5. Suba o container

```bat
docker compose up -d --build
```

O sistema estará disponível em: **http://localhost:9000**

(ou `http://IP_DO_SERVIDOR:9000` para outros usuários na rede)

### Comandos úteis

```bat
:: Ver logs em tempo real
docker compose logs -f

:: Parar
docker compose down

:: Atualizar após novo git pull
docker compose up -d --build
```

---

## Instalação manual (sem Docker)

Requer: Python 3.11+, Node.js 18+, ODBC Driver 17 for SQL Server.

```bat
git clone https://github.com/emersonmaia/informe-rendimento-esocial.git
cd informe-rendimento-esocial
setup.bat
```

Após o setup:

```bat
start_servidor.bat
```

---

## Estrutura

```
backend/          # API FastAPI
frontend/         # Interface React/Vite
setup_tabelas.py  # Cria as tabelas eSocial no SQL Server
connections.json  # Configuração local (NÃO commitar — tem senhas)
```

---

## Criar tabelas no banco (primeira vez)

Antes de importar, crie as tabelas eSocial em cada banco:

```bat
py -3 setup_tabelas.py
```
