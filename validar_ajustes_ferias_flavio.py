import csv
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path


PASTA_AJUSTES = Path(r"C:\brven\FLAVIO\ESOCIAL\AJUSTES_FERIAS")
SAIDA_DIR = Path(r"D:\agronil_informe_rendimento_com_esocial\chatgpt\DADOS_SQL_IMPORT")
ARQ_ANALITICO = SAIDA_DIR / "AJUSTES_FERIAS_FLAVIO_ANALITICO.csv"
ARQ_RESUMO = SAIDA_DIR / "AJUSTES_FERIAS_FLAVIO_RESUMO.csv"


def _tag_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _find_text(node: ET.Element, tag_name: str) -> str:
    for el in node.iter():
        if _tag_name(el.tag) == tag_name:
            return (el.text or "").strip()
    return ""


def _findall(node: ET.Element, tag_name: str):
    for el in node.iter():
        if _tag_name(el.tag) == tag_name:
            yield el


def _to_float(value: str) -> float:
    try:
        return float((value or "").strip())
    except Exception:
        return 0.0


def _mes_yyyy_mm(value: str) -> str:
    if not value:
        return ""
    return value[:7]


def _infer_func_from_name(file_name: str) -> str:
    m = re.search(r"func(\d+)", file_name, flags=re.IGNORECASE)
    return m.group(1) if m else ""


def _infer_tipo(file_name: str) -> str:
    lower = file_name.lower()
    if "pagamento" in lower:
        return "pagamento"
    if "totalizador" in lower:
        return "totalizador"
    return "desconhecido"


def parse_pagamento_xml(xml_path: Path) -> list[dict]:
    root = ET.parse(xml_path).getroot()

    per_apur = _find_text(root, "perApur")
    cpf_benef = _find_text(root, "cpfBenef")
    nr_recibo_evento = _find_text(root, "nrRecibo")
    func = _infer_func_from_name(xml_path.name)
    registros = []

    for info_pgto in _findall(root, "infoPgto"):
        dt_pgto = _find_text(info_pgto, "dtPgto")
        per_ref = _find_text(info_pgto, "perRef")
        ide_dmdev = _find_text(info_pgto, "ideDmDev")
        tp_pgto = _find_text(info_pgto, "tpPgto")
        vr_liq = _to_float(_find_text(info_pgto, "vrLiq"))

        registros.append(
            {
                "arquivo": xml_path.name,
                "tipo_arquivo": "pagamento",
                "func": func,
                "cpf": cpf_benef,
                "per_apur": per_apur,
                "per_ref": per_ref,
                "dt_pgto": dt_pgto,
                "mes_dt_pgto": _mes_yyyy_mm(dt_pgto),
                "ide_dmdev": ide_dmdev,
                "tp_pgto": tp_pgto,
                "vr_liq": vr_liq,
                "nr_recibo": nr_recibo_evento,
                "rend_trib": 0.0,
                "irrf": 0.0,
                "cod_receita": "",
                "origem_totalizador": "",
                "status_periodo": (
                    "ALINHADO"
                    if per_ref == _mes_yyyy_mm(dt_pgto)
                    else "PERREF_DIFERENTE_DO_PAGAMENTO"
                ),
            }
        )

    return registros


def parse_totalizador_xml(xml_path: Path) -> list[dict]:
    root = ET.parse(xml_path).getroot()

    per_apur = _find_text(root, "perApur")
    cpf_benef = _find_text(root, "cpfBenef")
    func = _infer_func_from_name(xml_path.name)
    registros = []

    for dm_dev in _findall(root, "dmDev"):
        per_ref = _find_text(dm_dev, "perRef")
        dt_pgto = _find_text(dm_dev, "dtPgto")
        ide_dmdev = _find_text(dm_dev, "ideDmDev")
        tp_pgto = _find_text(dm_dev, "tpPgto")
        cod_categ = _find_text(dm_dev, "codCateg")

        tot_apur = None
        for child in dm_dev:
            if _tag_name(child.tag) == "totApurMen":
                tot_apur = child
                break

        rend_trib = _to_float(_find_text(tot_apur, "vlrRendTrib")) if tot_apur is not None else 0.0
        irrf = _to_float(_find_text(tot_apur, "vlrCRMen")) if tot_apur is not None else 0.0
        cod_receita = _find_text(tot_apur, "CRMen") if tot_apur is not None else ""

        registros.append(
            {
                "arquivo": xml_path.name,
                "tipo_arquivo": "totalizador",
                "func": func,
                "cpf": cpf_benef,
                "per_apur": per_apur,
                "per_ref": per_ref,
                "dt_pgto": dt_pgto,
                "mes_dt_pgto": _mes_yyyy_mm(dt_pgto),
                "ide_dmdev": ide_dmdev,
                "tp_pgto": tp_pgto,
                "vr_liq": 0.0,
                "nr_recibo": "",
                "rend_trib": rend_trib,
                "irrf": irrf,
                "cod_receita": cod_receita,
                "origem_totalizador": cod_categ,
                "status_periodo": (
                    "ALINHADO"
                    if per_ref == _mes_yyyy_mm(dt_pgto)
                    else "PERREF_DIFERENTE_DO_PAGAMENTO"
                ),
            }
        )

    return registros


