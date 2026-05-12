from fastapi import APIRouter, HTTPException
from ..services import importador_service, job_service
from ..db import get_conn

router = APIRouter()


@router.get("/verificar")
def verificar_xmls():
    """Compara arquivos nas pastas vs banco — retorna os novos não importados."""
    return importador_service.verificar_novos_xmls()


@router.post("/s1210")
def importar_s1210():
    """Dispara importação dos XMLs S-1210 em background. Retorna job_id para polling."""
    try:
        job = importador_service.iniciar_importacao_s1210()
        return {"job_id": job.id, "status": "iniciado"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/s1200")
def importar_s1200():
    """Dispara importação dos XMLs S-1200 complementares em background."""
    try:
        job = importador_service.iniciar_importacao_s1200()
        return {"job_id": job.id, "status": "iniciado"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/s2299")
def importar_s2299():
    """Importa rescisões de ES_S2299 / ES_S2299_detVerbas para ESOCIAL_S1210_COMPL."""
    try:
        job = importador_service.iniciar_importacao_s2299()
        return {"job_id": job.id, "status": "iniciado"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/tudo")
def importar_tudo():
    """Dispara S-1210 e S-1200 em sequência (jobs separados)."""
    jobs = {}
    try:
        j1 = importador_service.iniciar_importacao_s1210()
        jobs["s1210"] = j1.id
    except RuntimeError as e:
        jobs["s1210_erro"] = str(e)

    try:
        j2 = importador_service.iniciar_importacao_s1200()
        jobs["s1200"] = j2.id
    except RuntimeError as e:
        jobs["s1200_erro"] = str(e)

    return jobs


@router.delete("/dados")
def limpar_dados():
    """Apaga todos os registros de ESOCIAL_S1210, detalhe e ESOCIAL_S1210_COMPL do banco ativo."""
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM ESOCIAL_S1210_COMPL")
        n_compl = cur.rowcount
        cur.execute("""
            IF EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210_DETALHE')
                DELETE FROM ESOCIAL_S1210_DETALHE
        """)
        n_detalhe = cur.rowcount
        cur.execute("DELETE FROM ESOCIAL_S1210")
        n_s1210 = cur.rowcount
        conn.commit()
        conn.close()
        return {"removidos_s1210": n_s1210, "removidos_s1210_detalhe": n_detalhe, "removidos_compl": n_compl}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
def listar_jobs():
    return [j.to_dict() for j in job_service.listar_jobs()]


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job.to_dict()
