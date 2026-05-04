import pyodbc, os, glob

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult'
)
cur = conn.cursor()

print("=== ES_S1210 (nativo) - colunas ===")
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'ES_S1210'
    ORDER BY ORDINAL_POSITION
""")
cols_es = [r[0] for r in cur.fetchall()]
print("  " + ", ".join(cols_es[:20]))
if len(cols_es) > 20:
    print("  ... e mais", len(cols_es)-20)

print()
print("=== ES_S1210 (nativo) - amostra ===")
try:
    cur.execute("SELECT TOP 3 cpfBenef_ideBenef FROM ES_S1210")
    for r in cur.fetchall():
        print(f"  CPF: {r[0]}")
    cur.execute("SELECT COUNT(*) FROM ES_S1210")
    print(f"  Total linhas: {cur.fetchone()[0]}")
except Exception as e:
    print(f"  ERRO: {e}")

print()
print("=== TBL_S5002 - colunas ===")
cur.execute("""
    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'TBL_S5002' ORDER BY ORDINAL_POSITION
""")
cols_tbl = [r[0] for r in cur.fetchall()]
print("  " + ", ".join(cols_tbl))

print()
print("=== TBL_S5002 - amostra (2025) ===")
try:
    cur.execute(f"SELECT TOP 5 {', '.join(cols_tbl[:8])} FROM TBL_S5002 ORDER BY {cols_tbl[0]} DESC")
    for r in cur.fetchall():
        print(f"  {list(r)}")
    cur.execute("SELECT COUNT(DISTINCT CPF) FROM TBL_S5002")
    print(f"  CPFs distintos: {cur.fetchone()[0]}")
except Exception as e:
    print(f"  ERRO: {e}")

print()
print("=== vw_decimo - todas as colunas ===")
cur.execute("""
    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'vw_decimo' ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f"  {r[0]}")

print()
print("=== vw_decimo - amostra completa (5 primeiros) ===")
cur.execute("SELECT TOP 5 * FROM vw_decimo ORDER BY FUNC")
cols = [d[0] for d in cur.description]
print("  Cols:", cols)
for r in cur.fetchall():
    print(f"  {list(r)}")

print()
print("=== Arquivos XML na pasta kiko S-1210 ===")
pasta = r'C:\brven\KIKO\ESOCIAL\XML_PORTAL'
if os.path.isdir(pasta):
    xmls = glob.glob(os.path.join(pasta, '**', '*.xml'), recursive=True)
    print(f"  Total XMLs: {len(xmls)}")
    for x in sorted(xmls)[:10]:
        print(f"  {os.path.relpath(x, pasta)}")
else:
    print(f"  Pasta nao encontrada: {pasta}")

print()
print("=== Arquivos XML na pasta kiko S-1200 ===")
pasta2 = r'C:\brven\KIKO\ESOCIAL\XML_APLICATIVO'
if os.path.isdir(pasta2):
    xmls2 = glob.glob(os.path.join(pasta2, '**', '*.xml'), recursive=True)
    print(f"  Total XMLs: {len(xmls2)}")
    for x in sorted(xmls2)[:10]:
        print(f"  {os.path.relpath(x, pasta2)}")
else:
    print(f"  Pasta nao encontrada: {pasta2}")

conn.close()
