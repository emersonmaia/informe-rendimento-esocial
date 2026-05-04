import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=100.110.194.113;"
    "DATABASE=folha_kiko;"
    "UID=sa;PWD=mult"
)

conn = pyodbc.connect(CONN_STR)
cur = conn.cursor()

for cpf in ["45022743809", "32577226802"]:
    cur.execute("DELETE FROM ESOCIAL_NOME_OVERRIDE WHERE CPF = ?", cpf)
    print(f"  Removido: {cpf}  ({cur.rowcount} linha)")

conn.commit()
conn.close()

# Mostrar o que ficou
conn = pyodbc.connect(CONN_STR)
cur = conn.cursor()
cur.execute("SELECT CPF, NOME FROM ESOCIAL_NOME_OVERRIDE ORDER BY NOME")
print("\nOverride atual:")
for r in cur.fetchall():
    print(f"  {r[0]} -> {r[1]}")
conn.close()
