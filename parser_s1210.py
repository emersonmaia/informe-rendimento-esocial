
# ==============================
# arquivo: parser_s1210.py
# ==============================
import xml.etree.ElementTree as ET


def parse_s1210(root, arquivo, empresa):
    ns = {'ns': root.tag.split('}')[0].strip('{')}

    try:
        cpf = root.find('.//ns:cpfBenef', ns).text
        comp = root.find('.//ns:perApur', ns).text
        dt_pgto = root.find('.//ns:dtPgto', ns).text

        rend = float(root.find('.//ns:vlrRendTrib', ns).text)
        inss = float(root.find('.//ns:vlrPrevOficial', ns).text)
        irrf = float(root.find('.//ns:vlrCRMen', ns).text)
        cod = root.find('.//ns:CRMen', ns).text

        return (cpf, empresa, comp, dt_pgto, rend, inss, irrf, cod, arquivo)
    except:
        return None
