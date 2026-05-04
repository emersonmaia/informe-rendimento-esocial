"""
Acha os XMLs dos 2 CPFs e exibe os dados do empregador (nrInsc, tpInsc, CAEPF).
"""
import os, glob, xml.etree.ElementTree as ET

PASTA = r'C:\brven\KIKO\ESOCIAL\XML_PORTAL'
CPF_ALVO = {"45022743809", "32577226802"}

xmls = glob.glob(os.path.join(PASTA, '**', '*.xml'), recursive=True)
encontrados = {}

for caminho in xmls:
    if len(encontrados) >= len(CPF_ALVO) * 3:  # pega ate 3 exemplos de cada
        break
    try:
        tree = ET.parse(caminho)
        root = tree.getroot()
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == 'cpfBenef':
                cpf = (elem.text or '').strip().replace('.','').replace('-','').zfill(11)
                if cpf in CPF_ALVO:
                    arq = os.path.basename(caminho)
                    if cpf not in encontrados:
                        encontrados[cpf] = []
                    if len(encontrados[cpf]) < 2:
                        encontrados[cpf].append(caminho)
    except:
        pass

print(f"CPFs procurados: {CPF_ALVO}")
print()

for cpf, arquivos in encontrados.items():
    print(f"CPF {cpf}:")
    for caminho in arquivos:
        print(f"  Arquivo: {os.path.basename(caminho)}")
        try:
            tree = ET.parse(caminho)
            root = tree.getroot()
            # Dados do empregador
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]
                if tag == 'ideEmpregador':
                    print(f"  Empregador:")
                    for child in elem:
                        t = child.tag.split('}')[-1]
                        print(f"    {t}: {child.text}")
                    break
            # Periodo de apuracao
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]
                if tag == 'perApur':
                    print(f"  perApur: {elem.text}")
                    break
        except Exception as e:
            print(f"  Erro: {e}")
        print()

if not encontrados:
    print("Nenhum arquivo encontrado com esses CPFs.")
