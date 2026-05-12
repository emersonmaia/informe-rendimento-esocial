"""
Importador de XMLs S-5001 (evtBasesTrab) para ES_S5001_GERAL.
Lê todas as pastas de XML, extrai campos, gera resumo markdown para IA,
vincula com ES_S1200 via cpfTrab+perApur ou matricula.
"""

import os
import re
import json
import pyodbc
from datetime import datetime
from xml.etree import ElementTree as ET

# ── Pastas de XML ──────────────────────────────────────────────────────────────
PASTAS = [
    (r"D:\agronil_informe_rendimento_com_esocial\consulta\entregues", "entregues"),
]

# Protocolos baixados via consulta lote no site do eSocial
SITE_BASE = r"D:\agronil_informe_rendimento_com_esocial\xml_consulta_site"
for sub in sorted(os.listdir(SITE_BASE)):
    sub_path = os.path.join(SITE_BASE, sub)
    if os.path.isdir(sub_path):
        PASTAS.append((sub_path, sub))

# Respostas individuais do eSocial — estrutura: consulta\{CNPJ}\{YYYYMM}\eSocial\
CONSULTA_BASE = r"D:\agronil_informe_rendimento_com_esocial\consulta"
for cnpj in sorted(os.listdir(CONSULTA_BASE)):
    cnpj_path = os.path.join(CONSULTA_BASE, cnpj)
    if not os.path.isdir(cnpj_path) or cnpj in ('entregues', 'esocial', 'consulta',
                                                   'Borland Shared', 'Docs', 'Logs'):
        continue
    for mes in sorted(os.listdir(cnpj_path)):
        mes_path = os.path.join(cnpj_path, mes)
        if not os.path.isdir(mes_path): continue
        esocial_path = os.path.join(mes_path, 'eSocial')
        if os.path.isdir(esocial_path):
            fonte = f"consulta_{cnpj[:8]}_{mes}"
            PASTAS.append((esocial_path, fonte))

NS = {
    'es5001': 'http://www.esocial.gov.br/schema/evt/evtBasesTrab/v_S_01_03_00',
    'dl':     'http://www.esocial.gov.br/schema/download/retornoProcessamento/v1_0_0',
}


def strip_ns(tag):
    return tag.split('}')[-1] if '}' in tag else tag


def xml_to_dict(elem):
    """Converte elemento XML em dict recursivo para JSON/markdown."""
    d = {}
    for child in elem:
        key = strip_ns(child.tag)
        val = xml_to_dict(child) if len(child) else (child.text or '').strip()
        if key in d:
            if not isinstance(d[key], list):
                d[key] = [d[key]]
            d[key].append(val)
        else:
            d[key] = val
    return d


