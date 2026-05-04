import os
import xml.etree.ElementTree as ET
import pyodbc

PASTA = r"D:\agronil_informe_rendimento_com_esocial\xml_consulta_site"

def get_conn():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.110.194.113;"
        "DATABASE=folha_agronil;"
        "UID=sa;"
        "PWD=mult"
    )

# 🔥 DETECTOR UNIVERSAL (FUNCIONA COM XML DE DOWNLOAD)
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


# ================= PARSERS =================

def _f(el): return float(el.text) if el is not None and el.text else 0.0
def _t(el): return el.text.strip() if el is not None and el.text else ''

def parse_s1210(node, empresa, arq):
    """
    Usa consolidApurMen (totais consolidados do XML) para capturar
    corretamente múltiplos dmDev e separar 13º salário do rendimento normal.
    Funciona tanto para sem-vínculo (autônomo) quanto com-vínculo (CLT).
    """
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    try:
        cpf     = node.find('.//ns:cpfBenef', ns).text.strip()
        per     = node.find('.//ns:perApur',   ns).text.strip()
        dtpgto  = _t(node.find('.//ns:dtPgto', ns))
        cr      = _t(node.find('.//ns:CRMen',  ns))

        consol = node.find('.//ns:consolidApurMen', ns)
        if consol is not None:
            rend    = _f(consol.find('ns:vlrRendTrib',      ns))
            inss    = _f(consol.find('ns:vlrPrevOficial',   ns))
            irrf    = _f(consol.find('ns:vlrCRMen',         ns))
            rend13  = _f(consol.find('ns:vlrRendTrib13',    ns))
            inss13  = _f(consol.find('ns:vlrPrevOficial13', ns))
            irrf13  = _f(consol.find('ns:vlrCR13Men',       ns))
        else:
            # fallback: soma todos os totApurMen
            rend = inss = irrf = rend13 = inss13 = irrf13 = 0.0
            for tot in node.findall('.//ns:totApurMen', ns):
                rend   += _f(tot.find('ns:vlrRendTrib',      ns))
                inss   += _f(tot.find('ns:vlrPrevOficial',   ns))
                irrf   += _f(tot.find('ns:vlrCRMen',         ns))
                rend13 += _f(tot.find('ns:vlrRendTrib13',    ns))
                inss13 += _f(tot.find('ns:vlrPrevOficial13', ns))
                irrf13 += _f(tot.find('ns:vlrCR13Men',       ns))

        return (cpf, empresa, per, dtpgto, rend, inss, irrf, cr, rend13, inss13, irrf13, arq)
    except:
        return None


def parse_s5001(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    dados = []

    cpf = node.find('.//ns:cpfTrab', ns)
    comp = node.find('.//ns:perApur', ns)

    if cpf is None:
        return []

    for info in node.findall('.//ns:infoCpCalc', ns):
        inss = info.find('ns:vrCpSeg', ns)
        desc = info.find('ns:vrDescSeg', ns)

        dados.append((
            cpf.text,
            empresa,
            comp.text,
            float(inss.text) if inss is not None else 0,
            float(desc.text) if desc is not None else 0,
            arq
        ))

    return dados


def parse_s5002(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    dados = []

    for ide in node.findall('.//ns:ideTrab', ns):
        cpf = ide.find('ns:cpfTrab', ns)
        comp = node.find('.//ns:perApur', ns)

        for ir in ide.findall('.//ns:infoIRRF', ns):
            base = ir.find('ns:vlrBaseIRRF', ns)
            irrf = ir.find('ns:vlrIRRF', ns)

            dados.append((
                cpf.text,
                empresa,
                comp.text,
                float(base.text) if base is not None else 0,
                float(irrf.text) if irrf is not None else 0,
                arq
            ))

    return dados


def parse_s5003(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}
    dados = []

    for ide in node.findall('.//ns:ideTrab', ns):
        cpf = ide.find('ns:cpfTrab', ns)
        comp = node.find('.//ns:perApur', ns)

        fgts = ide.find('.//ns:vrFgts', ns)

        dados.append((
            cpf.text,
            empresa,
            comp.text,
            float(fgts.text) if fgts is not None else 0,
            arq
        ))

    return dados


def parse_s5011(node, empresa, arq):
    ns = {'ns': node.tag.split('}')[0].strip('{')}

    try:
        comp = node.find('.//ns:perApur', ns).text
        inss = node.find('.//ns:vrCpApur', ns)
        irrf = node.find('.//ns:vrIrrf', ns)

        return [(
            empresa,
            comp,
            float(inss.text) if inss is not None else 0,
            float(irrf.text) if irrf is not None else 0,
            arq
        )]
    except:
        return []


# ================= PROCESSADOR =================

def processar():
    conn = get_conn()
    cursor = conn.cursor()

    s1210 = s5001 = s5002 = s5003 = s5011 = 0

    # Arquivos já importados por tabela (evita duplicatas ao rodar novamente)
    cursor.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210")
    ja_s1210 = {r[0] for r in cursor.fetchall()}

    print("Importando...\n")

    for raiz, _, arquivos in os.walk(PASTA):
        empresa = os.path.basename(raiz)

        for arq in arquivos:
            if not arq.endswith(".xml"):
                continue

            caminho = os.path.join(raiz, arq)

            try:
                root = ET.parse(caminho).getroot()
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
                        cursor.execute("INSERT INTO ESOCIAL_S5001 VALUES (?,?,?,?,?,?)", d)
                        s5001 += 1

                elif evento == 'S5002':
                    for d in parse_s5002(node, empresa, arq):
                        cursor.execute("INSERT INTO ESOCIAL_S5002 VALUES (?,?,?,?,?,?)", d)
                        s5002 += 1

                elif evento == 'S5003':
                    for d in parse_s5003(node, empresa, arq):
                        cursor.execute("INSERT INTO ESOCIAL_S5003 VALUES (?,?,?,?,?)", d)
                        s5003 += 1

                elif evento == 'S5011':
                    for d in parse_s5011(node, empresa, arq):
                        cursor.execute("INSERT INTO ESOCIAL_S5011 VALUES (?,?,?,?,?)", d)
                        s5011 += 1

            except Exception as e:
                print("Erro:", arq, e)

    conn.commit()
    conn.close()

    print("\n===== RESUMO =====")
    print("S1210:", s1210)
    print("S5001:", s5001)
    print("S5002:", s5002)
    print("S5003:", s5003)
    print("S5011:", s5011)


if __name__ == "__main__":
    processar()