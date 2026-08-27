#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pesquisa Level 3 (continuacao): mede a exposicao a exportacao da serie
IBGE PIA-Produto tabela 7752, categoria 54849 ("2422.2020 Bobinas a quente
de acos ao carbono, nao revestidos" - achado da pesquisa anterior,
docs/research/hrc_domestic_price_sources.md), contra a cesta HRC ja
validada do projeto (`NCM_BOBINA_QUENTE`, 13 NCMs, Comex Stat).

Pergunta: `quantidade_vendida`/`receita_liquida_de_vendas` da PIA-Produto
sao TOTAIS (mercado interno + exportacao combinados, confirmado pela nota
tecnica oficial do IBGE - ver docs/research/hrc_domestic_price_sources.md
secao 1) - o quanto disso e exportacao, e isso muda a leitura do preco
implicito como "preco domestico"?

NAO e codigo de producao. So leitura/impressao - nao escreve em nenhum
caminho de calculo do IPIA, nao cria fator de correcao na formula oficial.

Uso:
    python scripts/research/pia_hrc_export_exposure.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pandas as pd

import indices_setoriais as m
from steel_indicator.sources.comex import COMEX_URL, _post_json

CATEGORIA_HRC_PIA = 54849  # "2422.2020 Bobinas a quente de acos ao carbono, nao revestidos"
ANO_INI, ANO_FIM = 2014, 2023  # janela coberta pela PIA-Produto (tabela 7752)

# NCM_BOBINA_QUENTE inteira (13 codigos, cesta ja aprovada do projeto para
# import - reaproveitada aqui, sem alteracao, tambem para o fluxo de
# exportacao). "com_relevo" (72081000, chapa xadrez/relevo) e fisicamente
# distinto (relevo de superficie, produto de nicho) e provavelmente cai
# num codigo Prodlist proprio, nao 2422.2020 - reportado separadamente
# abaixo (INFERENCE, nao confirmado contra uma tabela de correspondencia
# NCM<->Prodlist oficial, que nao foi localizada nesta pesquisa).
NCMS_TODOS = sorted(sum(m.NCM_BOBINA_QUENTE.values(), []))
NCMS_SEM_RELEVO = sorted(set(NCMS_TODOS) - set(m.NCM_BOBINA_QUENTE["com_relevo"]))


def buscar_pia_hrc() -> pd.DataFrame:
    r_meta = __import__("requests").get(
        "https://servicodados.ibge.gov.br/api/v3/agregados/7752/metadados", timeout=60,
        headers={"User-Agent": "pesquisa-setorial/1.0"})
    r_meta.raise_for_status()
    categoria = next(c for c in next(
        cl for cl in r_meta.json()["classificacoes"] if cl["id"] == 1264)["categorias"]
        if c["id"] == CATEGORIA_HRC_PIA)
    print(f"Categoria PIA confirmada: {categoria['nome']} (unidade: {categoria['unidade']})")

    r = __import__("requests").get(
        "https://servicodados.ibge.gov.br/api/v3/agregados/7752/periodos/all/variaveis/864|1982",
        params={"localidades": "N1[all]", "classificacao": f"1264[{CATEGORIA_HRC_PIA}]"},
        timeout=60, headers={"User-Agent": "pesquisa-setorial/1.0"})
    r.raise_for_status()
    variaveis = r.json()
    series = {}
    for var in variaveis:
        serie = var["resultados"][0]["series"][0]["serie"]
        series[str(var["id"])] = {int(ano): float(v) for ano, v in serie.items()}

    df = pd.DataFrame({
        "receita_pia_mil_rs": pd.Series(series["864"]),
        "qtd_pia_t": pd.Series(series["1982"]),
    })
    df.index.name = "ano"
    return df.sort_index()


def buscar_cambio_anual_medio(ano_ini: int, ano_fim: int) -> pd.Series:
    """BCB SGS rejeita (406) janela de consulta de serie diaria acima de 10
    anos - mesmo workaround ja usado em scripts/gerar_serie_ipia_hrc_v2.py
    (`_cambio_historico_seguro_10anos`) e em
    scripts/research/ipia_hrc_ncm_coverage.py: busca em dois pedacos
    <=10 anos e concatena."""
    url = m.SGS_URL.format(cod=m.SGS["cambio_venda"])
    corte = ano_ini + 6
    janelas = [(f"01/01/{ano_ini}", f"31/12/{corte}"), (f"01/01/{corte + 1}", f"31/12/{ano_fim}")]
    pedacos = []
    for ini, fim in janelas:
        dados = m._get_json(url, {"dataInicial": ini, "dataFinal": fim})
        pdf = pd.DataFrame(dados)
        pdf["data"] = pd.to_datetime(pdf["data"], format="%d/%m/%Y")
        pdf["valor"] = pd.to_numeric(pdf["valor"], errors="coerce")
        pedacos.append(pdf.set_index("data")["valor"])
    cambio = pd.concat(pedacos).sort_index()
    cambio = cambio[~cambio.index.duplicated(keep="last")]
    anual = cambio.resample("YS").mean()
    anual.index = anual.index.year
    anual.index.name = "ano"
    return anual


