from fastapi import APIRouter, HTTPException, Query
from ..db import get_conn
from ..config import ANO_CAL

router = APIRouter()

_CPF_CLEAN = (
    "RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(CPF)),'.',''),'-',''),' ',''), 11)"
)

# Lista de funcionários: VIEW (FOLEVE×ES_S1200) UNION S1210 importado
# Params: ano, ano, ano (VIEW + S1210 + COMPL)
_SQL_FUNCIONARIOS = f"""
SELECT cpf, MAX(ISNULL(nome,'')) AS nome
FROM (
    SELECT LTRIM(RTRIM(cpfTrab_ideTrabalhador)) AS cpf,
           ISNULL(nm_trab, '') AS nome
    FROM VW_ESOCIAL_COM_TOTAL_MES_FOLHA_ES_S1200_FOLEVE
    WHERE ANO = ?

    UNION

    SELECT {_CPF_CLEAN} AS cpf, '' AS nome
    FROM ESOCIAL_S1210
    WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
      AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?

    UNION

    SELECT {_CPF_CLEAN} AS cpf, '' AS nome
    FROM ESOCIAL_S1210_COMPL
    WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
      AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
) u
WHERE cpf IS NOT NULL AND LEN(LTRIM(RTRIM(cpf))) >= 9
GROUP BY cpf
ORDER BY MAX(ISNULL(nome,''))
"""

