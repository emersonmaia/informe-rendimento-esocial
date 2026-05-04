

# ==============================
# arquivo: parser_s5001.py
# ==============================

def parse_s5001(root, arquivo, empresa):
    dados = []
    ns = {'ns': root.tag.split('}')[0].strip('{')}

    try:
        cpf = root.find('.//ns:cpfTrab', ns).text
        comp = root.find('.//ns:perApur', ns).text

        for info in root.findall('.//ns:infoCpCalc', ns):
            inss = info.find('ns:vrCpSeg', ns)
            desc = info.find('ns:vrDescSeg', ns)

            dados.append((
                cpf,
                empresa,
                comp,
                float(inss.text) if inss is not None else 0,
                float(desc.text) if desc is not None else 0,
                arquivo
            ))

    except:
        pass

    return dados
