import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult'
)
cur = conn.cursor()

# CPFs que aparecem no ESOCIAL_S1210 do kiko
print("=== CPFs no ESOCIAL_S1210 kiko (com rend > 0 em 2025) ===")
cur.execute("""
    SELECT DISTINCT
        RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) AS cpf_limpo
    FROM ESOCIAL_S1210
    WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
      AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
      AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
    ORDER BY 1
""")
cpfs_esocial = [r[0] for r in cur.fetchall()]
print(f"  Total: {len(cpfs_esocial)}")
for c in cpfs_esocial:
    print(f"  {c}")

print()
print("=== Tabelas no banco kiko que possuem coluna CPF ===")
cur.execute("""
    SELECT c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS c
    WHERE c.COLUMN_NAME LIKE '%CPF%'
      AND c.TABLE_NAME NOT LIKE 'ESOCIAL%'
    ORDER BY c.TABLE_NAME
""")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}  ({r[2]}  len={r[3]})")

print()
print("=== Tabelas com CPF e NOME (candidatas) ===")
cur.execute("""
    SELECT DISTINCT c1.TABLE_NAME
    FROM INFORMATION_SCHEMA.COLUMNS c1
    JOIN INFORMATION_SCHEMA.COLUMNS c2
        ON c1.TABLE_NAME = c2.TABLE_NAME
    WHERE c1.COLUMN_NAME LIKE '%CPF%'
      AND c2.COLUMN_NAME LIKE '%NOME%'
      AND c1.TABLE_NAME NOT LIKE 'ESOCIAL%'
    ORDER BY c1.TABLE_NAME
""")
tabelas = [r[0] for r in cur.fetchall()]
for t in tabelas:
    print(f"  {t}")

print()
# Testar cada tabela candidata para ver se acha os CPFs do eSocial
for tabela in tabelas:
    try:
        cur.execute(f"""
            SELECT TOP 3 CAST(CPF AS VARCHAR(30)) AS CPF, NOME FROM [{tabela}]
            WHERE REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)),'.',''),'-',''),' ','')
                  IN ('00637552113','02930194103','03229721241')
        """)
        rows = cur.fetchall()
        if rows:
            print(f"=== MATCH em {tabela} ===")
            for r in rows:
                print(f"  CPF:[{r[0]}]  NOME:{r[1]}")
    except Exception as e:
        pass

print()
print("=== CADEMP kiko - empresas cadastradas ===")
try:
    cur.execute("SELECT EMPRESA, NOME, INSCRICAO_FEDERAL FROM CADEMP")
    for r in cur.fetchall():
        print(f"  EMP:{r[0]}  NOME:{r[1]}  CNPJ:{r[2]}")
except Exception as e:
    print(f"  ERRO: {e}")

conn.close()