# Detalhe por funcionário: 4 fontes de dados por competência
# Params: cpf, ano (folha VIEW) | ano, cpf (S1210) | ano, cpf (COMPL) | ano, cpf (manual)
_SQL_POR_FUNC = f"""
WITH
folha AS (
    SELECT
        ANO, MES,
        CAST(ANO AS VARCHAR(4)) + '-' + RIGHT('0'+CAST(MES AS VARCHAR(2)),2)           AS comp_trabalho,
        CAST(CASE WHEN MES<12 THEN ANO   ELSE ANO+1 END AS VARCHAR(4))
        + '-' + RIGHT('0'+CAST(CASE WHEN MES<12 THEN MES+1 ELSE 1 END AS VARCHAR(2)),2) AS comp_pagto,
        MAX(CAST(DATA_PAGAMENTO AS DATE))   AS data_pagamento,
        SUM(TCREDITO)   AS folha_bruto,
        SUM(BASE_INSS)  AS folha_base_inss,
        SUM(INSS)       AS folha_inss,
        SUM(BASE_IRRF)  AS folha_base_irrf,
        SUM(IRRF)       AS folha_irrf,
        SUM(TLIQUIDO)   AS folha_liquido,
        SUM(BASE_FGTS)  AS folha_base_fgts,
        SUM(FGTS)       AS folha_fgts,
        MAX(CAST(PROTOCOLO_ENVIO AS VARCHAR(50)))  AS es_protocolo,
        MAX(CAST(NRRECIBO_ENVIO  AS VARCHAR(80)))  AS es_nrrecibo
    FROM VW_ESOCIAL_COM_TOTAL_MES_FOLHA_ES_S1200_FOLEVE
    WHERE LTRIM(RTRIM(cpfTrab_ideTrabalhador)) = ?
      AND ANO = ?
    GROUP BY ANO, MES
),
s1210 AS (
    SELECT
        COMPETENCIA,
        SUM(CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE REND_TRIB END) AS rend_trib,
        SUM(CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE INSS      END) AS inss,
        SUM(CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE IRRF      END) AS irrf,
        SUM(REND_TRIB_13) AS rend13,
        SUM(INSS_13)      AS inss13,
        SUM(IRRF_13)      AS irrf13,
        COUNT(*)          AS qtd
    FROM (
        SELECT COMPETENCIA, REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13
        FROM ESOCIAL_S1210
        WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
          AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
          AND RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(CPF)),'.',''),'-',''),' ',''), 11) = ?
          AND ID NOT IN (SELECT ROW_ID FROM ESOCIAL_S1210_EXCLUIR WHERE TABELA='S1210')
        UNION ALL
        SELECT COMPETENCIA, REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13
        FROM ESOCIAL_S1210_COMPL
        WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
          AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
          AND RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(CPF)),'.',''),'-',''),' ',''), 11) = ?
          AND ID NOT IN (SELECT ROW_ID FROM ESOCIAL_S1210_EXCLUIR WHERE TABELA='COMPL')
    ) x
    GROUP BY COMPETENCIA
),
manual AS (
    SELECT
        LEFT(COMPETENCIA, 7)                                           AS COMPETENCIA,
        SUM(CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE REND_TRIB END)    AS rend_trib,
        SUM(CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE INSS      END)    AS inss,
        SUM(CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE IRRF      END)    AS irrf,
        SUM(REND_TRIB_13) AS rend13,
        SUM(INSS_13)      AS inss13,
        SUM(IRRF_13)      AS irrf13,
        COUNT(*)          AS qtd
    FROM ESOCIAL_INFORME_AJUSTE_MANUAL
    WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
      AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
      AND RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(CPF)),'.',''),'-',''),' ',''), 11) = ?
    GROUP BY LEFT(COMPETENCIA, 7)
)
-- Parte 1: meses com dados de folha (com ou sem S1210)
SELECT
    f.ANO, f.MES,
    f.comp_trabalho                                                  AS competencia,
    ISNULL(CONVERT(VARCHAR(10), f.data_pagamento, 120), '')          AS data_pagamento,
    ROUND(f.folha_bruto,2)      AS folha_bruto,
    ROUND(f.folha_base_inss,2)  AS folha_base_inss,
    ROUND(f.folha_inss,2)       AS folha_inss,
    ROUND(f.folha_base_irrf,2)  AS folha_base_irrf,
    ROUND(f.folha_irrf,2)       AS folha_irrf,
    ROUND(f.folha_liquido,2)    AS folha_liquido,
    ROUND(f.folha_base_fgts,2)  AS folha_base_fgts,
    ROUND(f.folha_fgts,2)       AS folha_fgts,
    ISNULL(f.es_protocolo,'')   AS es_protocolo,
    ISNULL(f.es_nrrecibo,'')    AS es_nrrecibo,
    ROUND(ISNULL(s.rend_trib,0),2) AS s1210_rend_trib,
    ROUND(ISNULL(s.inss,0),2)      AS s1210_inss,
    ROUND(ISNULL(s.irrf,0),2)      AS s1210_irrf,
    ROUND(ISNULL(s.rend13,0),2)    AS s1210_rend13,
    ROUND(ISNULL(s.inss13,0),2)    AS s1210_inss13,
    ROUND(ISNULL(s.irrf13,0),2)    AS s1210_irrf13,
    ISNULL(s.qtd,0)                AS s1210_qtd,
    ROUND(ISNULL(m.rend_trib,0),2) AS manual_rend_trib,
    ROUND(ISNULL(m.inss,0),2)      AS manual_inss,
    ROUND(ISNULL(m.irrf,0),2)      AS manual_irrf,
    ROUND(ISNULL(m.rend13,0),2)    AS manual_rend13,
    ISNULL(m.qtd,0)                AS manual_qtd,
    ROUND(ISNULL(s.rend_trib,0)+ISNULL(m.rend_trib,0),2) AS pdf_rend_trib,
    ROUND(ISNULL(s.inss,0)+ISNULL(m.inss,0),2)           AS pdf_inss,
    ROUND(ISNULL(s.irrf,0)+ISNULL(m.irrf,0),2)           AS pdf_irrf,
    ROUND(ISNULL(s.rend13,0)+ISNULL(m.rend13,0),2)       AS pdf_rend13,
    ROUND(ISNULL(s.inss13,0)+ISNULL(m.inss13,0),2)       AS pdf_inss13,
    ROUND(ISNULL(s.irrf13,0)+ISNULL(m.irrf13,0),2)       AS pdf_irrf13,
    ROUND(f.folha_inss - (ISNULL(s.inss,0)+ISNULL(m.inss,0)),2) AS dif_inss,
    ROUND(f.folha_irrf - (ISNULL(s.irrf,0)+ISNULL(m.irrf,0)),2) AS dif_irrf
FROM folha f
LEFT JOIN s1210 s ON s.COMPETENCIA = f.comp_pagto
LEFT JOIN manual m ON m.COMPETENCIA = f.comp_pagto

UNION ALL

-- Parte 2: meses apenas em S1210 sem correspondência na folha
SELECT
    CAST(LEFT(s.COMPETENCIA,4) AS INT)
        - CASE WHEN CAST(RIGHT(s.COMPETENCIA,2) AS INT)=1 THEN 1 ELSE 0 END AS ANO,
    CASE WHEN CAST(RIGHT(s.COMPETENCIA,2) AS INT) > 1
         THEN CAST(RIGHT(s.COMPETENCIA,2) AS INT) - 1
         ELSE 12 END                                                          AS MES,
    CAST(
        CAST(LEFT(s.COMPETENCIA,4) AS INT)
        - CASE WHEN CAST(RIGHT(s.COMPETENCIA,2) AS INT)=1 THEN 1 ELSE 0 END
        AS VARCHAR(4))
    + '-' + RIGHT('0'+CAST(
        CASE WHEN CAST(RIGHT(s.COMPETENCIA,2) AS INT) > 1
             THEN CAST(RIGHT(s.COMPETENCIA,2) AS INT) - 1
             ELSE 12 END AS VARCHAR(2)), 2)                                   AS competencia,
    ''  AS data_pagamento,
    0 AS folha_bruto,    0 AS folha_base_inss, 0 AS folha_inss,
    0 AS folha_base_irrf, 0 AS folha_irrf,
    0 AS folha_liquido,  0 AS folha_base_fgts, 0 AS folha_fgts,
    '' AS es_protocolo,  '' AS es_nrrecibo,
    ROUND(s.rend_trib,2)  AS s1210_rend_trib,
    ROUND(s.inss,2)       AS s1210_inss,
    ROUND(s.irrf,2)       AS s1210_irrf,
    ROUND(s.rend13,2)     AS s1210_rend13,
    ROUND(s.inss13,2)     AS s1210_inss13,
    ROUND(s.irrf13,2)     AS s1210_irrf13,
    s.qtd                 AS s1210_qtd,
    ROUND(ISNULL(m.rend_trib,0),2) AS manual_rend_trib,
    ROUND(ISNULL(m.inss,0),2)      AS manual_inss,
    ROUND(ISNULL(m.irrf,0),2)      AS manual_irrf,
    ROUND(ISNULL(m.rend13,0),2)    AS manual_rend13,
    ISNULL(m.qtd,0)                AS manual_qtd,
    ROUND(s.rend_trib+ISNULL(m.rend_trib,0),2) AS pdf_rend_trib,
    ROUND(s.inss+ISNULL(m.inss,0),2)           AS pdf_inss,
    ROUND(s.irrf+ISNULL(m.irrf,0),2)           AS pdf_irrf,
    ROUND(s.rend13+ISNULL(m.rend13,0),2)       AS pdf_rend13,
    ROUND(s.inss13+ISNULL(m.inss13,0),2)       AS pdf_inss13,
    ROUND(s.irrf13+ISNULL(m.irrf13,0),2)       AS pdf_irrf13,
    ROUND(0-(s.inss+ISNULL(m.inss,0)),2)       AS dif_inss,
    ROUND(0-(s.irrf+ISNULL(m.irrf,0)),2)       AS dif_irrf
FROM s1210 s
LEFT JOIN manual m ON m.COMPETENCIA = s.COMPETENCIA
WHERE s.COMPETENCIA NOT IN (SELECT comp_pagto FROM folha)

ORDER BY ANO, MES
"""

