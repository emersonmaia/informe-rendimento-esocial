# Inventário do Projeto — esocial_conferencia

> Gerado pelo Scout em 2026-05-12
> Projeto: Agronil — Informe de Rendimento eSocial
> Linguagem principal: Python (FastAPI) + React

---

## 1. Visão Geral

Sistema web full-stack para importação de XMLs do eSocial (eventos S-1210, S-1200, S-5001, S-5002, S-5003, S-5011, S-2299) e geração de Informes de Rendimento (IRRF) em PDF para múltiplos clientes (multi-banco SQL Server).

**Ano calendário configurado:** 2025 (exercício 2026)

---

## 2. Estrutura de Pastas

```
chatgpt/
├── backend/                  ← API FastAPI
│   ├── __init__.py
│   ├── config.py             ← constantes ANO_CAL, EXERCICIO
│   ├── db.py                 ← gerenciamento de conexões SQL Server
│   ├── main.py               ← entry point FastAPI, registro de routers
│   ├── importar_s5001.py     ← script standalone de importação S-5001
│   ├── routers/
│   │   ├── ajustes_manuais.py       ← /api/ajustes-manuais
│   │   ├── conferencia.py           ← /api/conferencia
│   │   ├── conferencia_folha.py     ← /api/conferencia-folha
│   │   ├── configuracao.py          ← /api/config
│   │   ├── dashboard.py             ← /api/dashboard
│   │   ├── excluir.py               ← /api/excluir
│   │   ├── importacao.py            ← /api/importacao
│   │   ├── informes.py              ← /api/informes
│   │   ├── irpf.py                  ← /api/irpf
│   │   ├── nomes.py                 ← /api/nomes
│   │   └── pendencias_esocial.py    ← /api/pendencias-esocial
│   └── services/
│       ├── importador_service.py    ← lógica de importação XML (S-1210, S-1200, S-2299)
│       ├── informes_service.py      ← geração de PDFs (delega a gerar_informes.py)
│       └── job_service.py           ← controle de jobs assíncronos (threading)
├── frontend/                 ← SPA React + Ant Design
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── eslint.config.js
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── main.jsx          ← entry point React
│       ├── App.jsx           ← roteamento SPA, layout, modais de config
│       ├── App.css
│       ├── api.js            ← cliente Axios para o backend
│       ├── index.css
│       ├── assets/
│       └── pages/
│           ├── Dashboard.jsx           ← totalizadores gerais
│           ├── Importacao.jsx          ← disparo e polling de jobs de importação
│           ├── Informes.jsx            ← listagem e geração de PDFs
│           ├── Conferencia.jsx         ← conferência por funcionário
│           ├── ConferenciaFolha.jsx    ← folha×eSocial
│           ├── ConferenciaFuncionario.jsx ← detalhamento por CPF
│           ├── PendenciasEsocial.jsx   ← pendências
│           └── ComparacaoIRPF.jsx      ← comparação de IRPF declarado
├── DADOS_SQL_IMPORT/         ← arquivos CSV de ajuste manual
│   ├── AJUSTES_FERIAS_FLAVIO_ANALITICO.csv
│   ├── AJUSTES_FERIAS_FLAVIO_RESUMO.csv
│   ├── RETORNO_LOTE_RUBRICAS.csv
│   └── RETORNO_LOTE_S5002.csv
├── ── Scripts legados (raiz) ─────────────────────────────────────────────
│   ├── gerar_informes.py             ← gerador de PDFs (usado como módulo)
│   ├── gerar_informes_brven.py       ← variante para cliente brven
│   ├── importador_principal.py       ← importador S-1210 legado
│   ├── importador_brven.py           ← variante brven
│   ├── importador_s1200_compl.py     ← importador S-1200 complementar
│   ├── importador_xml_baixado_pelo_sistema_protocolo.py
│   ├── main_importador.py            ← CLI legado
│   ├── parser_s1210.py               ← parser XML S-1210
│   ├── parser_s5001.py               ← parser XML S-5001
│   ├── parser_s5002.py               ← parser XML S-5002
│   ├── db.py                         ← cópia legada da conexão (raiz)
│   ├── setup_tabelas.py              ← criação de tabelas
│   ├── setup_tabelas_mvr.py          ← variante MVR
│   ├── buscar_s1210_anual.py
│   ├── buscar_s5002_anual.py
│   ├── cadastrar_nomes_override.py
│   ├── conferencia_folha_esocial.py
│   ├── criar_tabela_override.py
│   ├── criar_tabela_override_agronil.py
│   ├── validar_ajustes_ferias_flavio.py
│   ├── analise_alinhamento.py
│   ├── importar_kiko_novo.py
│   ├── regerar_sergio.py
│   ├── remover_lilian_mirella.py
│   ├── ver_xml_bruto.py
│   ├── verificar_meses.py
│   ├── verificar_xml_13.py
│   └── diagnostico_*.py / investigar_*.py / inspecionar_*.py  (scripts de debug)
├── ── Infraestrutura ─────────────────────────────────────────────────────
│   ├── Dockerfile                  ← multi-stage: Node build + Python runtime
│   ├── docker-compose.yml          ← porta 9000, volumes: connections.json + pastas XML
│   ├── requirements_backend.txt    ← dependências Python
│   ├── connections.json.example    ← template de configuração multi-banco
│   ├── connections.json            ← arquivo real (fora do git, montado como volume)
│   ├── setup.bat                   ← setup Windows
│   ├── start_app.bat               ← inicialização rápida
│   ├── start_backend.bat
│   └── start_servidor.bat
├── ── Banco de Dados ──────────────────────────────────────────────────────
│   └── criar_tabelas_esocial.sql   ← DDL para folha_flavio, folha_kiko, folha_beatriz
├── ── Documentação / Modelos ──────────────────────────────────────────────
│   ├── Modelo_Rendimentos.pdf
│   ├── modelo_informe_rendimento_2025.pdf
│   ├── informe_rendimento_10.pdf
│   ├── declaracao_*.pdf
│   ├── views_conferencia_folha_esocial.txt
│   └── analise_projeto.md
└── ── Configuração ──────────────────────────────────────────────────────
    ├── .gitignore
    └── README.md
```

