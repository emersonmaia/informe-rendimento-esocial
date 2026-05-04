"""
Cria (ou garante existência de) todas as tabelas eSocial em cada banco folha_*.
Auto-detecta a collation do FOLFUN e aplica nas colunas texto das tabelas eSocial,
evitando conflito de agrupamento (erro 468) nos JOINs.
"""
import pyodbc

SERVER = '100.110.194.113'
UID    = 'sa'
PWD    = 'mult'

CONFIGS = {
    'folha_agronil': {
        'PASTA_XML':    r'D:\agronil_informe_rendimento_com_esocial\xml_consulta_site',
        'PASTA_PDF':    r'D:\agronil_informe_rendimento_com_esocial\informes_pdf',
        'ANO_CAL':      '2025',
        'DATA_EMISSAO': '27/01/2026',
    },
    'folha_kiko': {
        'PASTA_XML':    r'C:\brven\KIKO\ESOCIAL\XML_PORTAL',
        'PASTA_PDF':    r'C:\brven\KIKO\ESOCIAL\PDF',
        'ANO_CAL':      '2025',
        'DATA_EMISSAO': '27/01/2026',
    },
    'folha_flavio': {
        'PASTA_XML':    r'C:\brven\FLAVIO\ESOCIAL\XML_PORTAL',
        'PASTA_PDF':    r'C:\brven\FLAVIO\informes_pdf',
        'ANO_CAL':      '2025',
        'DATA_EMISSAO': '27/01/2026',
    },
    'folha_beatriz': {
        'PASTA_XML':    r'C:\brven\BEATRIZ\ESOCIAL\XML_PORTAL',
        'PASTA_PDF':    r'C:\brven\BEATRIZ\informes_pdf',
        'ANO_CAL':      '2025',
        'DATA_EMISSAO': '27/01/2026',
    },
}

# (tabela, coluna, tipo, nullable)
COLUNAS_TEXTO = [
    ('ESOCIAL_CONFIG',        'CHAVE',        'VARCHAR(50)',  'NOT NULL'),
    ('ESOCIAL_CONFIG',        'VALOR',        'VARCHAR(500)', 'NOT NULL'),
    ('ESOCIAL_S1210',         'CPF',          'VARCHAR(20)',  'NOT NULL'),
    ('ESOCIAL_S1210',         'EMPRESA',      'VARCHAR(100)', 'NOT NULL'),
    ('ESOCIAL_S1210',         'COMPETENCIA',  'VARCHAR(10)',  'NOT NULL'),
    ('ESOCIAL_S1210',         'DT_PAGTO',     'VARCHAR(20)',  'NULL'),
    ('ESOCIAL_S1210',         'COD_RECEITA',  'VARCHAR(20)',  'NULL'),
    ('ESOCIAL_S1210',         'ARQUIVO',      'VARCHAR(260)', 'NOT NULL'),
    ('ESOCIAL_S1210_COMPL',   'CPF',          'VARCHAR(20)',  'NOT NULL'),
    ('ESOCIAL_S1210_COMPL',   'COMPETENCIA',  'VARCHAR(10)',  'NOT NULL'),
    ('ESOCIAL_S1210_COMPL',   'DT_PAGTO',     'VARCHAR(20)',  'NULL'),
    ('ESOCIAL_S1210_COMPL',   'COD_RECEITA',  'VARCHAR(20)',  'NULL'),
    ('ESOCIAL_S1210_COMPL',   'ARQUIVO',      'VARCHAR(260)', 'NOT NULL'),
    ('ESOCIAL_S1210_COMPL',   'ORIGEM',       'VARCHAR(10)',  'NULL'),
    ('ESOCIAL_S5001',         'CPF',          'VARCHAR(20)',  'NOT NULL'),
    ('ESOCIAL_S5001',         'EMPRESA',      'VARCHAR(100)', 'NOT NULL'),
    ('ESOCIAL_S5001',         'COMPETENCIA',  'VARCHAR(10)',  'NOT NULL'),
    ('ESOCIAL_S5001',         'ARQUIVO',      'VARCHAR(260)', 'NOT NULL'),
    ('ESOCIAL_S5002',         'CPF',          'VARCHAR(20)',  'NOT NULL'),
    ('ESOCIAL_S5002',         'EMPRESA',      'VARCHAR(100)', 'NOT NULL'),
    ('ESOCIAL_S5002',         'COMPETENCIA',  'VARCHAR(10)',  'NOT NULL'),
    ('ESOCIAL_S5002',         'ARQUIVO',      'VARCHAR(260)', 'NOT NULL'),
    ('ESOCIAL_S5003',         'CPF',          'VARCHAR(20)',  'NOT NULL'),
    ('ESOCIAL_S5003',         'EMPRESA',      'VARCHAR(100)', 'NOT NULL'),
    ('ESOCIAL_S5003',         'COMPETENCIA',  'VARCHAR(10)',  'NOT NULL'),
    ('ESOCIAL_S5003',         'ARQUIVO',      'VARCHAR(260)', 'NOT NULL'),
    ('ESOCIAL_S5011',         'EMPRESA',      'VARCHAR(100)', 'NOT NULL'),
    ('ESOCIAL_S5011',         'COMPETENCIA',  'VARCHAR(10)',  'NOT NULL'),
    ('ESOCIAL_S5011',         'ARQUIVO',      'VARCHAR(260)', 'NOT NULL'),
    ('ESOCIAL_NOME_OVERRIDE', 'CPF',          'CHAR(11)',     'NOT NULL'),
    ('ESOCIAL_NOME_OVERRIDE', 'NOME',         'VARCHAR(200)', 'NOT NULL'),
]


