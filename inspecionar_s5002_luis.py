"""
Inspeciona TODOS os S-5002 de Luis Fernando em 30300398 e XML_PORTAL.
Procura o evento anual do 13 salario (indApuracao=2).
"""
import os, glob, xml.etree.ElementTree as ET

CPF_LUIS = "30270255893"

def inspecionar_s5002(caminho):
    try:
        tree = ET.parse(caminho)
        root = tree.getroot()
        ns = {}
        for elem in root.iter():
            if '}' in elem.tag:
                ns['ns'] = elem.tag.split('}')[0].strip('{')
                break

        # Verificar se tem o CPF do Luis
        conteudo_cpf = False
        for elem in root.iter():
            if elem.tag.split('}')[-1] == 'cpfBenef' and elem.text and CPF_LUIS in elem.text:
                conteudo_cpf = True
                break
        if not conteudo_cpf:
            return

        def _t(el): return el.text.strip() if el is not None and el.text else ''

        ind = _t(root.find('.//ns:indApuracao', ns))
        per = _t(root.find('.//ns:perApur', ns))

        # Pegar valores chave
        vals = {}
        for tag in ['vlrRendTrib', 'vlrRendTrib13', 'vlrPrevOficial', 'vlrPrevOficial13',
                    'vlrCRMen', 'vlrCR13Men']:
            total = sum(float(e.text) for e in root.iter()
                        if e.tag.split('}')[-1] == tag and e.text)
            vals[tag] = total

        print(f"\nArquivo: {os.path.basename(caminho)}")
        print(f"  indApuracao={ind} ({'ANUAL/13' if ind=='2' else 'MENSAL' if ind=='1' else '?'})  perApur={per}")
        print(f"  rend={vals['vlrRendTrib']:,.2f}  rend13={vals['vlrRendTrib13']:,.2f}")
        print(f"  inss={vals['vlrPrevOficial']:,.2f}  inss13={vals['vlrPrevOficial13']:,.2f}")
        print(f"  irrf={vals['vlrCRMen']:,.2f}  irrf13={vals['vlrCR13Men']:,.2f}")

    except Exception as e:
        print(f"  Erro em {os.path.basename(caminho)}: {e}")

print("=== S-5002 do Luis Fernando em 30300398 ===")
for f in glob.glob(r'C:\brven\KIKO\30300398\*.xml'):
    if 'S-5002' in f:
        inspecionar_s5002(f)

print("\n=== S-5002 do Luis Fernando em XML_PORTAL (amostra com r13>0) ===")
for f in glob.glob(r'C:\brven\KIKO\ESOCIAL\XML_PORTAL\*.xml'):
    if 'S-5002' not in f:
        continue
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
            txt = fh.read(5000)
        if CPF_LUIS not in txt:
            continue
        # verificar se tem r13
        tree = ET.parse(f)
        root = tree.getroot()
        for elem in root.iter():
            if elem.tag.split('}')[-1] == 'vlrRendTrib13' and elem.text and float(elem.text) > 0:
                inspecionar_s5002(f)
                break
    except:
        pass

print("\n=== S-5001 anual (13) do Luis Fernando em 30300398 ===")
for f in glob.glob(r'C:\brven\KIKO\30300398\*.xml'):
    if 'S-5001' not in f:
        continue
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
            txt = fh.read(5000)
        if CPF_LUIS not in txt:
            continue
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {}
        for elem in root.iter():
            if '}' in elem.tag:
                ns['ns'] = elem.tag.split('}')[0].strip('{')
                break
        def _t(el): return el.text.strip() if el is not None and el.text else ''
        ind = _t(root.find('.//ns:indApuracao', ns))
        per = _t(root.find('.//ns:perApur', ns))
        # soma bases com ind13
        base13 = inss13 = 0.0
        for el in root.iter():
            tag = el.tag.split('}')[-1]
            parent_ind13 = False
            # pegar infoBaseCS com ind13=1
            if tag == 'infoBaseCS':
                children = {c.tag.split('}')[-1]: c.text for c in el}
                if children.get('ind13') == '1':
                    tp = children.get('tpValor','')
                    val = float(children.get('valor', 0))
                    if tp == '11': base13 += val
                    if tp == '21': inss13 += val
        print(f"\n  {os.path.basename(f)}")
        print(f"  indApuracao={ind}  perApur={per}")
        print(f"  Base INSS 13: {base13:,.2f}  INSS 13: {inss13:,.2f}")
    except Exception as e:
        print(f"  Erro: {e}")