---

## 3. Tecnologias e Frameworks

### Backend — Python

| Componente | Tecnologia | Versão |
|---|---|---|
| Framework web | FastAPI | 0.135.3 |
| Servidor ASGI | Uvicorn | 0.44.0 |
| Banco de dados | SQL Server via pyodbc | 5.2.0 |
| Geração de PDF | ReportLab | 4.4.10 |
| Scheduler/Jobs | APScheduler | 3.11.2 |
| File watching | Watchdog | 6.0.0 |
| Upload multipart | python-multipart | 0.0.26 |
| Leitura PDF | pdfplumber | 0.11.5 |

### Frontend — JavaScript/React

| Componente | Tecnologia | Versão |
|---|---|---|
| UI Framework | React | 19.2.5 |
| Componentes UI | Ant Design | 6.3.7 |
| Roteamento | React Router DOM | 7.14.2 |
| HTTP Client | Axios | 1.15.2 |
| Build tool | Vite | 8.0.10 |
| Ícones | @ant-design/icons | 6.2.2 |

### Infraestrutura

| Componente | Tecnologia |
|---|---|
| Containerização | Docker (multi-stage), docker-compose |
| Banco de dados | Microsoft SQL Server (ODBC Driver 17) |
| Runtime Python | Python 3.13 (Debian slim) |
| Runtime Node | Node 20 (build only) |

---

## 4. Pontos de Entrada

| Arquivo | Tipo | Descrição |
|---|---|---|
| `backend/main.py` | server_entry | FastAPI app — registra todos os routers |
| `frontend/src/main.jsx` | app_entry | React SPA bootstrap |
| `frontend/index.html` | html_entry | HTML shell da SPA |
| `main_importador.py` | cli_legacy | CLI de importação legado |

**Comando de desenvolvimento:**
```
uvicorn backend.main:app --reload --port 9000
cd frontend && npm run dev
```

**Comando de produção (Docker):**
```
docker-compose up -d
```

---

## 5. APIs Registradas (backend/main.py)

| Prefixo | Router | Tag |
|---|---|---|
| `/api/config` | configuracao.router | Configuração |
| `/api/dashboard` | dashboard.router | Dashboard |
| `/api/importacao` | importacao.router | Importação |
| `/api/informes` | informes.router | Informes |
| `/api/conferencia` | conferencia.router | Conferência |
| `/api/conferencia-folha` | conferencia_folha.router | Conferência Folha |
| `/api/irpf` | irpf.router | IRPF |
| `/api/nomes` | nomes.router | Nomes Override |
| `/api/ajustes-manuais` | ajustes_manuais.router | Ajustes Manuais |
| `/api/pendencias-esocial` | pendencias_esocial.router | Pendências eSocial |
| `/api/excluir` | excluir.router | Exclusão de Linhas |
| `/api/health` | inline | Sistema |

---

## 6. Banco de Dados

**SGBD:** Microsoft SQL Server
**Gerenciador de conexões:** `backend/db.py` — lê `connections.json`, suporta múltiplos bancos, troca ativa em runtime

**Bancos configurados:**
- `folha_agronil` — banco principal (tabelas já existentes)
- `folha_flavio`, `folha_kiko`, `folha_beatriz` — criados via `criar_tabelas_esocial.sql`

**Tabelas eSocial (por banco):**

