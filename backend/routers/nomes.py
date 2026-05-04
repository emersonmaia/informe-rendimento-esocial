"""
CRUD para ESOCIAL_NOME_OVERRIDE — mapeamento manual CPF -> nome
para beneficiarios nao identificados em FOLFUN.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..db import get_conn

router = APIRouter()


class NomeOverride(BaseModel):
    cpf: str   # 11 digitos sem formatacao
    nome: str
    obs: str = ""


def _norm_cpf(cpf: str) -> str:
    return cpf.replace(".", "").replace("-", "").replace(" ", "").zfill(11)


@router.get("")
def listar_overrides():
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    cur.execute("SELECT CPF, NOME, OBS FROM ESOCIAL_NOME_OVERRIDE ORDER BY NOME")
    rows = cur.fetchall()
    conn.close()
    return [{"cpf": r[0], "nome": r[1], "obs": r[2] or ""} for r in rows]


@router.post("")
def salvar_override(body: NomeOverride):
    cpf = _norm_cpf(body.cpf)
    if len(cpf) != 11 or not cpf.isdigit():
        raise HTTPException(status_code=400, detail="CPF deve ter 11 dígitos numéricos")
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    cur.execute("""
        MERGE ESOCIAL_NOME_OVERRIDE AS tgt
        USING (SELECT ? AS CPF, ? AS NOME, ? AS OBS) AS src
            ON tgt.CPF = src.CPF
        WHEN MATCHED THEN UPDATE SET NOME = src.NOME, OBS = src.OBS
        WHEN NOT MATCHED THEN INSERT (CPF, NOME, OBS) VALUES (src.CPF, src.NOME, src.OBS);
    """, cpf, body.nome.strip(), body.obs.strip())
    conn.commit()
    conn.close()
    return {"cpf": cpf, "nome": body.nome.strip()}


@router.delete("/{cpf}")
def remover_override(cpf: str):
    cpf = _norm_cpf(cpf)
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    cur.execute("DELETE FROM ESOCIAL_NOME_OVERRIDE WHERE CPF = ?", cpf)
    n = cur.rowcount
    conn.commit()
    conn.close()
    if n == 0:
        raise HTTPException(status_code=404, detail="CPF não encontrado")
    return {"removido": cpf}
