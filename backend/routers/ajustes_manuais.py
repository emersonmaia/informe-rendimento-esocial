"""
Ajustes manuais mensais — lançamentos que complementam ou corrigem os dados
importados dos XMLs/tabelas eSocial.

Armazena em ESOCIAL_INFORME_AJUSTE_MANUAL (que faz parte da camada intermediária
somada para gerar o informe anual junto com ESOCIAL_S1210 e ESOCIAL_S1210_COMPL).
"""
import calendar
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from ..db import get_conn
from ..config import ANO_CAL

router = APIRouter()

_RE_COMP = re.compile(r'^\d{4}-\d{2}$')


class AjusteManual(BaseModel):
    id: Optional[int] = None
    cpf: str
    empresa: Optional[int] = None
    competencia: str                   # obrigatório, formato YYYY-MM
    dt_pagto: Optional[str] = None    # se vazio deriva do último dia da competência
    rend_trib: float = 0
    inss: float = 0
    irrf: float = 0
    rend_trib_13: float = 0
    inss_13: float = 0
    irrf_13: float = 0
    cod_receita: str = ""
    obs: str = ""

    @field_validator('competencia')
    @classmethod
    def validar_competencia(cls, v):
        v = (v or '').strip()
        if not _RE_COMP.match(v):
            raise ValueError('Competência deve estar no formato YYYY-MM (ex: 2025-11)')
        return v


def _norm_cpf(cpf: str) -> str:
    return cpf.replace(".", "").replace("-", "").replace(" ", "").zfill(11)


def _derivar_dt_pagto(competencia: str, dt_fornecido: Optional[str]) -> str:
    """Retorna dt_pagto fornecido ou, se vazio, o último dia da competência."""
    if dt_fornecido and dt_fornecido.strip():
        return dt_fornecido.strip()
    ano, mes = int(competencia[:4]), int(competencia[5:7])
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return f"{ano}-{mes:02d}-{ultimo_dia:02d}"


def _garantir_tabela(cur) -> None:
    cur.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_INFORME_AJUSTE_MANUAL')
        CREATE TABLE ESOCIAL_INFORME_AJUSTE_MANUAL (
            ID           INT IDENTITY(1,1) PRIMARY KEY,
            CPF          VARCHAR(20)   NOT NULL,
            EMPRESA      INT           NULL,
            COMPETENCIA  VARCHAR(10)   NOT NULL,
            DT_PAGTO     VARCHAR(20)   NOT NULL,
            REND_TRIB    DECIMAL(18,2) NOT NULL DEFAULT 0,
            INSS         DECIMAL(18,2) NOT NULL DEFAULT 0,
            IRRF         DECIMAL(18,2) NOT NULL DEFAULT 0,
            REND_TRIB_13 DECIMAL(18,2) NOT NULL DEFAULT 0,
            INSS_13      DECIMAL(18,2) NOT NULL DEFAULT 0,
            IRRF_13      DECIMAL(18,2) NOT NULL DEFAULT 0,
            COD_RECEITA  VARCHAR(20)   NULL,
            OBS          VARCHAR(300)  NULL,
            CRIADO_EM    DATETIME      NOT NULL DEFAULT GETDATE()
        )
    """)


@router.get("")
def listar_ajustes():
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    _garantir_tabela(cur)
    cur.execute("""
        SELECT ID, CPF, EMPRESA, COMPETENCIA, DT_PAGTO,
               REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13,
               COD_RECEITA, OBS, CRIADO_EM
        FROM ESOCIAL_INFORME_AJUSTE_MANUAL
        ORDER BY COMPETENCIA DESC, CPF, ID DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [{
        "id": r.ID,
        "cpf": r.CPF,
        "empresa": r.EMPRESA,
        "competencia": r.COMPETENCIA,
        "dt_pagto": r.DT_PAGTO,
        "rend_trib": float(r.REND_TRIB or 0),
        "inss": float(r.INSS or 0),
        "irrf": float(r.IRRF or 0),
        "rend_trib_13": float(r.REND_TRIB_13 or 0),
        "inss_13": float(r.INSS_13 or 0),
        "irrf_13": float(r.IRRF_13 or 0),
        "cod_receita": r.COD_RECEITA or "",
        "obs": r.OBS or "",
        "criado_em": r.CRIADO_EM.isoformat() if r.CRIADO_EM else None,
    } for r in rows]


@router.post("")
def salvar_ajuste(body: AjusteManual):
    cpf = _norm_cpf(body.cpf)
    if len(cpf) != 11 or not cpf.isdigit():
        raise HTTPException(status_code=400, detail="CPF deve ter 11 dígitos numéricos")

    competencia = body.competencia.strip()
    dt_pagto    = _derivar_dt_pagto(competencia, body.dt_pagto)

    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    _garantir_tabela(cur)

    if body.id:
        cur.execute("""
            UPDATE ESOCIAL_INFORME_AJUSTE_MANUAL
               SET CPF = ?, EMPRESA = ?, COMPETENCIA = ?, DT_PAGTO = ?,
                   REND_TRIB = ?, INSS = ?, IRRF = ?,
                   REND_TRIB_13 = ?, INSS_13 = ?, IRRF_13 = ?,
                   COD_RECEITA = ?, OBS = ?
             WHERE ID = ?
        """,
        cpf, body.empresa, competencia, dt_pagto,
        body.rend_trib, body.inss, body.irrf,
        body.rend_trib_13, body.inss_13, body.irrf_13,
        (body.cod_receita or '').strip(), (body.obs or '').strip(), body.id)
        if cur.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Ajuste manual não encontrado")
        ajuste_id = body.id
    else:
        cur.execute("""
            INSERT INTO ESOCIAL_INFORME_AJUSTE_MANUAL
                (CPF, EMPRESA, COMPETENCIA, DT_PAGTO,
                 REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13,
                 COD_RECEITA, OBS)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        cpf, body.empresa, competencia, dt_pagto,
        body.rend_trib, body.inss, body.irrf,
        body.rend_trib_13, body.inss_13, body.irrf_13,
        (body.cod_receita or '').strip(), (body.obs or '').strip())
        cur.execute("SELECT CAST(SCOPE_IDENTITY() AS INT)")
        ajuste_id = cur.fetchone()[0]

    conn.commit()
    conn.close()
    return {"id": ajuste_id, "cpf": cpf, "competencia": competencia, "dt_pagto": dt_pagto}


@router.delete("/{ajuste_id}")
def remover_ajuste(ajuste_id: int):
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    _garantir_tabela(cur)
    cur.execute("DELETE FROM ESOCIAL_INFORME_AJUSTE_MANUAL WHERE ID = ?", ajuste_id)
    n = cur.rowcount
    conn.commit()
    conn.close()
    if n == 0:
        raise HTTPException(status_code=404, detail="Ajuste manual não encontrado")
    return {"removido": ajuste_id}