| Tabela | Descrição |
|---|---|
| `ESOCIAL_S1210` | Totalizadores de pagamento (evento S-1210/S-1200) |
| `ESOCIAL_S1210_DETALHE` | Detalhe por dmDev/infoPgto |
| `ESOCIAL_S1210_COMPL` | Complementos: S-5001 (INSS férias), S-2299 (rescisão), S-1200 |
| `ESOCIAL_INFORME_AJUSTE_MANUAL` | Ajustes manuais de rendimento |
| `ESOCIAL_NOME_OVERRIDE` | Nomes de CPFs não identificados no cadastro |
| `ESOCIAL_S5001` | Bases de cálculo INSS (inativo, substituído por COMPL) |
| `ESOCIAL_S5002` | Bases IRRF por competência |
| `ESOCIAL_S5003` | Bases FGTS |
| `ESOCIAL_S5011` | Apuração patronal |
| `ESOCIAL_CONFIG` | Configurações chave-valor por banco |

**Tabelas legadas (sistema de origem — leitura apenas):**

| Tabela | Origem |
|---|---|
| `ES_S2299` | Sistema de folha legado — cabeçalho rescisão |
| `ES_S2299_detVerbas` | Detalhe de verbas rescisórias |
| `ES_S1010` | Tabela de rubricas (classificação natRubr/tpRubr) |
| `FOLFUN` | Cadastro de funcionários (fonte de nomes) |

**DDL:** `criar_tabelas_esocial.sql`

---

## 7. Configuração de Ambiente

**Arquivo:** `connections.json` (fora do git, montado como volume Docker)

```json
[
  {
    "id": "empresa1",
    "nome": "Nome da Empresa",
    "server": "IP_DO_SQL_SERVER",
    "database": "nome_do_banco",
    "uid": "sa",
    "pwd": "senha",
    "pasta_xml_s1210": "C:\\caminho\\xmls\\s1210",
    "pasta_xml_s1200": "C:\\caminho\\xmls\\s1200",
    "pasta_informes": "C:\\caminho\\pdfs"
  }
]
```

**Constantes:** `backend/config.py`
```python
ANO_CAL   = 2025
EXERCICIO = 2026
```

---

## 8. Docker e Implantação

**Dockerfile:** multi-stage
1. Estágio 1: `node:20-slim` — build do frontend com `npm ci && npm run build`
2. Estágio 2: `python:3.13-slim` — instala ODBC Driver 17, dependências Python, copia backend + dist frontend

**docker-compose.yml:**
- Porta: `9000:9000`
- Volumes: `connections.json` (runtime), pastas de XMLs e PDFs do host

**Endereços configurados:**
- Servidor: porta 9000
- SPA fallback: qualquer rota não-`/api` serve `index.html`

---

## 9. Cobertura de Testes

**Frameworks de teste detectados:** Nenhum
**Arquivos de teste (*.test.*, *.spec.*):** 0
**CI/CD:** Nenhum detectado

---

## 10. Contagem de Arquivos por Tipo

| Tipo | Extensão | Quantidade |
|---|---|---|
| Python | .py | 74 |
| React/JSX | .jsx | 10 |
| JavaScript | .js | 4 |
| SQL | .sql | 1 |
| Outros | csv, pdf, json, md, bat, toml, txt, svg, css, html | ~72 |
| **Total** | | **~161** |

---

## 11. Módulos Identificados

| Módulo | Descrição |
|---|---|
| `configuracao` | Gerenciamento de conexões multi-banco |
| `dashboard` | Totalizadores e resumo estatístico |
| `importacao` | Importação de XMLs eSocial (S-1210, S-1200, S-2299) |
| `informes` | Geração de PDFs de Informe de Rendimento |
| `conferencia` | Conferência de dados por funcionário |
| `conferencia_folha` | Comparação folha×eSocial |
| `irpf` | Comparação de IRPF declarado |
| `nomes` | Override de nomes de beneficiários |
| `ajustes_manuais` | Ajustes manuais de rendimento |
| `pendencias_esocial` | Pendências e inconsistências eSocial |
| `excluir` | Exclusão de linhas do banco |

---

## 12. Observações Arquiteturais

- **Multi-tenant por banco:** cada conexão em `connections.json` aponta para um banco SQL Server diferente; a troca é feita em runtime via `/api/config/ativar`
- **Jobs assíncronos:** importações rodam em threads separadas; o frontend faz polling via job_id
- **Scripts legados na raiz:** há ~50 scripts Python standalone (diagnóstico, debugging, importação pontual) que não fazem parte do servidor, mas o `informes_service.py` e `importador_service.py` importam `gerar_informes.py` e `importador_s1200_compl.py` da raiz via `sys.path`
- **Sem testes automatizados:** o projeto não possui suite de testes
- **Sem CI/CD:** não há pipelines configurados
