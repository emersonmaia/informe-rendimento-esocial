import os
import glob
import xml.etree.ElementTree as ET
import pyodbc

PASTA = r"D:\agronil_informe_rendimento_com_esocial\ESOCIAL\retornos\59069674000195"

# Mapeamento perApur → (COMPETENCIA, DT_PAGTO)
PERIODOS = {
    '2025-05': ('2025-06', '2025-06-06'),   # maio pago em junho
    '2025-11': ('2025-12', '2025-12-05'),   # novembro pago em dezembro
    '2025':    ('2025-12', '2025-12-20'),   # 13º pago em dezembro
}

# Rubricas de rendimento por codCateg
REND_RUBRS = {
    '722': 'BR00168',   # pró-labore
    '101': 'BR00001',   # salário CLT
}


def get_conn():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.110.194.113;"
        "DATABASE=folha_agronil;"
        "UID=sa;"
        "PWD=mult"
    )


def _f(val):
    try:
        return float(val) if val else 0.0
    except Exception:
        return 0.0


def parse_s1200(caminho):
    """
    Retorna dict com os campos extraídos do XML S-1200, ou None se não aplicável.
    Apenas perApur nos PERIODOS alvo, apenas arquivos ID*.xml.
    """
    try:
        root = ET.parse(caminho).getroot()
    except Exception as e:
        print(f"Erro parse XML {os.path.basename(caminho)}: {e}")
        return None

    def _t(tag):
        el = root.find(f'.//{{{tag}}}') if '{' in tag else None
        # usa wildcard namespace
        for el in root.iter():
            if el.tag.split('}')[-1] == tag:
                return el.text.strip() if el.text else ''
        return ''

    def _find(tag):
        for el in root.iter():
            if el.tag.split('}')[-1] == tag:
                return el
        return None

    per = _t('perApur')
    if per not in PERIODOS:
        return None

    cpf_el = _find('cpfTrab')
    if cpf_el is None:
        return None
    cpf = cpf_el.text.strip() if cpf_el.text else ''

    retif_el = _find('indRetif')
    retif = int(retif_el.text.strip()) if retif_el is not None and retif_el.text else 1

    cat_el = _find('codCateg')
    cat = cat_el.text.strip() if cat_el is not None and cat_el.text else ''

    # Coleta todas as rubricas
    rubrs = {}
    for item in root.iter():
        if item.tag.split('}')[-1] == 'itensRemun':
            cod = None
            vr = None
            for child in item:
                ctag = child.tag.split('}')[-1]
                if ctag == 'codRubr':
                    cod = child.text.strip() if child.text else ''
                elif ctag == 'vrRubr':
                    vr = _f(child.text)
            if cod:
                rubrs[cod] = rubrs.get(cod, 0.0) + vr

    comp, dtpgto = PERIODOS[per]

    if per == '2025':
        # 13º salário: apenas rubricas de 13º
        rend13 = rubrs.get('BR00035', 0.0)
        inss13 = rubrs.get('BR00914', 0.0)
        irrf13 = rubrs.get('BR00915', 0.0)
        if rend13 == 0 and inss13 == 0 and irrf13 == 0:
            return None
        return {
            'cpf': cpf, 'per': per, 'retif': retif, 'cat': cat,
            'comp': comp, 'dtpgto': dtpgto,
            'rend': 0.0, 'inss': 0.0, 'irrf': 0.0,
            'rend13': rend13, 'inss13': inss13, 'irrf13': irrf13,
        }
    else:
        # Salário mensal
        rend_rubr = REND_RUBRS.get(cat)
        if rend_rubr is None:
            # categoria não mapeada, ignora
            return None
        rend = rubrs.get(rend_rubr, 0.0)
        inss = rubrs.get('BR00002', 0.0)
        irrf = rubrs.get('BR00003', 0.0)
        if rend == 0 and inss == 0 and irrf == 0:
            return None
        return {
            'cpf': cpf, 'per': per, 'retif': retif, 'cat': cat,
            'comp': comp, 'dtpgto': dtpgto,
            'rend': rend, 'inss': inss, 'irrf': irrf,
            'rend13': 0.0, 'inss13': 0.0, 'irrf13': 0.0,
        }


def processar():
    # Lê apenas ID*.xml para evitar arquivos ret_ e cópias
    arquivos = sorted(glob.glob(os.path.join(PASTA, 'ID*.xml')))

    # Agrupa por (cpf, per) e mantém apenas o de maior indRetif
    # Em caso de empate, o nome do arquivo (maior = mais recente) prevalece
    melhor = {}  # (cpf, per) -> (retif, nome_arq, dados)

    for f in arquivos:
        dados = parse_s1200(f)
        if dados is None:
            continue
        chave = (dados['cpf'], dados['per'])
        retif = dados['retif']
        nome = os.path.basename(f)
        if chave not in melhor or retif > melhor[chave][0] or (retif == melhor[chave][0] and nome > melhor[chave][1]):
            melhor[chave] = (retif, nome, dados)

    conn = get_conn()
    cursor = conn.cursor()

    # Arquivos já importados
    cursor.execute("SELECT DISTINCT ARQUIVO FROM ESOCIAL_S1210_COMPL WHERE ORIGEM='S1200'")
    ja_importados = {r[0] for r in cursor.fetchall()}

    inseridos = 0
    pulados = 0

    for (cpf, per), (retif, nome, d) in sorted(melhor.items()):
        if nome in ja_importados:
            pulados += 1
            continue

        cursor.execute(
            "INSERT INTO ESOCIAL_S1210_COMPL "
            "(CPF, COMPETENCIA, DT_PAGTO, REND_TRIB, INSS, IRRF, "
            "REND_TRIB_13, INSS_13, IRRF_13, COD_RECEITA, ARQUIVO, ORIGEM) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                cpf, d['comp'], d['dtpgto'],
                d['rend'], d['inss'], d['irrf'],
                d['rend13'], d['inss13'], d['irrf13'],
                None, nome, 'S1200'
            )
        )
        inseridos += 1

    conn.commit()
    conn.close()

    print(f"\nInseridos: {inseridos}")
    print(f"Pulados (já importados): {pulados}")

    # Resumo por período
    print("\nResumo por perApur:")
    for per, grupo in sorted(
        {per: [] for _, per in melhor.keys()}.items()
    ):
        total = sum(1 for (_, p) in melhor if p == per)
        print(f"  {per}: {total} registros")


if __name__ == "__main__":
    processar()