def carregar_registros(pasta: Path) -> list[dict]:
    registros = []

    for xml_path in sorted(pasta.glob("*.xml")):
        tipo = _infer_tipo(xml_path.name)
        if tipo == "pagamento":
            registros.extend(parse_pagamento_xml(xml_path))
        elif tipo == "totalizador":
            registros.extend(parse_totalizador_xml(xml_path))

    return registros


def gerar_resumo(registros: list[dict]) -> list[dict]:
    resumo = {}

    for row in registros:
        chave = (row["func"], row["cpf"])
        if chave not in resumo:
            resumo[chave] = {
                "func": row["func"],
                "cpf": row["cpf"],
                "qtd_pagamentos": 0,
                "qtd_totalizadores": 0,
                "qtd_desalinhados": 0,
                "vr_liq_total": 0.0,
                "rend_trib_total": 0.0,
                "irrf_total": 0.0,
                "periodos_referencia": set(),
                "datas_pagamento": set(),
            }

        item = resumo[chave]
        if row["tipo_arquivo"] == "pagamento":
            item["qtd_pagamentos"] += 1
            item["vr_liq_total"] += row["vr_liq"]
        elif row["tipo_arquivo"] == "totalizador":
            item["qtd_totalizadores"] += 1
            item["rend_trib_total"] += row["rend_trib"]
            item["irrf_total"] += row["irrf"]

        if row["status_periodo"] != "ALINHADO":
            item["qtd_desalinhados"] += 1

        if row["per_ref"]:
            item["periodos_referencia"].add(row["per_ref"])
        if row["dt_pgto"]:
            item["datas_pagamento"].add(row["dt_pgto"])

    linhas = []
    for item in resumo.values():
        linhas.append(
            {
                "func": item["func"],
                "cpf": item["cpf"],
                "qtd_pagamentos": item["qtd_pagamentos"],
                "qtd_totalizadores": item["qtd_totalizadores"],
                "qtd_desalinhados": item["qtd_desalinhados"],
                "vr_liq_total": f"{item['vr_liq_total']:.2f}",
                "rend_trib_total": f"{item['rend_trib_total']:.2f}",
                "irrf_total": f"{item['irrf_total']:.2f}",
                "periodos_referencia": " | ".join(sorted(item["periodos_referencia"])),
                "datas_pagamento": " | ".join(sorted(item["datas_pagamento"])),
            }
        )

    return sorted(linhas, key=lambda x: (x["func"], x["cpf"]))


def salvar_csv(caminho: Path, linhas: list[dict], campos: list[str]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)


def main() -> None:
    registros = carregar_registros(PASTA_AJUSTES)

    campos_analitico = [
        "arquivo",
        "tipo_arquivo",
        "func",
        "cpf",
        "per_apur",
        "per_ref",
        "dt_pgto",
        "mes_dt_pgto",
        "ide_dmdev",
        "tp_pgto",
        "vr_liq",
        "nr_recibo",
        "rend_trib",
        "irrf",
        "cod_receita",
        "origem_totalizador",
        "status_periodo",
    ]
    salvar_csv(ARQ_ANALITICO, registros, campos_analitico)

    resumo = gerar_resumo(registros)
    campos_resumo = [
        "func",
        "cpf",
        "qtd_pagamentos",
        "qtd_totalizadores",
        "qtd_desalinhados",
        "vr_liq_total",
        "rend_trib_total",
        "irrf_total",
        "periodos_referencia",
        "datas_pagamento",
    ]
    salvar_csv(ARQ_RESUMO, resumo, campos_resumo)

    print(f"Registros analiticos: {len(registros)}")
    print(f"Resumo de funcionarios: {len(resumo)}")
    print(f"CSV analitico: {ARQ_ANALITICO}")
    print(f"CSV resumo: {ARQ_RESUMO}")


if __name__ == "__main__":
    main()
