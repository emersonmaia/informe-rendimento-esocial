"""
Importa os XMLs novos do banco kiko (pasta XML_PORTAL).
Processa todos os subdiretórios, ignorando arquivos já importados.
"""
import os
import glob
import xml.etree.ElementTree as ET
import pyodbc

PASTA = r'C:\brven\KIKO\ESOCIAL\XML_PORTAL'

def get_conn():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult'
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
    except:
        return None


def processar():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210")
    ja_s1210 = {r[0] for r in cursor.fetchall()}

    s1210 = erros = ignorados = 0
    print(f"Processando: {PASTA}\n")

    for raiz, _, arquivos in os.walk(PASTA):
        empresa = os.path.basename(raiz)
        novos_empresa = 0

        for arq in sorted(arquivos):
            if not arq.endswith('.xml'):
                continue
            if arq in ja_s1210:
                ignorados += 1
                continue

            caminho = os.path.join(raiz, arq)
            try:
                root = ET.parse(caminho).getroot()
                evento, node = extrair_evento(root)

                if evento == 'S1210':
                    d = parse_s1210(node, empresa, arq)
                    if d:
                        cursor.execute(
                            "INSERT INTO ESOCIAL_S1210 "
                            "(CPF,EMPRESA,COMPETENCIA,DT_PAGTO,REND_TRIB,INSS,IRRF,COD_RECEITA,"
                            "REND_TRIB_13,INSS_13,IRRF_13,ARQUIVO) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", d)
                        ja_s1210.add(arq)
                        s1210 += 1
                        novos_empresa += 1
                        if d[8] > 0:  # rend13
                            print(f"  13o: CPF={d[0]} emp={empresa} per={d[2]} rend13={d[8]:.2f} inss13={d[9]:.2f} irrf13={d[10]:.2f}")

            except Exception as e:
                erros += 1
                print(f"  Erro: {arq}: {e}")

        if novos_empresa > 0:
            print(f"  {empresa}: {novos_empresa} novos S-1210 importados")

    conn.commit()
    conn.close()

    print(f"\n===== RESUMO =====")
    print(f"S-1210 importados: {s1210}")
    print(f"Já existiam:       {ignorados}")
    print(f"Erros:             {erros}")


if __name__ == '__main__':
    processar()
