"""
Busca S-5002 anuais (indApuracao=2) na pasta 30300398 e inspeciona o do Luis Fernando.
"""
import os, glob

PASTA = r'C:\brven\KIKO\30300398'
CPF_LUIS = "30270255893"

anuais = []
mensais = []

for f in glob.glob(os.path.join(PASTA, '*.xml')):
    if 'S-5002' not in f:
        continue
    try:
        with open(f, encoding='utf-8', errors='ignore') as fh:
            txt = fh.read()
        if '<indApuracao>2</indApuracao>' in txt:
            anuais.append(f)
        else:
            mensais.append(f)
    except:
        pass

print(f"S-5002 mensais (indApuracao=1 ou sem): {len(mensais)}")
print(f"S-5002 anuais (indApuracao=2): {len(anuais)}")

print("\nAnuais encontrados:")
for f in anuais[:5]:
    print(f"  {os.path.basename(f)}")
    with open(f, encoding='utf-8', errors='ignore') as fh:
        txt = fh.read()
    if CPF_LUIS in txt:
        print("  *** CONTÉM CPF DO LUIS FERNANDO ***")
        # Mostrar valores chave
        import xml.etree.ElementTree as ET
        tree = ET.parse(f)
        root = tree.getroot()
        def _f(tag):
            total = sum(float(e.text) for e in root.iter()
                        if e.tag.split('}')[-1] == tag and e.text)
            return total
        print(f"    vlrRendTrib:    {_f('vlrRendTrib'):,.2f}")
        print(f"    vlrRendTrib13:  {_f('vlrRendTrib13'):,.2f}")
        print(f"    vlrPrevOficial: {_f('vlrPrevOficial'):,.2f}")
        print(f"    vlrPrevOfic13:  {_f('vlrPrevOficial13'):,.2f}")
        print(f"    vlrCRMen:       {_f('vlrCRMen'):,.2f}")
        print(f"    vlrCR13Men:     {_f('vlrCR13Men'):,.2f}")
        # Mostrar infoIR se existir
        for el in root.iter():
            if el.tag.split('}')[-1] == 'infoIR':
                tp = next((c.text for c in el if c.tag.split('}')[-1] == 'tpInfoIR'), '?')
                vl = next((c.text for c in el if c.tag.split('}')[-1] == 'valor'), '?')
                print(f"    infoIR tpInfoIR={tp}: {vl}")

# Verificar se o S-5001 anual tem perApur apontando para 2025
print("\nResumo S-5001 anuais de Luis Fernando:")
for f in glob.glob(os.path.join(PASTA, '*.xml')):
    if 'S-5001' not in f:
        continue
    with open(f, encoding='utf-8', errors='ignore') as fh:
        txt = fh.read()
    if CPF_LUIS in txt and 'indApuracao>2' in txt:
        print(f"  {os.path.basename(f)} - ANUAL 13")
    elif CPF_LUIS in txt:
        print(f"  {os.path.basename(f)} - MENSAL")
