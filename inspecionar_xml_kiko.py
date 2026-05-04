import os, glob, xml.etree.ElementTree as ET
from collections import Counter

PASTA = r'C:\brven\KIKO\ESOCIAL\XML_PORTAL'

xmls = glob.glob(os.path.join(PASTA, '**', '*.xml'), recursive=True)
print(f"Total XMLs: {len(xmls)}")

tipos = Counter()
exemplos = {}

for caminho in xmls[:500]:   # analisa os primeiros 500
    arq = os.path.basename(caminho)
    try:
        root = ET.parse(caminho).getroot()
        # Busca o primeiro filho relevante dentro do evento
        for ev in root.iter():
            tag_local = ev.tag.split('}')[-1].lower()
            if tag_local.startswith('evt'):
                tipos[tag_local] += 1
                if tag_local not in exemplos:
                    exemplos[tag_local] = arq
                break
    except:
        pass

print("\nTipos de evento encontrados:")
for t, n in tipos.most_common():
    print(f"  {t:<40}  qtd: {n:>5}  ex: {exemplos[t]}")

print()
# Verificar se algum arquivo tem evtIrrfBenef (S-1210)
print("Procurando evtIrrfBenef (S-1210) em TODOS os XMLs...")
encontrados = []
for caminho in xmls:
    try:
        with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
            conteudo = f.read(2000)  # só o início
        if 'evtIrrfBenef' in conteudo or 'EvtIrrfBenef' in conteudo:
            encontrados.append(os.path.basename(caminho))
    except:
        pass

if encontrados:
    print(f"  ENCONTROU {len(encontrados)} arquivo(s) com S-1210:")
    for e in encontrados[:10]:
        print(f"    {e}")
else:
    print("  NENHUM arquivo S-1210 (evtIrrfBenef) encontrado nesta pasta.")
    print("  Os XMLs desta pasta NAO contêm dados de pagamento/rendimento.")
