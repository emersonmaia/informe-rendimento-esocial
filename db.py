# ==============================
# IMPORTADOR ESOCIAL - VERSAO AJUSTADA
# ==============================
import os
import xml.etree.ElementTree as ET
import pyodbc

PASTA = r"D:\agronil_informe_rendimento_com_esocial\xml_consulta_site"

# ================= CONEXAO =================
def get_conn():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.110.194.113;"
        "DATABASE=folha_agronil;"
        "UID=sa;"
        "PWD=mult"
    )

# ================= DETECTOR UNIVERSAL =================
def get_evento(root):
    for el in root.iter():
        tag = el.tag.lower()
        if 'evtirrfbenef' in tag:
            return 'S1210', el
        if 'evtbasestrab' in tag:
            return 'S5001', el
        if 'evtirrf' in tag and 'benef' not in tag:
            return 'S5002', el
    return None, None

# ================= PARSER S1210 =================
def parse_s1210(root, empresa, arquivo):
    ns = {'ns': root.tag.split('}')[0].strip('{')}
    try:
        cpf = root.find('.//ns:cpfBenef', ns).text
        comp = root.find('.//ns:perApur', ns).text
        dt = root.find('.//ns:dtPgto', ns).text
        rend = float(root.find('.//ns:vlrRendTrib', ns).text)
        inss = float(root.find('.//ns:vlrPrevOficial', ns).text)
        irrf = float(root.find('.//ns:vlrCRMen', ns).text)
        cod = root.find('.//ns:CRMen', ns).text

        return (cpf, empresa, comp, dt, rend, inss, irrf, cod, arquivo)
    except:
        return None

# ================= PARSER S5001 =================
def parse_s5001(root, empresa, arquivo):
    dados = []
    ns = {'ns': root.tag.split('}')[0].strip('{')}

    try:
        cpf = root.find('.//ns:cpfTrab', ns)
        comp = root.find('.//ns:perApur', ns)

        if cpf is None or comp is None:
            return []

        for info in root.findall('.//ns:infoCpCalc', ns):
            inss = info.find('ns:vrCpSeg', ns)
            desc = info.find('ns:vrDescSeg', ns)

            dados.append((
                cpf.text,
                empresa,
                comp.text,
                float(inss.text) if inss is not None else 0,
                float(desc.text) if desc is not None else 0,
                arquivo
            ))
    except Exception as e:
        print("Erro S5001:", e)

    return dados

# ================= PARSER S5002 =================
def parse_s5002(root, empresa, arquivo):
    dados = []
    ns = {'ns': root.tag.split('}')[0].strip('{')}

    try:
        for ideTrab in root.findall('.//ns:ideTrab', ns):
            cpf = ideTrab.find('ns:cpfTrab', ns)
            comp = root.find('.//ns:perApur', ns)

            if cpf is None or comp is None:
                continue

            for ir in ideTrab.findall('.//ns:infoIRRF', ns):
                base = ir.find('ns:vlrBaseIRRF', ns)
                irrf = ir.find('ns:vlrIRRF', ns)

                dados.append((
                    cpf.text,
                    empresa,
                    comp.text,
                    float(base.text) if base is not None else 0,
                    float(irrf.text) if irrf is not None else 0,
                    arquivo
                ))

    except Exception as e:
        print("Erro S5002:", e)

    return dados

# ================= PROCESSADOR =================
def processar():
    conn = get_conn()
    cursor = conn.cursor()

    total = s1210 = s5001 = s5002 = 0

    print("🚀 Iniciando importação...\n")

    for raiz, _, arquivos in os.walk(PASTA):
        empresa = os.path.basename(raiz)

        for arq in arquivos:
            if not arq.lower().endswith('.xml'):
                continue

            total += 1
            caminho = os.path.join(raiz, arq)

            try:
                tree = ET.parse(caminho)
                root = tree.getroot()

                evento, node = get_evento(root)

                if evento == 'S1210':
                    dados = parse_s1210(root, empresa, arq)
                    if dados:
                        cursor.execute("""
                        INSERT INTO ESOCIAL_S1210
                        (CPF, EMPRESA, COMPETENCIA, DT_PAGTO, REND_TRIB, INSS, IRRF, COD_RECEITA, ARQUIVO)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, dados)
                        s1210 += 1

                elif evento == 'S5001':
                    lista = parse_s5001(node, empresa, arq)
                    for d in lista:
                        cursor.execute("""
                        INSERT INTO ESOCIAL_S5001
                        (CPF, EMPRESA, COMPETENCIA, VL_INSS, VL_DESCONTO, ARQUIVO)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, d)
                        s5001 += 1

                elif evento == 'S5002':
                    lista = parse_s5002(node, empresa, arq)
                    for d in lista:
                        cursor.execute("""
                        INSERT INTO ESOCIAL_S5002
                        (CPF, EMPRESA, COMPETENCIA, VL_BASE_IRRF, VL_IRRF, ARQUIVO)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, d)
                        s5002 += 1

            except Exception as e:
                print("❌ Erro:", caminho, e)

    conn.commit()
    conn.close()

    print("\n===== RESUMO =====")
    print(f"Total arquivos: {total}")
    print(f"S-1210: {s1210}")
    print(f"S-5001: {s5001}")
    print(f"S-5002: {s5002}")


if __name__ == "__main__":
    processar()