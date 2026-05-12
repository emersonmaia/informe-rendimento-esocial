"""
Geração e listagem de informes de rendimento.
"""
import sys
import io
import os
import contextlib
import threading
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent.parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import gerar_informes

from ..config import ANO_CAL
from ..db import get_conn, get_pasta_informes
from . import job_service

# CPF normalizado para 11 dígitos (elimina formatação e padeia zeros à esquerda)
_CPF_LIMPO = (
    "RIGHT('00000000000' + "
    "REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)), '.', ''), '-', ''), ' ', ''), 11)"
)


def _garantir_tabela_ajuste_manual(cur) -> None:
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


def iniciar_geracao_informes() -> "job_service.Job":
    if job_service.is_running("informes"):
        raise RuntimeError("Geração de informes já em andamento")
    job = job_service.criar_job("informes")

    from ..db import get_conn as _get_conn

    original_conn  = gerar_informes.get_conn
    original_pasta = gerar_informes.PASTA_SAIDA

    def _worker():
        gerar_informes.get_conn   = _get_conn
        pasta = get_pasta_informes()
        if pasta:
            gerar_informes.PASTA_SAIDA = pasta
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                gerar_informes.main()
            job_service.finalizar_job(job, "ok", buf.getvalue())
        except Exception as e:
            job_service.finalizar_job(job, "erro", f"{buf.getvalue()}\nERRO: {e}")
        finally:
            gerar_informes.get_conn   = original_conn
            gerar_informes.PASTA_SAIDA = original_pasta

    threading.Thread(target=_worker, daemon=True).start()
    return job


