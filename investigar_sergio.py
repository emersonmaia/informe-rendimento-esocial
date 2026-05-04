import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=100.110.194.113;DATABASE=folha_agronil;UID=sa;PWD=mult'
)
cur = conn.cursor()

print("=== FOLFUN - localizar Sergio ===")
cur.execute("SELECT DISTINCT CPF, NOME FROM FOLFUN WHERE NOME LIKE '%SERGIO%' OR NOME LIKE '%RGIO%'")
for r in cur.fetchall():
    print(f"  CPF: {r[0]}  NOME: {r[1]}")

print()
print("=== ESOCIAL_S1210 - todos os registros 13o salario (ano 2025) ===")
cur.execute("""
    SELECT
        CPF, COMPETENCIA, DT_PAGTO,
        REND_TRIB, INSS, IRRF,
        REND_TRIB_13, INSS_13, IRRF_13,
        ARQUIVO
    FROM ESOCIAL_S1210
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
      AND (REND_TRIB_13 > 0 OR INSS_13 > 0 OR IRRF_13 > 0)
    ORDER BY CPF, DT_PAGTO
""")
rows13 = cur.fetchall()
for r in rows13:
    print(f"  CPF:{r[0]} COMP:{r[1]} PAGTO:{r[2]}  R13:{r[6]}  INSS13:{r[7]}  IRRF13:{r[8]}")

print()
print("=== ESOCIAL_S1210_COMPL - registros 13o salario ===")
cur.execute("""
    SELECT
        CPF, COMPETENCIA, DT_PAGTO,
        REND_TRIB, INSS, IRRF,
        REND_TRIB_13, INSS_13, IRRF_13,
        ARQUIVO
    FROM ESOCIAL_S1210_COMPL
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
      AND (REND_TRIB_13 > 0 OR INSS_13 > 0 OR IRRF_13 > 0)
    ORDER BY CPF, DT_PAGTO
""")
for r in cur.fetchall():
    print(f"  CPF:{r[0]} COMP:{r[1]} PAGTO:{r[2]}  R13:{r[6]}  INSS13:{r[7]}  IRRF13:{r[8]}")

conn.close()
