"""
Cadastra os 5 nomes identificados na ESOCIAL_NOME_OVERRIDE do folha_kiko.
"""
import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=100.110.194.113;"
    "DATABASE=folha_kiko;"
    "UID=sa;PWD=mult"
)

NOMES = [
    ("36479673867", "TATIANE CRISTINA TEIXEIRA RUCINATO", "Empregada domestica CPF Francisco - mat 25606"),
    ("07268011865", "IVONETE DE SOUZA LACERDA",           "Empregada domestica CPF Francisco - mat 25607"),
    ("05148320885", "LEONOR DE FATIMA LACERDA SANTOS",    "Empregada domestica CPF Francisco - mat 25611"),
    ("45022743809", "LILIAN BEATRIZ INACIO FERRAZ",        ""),
    ("32577226802", "MIRELLA MONTUANI DIAS",               ""),
]

conn = pyodbc.connect(CONN_STR)
cur = conn.cursor()

for cpf, nome, obs in NOMES:
    cur.execute("""
        MERGE ESOCIAL_NOME_OVERRIDE AS tgt
        USING (SELECT ? AS CPF, ? AS NOME, ? AS OBS) AS src
            ON tgt.CPF = src.CPF
        WHEN MATCHED THEN UPDATE SET NOME = src.NOME, OBS = src.OBS
        WHEN NOT MATCHED THEN INSERT (CPF, NOME, OBS) VALUES (src.CPF, src.NOME, src.OBS);
    """, cpf, nome, obs)
    print(f"  OK: {cpf} -> {nome}")

conn.commit()
conn.close()
print("\nConcluido. 5 nomes cadastrados.")
