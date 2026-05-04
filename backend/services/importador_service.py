"""
Importação de XMLs eSocial para o banco ativo.

Não usa monkey-patching de módulos externos — captura conexão e pasta
no momento do disparo do job e passa direto para a lógica de importação.
Isso evita que troca de banco durante um import corrompendo outro banco.
"""
import io
import glob
import os
import contextlib
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

import pyodbc

from ..db import get_conn, get_active, build_conn_str, get_pasta_xml_s1210, get_pasta_xml_s1200
from . import job_service


# ── helpers de parse (copiados dos scripts originais) ─────────────────────────

def _f(el):
    return float(el.text) if el is not None and el.text else 0.0

def _t(el):
    return el.text.strip() if el is not None and el.text else ''


def _extrair_evento(root):
    for ev in root.findall('.//{*}retornoProcessamentoDownload/{*}evento'):
        esocial = ev.find('.//{*}eSocial')
        if esocial is None:
            continue
        for child in list(esocial):
            tag = child.tag.lower()
            if 'evtirrfbenef' in tag:
                return 'S1210', child
            if 'evtbasestrab' in tag:
                return 'S5001', child
            if 'evtirrf' in tag and 'benef' not in tag:
                return 'S5002', child
            if 'evtbasesfgts' in tag:
                return 'S5003', child
            if 'evtbases' in tag and 'trab' not in tag:
                return 'S5011', child
    return None, None


