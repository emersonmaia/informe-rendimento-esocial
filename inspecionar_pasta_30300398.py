"""
Analisa a pasta C:\brven\KIKO\30300398 para entender o que tem la.
"""
import os, glob, xml.etree.ElementTree as ET
from collections import Counter

PASTA = r'C:\brven\KIKO\30300398'
CPF_LUIS = "30270255893"

xmls = glob.glob(os.path.join(PASTA, '**', '*.xml'), recursive=True)
print(f"Total XMLs em 30300398: {len(xmls)}")

tipos = Counter()
s5002_luis = []

for caminho in xmls:
    arq = os.path.basename(caminho)
    # Detecta tipo pelo nome
    for tipo in ['S-5002', 'S-5001', 'S-5003', 'S-1210', 'S-1200']:
        if tipo in arq:
            tipos[tipo] += 1
            break

    # Verifica se tem S-5002 com CPF do Luis Fernando
    if 'S-5002' in arq:
        try:
            with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
                conteudo = f.read(3000)
            if CPF_LUIS in conteudo:
                s5002_luis.append(caminho)
        except:
            pass

print("\nTipos de arquivo:")
for t, n in tipos.most_common():
    print(f"  {t}: {n}")

print(f"\nS-5002 com CPF do Luis Fernando ({CPF_LUIS}): {len(s5002_luis)}")
for f in s5002_luis[:5]:
    print(f"  {os.path.basename(f)}")

# Inspecionar um S-5002 do Luis Fernando se existir
if s5002_luis:
    print("\n=== Conteudo do S-5002 (Luis Fernando - 13) ===")
    tree = ET.parse(s5002_luis[0])
    root = tree.getroot()
    ns = {}
    for elem in root.iter():
        if '}' in elem.tag:
            ns['ns'] = elem.tag.split('}')[0].strip('{')
            break

    def _t(el): return el.text.strip() if el is not None and el.text else ''
    def _f(el): return float(el.text) if el is not None and el.text else 0.0

    emp = root.find('.//ns:ideEmpregador', ns)
    if emp:
        print(f"Empregador: tpInsc={_t(emp.find('ns:tpInsc',ns))} nrInsc={_t(emp.find('ns:nrInsc',ns))}")
    per = root.find('.//ns:perApur', ns)
    print(f"perApur: {_t(per)}")
    ind = root.find('.//ns:indApuracao', ns)
    print(f"indApuracao: {_t(ind)} (1=mensal, 2=13o)")
    cpf = root.find('.//ns:cpfBenef', ns)
    print(f"cpfBenef: {_t(cpf)}")

    # Valores consolidados
    for tag in ['vlrRendTrib13', 'vlrPrevOficial13', 'vlrCR13Men',
                'vlrRendTrib', 'vlrPrevOficial', 'vlrCRMen']:
        for el in root.iter():
            if el.tag.split('}')[-1] == tag and el.text:
                print(f"  {tag}: {el.text}")

# Verificar CAEPF da pasta 30300318 tambem
print("\n=== Pasta 30300318 ===")
xmls2 = glob.glob(r'C:\brven\KIKO\30300318\*.xml')
print(f"Total: {len(xmls2)}")
for caminho in xmls2[:2]:
    try:
        tree = ET.parse(caminho)
        root = tree.getroot()
        for elem in root.iter():
            if elem.tag.split('}')[-1] == 'ideEmpregador':
                for child in elem:
                    t = child.tag.split('}')[-1]
                    print(f"  {t}: {child.text}")
                break
    except:
        pass
    break
