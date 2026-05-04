import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult'
)
cur = conn.cursor()

print("=== ESOCIAL_S1210 - amostra de CPFs ===")
cur.execute("SELECT TOP 5 CPF, LEN(LTRIM(RTRIM(CPF))) AS tam FROM ESOCIAL_S1210")
for r in cur.fetchall():
    print(f"  CPF: [{r[0]}]  len={r[1]}")

print()
print("=== FOLFUN - amostra de CPFs e NOMES ===")
cur.execute("SELECT TOP 10 CAST(CPF AS VARCHAR(30)) AS CPF, NOME FROM FOLFUN WHERE NOME IS NOT NULL AND NOME != ''")
for r in cur.fetchall():
    print(f"  CPF: [{r[0]}]  NOME: {r[1]}")

print()
print("=== CPF do ESOCIAL limpo vs CPF do FOLFUN limpo (amostra JOIN) ===")
cur.execute("""
    SELECT TOP 5
        s.CPF AS cpf_esocial,
        RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11) AS cpf_esocial_limpo,
        CAST(f.CPF AS VARCHAR(30)) AS cpf_folfun,
        RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(CAST(f.CPF AS VARCHAR(20)),'.',''),'-',''),' ',''), 11) AS cpf_folfun_limpo,
        f.NOME
    FROM ESOCIAL_S1210 s
    LEFT JOIN FOLFUN f
        ON RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(CAST(f.CPF AS VARCHAR(20)),'.',''),'-',''),' ',''), 11)
         = RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11)
    WHERE (REND_TRIB > 0 OR REND_TRIB_13 > 0)
""")
for r in cur.fetchall():
    print(f"  eSocial:[{r[0]}] -> [{r[1]}]  |  FOLFUN:[{r[2]}] -> [{r[3]}]  NOME:{r[4]}")

print()
print("=== FOLFUN - tipo e tamanho da coluna CPF ===")
cur.execute("""
    SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'FOLFUN' AND COLUMN_NAME = 'CPF'
""")
for r in cur.fetchall():
    print(f"  Tipo: {r[0]}  MaxLen/Prec: {r[1] or r[2]}  Scale: {r[3]}")

print()
print("=== FOLFUN - CPF zerado vs preenchido ===")
cur.execute("""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)),'.',''),'-',''),' ','') = '00000000000' THEN 1 ELSE 0 END) AS zerados,
        SUM(CASE WHEN REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)),'.',''),'-',''),' ','') != '00000000000' THEN 1 ELSE 0 END) AS validos
    FROM FOLFUN
""")
r = cur.fetchone()
print(f"  Total: {r[0]}  Zerados: {r[1]}  Validos: {r[2]}")

print()
print("=== Tentativa de JOIN por CPF especifico (006.375.521-13) ===")
CPF_TESTE = '00637552113'
cur.execute("""
    SELECT CAST(CPF AS VARCHAR(30)), NOME
    FROM FOLFUN
    WHERE RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)),'.',''),'-',''),' ',''), 11)
          = ?
""", CPF_TESTE)
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  CPF: [{r[0]}]  NOME: {r[1]}")
else:
    print("  NENHUM RESULTADO")

print()
print("=== FOLFUN - amostra com NUMCAD e CPF ===")
cur.execute("""
    SELECT TOP 5 NUMCAD, CAST(CPF AS VARCHAR(30)) AS CPF, NOME
    FROM FOLFUN
    WHERE NOME IS NOT NULL AND NOME != ''
    ORDER BY NUMCAD
""")
for r in cur.fetchall():
    print(f"  NUMCAD:{r[0]}  CPF:[{r[1]}]  NOME:{r[2]}")

conn.close()
