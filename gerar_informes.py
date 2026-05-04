# gerar_informes.py — Comprovante de Rendimentos IN RFB 2.060/2021
import os
import pyodbc
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

PASTA_SAIDA  = r"D:\agronil_informe_rendimento_com_esocial\informes_pdf"
ANO_CAL      = 2025          # ano-calendário
EXERCICIO    = 2026          # exercício
DATA_EMISSAO = '27/01/2026'

PRETO   = colors.black
CINZA_L = colors.HexColor('#AAAAAA')
BRANCO  = colors.white


def get_conn():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.110.194.113;"
        "DATABASE=folha_agronil;"
        "UID=sa;"
        "PWD=mult"
    )


def buscar_dados():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        WITH dados AS (
            SELECT CPF, DT_PAGTO, REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13
            FROM ESOCIAL_S1210
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
            UNION ALL
            SELECT CPF, DT_PAGTO, REND_TRIB, INSS, IRRF, REND_TRIB_13, INSS_13, IRRF_13
            FROM ESOCIAL_S1210_COMPL
            WHERE TRY_CAST(DT_PAGTO AS DATE) IS NOT NULL
              AND YEAR(TRY_CAST(DT_PAGTO AS DATE)) = ?
              AND (REND_TRIB > 0 OR REND_TRIB_13 > 0)
        )
        SELECT
            ISNULL(f.NOME, ISNULL(ov.NOME, 'NAO IDENTIFICADO')) AS NOME_FUNC,
            LTRIM(RTRIM(s.CPF))                                   AS CPF,
            ISNULL(e.NOME, '')                                    AS NOME_EMP,
            ISNULL(LTRIM(RTRIM(e.INSCRICAO_FEDERAL)), '')         AS CNPJ,
            ISNULL(e.ENDERECO, '')                                AS ENDERECO,
            ISNULL(CAST(e.NUMERO AS VARCHAR(20)), '')             AS NUMERO,
            ISNULL(CAST(e.BAIRRO  AS VARCHAR(100)), '')           AS BAIRRO,
            ISNULL(CAST(e.CIDADE  AS VARCHAR(100)), '')           AS CIDADE,
            ISNULL(CAST(e.ESTADO  AS VARCHAR(10)),  '')           AS ESTADO,
            CAST(f.EMPRESA AS VARCHAR(10))                        AS COD_EMPRESA,
            SUM(CASE WHEN s.REND_TRIB_13 > 0 AND ABS(s.REND_TRIB - s.REND_TRIB_13) < 0.02
                     THEN 0 ELSE s.REND_TRIB END)                 AS REND_TRIB,
            SUM(CASE WHEN s.REND_TRIB_13 > 0 AND ABS(s.REND_TRIB - s.REND_TRIB_13) < 0.02
                     THEN 0 ELSE s.INSS END)                      AS INSS,
            SUM(CASE WHEN s.REND_TRIB_13 > 0 AND ABS(s.REND_TRIB - s.REND_TRIB_13) < 0.02
                     THEN 0 ELSE s.IRRF END)                      AS IRRF,
            SUM(s.REND_TRIB_13)                                   AS REND_TRIB_13,
            SUM(s.INSS_13)                                        AS INSS_13,
            SUM(s.IRRF_13)                                        AS IRRF_13,
            ISNULL(e.NOME_RESPONS_DIRF, e.NOME)                   AS NOME_RESP
        FROM dados s
        LEFT JOIN (
            SELECT
                RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)), '.', ''), '-', ''), ' ', ''), 11) AS CPF_LIMPO,
                NOME,
                TRY_CAST(EMPRESA AS INT) AS EMPRESA
            FROM (
                SELECT
                    CPF, NOME, EMPRESA, DATA_RESCISAO,
                    ROW_NUMBER() OVER (
                        PARTITION BY RIGHT('00000000000' + REPLACE(REPLACE(REPLACE(CAST(CPF AS VARCHAR(20)), '.', ''), '-', ''), ' ', ''), 11)
                        ORDER BY
                            CASE WHEN DATA_RESCISAO IS NULL THEN 0 ELSE 1 END,
                            DATA_RESCISAO DESC
                    ) AS rn
                FROM FOLFUN
            ) x
            WHERE x.rn = 1
        ) f ON f.CPF_LIMPO = RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11)
        LEFT JOIN CADEMP e
            ON e.EMPRESA = f.EMPRESA
        LEFT JOIN ESOCIAL_NOME_OVERRIDE ov
            ON ov.CPF = RIGHT('00000000000' + LTRIM(RTRIM(s.CPF)), 11)
        GROUP BY
            f.NOME, ov.NOME, s.CPF, CAST(f.EMPRESA AS VARCHAR(10)),
            e.NOME, e.INSCRICAO_FEDERAL, e.ENDERECO, e.NUMERO,
            e.BAIRRO, e.CIDADE, e.ESTADO,
            e.NOME_RESPONS_DIRF
        ORDER BY e.NOME, ISNULL(f.NOME, ov.NOME)
    """, ANO_CAL, ANO_CAL)
    rows = cursor.fetchall()
    conn.close()
    return rows


def fmt_cpf(cpf):
    c = cpf.strip().replace('.', '').replace('-', '')
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if len(c) == 11 else cpf


def fmt_v(v):
    return f"{float(v or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# ── helpers de parágrafo ─────────────────────────────────────────────────────

def P(text, bold=False, sz=7, align=TA_LEFT):
    return Paragraph(str(text), ParagraphStyle('_',
        fontSize=sz,
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        alignment=align, leading=sz + 2.5))


def mk_table(data, cols, extras=None):
    base = [
        ('BOX',           (0, 0), (-1, -1), 0.4, PRETO),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, CINZA_L),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
    ]
    if extras:
        base.extend(extras)
    t = Table(data, colWidths=cols)
    t.setStyle(TableStyle(base))
    return t


# ── gerador do PDF ────────────────────────────────────────────────────────────

def montar_endereco(row):
    partes = [row.ENDERECO.strip()]
    num = row.NUMERO.strip().lstrip('0')
    if num:
        partes[0] += ', ' + num
    for campo in (row.BAIRRO, row.CIDADE):
        v = campo.strip()
        if v:
            partes.append(v)
    if row.ESTADO.strip():
        partes[-1] += ' - ' + row.ESTADO.strip()
    return ', '.join(p for p in partes if p)


def gerar_pdf(row):
    nome_func = row.NOME_FUNC
    cpf_fmt   = fmt_cpf(row.CPF)
    nome_emp  = row.NOME_EMP
    cnpj      = row.CNPJ
    rend      = float(row.REND_TRIB    or 0)
    inss      = float(row.INSS         or 0)
    irrf      = float(row.IRRF         or 0)
    rend13    = float(row.REND_TRIB_13 or 0)
    inss13    = float(row.INSS_13      or 0)
    irrf13    = float(row.IRRF_13      or 0)
    nome_resp = row.NOME_RESP or nome_emp

    filename = os.path.join(
        PASTA_SAIDA,
        f"informe_{ANO_CAL}_emp{row.COD_EMPRESA}_{row.CPF.strip()}.pdf"
    )

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        rightMargin=1.2*cm, leftMargin=1.2*cm,
        topMargin=1.2*cm,   bottomMargin=1.2*cm,
    )

    W   = A4[0] - 2.4*cm    # largura útil
    VW  = 2.6*cm             # coluna valores
    DW  = W - VW             # coluna descrição

    story = []

    # ── 0. CABEÇALHO ──────────────────────────────────────────────────────────
    esq = [
        P("MINISTÉRIO DA FAZENDA", bold=True, sz=8, align=TA_CENTER),
        P("Secretaria Especial da Receita Federal do Brasil", sz=7, align=TA_CENTER),
        P("Imposto sobre a Renda da Pessoa Física", bold=True, sz=7, align=TA_CENTER),
        P(f"Exercício de {EXERCICIO}", bold=True, sz=7, align=TA_CENTER),
    ]
    dir_ = [
        P("Comprovante de Rendimentos Pagos e de", sz=8, align=TA_CENTER),
        P("Imposto sobre a Renda Retido na Fonte", sz=8, align=TA_CENTER),
        Spacer(1, 3),
        P(f"Ano-calendário de {ANO_CAL}", bold=True, sz=9, align=TA_CENTER),
    ]
    story.append(mk_table([[esq, dir_]], [W * 0.46, W * 0.54], [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    # ── aviso ─────────────────────────────────────────────────────────────────
    aviso = (
        "Verifique as condições e o prazo para a apresentação da Declaração do Imposto sobre "
        "a Renda da Pessoa Física para este ano-calendário no sítio da Secretaria Especial da "
        "Receita Federal do Brasil na Internet, no endereço "
        "<https://www.gov.br/receitafederal/pt-br>."
    )
    story.append(mk_table(
        [[P(aviso, sz=6.5, align=TA_JUSTIFY)]], [W],
        [('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)],
    ))

    # ── 1. FONTE PAGADORA ─────────────────────────────────────────────────────
    story.append(mk_table([
        [P("1. Fonte Pagadora Pessoa Jurídica", bold=True, sz=7.5), ""],
        [P("CNPJ", bold=True, sz=6.5), P("Nome Empresarial/Nome Completo", bold=True, sz=6.5)],
        [P(cnpj, sz=7), P(nome_emp, sz=7)],
    ], [5*cm, W - 5*cm], [
        ('SPAN', (0, 0), (1, 0)),
    ]))

    # ── 2. BENEFICIÁRIO ───────────────────────────────────────────────────────
    story.append(mk_table([
        [P("2. Pessoa Física Beneficiária dos Rendimentos", bold=True, sz=7.5), ""],
        [P("CPF", bold=True, sz=6.5), P("Nome Completo", bold=True, sz=6.5)],
        [P(cpf_fmt, sz=7), P(nome_func, sz=7)],
        [P("Natureza do Rendimento", bold=True, sz=6.5), ""],
        [P("Rendimentos do trabalho sem vínculo empregatício", sz=7), ""],
    ], [5*cm, W - 5*cm], [
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 3), (1, 3)),
        ('SPAN', (0, 4), (1, 4)),
    ]))

    # ── helper: quadro 2 colunas ──────────────────────────────────────────────
    def quadro2(rows_data):
        return mk_table(rows_data, [DW, VW], [
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ])

    # ── 3. RENDIMENTOS TRIBUTÁVEIS ────────────────────────────────────────────
    story.append(quadro2([
        [P("3. Rendimentos Tributáveis, Deduções e Imposto sobre a Renda Retido da Fonte",
           bold=True, sz=7.5),
         P("Valores em reais", bold=True, sz=7, align=TA_RIGHT)],
        [P("1. Total dos rendimentos (inclusive férias)", sz=7),              P(fmt_v(rend), sz=7, align=TA_RIGHT)],
        [P("2. Contribuição previdenciária oficial", sz=7),                   P(fmt_v(inss), sz=7, align=TA_RIGHT)],
        [P("3. Contribuição a entidades de previdência complementar, pública ou privada, "
           "e a fundos de aposentadoria programada individual (Fapi)"
           "(preencher também o quadro 7)", sz=7),                            P("0,00", sz=7, align=TA_RIGHT)],
        [P("4. Pensão alimentícia (preencher também o quadro 7)", sz=7),      P("0,00", sz=7, align=TA_RIGHT)],
        [P("5. Imposto sobre a renda retido na fonte", sz=7),                 P(fmt_v(irrf), sz=7, align=TA_RIGHT)],
    ]))

    # ── 4. RENDIMENTOS ISENTOS ────────────────────────────────────────────────
    story.append(quadro2([
        [P("4. Rendimentos Isentos e Não Tributáveis", bold=True, sz=7.5),
         P("Valores em reais", bold=True, sz=7, align=TA_RIGHT)],
        [P("1. Parcela isenta dos proventos de aposentadoria, reserva remunerada, reforma e pensão "
           "(65 anos ou mais), exceto a parcela isenta do 13º (décimo terceiro) salário", sz=7),
         P("0,00", sz=7, align=TA_RIGHT)],
        [P("2. Parcela isenta do 13º salário de aposentadoria, reserva remunerada, reforma e pensão "
           "(65 anos ou mais)", sz=7),                                         P("0,00", sz=7, align=TA_RIGHT)],
        [P("3. Diárias e ajuda de custo", sz=7),                              P("0,00", sz=7, align=TA_RIGHT)],
        [P("4. Pensão e proventos de aposentadoria ou reforma por moléstia grave; proventos de "
           "aposentadoria ou reforma por acidente em serviço", sz=7),          P("0,00", sz=7, align=TA_RIGHT)],
        [P("5. Lucros e dividendos, apurados a partir de 1996, pagos por pessoa jurídica "
           "(lucro real, presumido ou arbitrado)", sz=7),                      P("0,00", sz=7, align=TA_RIGHT)],
        [P("6. Valores pagos ao titular ou sócio da microempresa ou empresa de pequeno porte, "
           "exceto pro labore, aluguéis ou serviços prestados", sz=7),         P("0,00", sz=7, align=TA_RIGHT)],
        [P("7. Indenizações por rescisão de contrato de trabalho, inclusive a título de PDV "
           "e por acidente de trabalho", sz=7),                               P("0,00", sz=7, align=TA_RIGHT)],
        [P("8. Juros de mora recebidos, devidos pelo atraso no pagamento de remuneração "
           "por exercício de emprego, cargo ou função", sz=7),                 P("0,00", sz=7, align=TA_RIGHT)],
        [P("9. Outros:", sz=7),                                               P("0,00", sz=7, align=TA_RIGHT)],
    ]))

    # ── 5. TRIBUTAÇÃO EXCLUSIVA ───────────────────────────────────────────────
    # O Quadro 5 pede "rendimento líquido" conforme IN RFB 2.060/2021:
    # campo 5.1 = bruto − INSS_13 − IRRF_13
    dec13_liq = rend13 - inss13 - irrf13
    story.append(quadro2([
        [P("5. Rendimentos Sujeitos à Tributação Exclusiva (rendimento líquido)", bold=True, sz=7.5),
         P("Valores em reais", bold=True, sz=7, align=TA_RIGHT)],
        [P("1. Décimo terceiro salário", sz=7),                               P(fmt_v(dec13_liq), sz=7, align=TA_RIGHT)],
        [P("2. Imposto sobre a renda retido na fonte sobre 13º salário", sz=7), P(fmt_v(irrf13), sz=7, align=TA_RIGHT)],
        [P("3. Outros", sz=7),                                                P("0,00", sz=7, align=TA_RIGHT)],
    ]))

    # ── 6. RECEBIDOS ACUMULADAMENTE ───────────────────────────────────────────
    C1 = DW - 3.8*cm
    C2 = 3.8*cm
    C3 = VW
    story.append(mk_table([
        [P("6. Rendimentos Recebidos Acumuladamente - Art. 12-A da Lei nº 7.713, de 1988 "
           "(sujeitos à tributação exclusiva)", bold=True, sz=7.5), "", ""],
        [P("6.1 Número do processo:", sz=7),
         P("Quantidade de meses", sz=7, align=TA_CENTER),
         P("0,0", sz=7, align=TA_RIGHT)],
        [P("Natureza do rendimento:", sz=7),
         P("Valores em reais", bold=True, sz=7, align=TA_RIGHT), ""],
        [P("1. Total dos rendimentos tributáveis (inclusive férias e décimo terceiro salário)", sz=7),
         P("0,00", sz=7, align=TA_RIGHT), ""],
        [P("2. Exclusão: Despesas com a ação judicial", sz=7),
         P("0,00", sz=7, align=TA_RIGHT), ""],
        [P("3. Dedução: Contribuição previdenciária oficial", sz=7),
         P("0,00", sz=7, align=TA_RIGHT), ""],
        [P("4. Dedução: Pensão alimentícia (preencher também o quadro 7)", sz=7),
         P("0,00", sz=7, align=TA_RIGHT), ""],
        [P("5. Imposto sobre a renda retido na fonte (IRRF)", sz=7),
         P("0,00", sz=7, align=TA_RIGHT), ""],
        [P("6. Rendimentos isentos de pensão, proventos de aposentadoria ou reforma por moléstia "
           "grave ou aposentadoria ou reforma por acidente em serviço", sz=7),
         P("0,00", sz=7, align=TA_RIGHT), ""],
    ], [C1, C2, C3], [
        ('SPAN', (0, 0), (2, 0)),
        ('SPAN', (1, 2), (2, 2)),
        ('SPAN', (1, 3), (2, 3)),
        ('SPAN', (1, 4), (2, 4)),
        ('SPAN', (1, 5), (2, 5)),
        ('SPAN', (1, 6), (2, 6)),
        ('SPAN', (1, 7), (2, 7)),
        ('SPAN', (1, 8), (2, 8)),
        ('ALIGN', (2, 1), (2, 1), 'RIGHT'),
        ('ALIGN', (1, 3), (1, -1), 'RIGHT'),
    ]))

    # ── 7. INFORMAÇÕES COMPLEMENTARES ────────────────────────────────────────
    story.append(mk_table([
        [P("7. Informações Complementares", bold=True, sz=7.5)],
        [P("", sz=7)],
    ], [W], [
        ('BOTTOMPADDING', (0, 1), (0, 1), 14),
    ]))

    # ── 8. RESPONSÁVEL PELAS INFORMAÇÕES ─────────────────────────────────────
    story.append(mk_table([
        [P("8. Responsável pelas Informações", bold=True, sz=7.5), "", ""],
        [P("Nome", bold=True, sz=6.5), P("Data", bold=True, sz=6.5), P("Assinatura", bold=True, sz=6.5)],
        [P(nome_resp, sz=7), P(DATA_EMISSAO, sz=7), P("", sz=7)],
    ], [W * 0.50, W * 0.18, W * 0.32], [
        ('SPAN', (0, 0), (2, 0)),
    ]))

    # ── rodapé ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3))
    story.append(P(
        "Aprovado pela Instrução Normativa RFB nº 2.060, de 13 de dezembro de 2021.",
        sz=6.5
    ))

    doc.build(story)
    return filename


def main():
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    dados = buscar_dados()
    if not dados:
        print(f"Nenhum dado encontrado.")
        return
    print(f"Gerando {len(dados)} informes — ano-calendário {ANO_CAL}\n")
    ok = erros = 0
    for row in dados:
        try:
            gerar_pdf(row)
            print(f"  OK  {row.NOME_FUNC:<40}  CPF: {fmt_cpf(row.CPF)}")
            ok += 1
        except Exception as e:
            print(f" ERR  CPF {row.CPF}: {e}")
            erros += 1
    print(f"\nConcluído — {ok} gerados, {erros} erros")
    print(f"PDFs em: {PASTA_SAIDA}")


if __name__ == "__main__":
    main()