def buscar_export_hrc(ncms: list[str], ano_ini: int, ano_fim: int) -> pd.DataFrame:
    payload = {
        "flow": "export", "monthDetail": False,
        "period": {"from": f"{ano_ini}-01", "to": f"{ano_fim}-12"},
        "filters": [{"filter": "ncm", "values": ncms}],
        "details": ["ncm"],
        "metrics": ["metricFOB", "metricKG"],
    }
    dados = _post_json(COMEX_URL, payload)
    lst = dados.get("data", {}).get("list", [])
    df = pd.DataFrame(lst)
    df["metricFOB"] = pd.to_numeric(df["metricFOB"], errors="coerce")
    df["metricKG"] = pd.to_numeric(df["metricKG"], errors="coerce")
    df["year"] = df["year"].astype(int)
    anual = df.groupby("year")[["metricFOB", "metricKG"]].sum()
    anual.index.name = "ano"
    return anual.rename(columns={"metricFOB": "export_fob_usd", "metricKG": "export_kg"})


def main() -> None:
    print("=== PIA-Produto: preco implicito HRC (receita/quantidade), 2014-2023 ===")
    pia = buscar_pia_hrc()
    print(pia)

    print("\n=== Comex Stat: exportacao da cesta HRC completa (13 NCMs), 2014-2023 ===")
    export_todos = buscar_export_hrc(NCMS_TODOS, ANO_INI, ANO_FIM)
    print(export_todos)

    print("\n=== Comex Stat: exportacao da cesta HRC SEM 'com_relevo' (12 NCMs), 2014-2023 ===")
    export_sem_relevo = buscar_export_hrc(NCMS_SEM_RELEVO, ANO_INI, ANO_FIM)
    print(export_sem_relevo)

    print("\n=== BCB SGS: cambio anual medio (para converter FOB USD -> R$, so leitura) ===")
    cambio_anual = buscar_cambio_anual_medio(ANO_INI, ANO_FIM)
    print(cambio_anual)

    tabela = pia.join(export_todos, how="left").join(
        export_sem_relevo, how="left", rsuffix="_sem_relevo")
    tabela["cambio_medio"] = cambio_anual.reindex(tabela.index)

    tabela["preco_pia_rs_t"] = tabela["receita_pia_mil_rs"] * 1000 / tabela["qtd_pia_t"]
    tabela["export_t"] = tabela["export_kg"] / 1000
    tabela["export_t_sem_relevo"] = tabela["export_kg_sem_relevo"] / 1000
    tabela["export_share_qty"] = tabela["export_t"] / tabela["qtd_pia_t"]
    tabela["export_share_qty_sem_relevo"] = tabela["export_t_sem_relevo"] / tabela["qtd_pia_t"]
    tabela["export_preco_usd_t"] = tabela["export_fob_usd"] / tabela["export_t"]
    tabela["export_preco_rs_t"] = tabela["export_preco_usd_t"] * tabela["cambio_medio"]

    domestic_qty_approx = tabela["qtd_pia_t"] - tabela["export_t"]
    receita_domestica_aprox = (tabela["receita_pia_mil_rs"] * 1000) - (
        tabela["export_fob_usd"] * tabela["cambio_medio"])
    tabela["preco_domestico_aprox_rs_t_SENSIBILIDADE"] = receita_domestica_aprox / domestic_qty_approx

    cols = ["qtd_pia_t", "receita_pia_mil_rs", "preco_pia_rs_t",
            "export_t", "export_t_sem_relevo", "export_share_qty", "export_share_qty_sem_relevo",
            "export_preco_usd_t", "export_preco_rs_t",
            "preco_domestico_aprox_rs_t_SENSIBILIDADE"]
    print("\n=== Tabela consolidada ===")
    with pd.option_context("display.width", 200, "display.max_columns", 20, "display.float_format", "{:,.2f}".format):
        print(tabela[cols])

    print("\n=== Materialidade do export_share_qty (cesta completa, 13 NCMs) ===")
    faixas = pd.cut(tabela["export_share_qty"] * 100, bins=[0, 5, 10, 20, 100],
                     labels=["<5%", "5-10%", "10-20%", ">20%"])
    print(faixas.value_counts().sort_index())
    print(f"minimo: {tabela['export_share_qty'].min()*100:.1f}%")
    print(f"mediana: {tabela['export_share_qty'].median()*100:.1f}%")
    print(f"maximo: {tabela['export_share_qty'].max()*100:.1f}%")
    print("\nPor ano:")
    for ano, v in tabela["export_share_qty"].items():
        print(f"  {ano}: {v*100:.1f}%")

    out_path = "data/processed/pia_hrc_export_exposure.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tabela.to_csv(out_path)
    print(f"\nCSV salvo em: {out_path}")


if __name__ == "__main__":
    main()
