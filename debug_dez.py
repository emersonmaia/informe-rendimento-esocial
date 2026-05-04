import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult"
)
cur = conn.cursor()

# Ver registros de dezembro 2025 para Jerry Adrian
cur.execute("""
    SELECT COMPETENCIA, DT_PAGTO, REND_TRIB, INSS, IRRF, REND_TRIB_13, EMPRESA, ARQUIVO
    FROM ESOCIAL_S1210
    WHERE RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = '18108574811'
    AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
    AND MONTH(TRY_CAST(DT_PAGTO AS DATE)) = 12
    ORDER BY DT_PAGTO, EMPRESA
""")
print("Jerry Adrian (18108574811) em dezembro 2025:")
for r in cur.fetchall():
    print(f"  comp={r[0]} dtpgto={r[1]} rt={r[2]:.2f} inss={r[3]:.2f} irrf={r[4]:.2f} rt13={r[5]:.2f} emp={r[6]}")

print()
# CPFs com 2+ registros em 05/12/2025
cur.execute("""
    SELECT
        RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) AS cpf_limpo,
        COUNT(*) as cnt,
        COUNT(DISTINCT EMPRESA) as emps
    FROM ESOCIAL_S1210
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
      AND MONTH(TRY_CAST(DT_PAGTO AS DATE)) = 12
      AND DAY(TRY_CAST(DT_PAGTO AS DATE)) = 5
    GROUP BY RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11)
    HAVING COUNT(*) > 1
    ORDER BY cnt DESC
""")
print("CPFs com multiplos registros em 05/12/2025:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} registros, {r[2]} empresas distintas")

conn.close()