# SQL legado (tela de conferência por mês — mantido)
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
        SUM(ft.BASE_INSS)                    AS BASE_INSS,
        SUM(ft.INSS)                         AS INSS,
        SUM(ft.BASE_IRRF)                    AS BASE_IRRF,
        SUM(ft.IRRF)                         AS IRRF,
        SUM(ft.TLIQUIDO)                     AS TLIQUIDO
    FROM FOLTOT ft
    JOIN FOLFUN fu ON fu.FUNC = ft.FUNC AND fu.EMPRESA = ft.EMPRESA
    LEFT JOIN FOLEVE fe ON fe.FUNC = ft.FUNC AND fe.MES  = ft.MES
                       AND fe.ANO  = ft.ANO  AND fe.EMPRESA = ft.EMPRESA
                       AND fe.PERIODO = ft.PERIODO
    WHERE ft.PERIODO = 2
      AND ft.ANO  = ?
      AND ft.MES  = ?
    GROUP BY {cpf}, ft.MES, ft.ANO
),
esocial AS (
    SELECT
        RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) AS CPF_LIMPO,
        SUM(REND_TRIB) AS REND_TRIB,
        SUM(INSS)      AS INSS,
        SUM(IRRF)      AS IRRF,
        MAX(ORIGEM)    AS ORIGEM,
        COUNT(*)       AS QTD_EVENTOS
    FROM (
        SELECT CPF, REND_TRIB, INSS, IRRF, 'S1210' AS ORIGEM
        FROM ESOCIAL_S1210
        WHERE COMPETENCIA = ?
          AND (REND_TRIB > 0 OR INSS > 0)
        UNION ALL
        SELECT CPF, REND_TRIB, INSS, IRRF, 'S1200' AS ORIGEM
        FROM ESOCIAL_S1210_COMPL
        WHERE COMPETENCIA = ?
          AND (REND_TRIB > 0 OR INSS > 0)
    ) x
    GROUP BY RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11)
)
SELECT
    f.CPF_LIMPO, f.NOME, f.MES_COMP, f.ANO_COMP,
    ISNULL(CONVERT(VARCHAR(10), f.DATA_PGTO, 120), '')  AS DATA_PGTO,
    ROUND(f.BASE_INSS, 2)                               AS folha_base_inss,
    ROUND(f.INSS, 2)                                    AS folha_inss,
    ROUND(ISNULL(e.REND_TRIB, 0), 2)                   AS es_rend_trib,
    ROUND(ISNULL(e.INSS, 0), 2)                        AS es_inss,
    ROUND(f.INSS - ISNULL(e.INSS, 0), 2)               AS dif_inss,
    ROUND(f.IRRF, 2)                                   AS folha_irrf,
    ROUND(ISNULL(e.IRRF, 0), 2)                        AS es_irrf,
    ROUND(f.IRRF - ISNULL(e.IRRF, 0), 2)               AS dif_irrf,
    ROUND(f.TLIQUIDO, 2)                               AS folha_liquido,
    ISNULL(e.ORIGEM, '')                               AS es_origem,
    ISNULL(e.QTD_EVENTOS, 0)                           AS es_qtd_eventos,
    CASE
        WHEN e.CPF_LIMPO IS NULL                                    THEN 'SEM_ESOCIAL'
        WHEN ABS(f.INSS - ISNULL(e.INSS, 0)) > 0.05
          OR ABS(f.IRRF - ISNULL(e.IRRF, 0)) > 0.05               THEN 'DIVERGENTE'
        ELSE 'OK'
    END AS status
