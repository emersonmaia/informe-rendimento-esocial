# Dependências — esocial_conferencia

> Gerado pelo Scout em 2026-05-12

---

## Backend Python

**Arquivo:** `requirements_backend.txt`
**Gerenciador:** pip

| Pacote | Versão | Finalidade |
|---|---|---|
| fastapi | 0.135.3 | Framework web ASGI — rotas, validação, OpenAPI automático |
| uvicorn[standard] | 0.44.0 | Servidor ASGI com suporte a WebSockets e reload |
| pyodbc | 5.2.0 | Conector ODBC para Microsoft SQL Server |
| reportlab | 4.4.10 | Geração programática de PDFs (Informes de Rendimento) |
| watchdog | 6.0.0 | Monitoramento de sistema de arquivos |
| apscheduler | 3.11.2 | Scheduler de jobs em background |
| python-multipart | 0.0.26 | Suporte a upload multipart/form-data no FastAPI |
| pdfplumber | 0.11.5 | Leitura e extração de texto de PDFs |

**Runtime Python:** 3.13 (conforme Dockerfile)

---

## Frontend JavaScript

**Arquivo:** `frontend/package.json`
**Gerenciador:** npm (lock: `package-lock.json`)

### Dependências de produção

| Pacote | Versão | Finalidade |
|---|---|---|
| react | ^19.2.5 | Framework de UI |
| react-dom | ^19.2.5 | Renderização React para DOM |
| react-router-dom | ^7.14.2 | Roteamento SPA client-side |
| antd | ^6.3.7 | Biblioteca de componentes UI (Ant Design) |
| @ant-design/icons | ^6.2.2 | Ícones do Ant Design |
| axios | ^1.15.2 | Cliente HTTP para chamadas ao backend |

### Dependências de desenvolvimento

| Pacote | Versão | Finalidade |
|---|---|---|
| vite | ^8.0.10 | Build tool e dev server |
| @vitejs/plugin-react | ^6.0.1 | Plugin Vite para React (Fast Refresh) |
| eslint | ^10.2.1 | Linter JavaScript |
| eslint-plugin-react-hooks | ^7.1.1 | Regras ESLint para hooks React |
| eslint-plugin-react-refresh | ^0.5.2 | Regras ESLint para React Refresh |
| @eslint/js | ^10.0.1 | Configuração base ESLint |
| @types/react | ^19.2.14 | Tipos TypeScript para React |
| @types/react-dom | ^19.2.3 | Tipos TypeScript para React DOM |
| globals | ^17.5.0 | Lista de globals para ESLint |

**Scripts npm:**
```json
{
  "dev":     "vite",
  "build":   "vite build",
  "lint":    "eslint .",
  "preview": "vite preview"
}
```

---

## Dependências de Sistema / Infraestrutura

| Componente | Versão | Observação |
|---|---|---|
| Microsoft ODBC Driver | 17 for SQL Server | Instalado no Dockerfile via apt |
| unixodbc-dev | — | Biblioteca ODBC no Linux |
| Node.js | 20 (slim) | Apenas para build do frontend |
| Python | 3.13 (slim) | Runtime de produção |
| Docker | — | Containerização |
| docker-compose | — | Orquestração local |

---

## Integrações Externas

| Integração | Tipo | Descrição |
|---|---|---|
| Microsoft SQL Server | Banco de dados | Via pyodbc + ODBC Driver 17; multi-banco |
| eSocial (XMLs) | Fonte de dados | Arquivos XML lidos de pastas locais/mapeadas |
| Sistema de Folha Legado | Banco leitura | Tabelas ES_S2299, ES_S1010, FOLFUN consultadas por JOIN |

---

## Vulnerabilidades e Observações

- `CORS allow_origins=["*"]` — backend aceita requisições de qualquer origem (adequado para uso interno/intranet, mas não para exposição pública)
- `connections.json` com credenciais de banco é montado como volume Docker e não deve entrar no git (`.gitignore` deve cobrir isso)
- Sem gerenciamento de versões de banco (migrations): DDL manual via `criar_tabelas_esocial.sql` e verificações `IF NOT EXISTS` inline no código
