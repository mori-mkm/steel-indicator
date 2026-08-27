#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage E10: executa `preco_domestico_hrc_pia_v2()` (PIA-Produto 2422.2020
+ IPP 242-Siderurgia via Proportional Denton, decisao Level 3 aprovada em
docs/research/hrc_domestic_price_sources.md) contra dado real, e compara
com a ancora corporativa V2 (`preco_domestico_hrc_mensal_v2`) so como
BENCHMARK/sanity-check - nunca para reancorar/fazer splice na serie PIA.

NAO e codigo de producao/publicacao: gera um artefato analitico de
VALIDACAO (CSV), nao conecta a --selftest/CLI/relatorio. Nao altera
`preco_domestico_hrc_mensal_v2` nem nenhum caminho legado.

Uso:
    python scripts/gerar_domestic_price_hrc_pia_v2.py

Produz:
    data/processed/domestic_price_hrc_pia_v2.csv
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd

import indices_setoriais as m

CSV_SAIDA = "data/processed/domestic_price_hrc_pia_v2.csv"


def main() -> None:
    print("=== Buscando PIA-Produto HRC (tabela SIDRA 7752, categoria 2422.2020) ===")
    pia = m.ibge_sidra_pia_hrc_anual()
    print(pia)

    print("\n=== Buscando IPP 242-Siderurgia (tabela SIDRA 6723) ===")
    ipp = m.ibge_sidra_ipp_siderurgia()
    print(f"  {len(ipp)} meses, {ipp.index.min():%Y-%m} a {ipp.index.max():%Y-%m}")

    print("\n=== Calculando Domestic Price HRC V2 - PIA (benchmarked + provisional) ===")
    serie = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)
    if serie.empty:
        print("  serie vazia - nenhum ano com PIA + 12 meses de IPP simultaneos. Nada a reportar.")
        return

    os.makedirs(os.path.dirname(CSV_SAIDA), exist_ok=True)
    serie.to_csv(CSV_SAIDA, index=False)
    print(f"\nCSV salvo em: {CSV_SAIDA}")

    bench = serie[~serie["is_provisional"]]
    prov = serie[serie["is_provisional"]]

    print("\n=== Cobertura ===")
    if not bench.empty:
        print(f"  primeiro mes benchmarked: {bench['reference_period'].min():%Y-%m}")
        print(f"  ultimo mes benchmarked:   {bench['reference_period'].max():%Y-%m}")
        print(f"  numero de meses benchmarked: {len(bench)}")
    if not prov.empty:
        print(f"  primeiro mes provisional: {prov['reference_period'].min():%Y-%m}")
        print(f"  ultimo mes provisional:   {prov['reference_period'].max():%Y-%m}")
        print(f"  numero de meses provisional: {len(prov)}")
    else:
        print("  nenhum mes provisional (IPP nao vai alem do ultimo ano PIA)")

    print("\n=== Nivel (R$/t) ===")
    print(f"  minimo:  {serie['preco_domestico_rs_t'].min():,.2f}")
    print(f"  mediana: {serie['preco_domestico_rs_t'].median():,.2f}")
    print(f"  maximo:  {serie['preco_domestico_rs_t'].max():,.2f}")

    print("\n=== Checagem: cada ano benchmarked bate a media alvo da PIA ===")
    for ano, g in bench.groupby("pia_reference_year"):
        media = g["preco_domestico_rs_t"].mean()
        alvo = float(pia.loc[ano, "preco_rs_t"])
        print(f"  {ano}: media={media:,.2f}  alvo_PIA={alvo:,.2f}  delta={media - alvo:+.6f}")

    print("\n=== Validacao contra a ancora corporativa V2 (benchmark, NUNCA calibracao) ===")
    try:
        corporate = m.preco_domestico_hrc_mensal_v2()
    except Exception as e:
        print(f"  nao foi possivel buscar a ancora corporativa ao vivo ({e}) - pulando validacao")
        corporate = None

    if corporate is not None and not corporate.empty:
        comp = serie.merge(
            corporate[["reference_period", "preco_domestico_rs_t"]].rename(
                columns={"preco_domestico_rs_t": "preco_corporate_rs_t"}),
            on="reference_period", how="inner")
        if comp.empty:
            print("  nenhum mes em comum entre PIA+IPP e a ancora corporativa - sem sobreposicao para validar")
        else:
            comp["delta_abs"] = comp["preco_domestico_rs_t"] - comp["preco_corporate_rs_t"]
            comp["delta_pct"] = comp["preco_domestico_rs_t"] / comp["preco_corporate_rs_t"] - 1.0
            print(comp[["reference_period", "preco_domestico_rs_t", "preco_corporate_rs_t",
                        "delta_abs", "delta_pct", "is_provisional"]].to_string(index=False))
            print(f"\n  delta_pct medio: {comp['delta_pct'].mean() * 100:+.2f}%")
            print(f"  delta_pct desvio-padrao: {comp['delta_pct'].std() * 100:.2f}pp "
                  f"(estabilidade da diferenca - quanto menor, mais estavel o gap)")
    else:
        print("  ancora corporativa vazia - sem sobreposicao para validar")


if __name__ == "__main__":
    main()
