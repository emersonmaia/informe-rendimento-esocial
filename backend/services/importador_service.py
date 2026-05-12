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

from ..db import get_conn, get_active, build_conn_str, get_pasta_xml_s1210, get_pasta_xml_s1200, get_periodos_s1200
from . import job_service


# ── helpers de parse (copiados dos scripts originais) ─────────────────────────

def _f(el):
    return float(el.text) if el is not None and el.text else 0.0

def _t(el):
    return el.text.strip() if el is not None and el.text else ''


def _tag_local(el):
    return el.tag.split('}', 1)[-1].lower()


def _find_text(node, path, ns):
    el = node.find(path, ns)
    return _t(el)


def _find_float(node, path, ns):
    return _f(node.find(path, ns))


def _garantir_tabela_s1210_detalhe(cursor) -> None:
    cursor.execute("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='ESOCIAL_S1210_DETALHE')
        CREATE TABLE ESOCIAL_S1210_DETALHE (
            ID            INT IDENTITY(1,1) PRIMARY KEY,
            CPF           VARCHAR(20)   NOT NULL,
            EMPRESA       VARCHAR(100)  NOT NULL,
            COMPETENCIA   VARCHAR(10)   NOT NULL,
            DT_PAGTO      VARCHAR(20)   NULL,
            PER_REF       VARCHAR(10)   NULL,
            IDE_DMDEV     VARCHAR(40)   NULL,
            TP_PGTO       VARCHAR(10)   NULL,
            VR_LIQ        DECIMAL(18,2) NOT NULL DEFAULT 0,
            REND_TRIB     DECIMAL(18,2) NOT NULL DEFAULT 0,
            INSS          DECIMAL(18,2) NOT NULL DEFAULT 0,
            IRRF          DECIMAL(18,2) NOT NULL DEFAULT 0,
            COD_RECEITA   VARCHAR(20)   NULL,
            ARQUIVO       VARCHAR(260)  NOT NULL,
            TIPO_XML      VARCHAR(30)   NOT NULL,
            NR_RECIBO     VARCHAR(80)   NULL,
            NR_REC_ARQ    VARCHAR(80)   NULL
        )
    """)


def _listar_arquivos_ja_importados(cursor) -> set[str]:
    arquivos = set()
    cursor.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210")
    arquivos.update(r[0] for r in cursor.fetchall())

    cursor.execute("""
        SELECT COUNT(*)
        FROM sys.tables
        WHERE name = 'ESOCIAL_S1210_DETALHE'
    """)
    if cursor.fetchone()[0]:
        cursor.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210_DETALHE")
        arquivos.update(r[0] for r in cursor.fetchall())

    cursor.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210_COMPL WHERE ORIGEM='S5001'")
    arquivos.update(r[0] for r in cursor.fetchall())

    return arquivos


def _extrair_eventos(root):
    eventos = []
    for el in root.iter():
        tag = _tag_local(el)
        if tag == 'evtpgtos':
            eventos.append(('S1210_PAGAMENTO', el))
        elif tag == 'evtirrfbenef':
            eventos.append(('S1210_TOTALIZADOR', el))
        elif tag == 'evtbasestrab':
            eventos.append(('S5001', el))
        elif tag == 'evtirrf':
            eventos.append(('S5002', el))
        elif tag == 'evtbasesfgts':
            eventos.append(('S5003', el))
        elif tag == 'evtbases':
            eventos.append(('S5011', el))
    return eventos


def _parse_s1210_totalizador(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    try:
        cpf = _find_text(node, './/ns:cpfBenef', ns)
        per = _find_text(node, './/ns:perApur', ns)
        nr_rec_arq = _find_text(node, './/ns:nrRecArqBase', ns)
        resumo = []
        detalhe = []

        for dm_dev in node.findall('.//ns:dmDev', ns):
            per_ref = _find_text(dm_dev, 'ns:perRef', ns)
            ide_dmdev = _find_text(dm_dev, 'ns:ideDmDev', ns)
            tp_pgto = _find_text(dm_dev, 'ns:tpPgto', ns)
            dt_pgto = _find_text(dm_dev, 'ns:dtPgto', ns)
            # totApurMen = mensal; totApurRes = rescisório — tenta os dois
            tot = dm_dev.find('ns:totApurMen', ns)
            if tot is None:
                tot = dm_dev.find('ns:totApurRes', ns)

            rend = _find_float(tot, 'ns:vlrRendTrib', ns) if tot is not None else 0.0
            inss = _find_float(tot, 'ns:vlrPrevOficial', ns) if tot is not None else 0.0
            irrf = _find_float(tot, 'ns:vlrCRMen', ns) if tot is not None else 0.0
            cr = _find_text(tot, 'ns:CRMen', ns) if tot is not None else ''
            rend13 = _find_float(tot, 'ns:vlrRendTrib13', ns) if tot is not None else 0.0
            inss13 = _find_float(tot, 'ns:vlrPrevOficial13', ns) if tot is not None else 0.0
            irrf13 = _find_float(tot, 'ns:vlrCR13Men', ns) if tot is not None else 0.0

            resumo.append((cpf, empresa, per, dt_pgto, rend, inss, irrf, cr, rend13, inss13, irrf13, arq))
            detalhe.append((
                cpf, empresa, per, dt_pgto, per_ref, ide_dmdev, tp_pgto,
                0.0, rend, inss, irrf, cr, arq, 'S1210_TOTALIZADOR', '', nr_rec_arq
            ))

        if not resumo:
            dt_pgto = _find_text(node, './/ns:dtPgto', ns)
            consol = node.find('.//ns:consolidApurMen', ns)
            if consol is None:
                consol = node.find('.//ns:consolidApurRes', ns)
            cr = _find_text(consol, 'ns:CRMen', ns) if consol is not None else ''
            rend = _find_float(consol, 'ns:vlrRendTrib', ns) if consol is not None else 0.0
            inss = _find_float(consol, 'ns:vlrPrevOficial', ns) if consol is not None else 0.0
            irrf = _find_float(consol, 'ns:vlrCRMen', ns) if consol is not None else 0.0
            rend13 = _find_float(consol, 'ns:vlrRendTrib13', ns) if consol is not None else 0.0
            inss13 = _find_float(consol, 'ns:vlrPrevOficial13', ns) if consol is not None else 0.0
            irrf13 = _find_float(consol, 'ns:vlrCR13Men', ns) if consol is not None else 0.0
            resumo.append((cpf, empresa, per, dt_pgto, rend, inss, irrf, cr, rend13, inss13, irrf13, arq))
            detalhe.append((
                cpf, empresa, per, dt_pgto, '', '', '',
                0.0, rend, inss, irrf, cr, arq, 'S1210_TOTALIZADOR', '', nr_rec_arq
            ))

        return resumo, detalhe
    except Exception:
        return [], []


def _parse_s1210_pagamento(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    try:
        cpf = _find_text(node, './/ns:cpfBenef', ns)
        per = _find_text(node, './/ns:perApur', ns)
        nr_recibo = _find_text(node, './/ns:nrRecibo', ns)
        cod_receita = _find_text(node, './/ns:tpCR', ns)
        detalhe = []

        for info_pgto in node.findall('.//ns:infoPgto', ns):
            detalhe.append((
                cpf,
                empresa,
                per,
                _find_text(info_pgto, 'ns:dtPgto', ns),
                _find_text(info_pgto, 'ns:perRef', ns),
                _find_text(info_pgto, 'ns:ideDmDev', ns),
                _find_text(info_pgto, 'ns:tpPgto', ns),
                _find_float(info_pgto, 'ns:vrLiq', ns),
                0.0,
                0.0,
                0.0,
                cod_receita,
                arq,
                'S1210_PAGAMENTO',
                nr_recibo,
                ''
            ))

        return detalhe
    except Exception:
        return []


def _parse_s5001(node, arq):
    """Extract (cpf, perApur, vrDescSeg) from evtBasesTrab node."""
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    try:
        cpf = _find_text(node, './/ns:cpfTrab', ns)
        per = _find_text(node, './/ns:perApur', ns)
        inss = _find_float(node, './/ns:vrDescSeg', ns)
        return cpf, per, inss
    except Exception:
        return '', '', 0.0


def _comp_pagto_apur(per_apur: str) -> str:
    """Return competência de pagamento = perApur + 1 month ('2025-07' → '2025-08')."""
    ano, mes = per_apur.split('-')
    ano, mes = int(ano), int(mes)
    return f"{ano+1}-01" if mes == 12 else f"{ano}-{mes+1:02d}"


def _inserir_s5001_seletivo(cursor, cpf: str, per_apur: str, inss: float, arq: str) -> bool:
    """
    Insert S-5001 INSS into ESOCIAL_S1210_COMPL only when the S-5002
    totalizador for the payment month (perApur+1) shows INSS=0.
    This covers vacation months where INSS is declared in the competência
    month but the payment-month totalizador reports zero.
    Returns True if a row was inserted.
    """
    if not cpf or not per_apur or inss < 0.05:
        return False
    if len(per_apur) != 7:  # skip annual summaries like '2025'
        return False

    comp = _comp_pagto_apur(per_apur)
    cpf_clean = cpf.zfill(11)

    cursor.execute("""
        SELECT ISNULL(SUM(INSS), -1) AS total_inss, MAX(DT_PAGTO) AS dt_pgto
        FROM ESOCIAL_S1210
        WHERE RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
          AND COMPETENCIA = ?
    """, cpf_clean, comp)
    row = cursor.fetchone()
    total_inss = float(row[0]) if row and row[0] is not None else -1.0
    dt_pgto    = row[1] if row else None

    # -1 → no S-5002 record at all (skip); ≥0.05 → S-5002 already has INSS (skip)
    if total_inss < 0 or total_inss >= 0.05:
        return False

    cursor.execute("""
        SELECT COUNT(*) FROM ESOCIAL_S1210_COMPL
        WHERE RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
          AND COMPETENCIA = ?
          AND ORIGEM = 'S5001'
    """, cpf_clean, comp)
    if cursor.fetchone()[0]:
        return False

    cursor.execute(
        "INSERT INTO ESOCIAL_S1210_COMPL "
        "(CPF, COMPETENCIA, DT_PAGTO, REND_TRIB, INSS, IRRF, "
        "REND_TRIB_13, INSS_13, IRRF_13, COD_RECEITA, ARQUIVO, ORIGEM) "
        "VALUES (?,?,?,0,?,0,0,0,0,NULL,?,'S5001')",
        cpf_clean, comp, dt_pgto, inss, arq
    )
    return True


# ── importação S-1210 (lógica própria, sem depender de módulo externo) ─────────

def _processar_s1210(conn_str: str, pasta: str) -> dict:
    conn   = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    _garantir_tabela_s1210_detalhe(cursor)

    ja_importados = _listar_arquivos_ja_importados(cursor)

    s1210 = s1210_detalhe = s5001 = erros = 0

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
                importou_arquivo = False
                for evento, node in _extrair_eventos(root):
                    if evento == 'S1210_TOTALIZADOR':
                        resumo_rows, detalhe_rows = _parse_s1210_totalizador(node, empresa, arq)
                        for row in resumo_rows:
                            cursor.execute(
                                "INSERT INTO ESOCIAL_S1210 "
                                "(CPF,EMPRESA,COMPETENCIA,DT_PAGTO,REND_TRIB,INSS,IRRF,COD_RECEITA,"
                                "REND_TRIB_13,INSS_13,IRRF_13,ARQUIVO) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row
                            )
                            s1210 += 1
                        for row in detalhe_rows:
                            cursor.execute(
                                "INSERT INTO ESOCIAL_S1210_DETALHE "
                                "(CPF,EMPRESA,COMPETENCIA,DT_PAGTO,PER_REF,IDE_DMDEV,TP_PGTO,VR_LIQ,"
                                "REND_TRIB,INSS,IRRF,COD_RECEITA,ARQUIVO,TIPO_XML,NR_RECIBO,NR_REC_ARQ) "
                                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row
                            )
                            s1210_detalhe += 1
                        importou_arquivo = importou_arquivo or bool(resumo_rows or detalhe_rows)
                    elif evento == 'S1210_PAGAMENTO':
                        detalhe_rows = _parse_s1210_pagamento(node, empresa, arq)
                        for row in detalhe_rows:
                            cursor.execute(
                                "INSERT INTO ESOCIAL_S1210_DETALHE "
                                "(CPF,EMPRESA,COMPETENCIA,DT_PAGTO,PER_REF,IDE_DMDEV,TP_PGTO,VR_LIQ,"
                                "REND_TRIB,INSS,IRRF,COD_RECEITA,ARQUIVO,TIPO_XML,NR_RECIBO,NR_REC_ARQ) "
                                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row
                            )
                            s1210_detalhe += 1
                        importou_arquivo = importou_arquivo or bool(detalhe_rows)
                    elif evento == 'S5001':
                        cpf, per, inss = _parse_s5001(node, arq)
                        if _inserir_s5001_seletivo(cursor, cpf, per, inss, arq):
                            s5001 += 1
                            print(f"  S5001 inserido: CPF={cpf} perApur={per} INSS={inss}")
                        importou_arquivo = True
                if importou_arquivo:
                    ja_importados.add(arq)
            except Exception as e:
                print(f"Erro: {arq} -> {e}")
                erros += 1

    conn.commit()
    conn.close()
    print(f"\nS1210 resumo importados: {s1210}  |  S1210 detalhe importados: {s1210_detalhe}  |  S5001 INSS inseridos: {s5001}  |  Erros: {erros}")
    return {"s1210": s1210, "s1210_detalhe": s1210_detalhe, "s5001": s5001, "erros": erros}


# ── importação S-1200 (delega ao script original mas com conn_str fixo) ───────

def _detectar_periodos_faltando(conn_str: str) -> dict:
    """
    Retorna apenas os períodos configurados em periodos_s1200 (connections.json)
    que ainda não têm dados em ESOCIAL_S1210 nem em ESOCIAL_S1210_COMPL.
    Evita importar meses que já existem no S-1210 do portal.
    """
    periodos_cfg = get_periodos_s1200()
    if not periodos_cfg:
        return {}, set()
    TODOS = {k: tuple(v) for k, v in periodos_cfg.items()}

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


# ── importação S-2299 (rescisão via tabelas de envio eSocial) ─────────────────

def _classificar_rubrica(descricao: str, cod: str) -> str:
    """Fallback por descrição quando natRubr/tpRubr não disponíveis."""
    d = (descricao or '').upper()
    c = (cod or '').upper()
    is_13 = (
        '13' in d or '13' in c
        or 'DECIMO TERCEIRO' in d or 'DÉCIMO TERCEIRO' in d
        or 'D.TERCEIRO' in d or 'XIII' in d or 'NATAL' in d
    )
    if 'I.N.S.S' in d or ('INSS' in d and 'DESCONTO' not in d):
        return 'INSS_13' if is_13 else 'INSS'
    if 'I.R.R.F' in d or 'IRRF' in d:
        return 'IRRF_13' if is_13 else 'IRRF'
    if 'FERIAS PROP' in d or '1/3 FERIAS' in d or 'AVISO PREVIO INDE' in d:
        return 'ISENTO'
    if is_13:
        return 'REND_13'
    return 'REND_TRIB'


def _classificar_com_esocial(descricao: str, nat_rubr, tp_rubr, cod: str = '') -> str:
    """
    Classificação precisa usando natRubr/tpRubr do ES_S1010.
    nat_rubr: 1=Vencimento  2=Desconto  3=Informativo  4=Inf.dedutível
    tp_rubr:  1=Remuneração 2=13°salário 3=Férias  ...
    """
    d   = (descricao or '').upper()
    nat = str(nat_rubr or '').strip()
    tp  = str(tp_rubr  or '').strip()

    if not nat and not tp:
        return _classificar_rubrica(descricao, cod)

    is_13 = (tp == '2')

    # INSS e IRRF identificados pela descrição (são nat=2 mas precisam ser separados)
    if 'I.N.S.S' in d or ('INSS' in d and 'DESCONTO' not in d):
        return 'INSS_13' if is_13 else 'INSS'
    if 'I.R.R.F' in d or 'IRRF' in d:
        return 'IRRF_13' if is_13 else 'IRRF'

    # Outros descontos (PIS, multas, etc.) → ignorar
    if nat == '2':
        return 'DESCONTO'

    # Informativos → ignorar
    if nat in ('3', '4'):
        return 'INFORMATIVO'

    # Proventos isentos por descrição
    if 'FERIAS PROP' in d or '1/3 FERIAS' in d or 'AVISO PREVIO INDE' in d:
        return 'ISENTO'

    # Proventos tributáveis
    if is_13:
        return 'REND_13'
    return 'REND_TRIB'


def _processar_s2299(conn_str: str) -> dict:
    """
    Lê ES_S2299 + ES_S2299_detVerbas (com join opcional para ES_S1010)
    e insere rescisões faltantes em ESOCIAL_S1210_COMPL com ORIGEM='S2299'.
    Usa natRubr/tpRubr do ES_S1010 para classificação precisa quando disponível.
    """
    conn   = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Verifica tabelas obrigatórias
    cursor.execute("""
        SELECT COUNT(*) FROM sys.tables
        WHERE name IN ('ES_S2299', 'ES_S2299_detVerbas')
    """)
    if cursor.fetchone()[0] < 2:
        conn.close()
        raise RuntimeError("Tabelas ES_S2299 / ES_S2299_detVerbas não encontradas neste banco.")

    # Verifica se ES_S1010 existe para classificação precisa
    cursor.execute("SELECT COUNT(*) FROM sys.tables WHERE name = 'ES_S1010'")
    tem_s1010 = cursor.fetchone()[0] > 0
    print(f"S2299: ES_S1010 disponível = {tem_s1010}")

    # Descobre coluna de descrição em ES_S2299_detVerbas
    cursor.execute("""
        SELECT LOWER(c.name) FROM sys.columns c
        JOIN sys.tables t ON c.object_id = t.object_id
        WHERE t.name = 'ES_S2299_detVerbas' AND LOWER(c.name) LIKE '%desc%'
    """)
    desc_col_rows = cursor.fetchall()
    col_desc = desc_col_rows[0][0] if desc_col_rows else 'DESCRICAO_RUBRICA'
    print(f"S2299: coluna descrição = {col_desc}")

    # Carrega todos os cabeçalhos S-2299
    cursor.execute("""
        SELECT e.Id_evtDeslig,
               LTRIM(RTRIM(e.cpfTrab_ideVinculo))       AS cpf,
               e.dtDeslig_infoDeslig                    AS dt_deslig,
               e.ANO, e.MES
        FROM ES_S2299 e
    """)
    cabecalhos = cursor.fetchall()
    print(f"S2299: {len(cabecalhos)} rescisões encontradas")

    # Carrega todas as rubricas de uma vez (evita N queries individuais)
    if tem_s1010:
        cursor.execute(f"""
            SELECT d.Id_evtDeslig,
                   LTRIM(RTRIM(d.codRubr))                              AS cod,
                   ISNULL(TRY_CAST(d.vrRubr AS DECIMAL(18,2)), 0)       AS vr,
                   LTRIM(RTRIM(ISNULL(d.[{col_desc}], '')))             AS descr,
                   ISNULL(CAST(s.natRubr_dadosRubrica AS VARCHAR(10)), '') AS nat,
                   ISNULL(CAST(s.tpRubr_dadosRubrica  AS VARCHAR(10)), '') AS tp
            FROM ES_S2299_detVerbas d
            LEFT JOIN ES_S1010 s
                   ON s.codRubr_ideRubrica    = d.codRubr
                  AND s.ideTabRubr_ideRubrica = d.ideTabRubr
        """)
    else:
        cursor.execute(f"""
            SELECT d.Id_evtDeslig,
                   LTRIM(RTRIM(d.codRubr))                              AS cod,
                   ISNULL(TRY_CAST(d.vrRubr AS DECIMAL(18,2)), 0)       AS vr,
                   LTRIM(RTRIM(ISNULL(d.[{col_desc}], '')))             AS descr,
                   ''                                                    AS nat,
                   ''                                                    AS tp
            FROM ES_S2299_detVerbas d
        """)

    # Agrupa rubricas por Id_evtDeslig
    from collections import defaultdict
    rubricas_por_evt = defaultdict(list)
    for r in cursor.fetchall():
        rubricas_por_evt[r[0]].append((str(r[1]), float(r[2]), str(r[3]), str(r[4]), str(r[5])))

    inseridos = 0
    ignorados = 0

    for cab in cabecalhos:
        id_evt = cab[0]
        cpf    = str(cab[1] or '').replace('.', '').replace('-', '').replace(' ', '').zfill(11)
        dt_raw = cab[2]
        if cab[3] is None or cab[4] is None:
            ignorados += 1
            continue
        ano  = int(cab[3])
        mes  = int(cab[4])
        comp = f"{ano}-{mes:02d}"

        # DT_PAGTO: usa data de desligamento ou último dia da competência como fallback
        if hasattr(dt_raw, 'strftime'):
            dt_pagto = dt_raw.strftime('%Y-%m-%d')
        elif dt_raw:
            dt_pagto = str(dt_raw).strip()[:10]
        else:
            import calendar
            dt_pagto = f"{ano}-{mes:02d}-{calendar.monthrange(ano, mes)[1]:02d}"

        # Evita duplicata S2299
        cursor.execute("""
            SELECT COUNT(*) FROM ESOCIAL_S1210_COMPL
            WHERE RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = ?
              AND COMPETENCIA = ?
              AND ORIGEM = 'S2299'
        """, cpf, comp)
        if cursor.fetchone()[0]:
            ignorados += 1
            print(f"  Ignorando {cpf} {comp} — já existe S2299")
            continue

        rend_trib = inss = irrf = rend_13 = inss_13 = irrf_13 = 0.0

        for cod, vr, descr, nat, tp in rubricas_por_evt.get(id_evt, []):
            tipo = _classificar_com_esocial(descr, nat, tp, cod)
            if   tipo == 'INSS':      inss      += abs(vr)
            elif tipo == 'INSS_13':   inss_13   += abs(vr)
            elif tipo == 'IRRF':      irrf      += abs(vr)
            elif tipo == 'IRRF_13':   irrf_13   += abs(vr)
            elif tipo == 'REND_13'  and vr > 0: rend_13   += vr
            elif tipo == 'REND_TRIB' and vr > 0: rend_trib += vr

        if rend_trib == 0 and inss == 0 and irrf == 0 and rend_13 == 0:
            print(f"  Pulando {cpf} {comp} — sem valores calculados")
            ignorados += 1
            continue

        arq = f"ES_S2299_{id_evt}"
        cursor.execute(
            "INSERT INTO ESOCIAL_S1210_COMPL "
            "(CPF, COMPETENCIA, DT_PAGTO, REND_TRIB, INSS, IRRF, "
            "REND_TRIB_13, INSS_13, IRRF_13, COD_RECEITA, ARQUIVO, ORIGEM) "
            "VALUES (?,?,?,?,?,?,?,?,?,NULL,?,'S2299')",
            cpf, comp, dt_pagto,
            round(rend_trib, 2), round(inss, 2), round(irrf, 2),
            round(rend_13, 2), round(inss_13, 2), round(irrf_13, 2),
            arq
        )
        inseridos += 1
        print(f"  Inserido {cpf} {comp}  REND={rend_trib:.2f} INSS={inss:.2f} IRRF={irrf:.2f}"
              f"  REND13={rend_13:.2f} INSS13={inss_13:.2f} IRRF13={irrf_13:.2f}")

    conn.commit()
    conn.close()
    print(f"\nS2299: {inseridos} inseridos, {ignorados} ignorados")
    return {"inseridos": inseridos, "ignorados": ignorados}


def iniciar_importacao_s2299() -> "job_service.Job":
    if job_service.is_running("s2299"):
        raise RuntimeError("Importação S-2299 já em andamento")
    conn_str = build_conn_str(get_active())
    job = job_service.criar_job("s2299")

    def _worker():
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                resultado = _processar_s2299(conn_str)
            job_service.finalizar_job(job, "ok", buf.getvalue(), resultado)
        except Exception as e:
            job_service.finalizar_job(job, "erro", f"{buf.getvalue()}\nERRO: {e}")

    threading.Thread(target=_worker, daemon=True).start()
    return job


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
    ja_s1210 = _listar_arquivos_ja_importados(cur)
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
            if ".S-1200." not in nome:
                continue
            if nome not in ja_compl:
                novos_s1200.append({"arquivo": nome})

    return {
        "novos_s1210":       novos_s1210,
        "total_novos_s1210": len(novos_s1210),
        "novos_s1200":       novos_s1200,
        "total_novos_s1200": len(novos_s1200),
        "ha_novos":          len(novos_s1210) > 0 or len(novos_s1200) > 0,
    }