def parse_s5001(xml_path):
    """Extrai campos do S-5001. Retorna dict ou None se não for S-5001."""
    try:
        xml_txt = open(xml_path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return None

    # Detecta schema S-5001
    if 'evtBasesTrab' not in xml_txt:
        return None

    try:
        root = ET.fromstring(xml_txt)
    except ET.ParseError:
        return None

    # Localiza evtBasesTrab em qualquer namespace
    evt = None
    for elem in root.iter():
        if strip_ns(elem.tag) == 'evtBasesTrab':
            evt = elem
            break
    if evt is None:
        return None

    def find_text(parent, *tags):
        for tag in tags:
            for elem in parent.iter():
                if strip_ns(elem.tag) == tag:
                    return (elem.text or '').strip()
        return ''

    id_evento    = evt.get('Id', '')
    nr_rec       = find_text(evt, 'nrRecArqBase')
    per_apur     = find_text(evt, 'perApur')
    ind_apuracao = find_text(evt, 'indApuracao')
    tp_insc_empr = find_text(evt, 'tpInsc')
    nr_insc_empr = ''
    cpf_trab     = find_text(evt, 'cpfTrab')
    matricula    = find_text(evt, 'matricula')
    cod_categ    = find_text(evt, 'codCateg')
    tp_insc_estab= ''
    nr_insc_estab= ''
    cod_lotacao  = find_text(evt, 'codLotacao')

    # ideEmpregador
    for elem in evt.iter():
        if strip_ns(elem.tag) == 'ideEmpregador':
            for c in elem:
                t = strip_ns(c.tag)
                if t == 'tpInsc': tp_insc_empr = (c.text or '').strip()
                if t == 'nrInsc': nr_insc_empr = (c.text or '').strip()
            break

    # ideEstabLot
    for elem in evt.iter():
        if strip_ns(elem.tag) == 'ideEstabLot':
            for c in elem:
                t = strip_ns(c.tag)
                if t == 'tpInsc': tp_insc_estab = (c.text or '').strip()
                if t == 'nrInsc': nr_insc_estab = (c.text or '').strip()
            break

    # Totais INSS (infoCpCalc)
    vr_cp_seg  = 0.0  # contribuição patronal
    vr_desc_seg = 0.0  # desconto empregado
    for elem in evt.iter():
        if strip_ns(elem.tag) == 'infoCpCalc':
            for c in elem:
                t = strip_ns(c.tag)
                if t == 'vrCpSeg':   vr_cp_seg  = float(c.text or 0)
                if t == 'vrDescSeg': vr_desc_seg = float(c.text or 0)
            break

    # Coleta infoBaseCS (bases e valores)
    bases = []
    for elem in evt.iter():
        if strip_ns(elem.tag) == 'infoBaseCS':
            b = {}
            for c in elem:
                b[strip_ns(c.tag)] = (c.text or '').strip()
            bases.append(b)

    # infoPerRef (períodos de referência)
    per_refs = []
    for elem in evt.iter():
        if strip_ns(elem.tag) == 'infoPerRef':
            pr = {'perRef': '', 'detalhes': []}
            for c in elem:
                t = strip_ns(c.tag)
                if t == 'perRef':
                    pr['perRef'] = (c.text or '').strip()
                elif t == 'detInfoPerRef':
                    det = {}
                    for cc in c:
                        det[strip_ns(cc.tag)] = (cc.text or '').strip()
                    pr['detalhes'].append(det)
            per_refs.append(pr)

    vr_total = vr_desc_seg  # desconto do empregado é o INSS retido

    # SQL Server rejeita XML com encoding declaration na coluna xml
    xml_retorno = re.sub(r'<\?xml[^?]*\?>', '', xml_txt).strip()

    # ── Gera resumo Markdown para IA ──────────────────────────────────────────
    tp_map = {'11': 'Base INSS', '21': 'INSS descontado', '22': 'INSS patronal',
              '51': 'Base IRRF', '61': 'IRRF retido'}
    md_lines = [
        f"# S-5001 eSocial — {per_apur}",
        f"**CPF:** {cpf_trab}  **Matrícula:** {matricula}  **Categoria:** {cod_categ}",
        f"**Empresa:** {nr_insc_empr}  **Estabelecimento:** {nr_insc_estab}",
        f"**Período:** {per_apur}  **indApuracao:** {ind_apuracao} ({'mensal' if ind_apuracao=='1' else '13° salário'})",
        f"**nrRecibo original (S-1200):** {nr_rec}",
        "",
        "## Contribuições",
        f"| Campo | Valor |",
        f"|-------|-------|",
        f"| INSS patronal (vrCpSeg) | R$ {vr_cp_seg:,.2f} |",
        f"| INSS desconto empregado (vrDescSeg) | R$ {vr_desc_seg:,.2f} |",
        "",
    ]
    if bases:
        md_lines += ["## Bases de cálculo", "| ind13 | Tipo | Valor |", "|-------|------|-------|"]
        for b in bases:
            tp = b.get('tpValor', '')
            desc = tp_map.get(tp, tp)
            md_lines.append(f"| {b.get('ind13','')} | {desc} | R$ {float(b.get('valor',0)):,.2f} |")
        md_lines.append("")

    if per_refs:
        md_lines += ["## Períodos de referência", "| Período | ind13 | Tipo | Valor |",
                     "|---------|-------|------|-------|"]
        for pr in per_refs:
            for det in pr['detalhes']:
                tp = det.get('tpVrPerRef', '')
                md_lines.append(
                    f"| {pr['perRef']} | {det.get('ind13','')} | {tp_map.get(tp,tp)} | R$ {float(det.get('vrPerRef',0)):,.2f} |"
                )
        md_lines.append("")

    md_lines.append(f"**ID Evento S-5001:** `{id_evento}`")
    resumo_md = "\n".join(md_lines)

    # JSON compacto para API de IA
    json_data = json.dumps({
        "evento": "S-5001",
        "id": id_evento,
        "nrRecibo_s1200": nr_rec,
        "perApur": per_apur,
        "indApuracao": ind_apuracao,
        "cpfTrab": cpf_trab,
        "matricula": matricula,
        "nrInsc_empregador": nr_insc_empr,
        "nrInsc_estab": nr_insc_estab,
        "codLotacao": cod_lotacao,
        "codCateg": cod_categ,
        "inss_patronal": vr_cp_seg,
        "inss_desconto": vr_desc_seg,
        "bases": bases,
        "periodos": per_refs,
    }, ensure_ascii=False, default=str)

    return {
        'id_evento':      id_evento,
        'nr_insc_empr':   nr_insc_empr,
        'tp_insc_empr':   tp_insc_empr,
        'tp_insc_estab':  tp_insc_estab,
        'nr_insc_estab':  nr_insc_estab,
        'per_apur':       per_apur,
        'cpf_trab':       cpf_trab,
        'matricula':      matricula,
        'vr_total':       vr_total,
        'nr_rec_evt':     nr_rec,
        'xml_retorno':    xml_retorno,
        'resumo_md':      resumo_md,
        'json_data':      json_data,
    }


def importar(conn_str, dry_run=False, limite=None):
    conn = pyodbc.connect(conn_str)
    conn.autocommit = False
    cur = conn.cursor()

    # Carrega IDs já importados
    cur.execute("SELECT Id_Evento FROM ES_S5001_GERAL WHERE Id_Evento IS NOT NULL")
    ja_importados = {r[0] for r in cur.fetchall()}
    print(f"Já importados: {len(ja_importados)}")

    # Mapa cpfTrab+perApur → Id_evtRemun (ES_S1200)
    cur.execute("""
        SELECT cpfTrab_ideTrabalhador, perApur_ideEvento,
               matricula_remunPerApur, Id_evtRemun
        FROM ES_S1200
        WHERE Id_evtRemun IS NOT NULL
    """)
    s1200_map = {}
    for r in cur.fetchall():
        key = (str(r[0] or '').strip(), str(r[1] or '').strip())
        s1200_map[key] = str(r[3] or '').strip()

    total_ok = total_skip = total_nao_s5001 = total_err = 0

    for pasta, fonte in PASTAS:
        if not os.path.exists(pasta):
            continue
        # Na pasta consulta_{cnpj}: só arquivos S5001 pelo nome para evitar leitura desnecessária
        if fonte.startswith('consulta_'):
            xmls = sorted(f for f in os.listdir(pasta)
                          if f.endswith('-S5001.xml') or (f.endswith('.xml') and 'S-5001' in f))
        else:
            xmls = sorted(f for f in os.listdir(pasta) if f.endswith('.xml'))
        print(f"\n{fonte}: {len(xmls)} XMLs", flush=True)

        for i, fname in enumerate(xmls):
            if limite and (total_ok + total_skip) >= limite:
                break

            fpath = os.path.join(pasta, fname)

            # Extrai ID do nome do arquivo
            m = re.match(r'(ID\w+)\.', fname)
            file_id = m.group(1) if m else fname

            if file_id in ja_importados:
                total_skip += 1
                continue

            data = parse_s5001(fpath)
            if data is None:
                total_nao_s5001 += 1
                continue

            if data['id_evento'] in ja_importados:
                total_skip += 1
                continue

            # Vínculo com ES_S1200
            key = (data['cpf_trab'], data['per_apur'])
            id_s1200 = s1200_map.get(key, '')

            if not dry_run:
                try:
                    def to_int(v):
                        try: return int(v) if v else None
                        except: return None

                    ti_empr  = to_int(data['tp_insc_empr'])
                    ti_estab = to_int(data['tp_insc_estab'])

                    # UPSERT: INSERT or UPDATE se já existe (retificação)
                    cur.execute("""
                        MERGE ES_S5001_GERAL AS T
                        USING (SELECT ? AS Id_Evento, ? AS nrInsc_Empregador,
                                      ? AS perApur, ? AS cpfTrab) AS S
                        ON (T.nrInsc_Empregador=S.nrInsc_Empregador
                            AND T.perApur=S.perApur AND T.cpfTrab=S.cpfTrab)
                        WHEN MATCHED THEN UPDATE SET
                            Id_Evento=S.Id_Evento,
                            tpInsc_Empregador=?, nrInsc_Estab=?,
                            tpInsc_Estab=?,
                            VR_TOTAL=?, nrRecEvt=?,
                            XML_RETORNO=?, RESUMO_MARKDOWN=?,
                            matricula=?, fonte_xml=?, Id_S1200=?,
                            dtImportacao=GETDATE()
                        WHEN NOT MATCHED THEN INSERT
                            (Id_Evento, tpInsc_Empregador, nrInsc_Empregador,
                             tpInsc_Estab, nrInsc_Estab, perApur, cpfTrab,
                             VR_TOTAL, nrRecEvt, XML_RETORNO, RESUMO_MARKDOWN,
                             dtImportacao, matricula, fonte_xml, Id_S1200)
                        VALUES (S.Id_Evento, ?, S.nrInsc_Empregador,
                                ?, ?, S.perApur, S.cpfTrab,
                                ?, ?, ?, ?,
                                GETDATE(), ?, ?, ?);
                    """,
                        # USING source params
                        data['id_evento'], data['nr_insc_empr'],
                        data['per_apur'], data['cpf_trab'],
                        # UPDATE SET params
                        ti_empr, data['nr_insc_estab'],
                        ti_estab,
                        data['vr_total'], data['nr_rec_evt'],
                        data['xml_retorno'], data['resumo_md'],
                        data['matricula'], fonte, id_s1200,
                        # INSERT VALUES params
                        ti_empr,
                        ti_estab, data['nr_insc_estab'],
                        data['vr_total'], data['nr_rec_evt'],
                        data['xml_retorno'], data['resumo_md'],
                        data['matricula'], fonte, id_s1200,
                    )
                    ja_importados.add(data['id_evento'])
                    total_ok += 1

                    if total_ok % 200 == 0:
                        conn.commit()
                        print(f"  ...{total_ok} importados/atualizados", flush=True)

                except Exception as e:
                    total_err += 1
                    if total_err <= 5:
                        print(f"  ERRO {fname}: {e}")
            else:
                total_ok += 1

    conn.commit()
    conn.close()
    print(f"\nFinalizado: {total_ok} importados/atualizados, {total_skip} já existiam, "
          f"{total_nao_s5001} outros eventos ignorados, {total_err} erros reais")
    return total_ok, total_skip, total_err


if __name__ == '__main__':
    CONN_STR = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.110.194.113;DATABASE=folha_agronil;"
        "UID=sa;PWD=mult;TrustServerCertificate=yes"
    )
    importar(CONN_STR)