def get_conn(banco):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={banco};UID={UID};PWD={PWD}"
    )


def detectar_collation(cursor):
    """Lê a collation da primeira coluna texto do FOLFUN. Fallback: collation do banco."""
    try:
        cursor.execute("""
            SELECT TOP 1 COLLATION_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'FOLFUN'
              AND DATA_TYPE IN ('varchar','nvarchar','char','nchar')
            ORDER BY ORDINAL_POSITION
        """)
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    # Fallback: collation padrão do banco atual
    try:
        cursor.execute("SELECT DATABASEPROPERTYEX(DB_NAME(), 'Collation')")
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    return None


def build_ddl(col):
    """Monta os CREATE TABLE usando a collation detectada."""
    return [
        f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_CONFIG')
        CREATE TABLE ESOCIAL_CONFIG (
            CHAVE   VARCHAR(50)  COLLATE {col} NOT NULL PRIMARY KEY,
            VALOR   VARCHAR(500) COLLATE {col} NOT NULL
        )
        """,
        f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210')
        CREATE TABLE ESOCIAL_S1210 (
            ID           INT IDENTITY(1,1) PRIMARY KEY,
            CPF          VARCHAR(20)   COLLATE {col} NOT NULL,
            EMPRESA      VARCHAR(100)  COLLATE {col} NOT NULL,
            COMPETENCIA  VARCHAR(10)   COLLATE {col} NOT NULL,
            DT_PAGTO     VARCHAR(20)   COLLATE {col} NULL,
            REND_TRIB    DECIMAL(18,2) NOT NULL DEFAULT 0,
            INSS         DECIMAL(18,2) NOT NULL DEFAULT 0,
            IRRF         DECIMAL(18,2) NOT NULL DEFAULT 0,
            COD_RECEITA  VARCHAR(20)   COLLATE {col} NULL,
            REND_TRIB_13 DECIMAL(18,2) NOT NULL DEFAULT 0,
            INSS_13      DECIMAL(18,2) NOT NULL DEFAULT 0,
            IRRF_13      DECIMAL(18,2) NOT NULL DEFAULT 0,
            ARQUIVO      VARCHAR(260)  COLLATE {col} NOT NULL
        )
        """,
        f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210_COMPL')
        CREATE TABLE ESOCIAL_S1210_COMPL (
            ID           INT IDENTITY(1,1) PRIMARY KEY,
            CPF          VARCHAR(20)   COLLATE {col} NOT NULL,
            COMPETENCIA  VARCHAR(10)   COLLATE {col} NOT NULL,
            DT_PAGTO     VARCHAR(20)   COLLATE {col} NULL,
            REND_TRIB    DECIMAL(18,2) NOT NULL DEFAULT 0,
            INSS         DECIMAL(18,2) NOT NULL DEFAULT 0,
            IRRF         DECIMAL(18,2) NOT NULL DEFAULT 0,
            REND_TRIB_13 DECIMAL(18,2) NOT NULL DEFAULT 0,
            INSS_13      DECIMAL(18,2) NOT NULL DEFAULT 0,
            IRRF_13      DECIMAL(18,2) NOT NULL DEFAULT 0,
            COD_RECEITA  VARCHAR(20)   COLLATE {col} NULL,
            ARQUIVO      VARCHAR(260)  COLLATE {col} NOT NULL,
            ORIGEM       VARCHAR(10)   COLLATE {col} NULL
        )
        """,
        f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S5001')
        CREATE TABLE ESOCIAL_S5001 (
            ID           INT IDENTITY(1,1) PRIMARY KEY,
            CPF          VARCHAR(20)   COLLATE {col} NOT NULL,
            EMPRESA      VARCHAR(100)  COLLATE {col} NOT NULL,
            COMPETENCIA  VARCHAR(10)   COLLATE {col} NOT NULL,
            VR_CP_SEG    DECIMAL(18,2) NOT NULL DEFAULT 0,
            VR_DESC_SEG  DECIMAL(18,2) NOT NULL DEFAULT 0,
            ARQUIVO      VARCHAR(260)  COLLATE {col} NOT NULL
        )
        """,
        f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S5002')
        CREATE TABLE ESOCIAL_S5002 (
            ID            INT IDENTITY(1,1) PRIMARY KEY,
            CPF           VARCHAR(20)   COLLATE {col} NOT NULL,
            EMPRESA       VARCHAR(100)  COLLATE {col} NOT NULL,
            COMPETENCIA   VARCHAR(10)   COLLATE {col} NOT NULL,
            VLR_BASE_IRRF DECIMAL(18,2) NOT NULL DEFAULT 0,
            VLR_IRRF      DECIMAL(18,2) NOT NULL DEFAULT 0,
            ARQUIVO       VARCHAR(260)  COLLATE {col} NOT NULL
        )
        """,
        f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S5003')
        CREATE TABLE ESOCIAL_S5003 (
            ID          INT IDENTITY(1,1) PRIMARY KEY,
            CPF         VARCHAR(20)   COLLATE {col} NOT NULL,
            EMPRESA     VARCHAR(100)  COLLATE {col} NOT NULL,
            COMPETENCIA VARCHAR(10)   COLLATE {col} NOT NULL,
            VR_FGTS     DECIMAL(18,2) NOT NULL DEFAULT 0,
            ARQUIVO     VARCHAR(260)  COLLATE {col} NOT NULL
        )
        """,
        f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S5011')
        CREATE TABLE ESOCIAL_S5011 (
            ID          INT IDENTITY(1,1) PRIMARY KEY,
            EMPRESA     VARCHAR(100)  COLLATE {col} NOT NULL,
            COMPETENCIA VARCHAR(10)   COLLATE {col} NOT NULL,
            VR_CP_APUR  DECIMAL(18,2) NOT NULL DEFAULT 0,
            VR_IRRF     DECIMAL(18,2) NOT NULL DEFAULT 0,
            ARQUIVO     VARCHAR(260)  COLLATE {col} NOT NULL
        )
        """,
        f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_NOME_OVERRIDE')
        CREATE TABLE ESOCIAL_NOME_OVERRIDE (
            CPF  CHAR(11)     COLLATE {col} NOT NULL PRIMARY KEY,
            NOME VARCHAR(200) COLLATE {col} NOT NULL
        )
        """,
    ]


