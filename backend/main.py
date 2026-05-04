"""
Backend FastAPI — Agronil Informe de Rendimento
Dev:  uvicorn backend.main:app --reload --port 9000
Prod: uvicorn backend.main:app --host 0.0.0.0 --port 9000
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import dashboard, importacao, informes, configuracao, conferencia, conferencia_folha, irpf, nomes

app = FastAPI(
    title="Agronil — Informe de Rendimento",
    description="API para importação de XMLs eSocial e geração de Informes de Rendimento",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(configuracao.router,  prefix="/api/config",       tags=["Configuração"])
app.include_router(dashboard.router,    prefix="/api/dashboard",    tags=["Dashboard"])
app.include_router(importacao.router,   prefix="/api/importacao",   tags=["Importação"])
app.include_router(informes.router,     prefix="/api/informes",     tags=["Informes"])
app.include_router(conferencia.router,       prefix="/api/conferencia",        tags=["Conferência"])
app.include_router(conferencia_folha.router, prefix="/api/conferencia-folha",   tags=["Conferência Folha"])
app.include_router(irpf.router,         prefix="/api/irpf",         tags=["IRPF"])
app.include_router(nomes.router,        prefix="/api/nomes",         tags=["Nomes Override"])


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"status": "ok", "versao": "1.0.0"}


# ── Serve o frontend buildado (produção) ────────────────────────────────────
# Em dev o Vite roda separado; em produção o build fica em frontend/dist/
_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    # Qualquer rota que não seja /api → devolve o index.html (SPA routing)
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        return FileResponse(str(_DIST / "index.html"))
