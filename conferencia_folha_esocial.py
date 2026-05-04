"""
Conferencia: Folha (FOLTOT via DATA_PAGAMENTO) vs ESOCIAL_S1210 (retorno eSocial via DT_PAGTO)

O alinhamento correto e pela DATA DE PAGAMENTO:
  - FOLTOT MES=N tem DATA_PAGAMENTO = dia 5 do mes N+1
  - ESOCIAL_S1210 COMPETENCIA=N+1 tem DT_PAGTO = dia 5 do mes N+1
  => JOIN por CPF + mes/ano do pagamento (DT_PAGTO = DATA_PAGAMENTO)
"""
import pyodbc

def get_conn():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult"
    )


SQL_CONFERENCIA = """
WITH folha AS (
    -- Totalizadores por CPF, agregados por pessoa (pode ter multiplas empresas)
    SELECT
        RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(
            ISNULL(fu.CPF,''), '.',''), '-',''), ' ',''), 11)    AS CPF_LIMPO,
        MAX(fu.NOME)                                             AS NOME,
        MAX(ft.MES)                                              AS MES_COMP,
        MAX(ft.ANO)                                              AS ANO_COMP,
        CAST(MAX(fe.DATA_PAGAMENTO) AS DATE)                     AS DATA_PGTO,
        SUM(ft.BASE_INSS)                                        AS BASE_INSS,
        SUM(ft.INSS)                                             AS INSS,
        SUM(ft.BASE_IRRF)                                        AS BASE_IRRF,
        SUM(ft.IRRF)                                             AS IRRF,
        SUM(ft.TLIQUIDO)                                         AS TLIQUIDO
    FROM FOLTOT ft
    JOIN FOLFUN fu ON fu.FUNC = ft.FUNC AND fu.EMPRESA = ft.EMPRESA
    JOIN FOLEVE fe ON fe.FUNC = ft.FUNC AND fe.MES = ft.MES
                  AND fe.ANO = ft.ANO    AND fe.EMPRESA = ft.EMPRESA
                  AND fe.PERIODO = ft.PERIODO
    WHERE ft.PERIODO = 2
      AND YEAR(CAST(fe.DATA_PAGAMENTO AS DATE)) = ?
      AND MONTH(CAST(fe.DATA_PAGAMENTO AS DATE)) = ?
    GROUP BY RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(
        ISNULL(fu.CPF,''), '.',''), '-',''), ' ',''), 11)
),
esocial_dedup AS (
    -- Deduplicar retificacoes: manter ultimo arquivo por CPF+DT_PAGTO+EMPRESA
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
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
      AND MONTH(TRY_CAST(DT_PAGTO AS DATE)) = ?
      AND REND_TRIB > 0
),
esocial AS (
    -- Somar por CPF+DT_PAGTO apos deduplicacao por empresa
    SELECT
        CPF_LIMPO,
        DT_PGTO,
        SUM(REND_TRIB) AS REND_TRIB,
        SUM(INSS)      AS INSS,
        SUM(IRRF)      AS IRRF
    FROM esocial_dedup
    WHERE rn = 1
    GROUP BY CPF_LIMPO, DT_PGTO
)
SELECT
    f.CPF_LIMPO,
    f.NOME,
    f.MES_COMP,
    f.ANO_COMP,
    f.DATA_PGTO,
    f.BASE_INSS            AS folha_base_inss,
    f.INSS                 AS folha_inss,
    ISNULL(e.REND_TRIB,0)  AS es_rend_trib,
    ISNULL(e.INSS,0)       AS es_inss,
    f.INSS - ISNULL(e.INSS,0)  AS dif_inss,
    f.IRRF                 AS folha_irrf,
    ISNULL(e.IRRF,0)       AS es_irrf,
    f.IRRF - ISNULL(e.IRRF,0)  AS dif_irrf,
    f.TLIQUIDO             AS folha_liquido,
    CASE
        WHEN e.CPF_LIMPO IS NULL THEN 'SEM_ESOCIAL'
        WHEN ABS(f.INSS - ISNULL(e.INSS,0)) > 0.05
          OR ABS(f.IRRF - ISNULL(e.IRRF,0)) > 0.05 THEN 'DIVERGENTE'
        ELSE 'OK'
    END AS status
FROM folha f
LEFT JOIN esocial e ON e.CPF_LIMPO = f.CPF_LIMPO
                    AND e.DT_PGTO = f.DATA_PGTO
ORDER BY
    CASE WHEN e.CPF_LIMPO IS NULL THEN 0
         WHEN ABS(f.INSS-ISNULL(e.INSS,0))>0.05 OR ABS(f.IRRF-ISNULL(e.IRRF,0))>0.05 THEN 1
         ELSE 2 END,
    ABS(f.INSS - ISNULL(e.INSS,0)) DESC
"""


def conferir(ano_pgto, mes_pgto):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(SQL_CONFERENCIA, ano_pgto, mes_pgto, ano_pgto, mes_pgto)
    rows = cur.fetchall()
    conn.close()

    total = sem_es = divergentes = ok = 0
    print(f"\nConferencia folha vs eSocial — pagamentos em {mes_pgto:02d}/{ano_pgto}")
    print(f"  (Competencia da folha = {mes_pgto-1 if mes_pgto>1 else 12}/{ano_pgto if mes_pgto>1 else ano_pgto-1})")
    hdr = f"  {'CPF':11}  {'Nome':32}  {'Comp':7}  {'f_inss':>8}  {'e_inss':>8}  {'dif_i':>8}  {'f_irrf':>8}  {'e_irrf':>8}  {'dif_irrf':>8}  STATUS"
    print(hdr)
    print("  " + "-" * 120)

    for r in rows:
        cpf, nome, mes_c, ano_c, dt_pgto, f_base, f_inss, e_rt, e_inss, dif_inss, f_irrf, e_irrf, dif_irrf, f_liq, status = r
        total += 1
        if status == 'SEM_ESOCIAL': sem_es += 1
        elif status == 'DIVERGENTE': divergentes += 1
        else: ok += 1

        comp = f"{int(ano_c)}-{int(mes_c):02d}"
        n = (nome or '')[:32]
        print(f"  {cpf:11}  {n:32}  {comp}  {float(f_inss):8.2f}  {float(e_inss):8.2f}  {float(dif_inss):+8.2f}  {float(f_irrf):8.2f}  {float(e_irrf):8.2f}  {float(dif_irrf):+8.2f}  {status}")

    print("  " + "-" * 120)
    print(f"  Total: {total} | OK: {ok} | Divergentes: {divergentes} | Sem eSocial: {sem_es}")
    return rows


if __name__ == "__main__":
    # Testar com pagamentos de novembro 2025 (competencia outubro)
    conferir(2025, 11)
    print()
    # Testar com pagamentos de dezembro 2025 (competencia novembro)
    conferir(2025, 12)
