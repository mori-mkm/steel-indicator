#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RESEARCH ONLY - nao altera ParamsIPIA, PPI oficial, IPIA, vintages,
VERSAO_METODOLOGIA nem reporting.

Sprint "IPIA-HRC - IMPORT PARITY SCOPE: COST vs OFFER/TRADER PRICE",
Secao 10: contrafactual isolado margem=0% (custo puro) vs margem=3%
(Current), com D_porto/D_interno fixos no Current (210/140) - isola
apenas o efeito de zerar a margem, reusando
`agregar_ipia_hrc_multi_ncm_mensal` (producao) como os scripts irmaos
desta serie de validacao. Faz chamadas de rede reais (Comex Stat,
BCB/SGS).

Uso:
    python scripts/contrafactual_margem_zero_vs_atual.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd

import indices_setoriais as m

DEFAULT = m.ParamsIPIA()
PRECO_DOMESTICO_HIPOTETICO = 4800.0  # mesmo valor/ressalva do script irmao - nao e o IPIA real


def rodar(df_bruto, p, dummy):
    out = m.agregar_ipia_hrc_multi_ncm_mensal(ano_ini=2019, ano_fim=2026, df_bruto=df_bruto, p=p,
                                                domestico_df=dummy)
    return out.set_index("reference_period")


def main():
    df_bruto = m._comex_bobina_bruto(2019, 2026)
    full_idx = pd.date_range("2019-01-01", "2026-07-01", freq="MS")
    dummy = pd.DataFrame({"preco_rs_t": 1.0}, index=full_idx)

    p_atual = DEFAULT
    p_zero = m.ParamsIPIA(despesas_porto_rs_t=DEFAULT.despesas_porto_rs_t,
                           frete_interno_rs_t=DEFAULT.frete_interno_rs_t,
                           margem_importador=0.0)

    r_atual = rodar(df_bruto, p_atual, dummy)
    r_zero = rodar(df_bruto, p_zero, dummy)

    idx = r_atual.index.intersection(r_zero.index)
    comp = pd.DataFrame({
        "ppi_atual": r_atual.loc[idx, "ppi_rs_t"],
        "ppi_zero": r_zero.loc[idx, "ppi_rs_t"],
    }).dropna()
    comp["delta_ppi_pct"] = (comp["ppi_zero"] / comp["ppi_atual"] - 1) * 100

    ipia_atual = PRECO_DOMESTICO_HIPOTETICO / comp["ppi_atual"] * 100
    ipia_zero = PRECO_DOMESTICO_HIPOTETICO / comp["ppi_zero"] * 100
    delta_ipia_pct = (ipia_zero / ipia_atual - 1) * 100
    cruzamentos = ((ipia_zero > 100) != (ipia_atual > 100)).sum()

    print(f"N meses comparados: {len(comp)}")
    print(f"Mean delta PPI (%%): {comp['delta_ppi_pct'].mean():.4f}")
    print(f"Max |delta PPI| (%%): {comp['delta_ppi_pct'].abs().max():.4f}")
    print(f"Mean delta IPIA_hipotetico (%%): {delta_ipia_pct.mean():.4f}")
    print(f"Max |delta IPIA_hipotetico| (%%): {delta_ipia_pct.abs().max():.4f}")
    print(f"Threshold crossings (IPIA_hipotetico, zero vs atual): {int(cruzamentos)}")
    print(f"PPI atual (mes mais recente, margem=3%%): R$ {comp['ppi_atual'].iloc[-1]:,.2f}/t")
    print(f"PPI zero  (mes mais recente, margem=0%%): R$ {comp['ppi_zero'].iloc[-1]:,.2f}/t")


if __name__ == "__main__":
    main()
