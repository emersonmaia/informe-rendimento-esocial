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
        MAX(ft.MES)                          AS MES_COMP,
        MAX(ft.ANO)                          AS ANO_COMP,
        CAST(MAX(fe.DATA_PAGAMENTO) AS DATE) AS DATA_PGTO,
        SUM(ft.BASE_INSS)                    AS BASE_INSS,
        SUM(ft.INSS)                         AS INSS,
        SUM(ft.BASE_IRRF)                    AS BASE_IRRF,
        SUM(ft.IRRF)                         AS IRRF,
        SUM(ft.TLIQUIDO)                     AS TLIQUIDO
    FROM FOLTOT ft
    JOIN FOLFUN fu ON fu.FUNC = ft.FUNC AND fu.EMPRESA = ft.EMPRESA
    JOIN FOLEVE fe ON fe.FUNC = ft.FUNC AND fe.MES  = ft.MES
                  AND fe.ANO  = ft.ANO  AND fe.EMPRESA = ft.EMPRESA
                  AND fe.PERIODO = ft.PERIODO
    WHERE ft.PERIODO = 2
      AND YEAR(CAST(fe.DATA_PAGAMENTO AS DATE))  = ?
      AND MONTH(CAST(fe.DATA_PAGAMENTO AS DATE)) = ?
    GROUP BY {cpf}
),
es_dedup AS (
    SELECT
        RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) AS CPF_LIMPO,
        TRY_CAST(DT_PAGTO AS DATE)                   AS DT_PGTO,
        EMPRESA,
        REND_TRIB, INSS, IRRF,
        ROW_NUMBER() OVER (
            PARTITION BY RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11),
                         TRY_CAST(DT_PAGTO AS DATE),
                         EMPRESA
            ORDER BY ARQUIVO DESC
        ) AS rn
    FROM ESOCIAL_S1210
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE))  = ?
      AND MONTH(TRY_CAST(DT_PAGTO AS DATE)) = ?
      AND REND_TRIB > 0
),
esocial AS (
    SELECT
        CPF_LIMPO, DT_PGTO,
        SUM(REND_TRIB) AS REND_TRIB,
        SUM(INSS)      AS INSS,
        SUM(IRRF)      AS IRRF
    FROM es_dedup
    WHERE rn = 1
    GROUP BY CPF_LIMPO, DT_PGTO
)
SELECT
    f.CPF_LIMPO,
    f.NOME,
    f.MES_COMP,
    f.ANO_COMP,
    CONVERT(VARCHAR(10), f.DATA_PGTO, 120)      AS DATA_PGTO,
    ROUND(f.BASE_INSS, 2)                       AS folha_base_inss,
    ROUND(f.INSS, 2)                            AS folha_inss,
    ROUND(ISNULL(e.REND_TRIB, 0), 2)            AS es_rend_trib,
    ROUND(ISNULL(e.INSS, 0), 2)                 AS es_inss,
    ROUND(f.INSS - ISNULL(e.INSS, 0), 2)        AS dif_inss,
    ROUND(f.IRRF, 2)                            AS folha_irrf,
    ROUND(ISNULL(e.IRRF, 0), 2)                 AS es_irrf,
    ROUND(f.IRRF - ISNULL(e.IRRF, 0), 2)        AS dif_irrf,
    ROUND(f.TLIQUIDO, 2)                        AS folha_liquido,
    CASE
        WHEN e.CPF_LIMPO IS NULL                                    THEN 'SEM_ESOCIAL'
        WHEN ABS(f.INSS - ISNULL(e.INSS, 0)) > 0.05
          OR ABS(f.IRRF - ISNULL(e.IRRF, 0)) > 0.05               THEN 'DIVERGENTE'
        ELSE 'OK'
    END AS status
FROM folha f
LEFT JOIN esocial e ON e.CPF_LIMPO = f.CPF_LIMPO
                    AND e.DT_PGTO  = f.DATA_PGTO
ORDER BY
    CASE WHEN e.CPF_LIMPO IS NULL THEN 0
         WHEN ABS(f.INSS - ISNULL(e.INSS, 0)) > 0.05
           OR ABS(f.IRRF - ISNULL(e.IRRF, 0)) > 0.05 THEN 1
         ELSE 2 END,
    ABS(f.INSS - ISNULL(e.INSS, 0)) DESC
""".format(cpf=_CPF_FOLFUN)


@router.get("")
def get_conferencia_folha(
    ano: int = Query(..., description="Ano do pagamento"),
    mes: int = Query(..., description="Mês do pagamento (1-12)"),
):
    if not (1 <= mes <= 12):
        raise HTTPException(status_code=422, detail="Mês deve ser entre 1 e 12")
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")

    try:
        cur = conn.cursor()
        cur.execute(_SQL, ano, mes, ano, mes)
        rows = cur.fetchall()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Erro na consulta: {e}")
    finally:
        conn.close()

    result = []
    for r in rows:
        result.append({
            "cpf":            r.CPF_LIMPO,
            "nome":           r.NOME or "",
            "mes_comp":       int(r.MES_COMP),
            "ano_comp":       int(r.ANO_COMP),
            "data_pgto":      r.DATA_PGTO,
            "folha_base_inss": float(r.folha_base_inss or 0),
            "folha_inss":     float(r.folha_inss or 0),
            "es_rend_trib":   float(r.es_rend_trib or 0),
            "es_inss":        float(r.es_inss or 0),
            "dif_inss":       float(r.dif_inss or 0),
            "folha_irrf":     float(r.folha_irrf or 0),
            "es_irrf":        float(r.es_irrf or 0),
            "dif_irrf":       float(r.dif_irrf or 0),
            "folha_liquido":  float(r.folha_liquido or 0),
            "status":         r.status,
        })
    return result
