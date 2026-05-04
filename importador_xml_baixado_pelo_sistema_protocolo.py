import lxml.etree as ET
import pandas as pd
import os
import glob
import sys

class ImportadorRetornoSistema:
    def __init__(self):
        self.pasta_retornos = r"D:\agronil_informe_rendimento_com_esocial\ESOCIAL\retornos\59069674000195"
        self.saida = "DADOS_SQL_IMPORT"
        os.makedirs(self.saida, exist_ok=True)

    def _find(self, node, tag):
        for c in node.iter():
            if tag in c.tag: return c.text
        return None

    def processar(self):
        arquivos = glob.glob(os.path.join(self.pasta_retornos, "*.xml"))
        print(f"Analisando {len(arquivos)} retornos do sistema...")
        
        bancos = { "RETORNO_LOTE_S5002": [], "RETORNO_LOTE_RUBRICAS": [] }

        for i, arq in enumerate(arquivos, 1):
            sys.stdout.write(f"\rProcessando {i}/{len(arquivos)}")
            try:
                tree = ET.parse(arq)
                root = tree.getroot()
                
                # Dados do Lote
                protocolo = self._find(root, 'protocoloEnvio')
                dh_recepcao = self._find(root, 'dhRecepcao')

                # 1. Extração de Rubricas do Recibo (Crucial para bater com o holerite)
                for rb in root.xpath("//*[local-name()='rubrica']"):
                    bancos["RETORNO_LOTE_RUBRICAS"].append({
                        "PROTOCOLO": protocolo,
                        "DATA_HORA": dh_recepcao,
                        "RECIBO_RUB": rb.get("nrR"),
                        "COD_RUBRICA": rb.get("cdR"),
                        "INCID_IR": rb.get("inIR"),
                        "ARQUIVO": os.path.basename(arq)
                    })

                # 2. Extração de Valores S5002 (IRRF) dentro do Lote
                for tot in root.xpath("//*[local-name()='tot' and @tipo='S5002']"):
                    cpf = self._find(tot, 'cpfBenef')
                    for dm in tot.xpath(".//*[local-name()='dmDev']"):
                        bancos["RETORNO_LOTE_S5002"].append({
                            "PROTOCOLO": protocolo,
                            "CPF": cpf,
                            "PER_REF": self._find(dm, 'perRef'),
                            "DT_PGTO": self._find(dm, 'dtPgto'),
                            "REND_TRIB": float(self._find(dm, 'vlrRendTrib') or 0),
                            "IR_RETIDO": float(self._find(dm, 'vlrCRMen') or 0),
                            "ARQUIVO": os.path.basename(arq)
                        })
            except: continue

        for k, v in bancos.items():
            if v: pd.DataFrame(v).to_csv(f"{self.saida}/{k}.csv", index=False, sep=";", encoding="utf-8-sig")
        
        print("\n[OK] Arquivos de Retorno processados com sucesso.")

if __name__ == "__main__":
    ImportadorRetornoSistema().processar()
