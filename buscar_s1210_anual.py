"""
Busca S-1210 na pasta 30300398 que contenham o 13 do Luis Fernando.
"""
import os, glob, xml.etree.ElementTree as ET

PASTA = r'C:\brven\KIKO\30300398'
CPF_LUIS = "30270255893"

print("S-1210 com CPF de Luis Fernando em 30300398:")
for f in glob.glob(os.path.join(PASTA, '*.xml')):
    if 'S-1210' not in f:
        continue
    try:
        with open(f, encoding='utf-8', errors='ignore') as fh:
            txt = fh.read()
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
        def _f(tag):
            return sum(float(e.text) for e in root.iter()
                       if e.tag.split('}')[-1] == tag and e.text)

        per = _t(root.find('.//ns:perApur', ns))
        ind = _t(root.find('.//ns:indApuracao', ns))
        dtpgto = _t(root.find('.//ns:dtPgto', ns))
        cpf = _t(root.find('.//ns:cpfBenef', ns))

        print(f"\n  {os.path.basename(f)}")
        print(f"  cpfBenef={cpf}  perApur={per}  indApuracao={ind}  dtPgto={dtpgto}")
        print(f"  vlrRendTrib={_f('vlrRendTrib'):,.2f}  vlrRendTrib13={_f('vlrRendTrib13'):,.2f}")
        print(f"  vlrPrevOficial={_f('vlrPrevOficial'):,.2f}  vlrPrevOficial13={_f('vlrPrevOficial13'):,.2f}")
        print(f"  vlrCRMen={_f('vlrCRMen'):,.2f}  vlrCR13Men={_f('vlrCR13Men'):,.2f}")

        # Verificar infoPerRef com ind13=1 (13 salario)
        for el in root.iter():
            if el.tag.split('}')[-1] == 'detPgtoFl':
                per_ref = _t(el.find('ns:perRef', ns))
                vr_liq = _t(el.find('ns:vrLiq', ns))
                dm = _t(el.find('ns:ideDmDev', ns))
                print(f"  detPgtoFl: perRef={per_ref}  ideDmDev={dm}  vrLiq={vr_liq}")

    except Exception as e:
        print(f"  Erro: {e}")

# Verificar quantos S-1210 existem na pasta
total = len([f for f in glob.glob(os.path.join(PASTA, '*.xml')) if 'S-1210' in f])
print(f"\nTotal S-1210 em 30300398: {total}")
