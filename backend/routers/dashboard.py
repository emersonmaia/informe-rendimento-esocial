import os
from fastapi import APIRouter, HTTPException
from ..db import get_conn, get_pasta_informes
from ..config import ANO_CAL

router = APIRouter()


@router.get("")
def get_dashboard():
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão com o banco: {e}")
    try:
        return _query_dashboard(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar banco: {e}")


def _query_dashboard(conn):
    cur = conn.cursor()

    cur.execute("""
        WITH dados AS (
            SELECT CPF, REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13
            FROM ESOCIAL_S1210
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0 OR INSS > 0 OR INSS_13 > 0)
            UNION ALL
            SELECT CPF, REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13
            FROM ESOCIAL_S1210_COMPL
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0 OR INSS > 0 OR INSS_13 > 0)
        )
        SELECT
            COUNT(DISTINCT CPF)  AS beneficiarios,
            SUM(REND_TRIB)       AS total_rend,
            SUM(INSS)            AS total_inss,
            SUM(IRRF)            AS total_irrf,
            SUM(REND_TRIB_13)    AS total_rend13,
            SUM(INSS_13)         AS total_inss13,
            SUM(IRRF_13)         AS total_irrf13
        FROM dados
    """, ANO_CAL, ANO_CAL)
    r = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM ESOCIAL_S1210")
    total_s1210 = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM ESOCIAL_S1210_COMPL")
    total_compl = cur.fetchone()[0]

    cur.execute("""
        SELECT TOP 5 ARQUIVO, COMPETENCIA, CPF
        FROM ESOCIAL_S1210
        ORDER BY ID DESC
    """)
    ultimas = [{"arquivo": x[0], "competencia": x[1], "cpf": x[2]} for x in cur.fetchall()]

    conn.close()

    pdfs = 0
    pasta = get_pasta_informes()
    if pasta and os.path.isdir(pasta):
        pdfs = sum(1 for f in os.listdir(pasta) if f.endswith(".pdf"))

    return {
        "ano_cal": ANO_CAL,
        "beneficiarios": r[0] or 0,
        "total_rend":    round(float(r[1] or 0), 2),
        "total_inss":    round(float(r[2] or 0), 2),
        "total_irrf":    round(float(r[3] or 0), 2),
        "total_rend13":  round(float(r[4] or 0), 2),
        "total_inss13":  round(float(r[5] or 0), 2),
        "total_irrf13":  round(float(r[6] or 0), 2),
        "registros_s1210": total_s1210,
        "registros_compl": total_compl,
        "pdfs_gerados": pdfs,
        "ultimas_importacoes": ultimas,
    }
