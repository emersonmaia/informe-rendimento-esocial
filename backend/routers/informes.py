import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..services import informes_service, job_service
from ..config import ANO_CAL
from ..db import get_pasta_informes

router = APIRouter()


@router.get("")
def listar_informes():
    """Retorna todos os beneficiários com totais e indicação se PDF foi gerado."""
    return informes_service.listar_informes()


@router.post("/gerar")
def gerar_informes():
    """Dispara geração de todos os PDFs em background."""
    try:
        job = informes_service.iniciar_geracao_informes()
        return {"job_id": job.id, "status": "iniciado"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/pdf/{cod_empresa}/{cpf}")
def download_pdf(cod_empresa: str, cpf: str):
    """Download do PDF individual de um beneficiário."""
    nome_arquivo = f"informe_{ANO_CAL}_emp{cod_empresa}_{cpf}.pdf"
    caminho = os.path.join(get_pasta_informes(), nome_arquivo)
    if not os.path.isfile(caminho):
        raise HTTPException(status_code=404, detail="PDF não encontrado. Gere os informes primeiro.")
    return FileResponse(
        caminho,
        media_type="application/pdf",
        filename=nome_arquivo,
    )


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job.to_dict()