def listar_informes() -> list[dict]:
    """Retorna todos os beneficiários com totais e flag se o PDF existe."""
    conn = get_conn()
    cur = conn.cursor()
    _garantir_tabela_ajuste_manual(cur)
    # garante tabelas auxiliares (pode ser banco novo sem importação ainda)
    for ddl in [
        """IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210')
           CREATE TABLE ESOCIAL_S1210 (CPF VARCHAR(20), COMPETENCIA VARCHAR(10), DT_PAGTO VARCHAR(20),
           REND_TRIB DECIMAL(18,2) DEFAULT 0, INSS DECIMAL(18,2) DEFAULT 0, IRRF DECIMAL(18,2) DEFAULT 0,
           REND_TRIB_13 DECIMAL(18,2) DEFAULT 0, INSS_13 DECIMAL(18,2) DEFAULT 0, IRRF_13 DECIMAL(18,2) DEFAULT 0)""",
        """IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210_COMPL')
           CREATE TABLE ESOCIAL_S1210_COMPL (CPF VARCHAR(20), COMPETENCIA VARCHAR(10), DT_PAGTO VARCHAR(20),
           REND_TRIB DECIMAL(18,2) DEFAULT 0, INSS DECIMAL(18,2) DEFAULT 0, IRRF DECIMAL(18,2) DEFAULT 0,
           REND_TRIB_13 DECIMAL(18,2) DEFAULT 0, INSS_13 DECIMAL(18,2) DEFAULT 0, IRRF_13 DECIMAL(18,2) DEFAULT 0,
           ORIGEM VARCHAR(20) NULL)""",
        """IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_NOME_OVERRIDE')
           CREATE TABLE ESOCIAL_NOME_OVERRIDE (CPF VARCHAR(11) NOT NULL PRIMARY KEY,
           NOME VARCHAR(200) NOT NULL, OBS VARCHAR(300) NULL)""",
        """IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210_EXCLUIR')
           CREATE TABLE ESOCIAL_S1210_EXCLUIR (
               ID INT IDENTITY(1,1) PRIMARY KEY, TABELA VARCHAR(10) NOT NULL,
               ROW_ID INT NOT NULL, CPF VARCHAR(20) NOT NULL,
               MOTIVO VARCHAR(300) NULL, CRIADO_EM DATETIME NOT NULL DEFAULT GETDATE())""",
    ]:
        cur.execute(ddl)
    conn.commit()
    cur.execute(f"""
        WITH dados AS (
            SELECT CAST(CPF AS VARCHAR(20)) COLLATE DATABASE_DEFAULT AS CPF,
                   CAST(NULL AS INT) AS EMPRESA_MANUAL,
                   CAST(DT_PAGTO AS VARCHAR(20)) COLLATE DATABASE_DEFAULT AS DT_PAGTO,
                   REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13,
                   CAST('ESOCIAL' AS VARCHAR(10)) COLLATE DATABASE_DEFAULT AS ORIGEM
            FROM ESOCIAL_S1210
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0 OR INSS > 0 OR INSS_13 > 0)
              AND ID NOT IN (SELECT ROW_ID FROM ESOCIAL_S1210_EXCLUIR WHERE TABELA='S1210')
            UNION ALL
            SELECT CAST(CPF AS VARCHAR(20)) COLLATE DATABASE_DEFAULT AS CPF,
                   CAST(NULL AS INT) AS EMPRESA_MANUAL,
                   CAST(DT_PAGTO AS VARCHAR(20)) COLLATE DATABASE_DEFAULT AS DT_PAGTO,
                   REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13,
                   CAST('COMPL' AS VARCHAR(10)) COLLATE DATABASE_DEFAULT AS ORIGEM
            FROM ESOCIAL_S1210_COMPL
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0 OR INSS > 0 OR INSS_13 > 0)
              AND ID NOT IN (SELECT ROW_ID FROM ESOCIAL_S1210_EXCLUIR WHERE TABELA='COMPL')
            UNION ALL
            SELECT CAST(CPF AS VARCHAR(20)) COLLATE DATABASE_DEFAULT AS CPF,
                   EMPRESA AS EMPRESA_MANUAL,
                   CAST(DT_PAGTO AS VARCHAR(20)) COLLATE DATABASE_DEFAULT AS DT_PAGTO,
                   REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13,
                   CAST('MANUAL' AS VARCHAR(10)) COLLATE DATABASE_DEFAULT AS ORIGEM
            FROM ESOCIAL_INFORME_AJUSTE_MANUAL
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0 OR IRRF > 0 OR IRRF_13 > 0 OR INSS > 0 OR INSS_13 > 0)
        )
        SELECT
            ISNULL(f.NOME, ISNULL(ov.NOME, 'NAO IDENTIFICADO')) AS nome,
            LTRIM(RTRIM(s.CPF))                                   AS cpf,
            ISNULL(e.NOME, '')                                    AS empresa,
            ISNULL(LTRIM(RTRIM(e.INSCRICAO_FEDERAL)), '')         AS cnpj,
            ISNULL(CAST(COALESCE(f.EMPRESA, s.EMPRESA_MANUAL) AS VARCHAR(10)), '') AS cod_empresa,
            SUM(CASE WHEN s.REND_TRIB_13 > 0 THEN 0 ELSE s.REND_TRIB END) AS rend_trib,
            SUM(CASE WHEN s.REND_TRIB_13 > 0 THEN 0 ELSE s.INSS END)     AS inss,
            SUM(CASE WHEN s.REND_TRIB_13 > 0 THEN 0 ELSE s.IRRF END)     AS irrf,
            SUM(s.REND_TRIB_13)                                   AS rend_trib_13,
            SUM(s.INSS_13)                                        AS inss_13,
            SUM(s.IRRF_13)                                        AS irrf_13,
            MAX(CASE WHEN s.ORIGEM = 'MANUAL' THEN 1 ELSE 0 END)  AS tem_ajuste_manual,
            MAX(CASE WHEN f.CPF_LIMPO IS NOT NULL OR ov.CPF IS NOT NULL THEN 1 ELSE 0 END) AS identificado
        FROM dados s
        LEFT JOIN (
            SELECT
                {_CPF_LIMPO} AS CPF_LIMPO,
                NOME,
                TRY_CAST(EMPRESA AS INT) AS EMPRESA
            FROM (
                SELECT CPF, NOME, EMPRESA, DATA_RESCISAO,
                    ROW_NUMBER() OVER (
                        PARTITION BY {_CPF_LIMPO}
                        ORDER BY CASE WHEN DATA_RESCISAO IS NULL THEN 0 ELSE 1 END,
                                 DATA_RESCISAO DESC
                    ) AS rn
                FROM FOLFUN
            ) x WHERE x.rn = 1
        ) f ON f.CPF_LIMPO = RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11)
        LEFT JOIN CADEMP e ON e.EMPRESA = COALESCE(f.EMPRESA, s.EMPRESA_MANUAL)
        LEFT JOIN ESOCIAL_NOME_OVERRIDE ov
            ON ov.CPF = RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11)
        GROUP BY
            f.NOME, ov.NOME, s.CPF, CAST(COALESCE(f.EMPRESA, s.EMPRESA_MANUAL) AS VARCHAR(10)),
            e.NOME, e.INSCRICAO_FEDERAL, e.ENDERECO, e.NUMERO,
            e.BAIRRO, e.CIDADE, e.ESTADO, e.NOME_RESPONS_DIRF
        ORDER BY e.NOME, ISNULL(f.NOME, ov.NOME)
    """, ANO_CAL, ANO_CAL, ANO_CAL)

    rows = cur.fetchall()
    conn.close()

    pasta = get_pasta_informes()
    resultado = []
    for r in rows:
        cpf_clean = r.cpf.strip()
        cod_emp   = (r.cod_empresa or '').strip()
        pdf_nome  = f"informe_{ANO_CAL}_emp{cod_emp}_{cpf_clean}.pdf"
        pdf_path  = os.path.join(pasta, pdf_nome) if pasta else ''

        rend13 = float(r.rend_trib_13 or 0)
        irrf13 = float(r.irrf_13 or 0)
        inss13 = float(r.inss_13 or 0)

        resultado.append({
            "nome":      r.nome,
            "cpf":       cpf_clean,
            "empresa":   r.empresa,
            "cnpj":      r.cnpj,
            "cod_empresa": cod_emp,
            "rend_trib": float(r.rend_trib or 0),
            "inss":      float(r.inss or 0),
            "irrf":      float(r.irrf or 0),
            "rend_trib_13": rend13,
            "inss_13":   inss13,
            "irrf_13":   irrf13,
            "decimo_terceiro_liquido": rend13 - inss13 - irrf13,
            "tem_ajuste_manual": bool(r.tem_ajuste_manual),
            "identificado":      bool(r.identificado),
            "pdf_existe": bool(pdf_path and os.path.isfile(pdf_path)),
            "pdf_nome":  pdf_nome,
        })

    return resultado
