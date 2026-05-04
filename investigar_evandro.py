import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=100.110.194.113;DATABASE=folha_agronil;UID=sa;PWD=mult'
)
cur = conn.cursor()

CPF = '11863837809'  # Evandro Navarro

cur.execute("""
    SELECT CPF, COMPETENCIA, DT_PAGTO,
           REND_TRIB, INSS, IRRF,
           REND_TRIB_13, INSS_13, IRRF_13,
           'S1210' AS origem
    FROM ESOCIAL_S1210
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
      AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
    UNION ALL
    SELECT CPF, COMPETENCIA, DT_PAGTO,
           REND_TRIB, INSS, IRRF,
           REND_TRIB_13, INSS_13, IRRF_13,
           'S1200' AS origem
    FROM ESOCIAL_S1210_COMPL
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
      AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
    ORDER BY DT_PAGTO, COMPETENCIA
""", CPF, CPF)

rows = cur.fetchall()
r13 = i13 = ir13 = 0
for r in rows:
    r13  += float(r[6] or 0)
    i13  += float(r[7] or 0)
    ir13 += float(r[8] or 0)
    if r[6] or r[7] or r[8]:
        print("[%s] COMP:%s PAGTO:%s" % (r[9], r[1], r[2]))
        print("  REND13:%10.2f  INSS13:%8.2f  IRRF13:%8.2f" % (r[6] or 0, r[7] or 0, r[8] or 0))

print()
print("13 Bruto        = %10.2f" % r13)
print("INSS 13         = %10.2f" % i13)
print("IRRF 13         = %10.2f" % ir13)
print("                  ----------")
print("Bruto - INSS    = %10.2f  (rend13 - inss13 apenas)" % (r13 - i13))
print("- INSS e -IRRF  = %10.2f  (rend13 - inss13 - irrf13 = campo 5.1 atual)" % (r13 - i13 - ir13))
conn.close()
