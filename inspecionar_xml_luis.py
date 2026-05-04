"""
Inspeciona o S-5001 encontrado pelo usuario para Luis Fernando Savioli.
"""
import xml.etree.ElementTree as ET

ARQUIVO = r'C:\brven\KIKO\30300398\ID0010000000000000000000036695106011.S-5001.xml'

tree = ET.parse(ARQUIVO)
root = tree.getroot()

def _t(el): return el.text.strip() if el is not None and el.text else ''
def _f(el): return float(el.text) if el is not None and el.text else 0.0

# Exibe tudo estruturado
def dump(elem, indent=0):
    tag = elem.tag.split('}')[-1]
    text = elem.text.strip() if elem.text and elem.text.strip() else ''
    children = list(elem)
    if not children and text:
        print('  ' * indent + f'<{tag}> {text}')
    elif not children:
        pass
    else:
        print('  ' * indent + f'<{tag}>')
        for c in children:
            dump(c, indent + 1)

print("=== ESTRUTURA COMPLETA ===")
dump(root)

print()
print("=== DADOS CHAVE ===")
ns_map = {}
for elem in root.iter():
    tag = elem.tag
    if '}' in tag:
        ns = tag.split('}')[0].strip('{')
        ns_map['ns'] = ns
        break

ns = {'ns': ns_map.get('ns', '')}

# Empregador
emp = root.find('.//ns:ideEmpregador', ns)
if emp is not None:
    print(f"Empregador: tpInsc={_t(emp.find('ns:tpInsc',ns))}  nrInsc={_t(emp.find('ns:nrInsc',ns))}")

# Periodo
per = root.find('.//ns:perApur', ns)
print(f"Periodo: {_t(per)}")

# Trabalhador
cpf = root.find('.//ns:cpfTrab', ns)
print(f"CPF trabalhador: {_t(cpf)}")

# Todos os valores monetarios relevantes
print("\nValores encontrados:")
tags_interesse = ['vlrRendTrib', 'vlrRendTrib13', 'vlrPrevOficial', 'vlrPrevOficial13',
                  'vlrCRMen', 'vlrCR13Men', 'vlrBcCpSeg', 'vlrBcCpSeg13',
                  'vlrDescSeg', 'vlrDescSeg13', 'vlrBaseIRRF', 'vlrIRRF',
                  'vrCpSeg', 'vrDescSeg', 'vrCpSeg13', 'vrDescSeg13']
for tag in tags_interesse:
    for el in root.iter():
        if el.tag.split('}')[-1] == tag and el.text:
            print(f"  {tag}: {el.text}")
