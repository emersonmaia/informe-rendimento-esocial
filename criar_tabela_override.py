"""
Cria tabela ESOCIAL_NOME_OVERRIDE no banco ativo e popula com os nomes
dos 2 dependentes ja conhecidos.
Executado uma vez; pode ser re-executado sem problemas.
"""
import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=100.110.194.113;"
    "DATABASE=folha_kiko;"
    "UID=sa;PWD=mult"
)

conn = pyodbc.connect(CONN_STR)
cur = conn.cursor()

# Criar tabela se nao existir
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
print("Tabela ESOCIAL_NOME_OVERRIDE OK.")

# Popular com os 2 dependentes conhecidos
overrides = [
    ("29372255866", "MILENA RENATA DA CRUZ SAVIOLI",
     "Dependente de FUNC 14 (CPF 167.204.298-41 PLINIO SAVIOLI NETO) - pensao alimenticia"),
    ("39189138805", "CLEZIA RESENDE SOUSA CHAVES",
     "Dependente de FUNC 152 (CPF 279.405.478-36) - pensao alimenticia"),
]

for cpf, nome, obs in overrides:
    cur.execute("""
        MERGE ESOCIAL_NOME_OVERRIDE AS tgt
        USING (SELECT ? AS CPF, ? AS NOME, ? AS OBS) AS src
            ON tgt.CPF = src.CPF
        WHEN MATCHED THEN UPDATE SET NOME = src.NOME, OBS = src.OBS
        WHEN NOT MATCHED THEN INSERT (CPF, NOME, OBS) VALUES (src.CPF, src.NOME, src.OBS);
    """, cpf, nome, obs)
    print(f"  Inserido/atualizado: {cpf} -> {nome}")

conn.commit()
conn.close()
print("\nTabela populada. Para adicionar os outros 5 CPFs, use a interface de configuracao")
print("ou execute INSERT INTO ESOCIAL_NOME_OVERRIDE (CPF,NOME) VALUES ('cpf11dig','NOME').")