def _pk_name(cursor, tabela):
    """Retorna o nome da PRIMARY KEY da tabela, ou None."""
    cursor.execute("""
        SELECT kc.name
        FROM sys.key_constraints kc
        JOIN sys.tables t ON t.object_id = kc.parent_object_id
        WHERE kc.type = 'PK' AND t.name = ?
    """, tabela)
    row = cursor.fetchone()
    return row[0] if row else None


def corrigir_collation(cursor, collation):
    """Altera a collation das colunas texto já existentes nas tabelas eSocial."""
    for tabela, coluna, tipo, nulidade in COLUNAS_TEXTO:
        # Verifica se precisa alterar
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
              AND COLLATION_NAME != ?
        """, tabela, coluna, collation)
        if cursor.fetchone()[0] == 0:
            continue  # já está correto ou tabela/coluna não existe

        # Verifica se a coluna faz parte da PK
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
              AND CONSTRAINT_NAME IN (
                  SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                  WHERE TABLE_NAME = ? AND CONSTRAINT_TYPE = 'PRIMARY KEY'
              )
        """, tabela, coluna, tabela)
        is_pk = cursor.fetchone()[0] > 0

        try:
            if is_pk:
                pk = _pk_name(cursor, tabela)
                if pk:
                    cursor.execute(f"ALTER TABLE {tabela} DROP CONSTRAINT [{pk}]")
                cursor.execute(
                    f"ALTER TABLE {tabela} ALTER COLUMN {coluna} {tipo} COLLATE {collation} {nulidade}"
                )
                cursor.execute(
                    f"ALTER TABLE {tabela} ADD CONSTRAINT PK_{tabela}_{coluna} PRIMARY KEY ({coluna})"
                )
            else:
                cursor.execute(
                    f"ALTER TABLE {tabela} ALTER COLUMN {coluna} {tipo} COLLATE {collation} {nulidade}"
                )
        except Exception as e:
            print(f"      Aviso ALTER {tabela}.{coluna}: {e}")


def upsert_config(cursor, chave, valor):
    cursor.execute(
        "IF EXISTS (SELECT 1 FROM ESOCIAL_CONFIG WHERE CHAVE=?) "
        "  UPDATE ESOCIAL_CONFIG SET VALOR=? WHERE CHAVE=? "
        "ELSE "
        "  INSERT INTO ESOCIAL_CONFIG (CHAVE,VALOR) VALUES (?,?)",
        chave, valor, chave, chave, valor
    )


def processar_banco(banco, cfg):
    print(f"\n  [{banco}]")
    try:
        conn   = get_conn(banco)
        cursor = conn.cursor()

        collation = detectar_collation(cursor)
        print(f"    Collation detectada: {collation}")

        # 1. Cria tabelas que ainda não existem (com collation correta)
        for ddl in build_ddl(collation):
            cursor.execute(ddl)

        # 2. Corrige collation das tabelas já existentes
        corrigir_collation(cursor, collation)

        # 3. Grava config
        for chave, valor in cfg.items():
            upsert_config(cursor, chave, valor)

        conn.commit()
        conn.close()
        print(f"    OK — tabelas e collation corrigidas.")
    except Exception as e:
        print(f"    ERRO: {e}")


if __name__ == '__main__':
    print("=== Setup tabelas eSocial (com correção de collation) ===")
    for banco, cfg in CONFIGS.items():
        processar_banco(banco, cfg)
    print("\nConcluído.")
