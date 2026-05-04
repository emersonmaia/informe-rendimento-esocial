"""Regera só o informe do Sergio Diniz Junqueira para conferência."""
import sys
sys.path.insert(0, r'D:\agronil_informe_rendimento_com_esocial\chatgpt')
import gerar_informes

CPF_SERGIO = '25766313802'

os_dados = gerar_informes.buscar_dados()
for row in os_dados:
    cpf_limpo = row.CPF.strip().replace('.','').replace('-','').replace(' ','').zfill(11)
    if cpf_limpo == CPF_SERGIO:
        print(f"Funcionário : {row.NOME_FUNC}")
        print(f"CPF         : {gerar_informes.fmt_cpf(row.CPF)}")
        print(f"REND_TRIB   : {float(row.REND_TRIB or 0):>12.2f}")
        print(f"INSS        : {float(row.INSS or 0):>12.2f}")
        print(f"IRRF        : {float(row.IRRF or 0):>12.2f}")
        print(f"REND_TRIB_13: {float(row.REND_TRIB_13 or 0):>12.2f}  (bruto)")
        print(f"INSS_13     : {float(row.INSS_13 or 0):>12.2f}")
        print(f"IRRF_13     : {float(row.IRRF_13 or 0):>12.2f}")
        rend13 = float(row.REND_TRIB_13 or 0)
        inss13 = float(row.INSS_13 or 0)
        irrf13 = float(row.IRRF_13 or 0)
        liq = rend13 - inss13 - irrf13
        print(f"13 LIQ      : {liq:>12.2f}  (= campo 5.1 no informe)")
        print()
        arquivo = gerar_informes.gerar_pdf(row)
        print(f"PDF gerado: {arquivo}")
        break
else:
    print("Sergio nao encontrado!")