def _parse_s1210(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    try:
        cpf    = node.find('.//ns:cpfBenef', ns).text.strip()
        per    = node.find('.//ns:perApur',   ns).text.strip()
        dtpgto = _t(node.find('.//ns:dtPgto', ns))
        cr     = _t(node.find('.//ns:CRMen',  ns))
        consol = node.find('.//ns:consolidApurMen', ns)
        if consol is not None:
            rend   = _f(consol.find('ns:vlrRendTrib',      ns))
            inss   = _f(consol.find('ns:vlrPrevOficial',   ns))
            irrf   = _f(consol.find('ns:vlrCRMen',         ns))
            rend13 = _f(consol.find('ns:vlrRendTrib13',    ns))
            inss13 = _f(consol.find('ns:vlrPrevOficial13', ns))
            irrf13 = _f(consol.find('ns:vlrCR13Men',       ns))
        else:
            rend = inss = irrf = rend13 = inss13 = irrf13 = 0.0
            for tot in node.findall('.//ns:totApurMen', ns):
                rend   += _f(tot.find('ns:vlrRendTrib',      ns))
                inss   += _f(tot.find('ns:vlrPrevOficial',   ns))
                irrf   += _f(tot.find('ns:vlrCRMen',         ns))
                rend13 += _f(tot.find('ns:vlrRendTrib13',    ns))
                inss13 += _f(tot.find('ns:vlrPrevOficial13', ns))
                irrf13 += _f(tot.find('ns:vlrCR13Men',       ns))
        return (cpf, empresa, per, dtpgto, rend, inss, irrf, cr, rend13, inss13, irrf13, arq)
    except Exception:
        return None


# ── importação S-1210 (lógica própria, sem depender de módulo externo) ─────────

def _processar_s1210(conn_str: str, pasta: str) -> dict:
    conn   = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210")
    ja_importados = {r[0] for r in cursor.fetchall()}

    s1210 = erros = 0

    for raiz, _, arquivos in os.walk(pasta):
        empresa = os.path.basename(raiz)
        for arq in sorted(arquivos):
            if not arq.endswith('.xml'):
                continue
            if arq in ja_importados:
                continue
            caminho = os.path.join(raiz, arq)
            try:
                root   = ET.parse(caminho).getroot()
                evento, node = _extrair_evento(root)
                if evento != 'S1210':
                    continue
                d = _parse_s1210(node, empresa, arq)
                if d:
                    cursor.execute(
                        "INSERT INTO ESOCIAL_S1210 "
                        "(CPF,EMPRESA,COMPETENCIA,DT_PAGTO,REND_TRIB,INSS,IRRF,COD_RECEITA,"
                        "REND_TRIB_13,INSS_13,IRRF_13,ARQUIVO) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", d
                    )
                    ja_importados.add(arq)
                    s1210 += 1
            except Exception as e:
                print(f"Erro: {arq} -> {e}")
                erros += 1

    conn.commit()
    conn.close()
    print(f"\nS1210 importados: {s1210}  |  Erros: {erros}")
    return {"s1210": s1210, "erros": erros}


# ── importação S-1200 (delega ao script original mas com conn_str fixo) ───────

def _detectar_periodos_faltando(conn_str: str) -> dict:
    """
    Retorna apenas os períodos do PERIODOS padrão que ainda não têm dados
    em ESOCIAL_S1210 nem em ESOCIAL_S1210_COMPL para o ano de 2025.
    Isso evita importar meses que já existem no S-1210 do portal.
    """
    # Todos os períodos possíveis (mesmo mapeamento do script original)
    TODOS = {
        '2025-05': ('2025-06', '2025-06-06'),
        '2025-11': ('2025-12', '2025-12-05'),
        '2025':    ('2025-12', '2025-12-20'),
    }
    conn = pyodbc.connect(conn_str)
    cur  = conn.cursor()

    # Competências já presentes no S1210 (portal)
    cur.execute("SELECT DISTINCT COMPETENCIA FROM ESOCIAL_S1210")
    comps_s1210 = {r[0] for r in cur.fetchall()}

    # Períodos já importados via COMPL (evita reimportar)
    cur.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210_COMPL WHERE ORIGEM='S1200'")
    arqs_compl = {r[0] for r in cur.fetchall()}

    conn.close()

    faltando = {}
    for per, mapa in TODOS.items():
        comp_alvo = mapa[0]          # competência que vai para o informe
        if comp_alvo not in comps_s1210:
            faltando[per] = mapa
    return faltando, arqs_compl


def _processar_s1200(conn_str: str, pasta: str) -> dict:
    """
    Importa S-1200 complementar apenas para os períodos que ainda faltam
    no banco destino, evitando duplicatas com o S-1210 do portal.
    """
    import sys
    from pathlib import Path
    _SCRIPTS_DIR = Path(__file__).parent.parent.parent
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    import importador_s1200_compl as mod

    periodos_faltando, arqs_ja_importados = _detectar_periodos_faltando(conn_str)

    if not periodos_faltando:
        print("Nenhum periodo faltando — nada a importar do S-1200.")
        return {}

    print(f"Periodos faltando: {list(periodos_faltando.keys())}")

    def _frozen_conn():
        return pyodbc.connect(conn_str)

    original_conn    = mod.get_conn
    original_pasta   = mod.PASTA
    original_periodos = mod.PERIODOS
    mod.get_conn  = _frozen_conn
    mod.PASTA     = pasta
    mod.PERIODOS  = periodos_faltando
    try:
        mod.processar()
    finally:
        mod.get_conn   = original_conn
        mod.PASTA      = original_pasta
        mod.PERIODOS   = original_periodos
    return {}


# ── funções públicas ───────────────────────────────────────────────────────────

def iniciar_importacao_s1210() -> "job_service.Job":
    if job_service.is_running("s1210"):
        raise RuntimeError("Importação S-1210 já em andamento")
    pasta = get_pasta_xml_s1210()
    if not pasta:
        raise RuntimeError(
            "Pasta de XMLs S-1210 não configurada para este banco. "
            "Edite a conexão e preencha o campo 'Pasta XML S-1210'."
        )
    # Congela conn_str AGORA — troca de banco posterior não afeta este job
    conn_str = build_conn_str(get_active())
    job = job_service.criar_job("s1210")

    def _worker():
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                resultado = _processar_s1210(conn_str, pasta)
            job_service.finalizar_job(job, "ok", buf.getvalue(), resultado)
        except Exception as e:
            job_service.finalizar_job(job, "erro", f"{buf.getvalue()}\nERRO: {e}")

    threading.Thread(target=_worker, daemon=True).start()
    return job


def iniciar_importacao_s1200() -> "job_service.Job":
    if job_service.is_running("s1200"):
        raise RuntimeError("Importação S-1200 já em andamento")
    pasta = get_pasta_xml_s1200()
    if not pasta:
        raise RuntimeError(
            "Pasta de XMLs S-1200 não configurada para este banco. "
            "Edite a conexão e preencha o campo 'Pasta XML S-1200'."
        )
    conn_str = build_conn_str(get_active())
    job = job_service.criar_job("s1200")

    def _worker():
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                _processar_s1200(conn_str, pasta)
            job_service.finalizar_job(job, "ok", buf.getvalue())
        except Exception as e:
            job_service.finalizar_job(job, "erro", f"{buf.getvalue()}\nERRO: {e}")

    threading.Thread(target=_worker, daemon=True).start()
    return job


# ── verificação de XMLs novos ──────────────────────────────────────────────────

def verificar_novos_xmls() -> dict:
    pasta_s1210 = get_pasta_xml_s1210()
    pasta_s1200 = get_pasta_xml_s1200()

    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210")
    ja_s1210 = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210_COMPL")
    ja_compl = {r[0] for r in cur.fetchall()}
    conn.close()

    IGNORAR = (".S-5001.", ".S-5002.", ".S-5003.", ".S-5011.", ".S-5013.")
    novos_s1210 = []
    if pasta_s1210:
        for raiz, _, arqs in os.walk(pasta_s1210):
            empresa = os.path.basename(raiz)
            for arq in sorted(arqs):
                if not arq.endswith(".xml"):
                    continue
                if any(p in arq for p in IGNORAR):
                    continue
                if arq not in ja_s1210:
                    novos_s1210.append({"arquivo": arq, "empresa": empresa})

    novos_s1200 = []
    if pasta_s1200:
        for f in glob.glob(os.path.join(pasta_s1200, "ID*.xml")):
            nome = os.path.basename(f)
            if nome not in ja_compl:
                novos_s1200.append({"arquivo": nome})

    return {
        "novos_s1210":       novos_s1210,
        "total_novos_s1210": len(novos_s1210),
        "novos_s1200":       novos_s1200,
        "total_novos_s1200": len(novos_s1200),
        "ha_novos":          len(novos_s1210) > 0 or len(novos_s1200) > 0,
    }
