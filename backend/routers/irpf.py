from fastapi import APIRouter, HTTPException
from ..db import get_conn
from ..config import ANO_CAL

router = APIRouter()


@router.get("/totais/{cpf}")
def get_totais_cpf(cpf: str):
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")

    cpf_clean = cpf.replace(".", "").replace("-", "").replace(" ", "").zfill(11)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            SUM(REND_TRIB)    AS rend_trib,
            SUM(INSS)         AS inss,
            SUM(IRRF)         AS irrf,
            SUM(REND_TRIB_13) AS rend_trib_13,
            SUM(INSS_13)      AS inss_13,
            SUM(IRRF_13)      AS irrf_13
        FROM (
            SELECT REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13
            FROM ESOCIAL_S1210
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
              AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
            UNION ALL
            SELECT REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13
            FROM ESOCIAL_S1210_COMPL
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
              AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
        ) x
    """, ANO_CAL, cpf_clean, ANO_CAL, cpf_clean)

    r = cur.fetchone()
    conn.close()

    rend13 = float(r.rend_trib_13 or 0) if r else 0
    inss13 = float(r.inss_13 or 0) if r else 0
    irrf13 = float(r.irrf_13 or 0) if r else 0

    return {
        "cpf":       cpf_clean,
        "rend_trib": float(r.rend_trib or 0) if r else 0,
        "inss":      float(r.inss or 0) if r else 0,
        "irrf":      float(r.irrf or 0) if r else 0,
        "rend_trib_13": rend13,
        "inss_13":   inss13,
        "irrf_13":   irrf13,
        "decimo_terceiro_liquido": rend13 - inss13 - irrf13,
    }
