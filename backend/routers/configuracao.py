import pyodbc
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import db

router = APIRouter()


class NovaConexao(BaseModel):
    id: str
    nome: str
    server: str
    database: str
    uid: str
    pwd: str
    pasta_xml_s1210: str = ""
    pasta_xml_s1200: str = ""
    pasta_informes: str = ""


@router.get("/conexoes")
def listar_conexoes():
    ativa = db.get_active()
    return {
        "ativa": ativa.get("id"),
        "conexoes": db.get_connections(),
    }


@router.post("/conexoes/novo")
def adicionar_conexao(nova: NovaConexao):
    conn_dict = nova.model_dump()
    try:
        c = pyodbc.connect(db.build_conn_str(conn_dict), timeout=10)
        c.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Conexão falhou: {e}")
    try:
        db.add_connection(conn_dict)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "ok"}


@router.post("/conexoes/ativar/{conn_id}")
def ativar_conexao(conn_id: str):
    try:
        conn = db.set_active(conn_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        c = db.get_conn()
        c.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Conexão falhou: {e}")
    return {"status": "ok", "ativa": conn}


@router.put("/conexoes/{conn_id}")
def atualizar_conexao(conn_id: str, dados: NovaConexao):
    try:
        db.update_connection(conn_id, dados.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}


@router.get("/conexoes/testar/{conn_id}")
def testar_conexao(conn_id: str):
    conns = db.get_connections()
    c = next((x for x in conns if x["id"] == conn_id), None)
    if not c:
        raise HTTPException(status_code=404, detail=f"Conexão '{conn_id}' não encontrada")
    try:
        conn = pyodbc.connect(db.build_conn_str(c), timeout=10)
        conn.close()
        return {"status": "ok", "mensagem": "Conexão bem-sucedida"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/conexoes/{conn_id}")
def remover_conexao(conn_id: str):
    db.remove_connection(conn_id)
    return {"status": "ok"}


@router.get("/diagnostico")
def diagnostico():
    """Diagnóstico: verifica FOLFUN vs ESOCIAL_S1210 no banco ativo."""
    try:
        conn = db.get_conn()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sem conexão: {e}")

    cur = conn.cursor()
    r = {}

    def q(label, sql, *params):
        try:
            cur.execute(sql, *params)
            rows = cur.fetchall()
            if len(rows) == 1 and len(rows[0]) == 1:
                r[label] = rows[0][0]
            else:
                r[label] = [list(row) for row in rows]
        except Exception as e:
            r[label] = f"ERRO: {e}"

    # Colunas do FOLFUN
    q("folfun_colunas", """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'FOLFUN'
        ORDER BY ORDINAL_POSITION
    """)

    # CPF zerado vs preenchido
    q("folfun_cpf_zerado", """
        SELECT COUNT(*) FROM FOLFUN
        WHERE REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)),'.',''),'-',''),' ','') = '00000000000'
    """)
    q("folfun_cpf_valido", """
        SELECT COUNT(*) FROM FOLFUN
        WHERE REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)),'.',''),'-',''),' ','') != '00000000000'
    """)

    # Amostra com CPF válido
    q("folfun_cpf_valido_amostra", """
        SELECT TOP 5 CAST(CPF AS VARCHAR(30)), NOME FROM FOLFUN
        WHERE REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)),'.',''),'-',''),' ','') != '00000000000'
    """)

    # Amostra CPFs do ESOCIAL
    q("esocial_cpf_amostra", "SELECT TOP 5 CPF FROM ESOCIAL_S1210")

    # JOIN com limpeza
    q("join_esocial_folfun", """
        SELECT COUNT(*) FROM ESOCIAL_S1210 s
        JOIN FOLFUN f ON
            RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(CAST(f.CPF AS VARCHAR(20)),'.',''),'-',''),' ',''), 11)
            = RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11)
    """)

    # Tabelas com coluna CPF e coluna NOME (candidatas para nome do funcionário)
    q("tabelas_cpf_e_nome", """
        SELECT c1.TABLE_NAME
        FROM INFORMATION_SCHEMA.COLUMNS c1
        JOIN INFORMATION_SCHEMA.COLUMNS c2
          ON c1.TABLE_NAME = c2.TABLE_NAME
        WHERE c1.COLUMN_NAME LIKE '%CPF%'
          AND c2.COLUMN_NAME LIKE '%NOME%'
          AND c1.TABLE_NAME NOT IN ('ESOCIAL_S1210','ESOCIAL_S1210_COMPL','ESOCIAL_S1200_COMPL')
        ORDER BY c1.TABLE_NAME
    """)

    # Tenta tabela TABPRO (comum no Senior)
    q("tabpro_amostra", """
        SELECT TOP 3 * FROM TABPRO
    """)

    # Tenta tabela FOLCALC (folha calculada)
    q("folcalc_colunas", """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'FOLCALC' ORDER BY ORDINAL_POSITION
    """)

    # Verifica se FOLFUN tem NUMCAD
    q("folfun_numcad_existe", """
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'FOLFUN' AND COLUMN_NAME = 'NUMCAD'
    """)

    # Tenta mapear CPF via FOLFUN usando NUMCAD em outra tabela
    q("tabelas_com_numcad_e_cpf", """
        SELECT c1.TABLE_NAME
        FROM INFORMATION_SCHEMA.COLUMNS c1
        JOIN INFORMATION_SCHEMA.COLUMNS c2
          ON c1.TABLE_NAME = c2.TABLE_NAME
        WHERE c1.COLUMN_NAME = 'NUMCAD'
          AND c2.COLUMN_NAME LIKE '%CPF%'
          AND c1.TABLE_NAME != 'FOLFUN'
        ORDER BY c1.TABLE_NAME
    """)

    conn.close()
    return r
