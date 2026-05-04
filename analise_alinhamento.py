"""Verifica alinhamento de periodo: DATA_PAGAMENTO da folha vs DT_PAGTO do esocial"""
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=100.110.194.113;DATABASE=folha_kiko;UID=sa;PWD=mult"
)
cur = conn.cursor()

# Luis Fernando FOLTOT + DATA_PAGAMENTO para out-dez 2025
cur.execute("""
    SELECT ft.FUNC, ft.MES, ft.ANO, fu.CPF, fu.NOME, fe.DATA_PAGAMENTO,
           ft.INSS, ft.IRRF, ft.BASE_INSS
    FROM FOLTOT ft
    JOIN FOLFUN fu ON fu.FUNC = ft.FUNC AND fu.EMPRESA = ft.EMPRESA
    JOIN FOLEVE fe ON fe.FUNC = ft.FUNC AND fe.MES = ft.MES AND fe.ANO = ft.ANO
    WHERE ft.PERIODO = 2 AND ft.ANO = 2025 AND ft.MES IN (10,11,12)
      AND fu.NOME LIKE '%LUIS FERNANDO SAV%'
    ORDER BY ft.MES
""")
print("Luis Fernando FOLTOT + DATA_PAGAMENTO (out-dez 2025):")
for r in cur.fetchall():
    print(f"  mes={r[1]} ano={r[2]} base_inss={r[8]:.2f} inss={r[6]:.2f} irrf={r[7]:.2f} data_pgto={r[5]}")

print()
# Luis Fernando ESOCIAL_S1210 out-dez 2025
cur.execute("""
    SELECT COMPETENCIA, DT_PAGTO, REND_TRIB, INSS, IRRF
    FROM ESOCIAL_S1210
    WHERE RIGHT('00000000000' + LTRIM(RTRIM(CPF)), 11) = '30270255893'
    AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = 2025
    AND MONTH(TRY_CAST(DT_PAGTO AS DATE)) IN (10,11,12)
    ORDER BY DT_PAGTO
""")
print("Luis Fernando ESOCIAL_S1210 (pagos em out-dez 2025):")
for r in cur.fetchall():
    print(f"  comp={r[0]} dtpgto={r[1]} rend={r[2]:.2f} inss={r[3]:.2f} irrf={r[4]:.2f}")

print()
# Ver DATA_PAGAMENTO padrao em FOLEVE para novembro 2025
cur.execute("""
    SELECT TOP 5 fe.MES, fe.ANO, fe.DATA_PAGAMENTO, fu.NOME
    FROM FOLEVE fe
    JOIN FOLFUN fu ON fu.FUNC = fe.FUNC AND fu.EMPRESA = fe.EMPRESA
    WHERE fe.ANO = 2025 AND fe.MES = 11 AND fe.PERIODO = 2
    ORDER BY fe.FUNC
""")
print("FOLEVE novembro 2025 - DATA_PAGAMENTO (amostra):")
for r in cur.fetchall():
    print(f"  mes={r[0]} ano={r[1]} data_pgto={r[2]} nome={r[3]}")

conn.close()