FROM folha f
LEFT JOIN esocial e ON e.CPF_LIMPO = f.CPF_LIMPO
ORDER BY
    CASE WHEN e.CPF_LIMPO IS NULL THEN 0
         WHEN ABS(f.INSS - ISNULL(e.INSS, 0)) > 0.05
           OR ABS(f.IRRF - ISNULL(e.IRRF, 0)) > 0.05 THEN 1
         ELSE 2 END,
    ABS(f.INSS - ISNULL(e.INSS, 0)) DESC
""".format(cpf=_CPF_FOLFUN)


@router.get("/funcionarios")
def get_funcionarios(ano: int = Query(default=None)):
    ano = ano or ANO_CAL
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    try:
        cur = conn.cursor()
        cur.execute(_SQL_FUNCIONARIOS, ano, ano, ano)
        rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar funcionários: {e}")
    finally:
        conn.close()
    return [{"cpf": r.cpf, "nome": r.nome or ""} for r in rows]


_DDL_EXCLUIR = """
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210_EXCLUIR')
CREATE TABLE ESOCIAL_S1210_EXCLUIR (
    ID        INT IDENTITY(1,1) PRIMARY KEY,
    TABELA    VARCHAR(10) NOT NULL,
    ROW_ID    INT NOT NULL,
    CPF       VARCHAR(20) NOT NULL,
    MOTIVO    VARCHAR(300) NULL,
    CRIADO_EM DATETIME    NOT NULL DEFAULT GETDATE()
)
"""

_DDL_MANUAL = """
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
"""


@router.get("/por-funcionario/{cpf}")
def get_por_funcionario(cpf: str, ano: int = Query(default=None)):
    ano = ano or ANO_CAL
    cpf_clean = cpf.replace(".", "").replace("-", "").replace(" ", "").zfill(11)
    try:
        conn = get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")
    try:
        cur = conn.cursor()
        # garante tabelas auxiliares antes da query principal
        cur.execute(_DDL_EXCLUIR)
        cur.execute(_DDL_MANUAL)
        conn.commit()
        cur.execute(
            _SQL_POR_FUNC,
            cpf_clean, ano,         # folha (VIEW)
            ano, cpf_clean,          # s1210 (S1210)
            ano, cpf_clean,          # s1210 (COMPL)
            ano, cpf_clean,          # manual
        )
        rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na consulta: {e}")
    finally:
        conn.close()

    result = []
    for r in rows:
        result.append({
            "competencia":      r.competencia,
            "mes":              int(r.MES),
            "ano":              int(r.ANO),
            "data_pagamento":   r.data_pagamento or "",
            # Folha (FOLEVE)
            "folha_bruto":      float(r.folha_bruto or 0),
            "folha_base_inss":  float(r.folha_base_inss or 0),
            "folha_inss":       float(r.folha_inss or 0),
            "folha_base_irrf":  float(r.folha_base_irrf or 0),
            "folha_irrf":       float(r.folha_irrf or 0),
            "folha_liquido":    float(r.folha_liquido or 0),
            "folha_base_fgts":  float(r.folha_base_fgts or 0),
            "folha_fgts":       float(r.folha_fgts or 0),
            "es_protocolo":     str(r.es_protocolo or ""),
            "es_nrrecibo":      str(r.es_nrrecibo or ""),
            # S1210 importado
            "s1210_rend_trib":  float(r.s1210_rend_trib or 0),
            "s1210_inss":       float(r.s1210_inss or 0),
            "s1210_irrf":       float(r.s1210_irrf or 0),
            "s1210_rend13":     float(r.s1210_rend13 or 0),
            "s1210_inss13":     float(r.s1210_inss13 or 0),
            "s1210_irrf13":     float(r.s1210_irrf13 or 0),
            "s1210_qtd":        int(r.s1210_qtd or 0),
            # Ajuste manual
            "manual_rend_trib": float(r.manual_rend_trib or 0),
            "manual_inss":      float(r.manual_inss or 0),
            "manual_irrf":      float(r.manual_irrf or 0),
            "manual_rend13":    float(r.manual_rend13 or 0),
            "manual_qtd":       int(r.manual_qtd or 0),
            # Total PDF (S1210 + manual)
            "pdf_rend_trib":    float(r.pdf_rend_trib or 0),
            "pdf_inss":         float(r.pdf_inss or 0),
            "pdf_irrf":         float(r.pdf_irrf or 0),
            "pdf_rend13":       float(r.pdf_rend13 or 0),
            "pdf_inss13":       float(r.pdf_inss13 or 0),
            "pdf_irrf13":       float(r.pdf_irrf13 or 0),
            # Diferenças (Folha − PDF)
            "dif_inss":         float(r.dif_inss or 0),
            "dif_irrf":         float(r.dif_irrf or 0),
        })
    return result


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

    next_year  = ano if mes < 12 else ano + 1
    next_month = mes + 1 if mes < 12 else 1
    competencia_pagto = f"{next_year}-{next_month:02d}"

    try:
        cur = conn.cursor()
        cur.execute(_SQL, ano, mes, competencia_pagto, competencia_pagto)
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
            "competencia_pagto": competencia_pagto,
            "nome":            r.NOME or "",
            "mes_comp":        int(r.MES_COMP),
            "ano_comp":        int(r.ANO_COMP),
            "data_pgto":       r.DATA_PGTO or "",
            "folha_base_inss": float(r.folha_base_inss or 0),
            "folha_inss":      float(r.folha_inss or 0),
            "es_rend_trib":    float(r.es_rend_trib or 0),
            "es_inss":         float(r.es_inss or 0),
            "dif_inss":        float(r.dif_inss or 0),
            "folha_irrf":      float(r.folha_irrf or 0),
            "es_irrf":         float(r.es_irrf or 0),
            "dif_irrf":        float(r.dif_irrf or 0),
            "folha_liquido":   float(r.folha_liquido or 0),
            "es_origem":       r.es_origem or "",
            "es_qtd_eventos":  int(r.es_qtd_eventos or 0),
            "status":          r.status,
        })
    return result
