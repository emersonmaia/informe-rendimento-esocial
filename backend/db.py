import json
import pyodbc
from pathlib import Path

_CONNECTIONS_FILE = Path(__file__).parent.parent / "connections.json"

_active: dict = {}


def _load_connections() -> list[dict]:
    if not _CONNECTIONS_FILE.exists():
        return []
    with open(_CONNECTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_connections(conns: list[dict]):
    with open(_CONNECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(conns, f, ensure_ascii=False, indent=2)


def get_connections() -> list[dict]:
    return _load_connections()


def get_active() -> dict:
    global _active
    if _active:
        return _active
    conns = _load_connections()
    if conns:
        _active = conns[0]
    return _active


def set_active(conn_id: str) -> dict:
    global _active
    conns = _load_connections()
    for c in conns:
        if c["id"] == conn_id:
            _active = c
            return c
    raise ValueError(f"Conexão '{conn_id}' não encontrada")


def add_connection(conn: dict):
    conns = _load_connections()
    if any(c["id"] == conn["id"] for c in conns):
        raise ValueError(f"ID '{conn['id']}' já existe")
    conns.append(conn)
    _save_connections(conns)


def update_connection(conn_id: str, dados: dict):
    conns = _load_connections()
    for i, c in enumerate(conns):
        if c["id"] == conn_id:
            update = {k: v for k, v in dados.items() if k != "id"}
            if not update.get("pwd"):  # mantém a senha existente se vier vazia
                update["pwd"] = c.get("pwd", "")
            conns[i] = {**c, **update}
            _save_connections(conns)
            global _active
            if _active.get("id") == conn_id:
                _active = conns[i]
            return
    raise ValueError(f"Conexão '{conn_id}' não encontrada")


def remove_connection(conn_id: str):
    global _active
    conns = [c for c in _load_connections() if c["id"] != conn_id]
    _save_connections(conns)
    if _active.get("id") == conn_id:
        _active = conns[0] if conns else {}


def build_conn_str(c: dict) -> str:
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={c['server']};"
        f"DATABASE={c['database']};"
        f"UID={c['uid']};"
        f"PWD={c['pwd']}"
    )


def get_conn():
    return pyodbc.connect(build_conn_str(get_active()))


# ── Acessores de pasta do cliente ativo ──────────────────────────────────────

def get_pasta_xml_s1210() -> str:
    return get_active().get("pasta_xml_s1210", "")


def get_pasta_xml_s1200() -> str:
    return get_active().get("pasta_xml_s1200", "")


def get_pasta_informes() -> str:
    return get_active().get("pasta_informes", "")
