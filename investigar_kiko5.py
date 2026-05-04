import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult'
)
cur = conn.cursor()

print("=== ES_S1210 nativo - TODAS as colunas ===")
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'ES_S1210'
    ORDER BY ORDINAL_POSITION
""")
all_cols = [(r[0], r[1]) for r in cur.fetchall()]
for c in all_cols:
    print(f"  {c[0]}  ({c[1]})")

print()
print("=== ES_S1210 - uma linha completa (CPF 40463742842 - ISABELE) ===")
cur.execute("SELECT TOP 1 * FROM ES_S1210 WHERE cpfBenef_ideBenef = '40463742842'")
row = cur.fetchone()
if row:
    for i, c in enumerate(all_cols):
        if row[i] is not None and row[i] != '':
            print(f"  {c[0]} = {row[i]}")

print()
print("=== Campos financeiros do ES_S1210 (colunas com 'vr' ou 'vlr' ou 'vl' no nome) ===")
financeiros = [c[0] for c in all_cols if any(x in c[0].lower() for x in ['_vr', 'vlr', '_ir', 'inss', 'rend', 'trib', 'prev'])]
for c in financeiros:
    print(f"  {c}")

print()
print("=== ES_S1210 - soma por CPF (2025) com campos financeiros ===")
# Tentar identificar quais colunas têm os valores que precisamos
# Buscar colunas de rendimento e INSS
try:
    cur.execute("""
        SELECT
            cpfBenef_ideBenef AS cpf,
            perApur_ideEvento AS competencia,
            dtPgto_infoPgto   AS dt_pagto,
            vrLiq_detPgtoFl   AS vr_liq
        FROM ES_S1210
        WHERE cpfBenef_ideBenef = '40463742842'
        ORDER BY dtPgto_infoPgto
    """)
    for r in cur.fetchall():
        print(f"  CPF:{r[0]} COMP:{r[1]} PAGTO:{r[2]} LIQ:{r[3]}")
except Exception as e:
    print(f"  ERRO: {e}")

print()
print("=== Verificando consolidApurMen no ES_S1210 ===")
col_names = [c[0].lower() for c in all_cols]
consol_cols = [c[0] for c in all_cols if any(x in c[0].lower() for x in ['rendtrib', 'prevoficial', 'crmен', 'crmen', 'rendtrib13', 'prevoficial13', 'cr13'])]
if consol_cols:
    for c in consol_cols:
        print(f"  ENCONTRADO: {c}")
else:
    print("  Não encontrou colunas de consolidApurMen diretamente")

print()
print("=== es_s1210_detPgtoFl - colunas e amostra ===")
try:
    cur.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'es_s1210_detPgtoFl'
        ORDER BY ORDINAL_POSITION
    """)
    cols_det = [r[0] for r in cur.fetchall()]
    print(f"  Colunas: {cols_det}")
    cur.execute(f"SELECT TOP 3 {','.join(cols_det[:10])} FROM es_s1210_detPgtoFl ORDER BY cpfBenef_ideTrabalhador")
    for r in cur.fetchall():
        print(f"  {list(r)}")
except Exception as e:
    print(f"  ERRO: {e}")

conn.close()
