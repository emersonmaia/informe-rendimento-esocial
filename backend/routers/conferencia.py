from fastapi import APIRouter, HTTPException
from ..db import get_conn
from ..config import ANO_CAL

router = APIRouter()

_CPF_LIMPO_FOLFUN = (
    "RIGHT('00000000000' + "
    "REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)), '.', ''), '-', ''), ' ', ''), 11)"
)


@router.get("")
def get_conferencia():
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")

    cur = conn.cursor()
    cur.execute(f"""
        WITH esocial AS (
            SELECT
                RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) AS cpf_limpo,
                SUM(REND_TRIB)    AS rend_trib,
                SUM(INSS)         AS inss,
                SUM(IRRF)         AS irrf,
                SUM(REND_TRIB_13) AS rend_trib_13,
                SUM(INSS_13)      AS inss_13,
                SUM(IRRF_13)      AS irrf_13,
                COUNT(*)          AS qtd_eventos
            FROM (
                SELECT CPF,
                    CASE WHEN REND_TRIB_13 > 0 AND ABS(REND_TRIB - REND_TRIB_13) < 0.02 THEN 0 ELSE REND_TRIB END AS REND_TRIB,
                    CASE WHEN REND_TRIB_13 > 0 AND ABS(REND_TRIB - REND_TRIB_13) < 0.02 THEN 0 ELSE INSS END AS INSS,
                    CASE WHEN REND_TRIB_13 > 0 AND ABS(REND_TRIB - REND_TRIB_13) < 0.02 THEN 0 ELSE IRRF END AS IRRF,
                    REND_TRIB_13, INSS_13, IRRF_13
                FROM ESOCIAL_S1210
                WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
                  AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
                  AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
                UNION ALL
                SELECT CPF,
                    CASE WHEN REND_TRIB_13 > 0 AND ABS(REND_TRIB - REND_TRIB_13) < 0.02 THEN 0 ELSE REND_TRIB END AS REND_TRIB,
                    CASE WHEN REND_TRIB_13 > 0 AND ABS(REND_TRIB - REND_TRIB_13) < 0.02 THEN 0 ELSE INSS END AS INSS,
                    CASE WHEN REND_TRIB_13 > 0 AND ABS(REND_TRIB - REND_TRIB_13) < 0.02 THEN 0 ELSE IRRF END AS IRRF,
                    REND_TRIB_13, INSS_13, IRRF_13
                FROM ESOCIAL_S1210_COMPL
                WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
                  AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
                  AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
            ) x
            GROUP BY RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11)
        ),
        folfun_dedup AS (
            SELECT
                {_CPF_LIMPO_FOLFUN} AS cpf_limpo,
                NOME,
                TRY_CAST(EMPRESA AS INT) AS EMPRESA,
                ROW_NUMBER() OVER (
                    PARTITION BY {_CPF_LIMPO_FOLFUN}
                    ORDER BY CASE WHEN DATA_RESCISAO IS NULL THEN 0 ELSE 1 END,
                             DATA_RESCISAO DESC
                ) AS rn
            FROM FOLFUN
        )
        SELECT
            e.cpf_limpo,
            ISNULL(f.NOME, ISNULL(ov.NOME, 'NAO IDENTIFICADO')) AS nome,
            ISNULL(CAST(f.EMPRESA AS VARCHAR(10)), '')            AS cod_empresa,
            ISNULL(emp.NOME, '')                                  AS empresa,
            e.rend_trib, e.inss, e.irrf,
            e.rend_trib_13, e.inss_13, e.irrf_13,
            e.qtd_eventos,
            CASE WHEN f.cpf_limpo IS NOT NULL OR ov.CPF IS NOT NULL THEN 1 ELSE 0 END AS identificado
        FROM esocial e
        LEFT JOIN folfun_dedup f ON f.cpf_limpo = e.cpf_limpo AND f.rn = 1
        LEFT JOIN CADEMP emp ON emp.EMPRESA = f.EMPRESA
        LEFT JOIN ESOCIAL_NOME_OVERRIDE ov ON ov.CPF = e.cpf_limpo
        ORDER BY identificado ASC, emp.NOME, ISNULL(f.NOME, ov.NOME)
    """, ANO_CAL, ANO_CAL)

    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        rend13 = float(r.rend_trib_13 or 0)
        inss13 = float(r.inss_13 or 0)
        irrf13 = float(r.irrf_13 or 0)
        result.append({
            "cpf":        r.cpf_limpo,
            "nome":       r.nome,
            "cod_empresa": r.cod_empresa,
            "empresa":    r.empresa,
            "rend_trib":  float(r.rend_trib or 0),
            "inss":       float(r.inss or 0),
            "irrf":       float(r.irrf or 0),
            "rend_trib_13": rend13,
            "inss_13":    inss13,
            "irrf_13":    irrf13,
            "decimo_terceiro_liquido": rend13 - inss13 - irrf13,
            "qtd_eventos": r.qtd_eventos,
            "identificado": bool(r.identificado),
        })
    return result


@router.get("/por_mes/{cpf}")
def get_por_mes(cpf: str):
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")

    cpf_clean = cpf.replace(".", "").replace("-", "").replace(" ", "").zfill(11)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COMPETENCIA,
            DT_PAGTO,
            REND_TRIB, INSS, IRRF,
            REND_TRIB_13, INSS_13, IRRF_13,
            'S1210' AS origem
        FROM ESOCIAL_S1210
        WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
          AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
          AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
          AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
        UNION ALL
        SELECT
            COMPETENCIA,
            DT_PAGTO,
            REND_TRIB, INSS, IRRF,
            REND_TRIB_13, INSS_13, IRRF_13,
            'S1200' AS origem
        FROM ESOCIAL_S1210_COMPL
        WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
          AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
          AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
          AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
        ORDER BY DT_PAGTO, COMPETENCIA
    """, ANO_CAL, cpf_clean, ANO_CAL, cpf_clean)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "competencia":  r.COMPETENCIA,
            "dt_pagto":     str(r.DT_PAGTO),
            "rend_trib":    float(r.REND_TRIB or 0),
            "inss":         float(r.INSS or 0),
            "irrf":         float(r.IRRF or 0),
            "rend_trib_13": float(r.REND_TRIB_13 or 0),
            "inss_13":      float(r.INSS_13 or 0),
            "irrf_13":      float(r.IRRF_13 or 0),
            "origem":       r.origem,
        }
        for r in rows
    ]
