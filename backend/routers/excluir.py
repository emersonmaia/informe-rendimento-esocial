"""
Exclusão de linhas eSocial da soma do informe.
Marca registros de ESOCIAL_S1210 ou ESOCIAL_S1210_COMPL como
"não somar" sem remover os dados originais.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..db import get_conn

router = APIRouter()


class Exclusao(BaseModel):
    tabela: str   # 'S1210' ou 'COMPL'
    row_id: int
    cpf: str
    motivo: str = ""


def _garantir_tabela(cur) -> None:
    cur.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210_EXCLUIR')
        CREATE TABLE ESOCIAL_S1210_EXCLUIR (
            ID        INT IDENTITY(1,1) PRIMARY KEY,
            TABELA    VARCHAR(10) NOT NULL,
            ROW_ID    INT NOT NULL,
            CPF       VARCHAR(20) NOT NULL,
            MOTIVO    VARCHAR(300) NULL,
            CRIADO_EM DATETIME    NOT NULL DEFAULT GETDATE()
        )
    """)
    cur.connection.commit()


@router.get("/{cpf}")
def listar_exclusoes(cpf: str):
    cpf = cpf.replace('.', '').replace('-', '').replace(' ', '').zfill(11)
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    _garantir_tabela(cur)
    cur.execute("""
        SELECT ID, TABELA, ROW_ID, CPF, MOTIVO, CRIADO_EM
        FROM ESOCIAL_S1210_EXCLUIR
        WHERE RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
        ORDER BY ID
    """, cpf)
    rows = cur.fetchall()
    conn.close()
    return [{"id": r.ID, "tabela": r.TABELA, "row_id": r.ROW_ID,
             "cpf": r.CPF, "motivo": r.MOTIVO or ""} for r in rows]


@router.post("")
def excluir_linha(body: Exclusao):
    if body.tabela not in ('S1210', 'COMPL'):
        raise HTTPException(status_code=400, detail="tabela deve ser 'S1210' ou 'COMPL'")
    cpf = body.cpf.replace('.', '').replace('-', '').replace(' ', '').zfill(11)
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    _garantir_tabela(cur)
    cur.execute(
        "SELECT ID FROM ESOCIAL_S1210_EXCLUIR WHERE TABELA=? AND ROW_ID=?",
        body.tabela, body.row_id
    )
    existing = cur.fetchone()
    if existing:
        conn.close()
        return {"id": existing.ID, "tabela": body.tabela, "row_id": body.row_id}
    cur.execute(
        "INSERT INTO ESOCIAL_S1210_EXCLUIR (TABELA, ROW_ID, CPF, MOTIVO) VALUES (?,?,?,?)",
        body.tabela, body.row_id, cpf, (body.motivo or '').strip()
    )
    cur.execute("SELECT CAST(SCOPE_IDENTITY() AS INT)")
    new_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return {"id": new_id, "tabela": body.tabela, "row_id": body.row_id}


@router.delete("/{exclusao_id}")
def restaurar_linha(exclusao_id: int):
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    cur = conn.cursor()
    _garantir_tabela(cur)
    cur.execute("DELETE FROM ESOCIAL_S1210_EXCLUIR WHERE ID=?", exclusao_id)
    n = cur.rowcount
    conn.commit()
    conn.close()
    if n == 0:
        raise HTTPException(status_code=404, detail="Exclusão não encontrada")
    return {"restaurado": exclusao_id}
