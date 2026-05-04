"""
Cria tabela ESOCIAL_NOME_OVERRIDE em ambos os bancos (agronil e kiko).
"""
import pyodbc

DBS = [
    ("folha_agronil", "DRIVER={ODBC Driver 17 for SQL Server};SERVER=100.110.194.113;DATABASE=folha_agronil;UID=sa;PWD=mult"),
    ("folha_kiko",    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult"),
]

for db_name, conn_str in DBS:
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()
    cur.execute("""
        IF NOT EXISTS (
            SELECT 1 FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'ESOCIAL_NOME_OVERRIDE'
        )
        CREATE TABLE ESOCIAL_NOME_OVERRIDE (
            CPF   VARCHAR(11) PRIMARY KEY,
            NOME  VARCHAR(200) NOT NULL,
            OBS   VARCHAR(500) NULL
        )
    """)
    conn.commit()
    conn.close()
    print(f"  {db_name}: ESOCIAL_NOME_OVERRIDE OK")

print("Concluido.")
