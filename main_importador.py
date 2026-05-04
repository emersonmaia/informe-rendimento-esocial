# ==============================
# arquivo: main_importador.py
# ==============================
import os
import xml.etree.ElementTree as ET

from db import get_conn
from parser_s1210 import parse_s1210
from parser_s5001 import parse_s5001
from parser_s5002 import parse_s5002

PASTA = r"D:\agronil_informe_rendimento_com_esocial\xml_consulta_site"


def processar():
    conn = get_conn()
    cursor = conn.cursor()

    for raiz, _, arquivos in os.walk(PASTA):
        empresa = os.path.basename(raiz)

        for arq in arquivos:
            if not arq.lower().endswith('.xml'):
                continue

            caminho = os.path.join(raiz, arq)

            try:
                tree = ET.parse(caminho)
                root = tree.getroot()

                # S-1210
                if root.find('.//{*}evtIrrfBenef') is not None:
                    dados = parse_s1210(root, arq, empresa)
                    if dados:
                        cursor.execute("""
                        INSERT INTO ESOCIAL_S1210
                        (CPF, EMPRESA, COMPETENCIA, DT_PAGTO, REND_TRIB, INSS, IRRF, COD_RECEITA, ARQUIVO)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, dados)

                # S-5001
                elif root.find('.//{*}evtBasesTrab') is not None:
                    lista = parse_s5001(root, arq, empresa)
                    for d in lista:
                        cursor.execute("""
                        INSERT INTO ESOCIAL_S5001
                        (CPF, EMPRESA, COMPETENCIA, VL_INSS, VL_DESCONTO, ARQUIVO)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, d)

                # S-5002
                elif root.find('.//{*}evtIrrf') is not None:
                    lista = parse_s5002(root, arq, empresa)
                    for d in lista:
                        cursor.execute("""
                        INSERT INTO ESOCIAL_S5002
                        (CPF, EMPRESA, COMPETENCIA, VL_BASE_IRRF, VL_IRRF, ARQUIVO)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, d)

            except Exception as e:
                print("Erro:", caminho, e)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    processar()
