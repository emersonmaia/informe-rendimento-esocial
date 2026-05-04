import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=100.110.194.113;DATABASE=folha_agronil;UID=sa;PWD=mult'
)
cur = conn.cursor()

CPF = '25766313802'  # Sergio Diniz Junqueira

print("=== TODOS os eventos do Sergio em 2025 (S1210 + COMPL) ===")
cur.execute("""
    SELECT
        CPF, COMPETENCIA, DT_PAGTO,
        REND_TRIB, INSS, IRRF,
        REND_TRIB_13, INSS_13, IRRF_13,
        ARQUIVO, 'S1210' AS origem
    FROM ESOCIAL_S1210
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
      AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
    UNION ALL
    SELECT
        CPF, COMPETENCIA, DT_PAGTO,
        REND_TRIB, INSS, IRRF,
        REND_TRIB_13, INSS_13, IRRF_13,
        ARQUIVO, 'S1200' AS origem
    FROM ESOCIAL_S1210_COMPL
    WHERE YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
      AND RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
    ORDER BY DT_PAGTO, COMPETENCIA
""", CPF, CPF)

total_rend = 0
total_inss = 0
total_irrf = 0
total_r13  = 0
total_i13  = 0
total_irrf13 = 0

rows = cur.fetchall()
for r in rows:
    print(f"  [{r[10]}] CPF:{r[0]} COMP:{r[1]} PAGTO:{r[2]}")
    print(f"          REND:{r[3]:>10.2f}  INSS:{r[4]:>8.2f}  IRRF:{r[5]:>8.2f}")
    print(f"          R13: {r[6]:>10.2f}  I13: {r[7]:>8.2f}  IRRF13:{r[8]:>8.2f}")
    print(f"          ARQ: {r[9]}")
    total_rend   += float(r[3] or 0)
    total_inss   += float(r[4] or 0)
    total_irrf   += float(r[5] or 0)
    total_r13    += float(r[6] or 0)
    total_i13    += float(r[7] or 0)
    total_irrf13 += float(r[8] or 0)

print()
print(f"TOTAIS:")
print(f"  Rend. Trib.:  {total_rend:>10.2f}")
print(f"  INSS:         {total_inss:>10.2f}")
print(f"  IRRF:         {total_irrf:>10.2f}")
print(f"  13 Bruto:     {total_r13:>10.2f}")
print(f"  INSS 13:      {total_i13:>10.2f}")
print(f"  IRRF 13:      {total_irrf13:>10.2f}")
print(f"  13 LIQUIDO:   {total_r13 - total_i13 - total_irrf13:>10.2f}  (= R13 - INSS13 - IRRF13)")

print()
print(f"CONFERENCIA: 8157.41 - 951.64 - 968.58 = {8157.41 - 951.64 - 968.58:.2f}")

conn.close()
