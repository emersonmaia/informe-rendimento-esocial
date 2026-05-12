from fastapi import APIRouter, HTTPException
from ..db import get_conn
from ..config import ANO_CAL

router = APIRouter()


def _garantir_tabelas(cur) -> None:
    """Cria tabelas auxiliares caso ainda não existam no banco ativo."""
    cur.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210')
        CREATE TABLE ESOCIAL_S1210 (
            CPF VARCHAR(20), COMPETENCIA VARCHAR(10), DT_PAGTO VARCHAR(20),
            REND_TRIB DECIMAL(18,2) DEFAULT 0, INSS DECIMAL(18,2) DEFAULT 0,
            IRRF DECIMAL(18,2) DEFAULT 0, REND_TRIB_13 DECIMAL(18,2) DEFAULT 0,
            INSS_13 DECIMAL(18,2) DEFAULT 0, IRRF_13 DECIMAL(18,2) DEFAULT 0
        )
    """)
    cur.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210_COMPL')
        CREATE TABLE ESOCIAL_S1210_COMPL (
            CPF VARCHAR(20), COMPETENCIA VARCHAR(10), DT_PAGTO VARCHAR(20),
            REND_TRIB DECIMAL(18,2) DEFAULT 0, INSS DECIMAL(18,2) DEFAULT 0,
            IRRF DECIMAL(18,2) DEFAULT 0, REND_TRIB_13 DECIMAL(18,2) DEFAULT 0,
            INSS_13 DECIMAL(18,2) DEFAULT 0, IRRF_13 DECIMAL(18,2) DEFAULT 0,
            ORIGEM VARCHAR(20) NULL
        )
    """)
    cur.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_NOME_OVERRIDE')
        CREATE TABLE ESOCIAL_NOME_OVERRIDE (
            CPF  VARCHAR(11) NOT NULL PRIMARY KEY,
            NOME VARCHAR(200) NOT NULL,
            OBS  VARCHAR(300) NULL
        )
    """)
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
    cur.connection.commit()  # persiste DDL imediatamente (evita rollback no close)


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
    _garantir_tabelas(cur)
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
                    CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE REND_TRIB END AS REND_TRIB,
                    CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE INSS END AS INSS,
                    CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE IRRF END AS IRRF,
                    REND_TRIB_13, INSS_13, IRRF_13
                FROM ESOCIAL_S1210
                WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
                  AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
                  AND (REND_TRIB > 0 OR REND_TRIB_13 > 0 OR INSS > 0 OR INSS_13 > 0)
                  AND ID NOT IN (SELECT ROW_ID FROM ESOCIAL_S1210_EXCLUIR WHERE TABELA='S1210')
                UNION ALL
                SELECT CPF,
                    CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE REND_TRIB END AS REND_TRIB,
                    CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE INSS END AS INSS,
                    CASE WHEN REND_TRIB_13 > 0 THEN 0 ELSE IRRF END AS IRRF,
                    REND_TRIB_13, INSS_13, IRRF_13
                FROM ESOCIAL_S1210_COMPL
                WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
                  AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
                  AND (REND_TRIB > 0 OR REND_TRIB_13 > 0 OR INSS > 0 OR INSS_13 > 0)
                  AND ID NOT IN (SELECT ROW_ID FROM ESOCIAL_S1210_EXCLUIR WHERE TABELA='COMPL')
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
    _garantir_tabelas(cur)
    cur.execute("""
        SELECT
            s.COMPETENCIA, s.DT_PAGTO,
            s.REND_TRIB, s.INSS, s.IRRF,
            s.REND_TRIB_13, s.INSS_13, s.IRRF_13,
            'S1210' AS origem,
            CAST(NULL AS INT) AS manual_id,
            s.ID AS row_id,
            'S1210' AS tabela,
            CASE WHEN ex.ID IS NOT NULL THEN 1 ELSE 0 END AS excluido,
            ex.ID AS excluir_id
        FROM ESOCIAL_S1210 s
        LEFT JOIN ESOCIAL_S1210_EXCLUIR ex ON ex.TABELA = 'S1210' AND ex.ROW_ID = s.ID
        WHERE TRY_CAST(s.DT_PAGTO AS DATE) IS NOT NULL
          AND YEAR(TRY_CAST(s.DT_PAGTO AS DATE)) = ?
          AND (s.REND_TRIB > 0 OR s.REND_TRIB_13 > 0 OR s.INSS > 0 OR s.INSS_13 > 0 OR s.IRRF > 0)
          AND RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11) = ?
        UNION ALL
        SELECT
            s.COMPETENCIA, s.DT_PAGTO,
            s.REND_TRIB, s.INSS, s.IRRF,
            s.REND_TRIB_13, s.INSS_13, s.IRRF_13,
            ISNULL(s.ORIGEM, 'S1200') AS origem,
            CAST(NULL AS INT) AS manual_id,
            s.ID AS row_id,
            'COMPL' AS tabela,
            CASE WHEN ex.ID IS NOT NULL THEN 1 ELSE 0 END AS excluido,
            ex.ID AS excluir_id
        FROM ESOCIAL_S1210_COMPL s
        LEFT JOIN ESOCIAL_S1210_EXCLUIR ex ON ex.TABELA = 'COMPL' AND ex.ROW_ID = s.ID
        WHERE TRY_CAST(s.DT_PAGTO AS DATE) IS NOT NULL
          AND YEAR(TRY_CAST(s.DT_PAGTO AS DATE)) = ?
          AND (s.REND_TRIB > 0 OR s.REND_TRIB_13 > 0 OR s.INSS > 0 OR s.INSS_13 > 0 OR s.IRRF > 0)
          AND RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11) = ?
        UNION ALL
        SELECT
            COMPETENCIA, DT_PAGTO,
            REND_TRIB, INSS, IRRF,
            REND_TRIB_13, INSS_13, IRRF_13,
            'MANUAL' AS origem,
            ID AS manual_id,
            CAST(NULL AS INT) AS row_id,
            'MANUAL' AS tabela,
            CAST(0 AS INT) AS excluido,
            CAST(NULL AS INT) AS excluir_id
        FROM ESOCIAL_INFORME_AJUSTE_MANUAL
        WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
          AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
          AND (REND_TRIB > 0 OR REND_TRIB_13 > 0 OR INSS > 0 OR INSS_13 > 0 OR IRRF > 0 OR IRRF_13 > 0)
          AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
        ORDER BY COMPETENCIA, DT_PAGTO, origem
    """, ANO_CAL, cpf_clean, ANO_CAL, cpf_clean, ANO_CAL, cpf_clean)

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
            "manual_id":    int(r.manual_id) if r.manual_id is not None else None,
            "row_id":       int(r.row_id) if r.row_id is not None else None,
            "tabela":       r.tabela,
            "excluido":     bool(r.excluido),
            "excluir_id":   int(r.excluir_id) if r.excluir_id is not None else None,
        }
        for r in rows
    ]
