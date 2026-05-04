"""
Importador de XMLs eSocial para folha_flavio e folha_beatriz.
Pastas:
  C:\brven\FLAVIO\ESOCIAL\XML_PORTAL   -> folha_flavio
  C:\brven\BEATRIZ\ESOCIAL\XML_PORTAL  -> folha_beatriz
"""
import os
import xml.etree.ElementTree as ET
import pyodbc

EMPRESAS = [
    {
        'pasta':  r"C:\brven\FLAVIO\ESOCIAL\XML_PORTAL",
        'banco':  'folha_flavio',
        'label':  'FLAVIO',
    },
    {
        'pasta':  r"C:\brven\BEATRIZ\ESOCIAL\XML_PORTAL",
        'banco':  'folha_beatriz',
        'label':  'BEATRIZ',
    },
]

SERVER = '100.110.194.113'
UID    = 'sa'
PWD    = 'mult'


def get_conn(banco):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={banco};UID={UID};PWD={PWD}"
    )


def extrair_evento(root):
    eventos = root.findall('.//{*}retornoProcessamentoDownload/{*}evento')
    for ev in eventos:
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


def _f(el): return float(el.text) if el is not None and el.text else 0.0
def _t(el): return el.text.strip() if el is not None and el.text else ''


def parse_s1210(node, empresa, arq):
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


def parse_s5001(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    dados = []
    cpf  = node.find('.//ns:cpfTrab', ns)
    comp = node.find('.//ns:perApur',  ns)
    if cpf is None:
        return []
    for info in node.findall('.//ns:infoCpCalc', ns):
        inss = info.find('ns:vrCpSeg',   ns)
        desc = info.find('ns:vrDescSeg', ns)
        dados.append((
            cpf.text, empresa, comp.text,
            float(inss.text) if inss is not None else 0,
            float(desc.text) if desc is not None else 0,
            arq
        ))
    return dados


def parse_s5002(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    dados = []
    for ide in node.findall('.//ns:ideTrab', ns):
        cpf  = ide.find('ns:cpfTrab', ns)
        comp = node.find('.//ns:perApur', ns)
        for ir in ide.findall('.//ns:infoIRRF', ns):
            base = ir.find('ns:vlrBaseIRRF', ns)
            irrf = ir.find('ns:vlrIRRF',     ns)
            dados.append((
                cpf.text, empresa, comp.text,
                float(base.text) if base is not None else 0,
                float(irrf.text) if irrf is not None else 0,
                arq
            ))
    return dados


def parse_s5003(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    dados = []
    for ide in node.findall('.//ns:ideTrab', ns):
        cpf  = ide.find('ns:cpfTrab', ns)
        comp = node.find('.//ns:perApur', ns)
        fgts = ide.find('.//ns:vrFgts',  ns)
        dados.append((
            cpf.text, empresa, comp.text,
            float(fgts.text) if fgts is not None else 0,
            arq
        ))
    return dados


def parse_s5011(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    try:
        comp = node.find('.//ns:perApur',  ns).text
        inss = node.find('.//ns:vrCpApur', ns)
        irrf = node.find('.//ns:vrIrrf',   ns)
        return [(
            empresa, comp,
            float(inss.text) if inss is not None else 0,
            float(irrf.text) if irrf is not None else 0,
            arq
        )]
    except Exception:
        return []


def processar_empresa(cfg):
    pasta = cfg['pasta']
    banco = cfg['banco']
    label = cfg['label']

    print(f"\n{'='*55}")
    print(f"  {label}  ->  {banco}")
    print(f"  pasta: {pasta}")
    print(f"{'='*55}")

    if not os.path.isdir(pasta):
        print(f"  AVISO: pasta não encontrada, pulando.")
        return

    conn   = get_conn(banco)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210")
    ja_s1210 = {r[0] for r in cursor.fetchall()}

    s1210 = s5001 = s5002 = s5003 = s5011 = erros = 0

    for raiz, _, arquivos in os.walk(pasta):
        empresa = os.path.basename(raiz)

        for arq in sorted(arquivos):
            if not arq.endswith('.xml'):
                continue

            caminho = os.path.join(raiz, arq)
            try:
                root   = ET.parse(caminho).getroot()
                evento, node = extrair_evento(root)

                if evento == 'S1210':
                    if arq in ja_s1210:
                        continue
                    d = parse_s1210(node, empresa, arq)
                    if d:
                        cursor.execute(
                            "INSERT INTO ESOCIAL_S1210 "
                            "(CPF,EMPRESA,COMPETENCIA,DT_PAGTO,REND_TRIB,INSS,IRRF,COD_RECEITA,"
                            "REND_TRIB_13,INSS_13,IRRF_13,ARQUIVO) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", d)
                        ja_s1210.add(arq)
                        s1210 += 1

                elif evento == 'S5001':
                    for d in parse_s5001(node, empresa, arq):
                        cursor.execute(
                            "INSERT INTO ESOCIAL_S5001 "
                            "(CPF,EMPRESA,COMPETENCIA,VR_CP_SEG,VR_DESC_SEG,ARQUIVO) "
                            "VALUES (?,?,?,?,?,?)", d)
                        s5001 += 1

                elif evento == 'S5002':
                    for d in parse_s5002(node, empresa, arq):
                        cursor.execute(
                            "INSERT INTO ESOCIAL_S5002 "
                            "(CPF,EMPRESA,COMPETENCIA,VLR_BASE_IRRF,VLR_IRRF,ARQUIVO) "
                            "VALUES (?,?,?,?,?,?)", d)
                        s5002 += 1

                elif evento == 'S5003':
                    for d in parse_s5003(node, empresa, arq):
                        cursor.execute(
                            "INSERT INTO ESOCIAL_S5003 "
                            "(CPF,EMPRESA,COMPETENCIA,VR_FGTS,ARQUIVO) "
                            "VALUES (?,?,?,?,?)", d)
                        s5003 += 1

                elif evento == 'S5011':
                    for d in parse_s5011(node, empresa, arq):
                        cursor.execute(
                            "INSERT INTO ESOCIAL_S5011 "
                            "(EMPRESA,COMPETENCIA,VR_CP_APUR,VR_IRRF,ARQUIVO) "
                            "VALUES (?,?,?,?,?)", d)
                        s5011 += 1

            except Exception as e:
                print(f"  ERRO: {arq} -> {e}")
                erros += 1

    conn.commit()
    conn.close()

    print(f"  S1210 : {s1210}")
    print(f"  S5001 : {s5001}")
    print(f"  S5002 : {s5002}")
    print(f"  S5003 : {s5003}")
    print(f"  S5011 : {s5011}")
    if erros:
        print(f"  ERROS : {erros}")


if __name__ == '__main__':
    for cfg in EMPRESAS:
        processar_empresa(cfg)
    print("\nImportação concluída.")
