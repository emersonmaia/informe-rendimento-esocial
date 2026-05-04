# ==============================
# arquivo: parser_s5002.py
# ==============================

def parse_s5002(root, arquivo, empresa):
    dados = []
    ns = {'ns': root.tag.split('}')[0].strip('{')}

    try:
        for ideTrab in root.findall('.//ns:ideTrab', ns):
            cpf = ideTrab.find('ns:cpfTrab', ns).text
            comp = root.find('.//ns:perApur', ns).text

            for ir in ideTrab.findall('.//ns:infoIRRF', ns):
                base = ir.find('ns:vlrBaseIRRF', ns)
                irrf = ir.find('ns:vlrIRRF', ns)

                dados.append((
                    cpf,
                    empresa,
                    comp,
                    float(base.text) if base is not None else 0,
                    float(irrf.text) if irrf is not None else 0,
                    arquivo
                ))

    except:
        pass

    return dados


