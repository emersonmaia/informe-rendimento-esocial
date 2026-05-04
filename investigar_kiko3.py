import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult'
)
cur = conn.cursor()

# CPFs do FOLFUN kiko (os do usuario)
cpfs_folfun = [
    '13878750862','62733524887','97977551853','05454323837','74786610844',
    '98184121849','19630669870','11575369800','35193487807','97133493268',
    '62133861815','30270255893','10706471873','16394455873','03502866805',
    '27940547836','83083561415','40463742842','33579585894','37765700839',
    '77542789368','35848946892','45104132897','38163375892','03365817344',
    '04427877311','48811099870','38338576840','40711444838','16722180808',
    '18108574811','65105575920','15991228809','31631009885','06559487830',
    '16394362867','32369558806','02002827869','04745901860','06479241371',
    '57222484876','46402693806','53384994876','49277326816','12591731861',
    '49579980861','28631540870','46951152802','08076032601','10906964857',
    '43206534836','23313245811','29569136898','33797150857','15720673814',
    '11858029678','00469952504','56655355672','39521889802','19631832821',
    '39709703854','36759584856','44044935840','23325599818','41534252819',
    '26475160814','45309401873','05427445897','20403877814','06479241371',
]

print("=== Checando se CPFs do FOLFUN aparecem em ES_S1210 (sistema nativo) ===")
try:
    cur.execute("SELECT TOP 5 cpfBenef_ideBenef, nrInsc_infoRubricas FROM ES_S1210 ORDER BY 1")
    rows = cur.fetchall()
    print(f"  ES_S1210 nativo - primeiros registros:")
    for r in rows:
        print(f"    CPF:{r[0]}")

    cur.execute("SELECT COUNT(DISTINCT cpfBenef_ideBenef) FROM ES_S1210")
    print(f"  Total CPFs distintos em ES_S1210: {cur.fetchone()[0]}")

    # CPFs do FOLFUN que aparecem em ES_S1210
    cur.execute("""
        SELECT DISTINCT cpfBenef_ideBenef
        FROM ES_S1210
        WHERE cpfBenef_ideBenef IN (
            SELECT RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)),'.',''),'-',''),' ',''), 11)
            FROM FOLFUN
        )
    """)
    matches = cur.fetchall()
    print(f"  CPFs do FOLFUN encontrados no ES_S1210: {len(matches)}")
    for r in matches:
        print(f"    {r[0]}")
except Exception as e:
    print(f"  ERRO ES_S1210: {e}")

print()
print("=== TBL_S5002 - amostra ===")
try:
    cur.execute("SELECT TOP 3 CPF, NOME, COMPETENCIA, VLRRENDTRIB FROM TBL_S5002 ORDER BY COMPETENCIA DESC")
    for r in cur.fetchall():
        print(f"  CPF:{r[0]}  NOME:{r[1]}  COMP:{r[2]}  REND:{r[3]}")
    cur.execute("SELECT COUNT(DISTINCT CPF) FROM TBL_S5002 WHERE COMPETENCIA LIKE '2025%'")
    print(f"  Total CPFs distintos 2025: {cur.fetchone()[0]}")
except Exception as e:
    print(f"  ERRO TBL_S5002: {e}")

print()
print("=== TBL_S1210 - amostra ===")
try:
    cur.execute("SELECT TOP 3 CPF, NOME, COMPETENCIA FROM TBL_S1210 ORDER BY COMPETENCIA DESC")
    for r in cur.fetchall():
        print(f"  CPF:{r[0]}  NOME:{r[1]}  COMP:{r[2]}")
except Exception as e:
    print(f"  ERRO TBL_S1210: {e}")

print()
print("=== CPF_FUNC - amostra ===")
try:
    cur.execute("SELECT TOP 5 * FROM CPF_FUNC")
    cols = [d[0] for d in cur.description]
    print(f"  Colunas: {cols}")
    for r in cur.fetchall():
        print(f"  {list(r)}")
except Exception as e:
    print(f"  ERRO CPF_FUNC: {e}")

print()
print("=== ES_S2200 - amostra (admissoes) - CPF e NOME ===")
try:
    cur.execute("""
        SELECT TOP 10
            cpfTrab_trabalhador,
            nmTrab_trabalhador,
            dtAdm_vinculo
        FROM ES_S2200
        ORDER BY dtAdm_vinculo DESC
    """)
    for r in cur.fetchall():
        print(f"  CPF:{r[0]}  NOME:{r[1]}  ADM:{r[2]}")
except Exception as e:
    print(f"  ERRO ES_S2200: {e}")

print()
print("=== VW_FOLDIRF - amostra (DIRF view) ===")
try:
    cur.execute("SELECT TOP 5 FUNCIONARIO_CPF, FUNCIONARIO_NOME FROM VW_FOLDIRF")
    for r in cur.fetchall():
        print(f"  CPF:{r[0]}  NOME:{r[1]}")
except Exception as e:
    print(f"  ERRO VW_FOLDIRF: {e}")

print()
print("=== vw_decimo - amostra (13 salario view) ===")
try:
    cur.execute("SELECT TOP 5 * FROM vw_decimo")
    cols = [d[0] for d in cur.description]
    print(f"  Colunas: {cols}")
    for r in cur.fetchall():
        print(f"  {list(r[:6])}")
except Exception as e:
    print(f"  ERRO vw_decimo: {e}")

conn.close()
