from fastapi import APIRouter, HTTPException, Query
from ..db import get_conn

router = APIRouter()

_CPF_FOLFUN = (
    "RIGHT('00000000000' + REPLACE(REPLACE(REPLACE("
    "ISNULL(CAST(fu.CPF AS VARCHAR(20)),''), '.',''), '-',''), ' ',''), 11)"
)

_SQL = """
WITH folha AS (
    SELECT
        {cpf}                                AS CPF_LIMPO,
        MAX(fu.NOME)                         AS NOME,
        ft.MES                               AS MES_COMP,
        ft.ANO                               AS ANO_COMP,
        CAST(MAX(fe.DATA_PAGAMENTO) AS DATE) AS DATA_PGTO,
        SUM(ft.INSS)                         AS FOLHA_INSS,
        CASE
            WHEN ft.MES < 12
            THEN CONCAT(CAST(ft.ANO AS VARCHAR(4)), '-',
                        RIGHT('0' + CAST((ft.MES + 1) AS VARCHAR(2)), 2))
            ELSE CONCAT(CAST((ft.ANO + 1) AS VARCHAR(4)), '-01')
        END                                  AS COMP_PAGTO
    FROM FOLTOT ft
    JOIN FOLFUN fu ON fu.FUNC = ft.FUNC AND fu.EMPRESA = ft.EMPRESA
    LEFT JOIN FOLEVE fe ON fe.FUNC = ft.FUNC AND fe.MES  = ft.MES
                       AND fe.ANO  = ft.ANO  AND fe.EMPRESA = ft.EMPRESA
                       AND fe.PERIODO = ft.PERIODO
    WHERE ft.PERIODO = 2
      AND ft.ANO = ?
    GROUP BY {cpf}, ft.MES, ft.ANO
),
esocial AS (
    SELECT
        RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) AS CPF_LIMPO,
        COMPETENCIA,
        SUM(INSS)  AS INSS,
        COUNT(*)   AS QTD
    FROM (
        SELECT CPF, INSS, COMPETENCIA
        FROM ESOCIAL_S1210
        WHERE REND_TRIB > 0 OR INSS > 0
        UNION ALL
        SELECT CPF, INSS, COMPETENCIA
        FROM ESOCIAL_S1210_COMPL
        WHERE REND_TRIB > 0 OR INSS > 0
    ) x
    GROUP BY RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11), COMPETENCIA
)
SELECT
    f.CPF_LIMPO,
    f.NOME,
    f.ANO_COMP,
    f.MES_COMP,
    ISNULL(CONVERT(VARCHAR(10), f.DATA_PGTO, 120), '') AS DATA_PGTO,
    f.COMP_PAGTO                                       AS COMPETENCIA_PAGTO,
    ROUND(f.FOLHA_INSS, 2)                             AS FOLHA_INSS,
    ISNULL(ROUND(e.INSS, 2), 0)                        AS ES_INSS,
    ISNULL(e.QTD, 0)                                   AS QTD_EVENTOS,
    CASE
        WHEN e.CPF_LIMPO IS NULL                     THEN 'SEM_ESOCIAL'
        WHEN e.INSS < 0.05 AND f.FOLHA_INSS >= 0.05 THEN 'INSS_ZERO'
        ELSE 'OK'
    END AS PENDENCIA
FROM folha f
LEFT JOIN esocial e ON e.CPF_LIMPO = f.CPF_LIMPO
                   AND e.COMPETENCIA = f.COMP_PAGTO
WHERE e.CPF_LIMPO IS NULL
   OR (e.INSS < 0.05 AND f.FOLHA_INSS >= 0.05)
ORDER BY f.MES_COMP, f.NOME
""".format(cpf=_CPF_FOLFUN)


@router.get("")
def get_pendencias_esocial(
    ano: int = Query(..., description="Ano de competência da folha"),
):
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")

    try:
        cur = conn.cursor()
        cur.execute(_SQL, ano)
        rows = cur.fetchall()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Erro na consulta: {e}")
    finally:
        conn.close()

    result = []
    for r in rows:
        result.append({
            "cpf":               r.CPF_LIMPO,
            "nome":              r.NOME or "",
            "ano_comp":          int(r.ANO_COMP),
            "mes_comp":          int(r.MES_COMP),
            "data_pgto":         r.DATA_PGTO or "",
            "competencia_pagto": r.COMPETENCIA_PAGTO,
            "folha_inss":        float(r.FOLHA_INSS or 0),
            "es_inss":           float(r.ES_INSS or 0),
            "qtd_eventos":       int(r.QTD_EVENTOS or 0),
            "pendencia":         r.PENDENCIA,
        })
    return result
