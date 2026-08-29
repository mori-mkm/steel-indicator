#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validacao/decomposicao economica do IPIA-HRC V2 ja gerado por
`scripts/gerar_serie_ipia_hrc_v2.py` (`data/processed/ipia_hrc_v2_monthly.csv`).

NAO e um novo caminho de calculo, NAO altera metodologia e NAO conecta o V2
a --selftest/CLI/relatorio. So decompoe, em componentes ja existentes do
motor (`src/indices_setoriais.py`), os meses ja calculados pelo pipeline V2
real, e compara contra o caminho legado (`calcular_ipia_mensal`) para os
mesmos meses.

Busca dado real (Comex Stat, BCB/SGS, IBGE/SIDRA) apenas para a janela
2025-2026 (a janela hoje calculavel) - nao repete a busca completa
2012-2026 de `gerar_serie_ipia_hrc_v2.py` (mais lenta e mais sujeita a rate
limit da Comex Stat); os componentes de meses fora dessa janela nao existem
de qualquer forma (publication_status=UNKNOWN, sem ipia_hrc_v2).

Uso:
    python scripts/validar_ipia_hrc_v2.py

Produz:
    data/processed/ipia_hrc_v2_validation_components.csv
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m

ANO_INI, ANO_FIM = 2025, 2026
CSV_MENSAL_V2 = "data/processed/ipia_hrc_v2_monthly.csv"
CSV_SAIDA = "data/processed/ipia_hrc_v2_validation_components.csv"


def decompor_import_side(df_bruto: pd.DataFrame, ano_ini: int, ano_fim: int,
                          p: m.ParamsIPIA) -> pd.DataFrame:
    """Reconstroi, por mes, os componentes do PPI_COST bottom-up (mesma
    formula de `custo_importacao_bottom_up_mensal`/`_ppi_cost_brl_t` - nao
    reimplementada, so agregada por mes com media ponderada por KG, que
    preserva a soma porque `despesas_porto`/`frete_interno` sao a mesma
    constante em todo grupo do mes). Desde a metodologia 1.5/ADR 0015,
    `_ppi_cost_brl_t` NAO inclui mais margem comercial - `ppi_reconstruido_rs_t`
    abaixo e PPI_COST puro; `ppi_offer_reconstruido_rs_t` (camada analitica,
    `calcular_ppi_offer`) e mantido so para referencia/comparacao contra o
    comportamento pre-1.5."""
    datas = pd.to_datetime(df_bruto["year"].astype(str) + "-"
                            + df_bruto["monthNumber"].astype(str).str.zfill(2) + "-01")
    idx_mensal = pd.date_range(datas.min(), datas.max(), freq="MS")
    cambio = m.sgs(m.SGS["cambio_venda"], inicio=f"01/01/{ano_ini}").reindex(idx_mensal, method="ffill")

    grupos = m.custo_importacao_bottom_up_mensal(df_bruto, cambio, p=p)
    if grupos.empty:
        return grupos
    grupos = grupos.copy()
    grupos["fob_usd_t"] = 1000 * grupos["fob_usd"] / grupos["kg"]
    grupos["seguro_usd_t"] = 1000 * grupos["seguro_usd"] / grupos["kg"]
    grupos["ii_brl_t"] = grupos["cif_brl_t"] * grupos["aliquota_ii"]
    grupos["afrmm_brl_t"] = grupos["frete_usd_t"] * grupos["cambio_mes"] * grupos["aliquota_afrmm"]
    grupos["antidumping_brl_t"] = grupos["antidumping_usd_t"] * grupos["cambio_mes"]

    linhas = []
    for data, g in grupos.groupby("data"):
        w = g["kg"]

        def wavg(col: str) -> float:
            return float(np.average(g[col], weights=w))

        cif_brl_t = wavg("cif_brl_t")
        ii_brl_t = wavg("ii_brl_t")
        afrmm_brl_t = wavg("afrmm_brl_t")
        ad_brl_t = wavg("antidumping_brl_t")
        frete_usd_t = wavg("frete_usd_t")
        cambio_mes = float(g["cambio_mes"].iloc[0])  # mesmo cambio p/ todo grupo do mes (reindex por mes)

        ppi_cost_reconstruido = cif_brl_t + ii_brl_t + afrmm_brl_t + ad_brl_t \
            + p.despesas_porto_rs_t + p.frete_interno_rs_t
        ppi_offer_reconstruido = m.calcular_ppi_offer(ppi_cost_reconstruido, p.margem_importador)

        linhas.append({
            "reference_period": data,
            "fob_usd_t": wavg("fob_usd_t"),
            "frete_usd_t": frete_usd_t,
            "seguro_usd_t": wavg("seguro_usd_t"),
            "cif_usd_t": wavg("cif_usd_t"),
            "cambio": cambio_mes,
            "cif_brl_t": cif_brl_t,
            "ii_brl_t": ii_brl_t,
            "afrmm_brl_t": afrmm_brl_t,
            "antidumping_brl_t": ad_brl_t,
            "aliquota_ii_efetiva": ii_brl_t / cif_brl_t if cif_brl_t else np.nan,
            "aliquota_afrmm_efetiva": afrmm_brl_t / (frete_usd_t * cambio_mes) if frete_usd_t else np.nan,
            "despesas_porto_rs_t": p.despesas_porto_rs_t,
            "frete_interno_rs_t": p.frete_interno_rs_t,
            "margem_importador_pct": p.margem_importador,
            "ppi_reconstruido_rs_t": ppi_cost_reconstruido,
            "ppi_offer_reconstruido_rs_t": ppi_offer_reconstruido,
        })
    return pd.DataFrame(linhas).sort_values("reference_period").reset_index(drop=True)


def montar_legacy(df_bruto: pd.DataFrame, ano_ini: int, ano_fim: int) -> pd.DataFrame:
    """PPI/preco domestico do caminho LEGADO (mesmas funcoes de
    `calcular_ipia_mensal`, sem chamar o orquestrador inteiro - evita a
    chamada de rede extra de `taxa_penetracao_importacao_planos_mensal`,
    que nao entra nesta comparacao)."""
    bobina = m.serie_mensal_preco_bobina(ano_ini, ano_fim, df_bruto=df_bruto).set_index("data")
    cambio = m.sgs(m.SGS["cambio_venda"], inicio=f"01/01/{ano_ini}").reindex(bobina.index, method="ffill")
    custo = m.custo_importacao_rs_t(bobina["preco_usd_t_publicado"], bobina["frete_usd_t"],
                                     bobina["seguro_usd_t"], cambio, m.ParamsIPIA())
    trimestral = m.carregar_preco_domestico_trimestral()
    blend = m.preco_domestico_ponderado(trimestral)
    ipp = m.ibge_sidra_ipp_metalurgia()
    domestico = m.encadear_preco_domestico_mensal(blend, ipp)
    idx = bobina.index.intersection(domestico.index)
    return pd.DataFrame({
        "preco_domestico_legacy_rs_t": domestico.loc[idx, "preco_rs_t"],
        "ppi_legacy_rs_t": custo.loc[idx, "ppi_brl_t"],
    })


def main() -> None:
    print(f"=== Buscando dado bruto do Comex Stat ({ANO_INI}-{ANO_FIM}) ===")
    df_bruto = m._comex_bobina_bruto(ANO_INI, ANO_FIM)
    print(f"  {len(df_bruto)} linhas brutas")

    p = m.ParamsIPIA()

    print("\n=== Decompondo import side (bottom-up multi-NCM) ===")
    componentes = decompor_import_side(df_bruto, ANO_INI, ANO_FIM, p)
    print(f"  {len(componentes)} meses com grupo(s) conhecido(s)")

    print("\n=== Domestic Price V2 (ao vivo, reproduzido - checagem contra o CSV ja gerado) ===")
    dom_v2 = m.preco_domestico_hrc_mensal_v2().rename(
        columns={"companies_used": "companies_used_domv2_reproduzido"})

    print("\n=== Caminho legado (calcular_ipia_mensal, sem penetracao) ===")
    legacy = montar_legacy(df_bruto, ANO_INI, ANO_FIM)

    print("\n=== Serie IPIA-HRC V2 ja gerada (data/processed/ipia_hrc_v2_monthly.csv) ===")
    serie_v2 = pd.read_csv(CSV_MENSAL_V2, parse_dates=["reference_period"])
    calculaveis = serie_v2[serie_v2["ipia_hrc_v2"].notna()].copy()
    print(f"  {len(calculaveis)} meses calculaveis no CSV ja gerado")

    out = calculaveis.merge(componentes, on="reference_period", how="left")
    out = out.merge(dom_v2[["reference_period", "companies_used_domv2_reproduzido"]],
                     on="reference_period", how="left")
    out = out.merge(legacy.reset_index().rename(columns={"data": "reference_period"}),
                     on="reference_period", how="left")

    divergentes = out.loc[out["companies_used"] != out["companies_used_domv2_reproduzido"], "reference_period"]
    if not divergentes.empty:
        print(f"  [ATENCAO] companies_used diverge entre CSV ja gerado e reproducao ao vivo em: "
              f"{', '.join(d.strftime('%Y-%m') for d in divergentes)}")
    else:
        print("  companies_used bate exatamente entre o CSV ja gerado e a reproducao ao vivo (15/15 meses)")

    out["domestic_minus_ppi_rs_t"] = out["preco_domestico_rs_t"] - out["ppi_rs_t"]
    out["domestic_premium_pct"] = out["preco_domestico_rs_t"] / out["ppi_rs_t"] - 1.0
    out["ipia_recomputado_da_formula"] = (1.0 + out["domestic_premium_pct"]) * 100.0
    out["ipia_check_delta"] = out["ipia_hrc_v2"] - out["ipia_recomputado_da_formula"]

    out["ppi_reconstruido_delta_pct"] = out["ppi_reconstruido_rs_t"] / out["ppi_rs_t"] - 1.0

    out["ppi_legacy_delta_abs"] = out["ppi_rs_t"] - out["ppi_legacy_rs_t"]
    out["ppi_legacy_delta_pct"] = out["ppi_rs_t"] / out["ppi_legacy_rs_t"] - 1.0
    out["domestic_legacy_delta_abs"] = out["preco_domestico_rs_t"] - out["preco_domestico_legacy_rs_t"]
    out["domestic_legacy_delta_pct"] = out["preco_domestico_rs_t"] / out["preco_domestico_legacy_rs_t"] - 1.0

    cols = [
        "reference_period",
        # domestico
        "preco_domestico_rs_t", "anchor_price_rs_t", "anchor_reference_period",
        "companies_used", "domestic_is_proxy",
        # importacao
        "fob_usd_t", "frete_usd_t", "seguro_usd_t", "cif_usd_t", "cambio", "cif_brl_t",
        "ii_brl_t", "afrmm_brl_t", "antidumping_brl_t", "aliquota_ii_efetiva", "aliquota_afrmm_efetiva",
        "despesas_porto_rs_t", "frete_interno_rs_t", "margem_importador_pct",
        "ppi_rs_t", "ppi_reconstruido_rs_t", "ppi_offer_reconstruido_rs_t", "ppi_reconstruido_delta_pct",
        # indice
        "ipia_hrc_v2", "domestic_minus_ppi_rs_t", "domestic_premium_pct",
        "ipia_recomputado_da_formula", "ipia_check_delta",
        # benchmark legado
        "ppi_legacy_rs_t", "ppi_legacy_delta_abs", "ppi_legacy_delta_pct",
        "preco_domestico_legacy_rs_t", "domestic_legacy_delta_abs", "domestic_legacy_delta_pct",
        "total_kg", "known_policy_kg",
    ]
    out = out[cols].sort_values("reference_period").reset_index(drop=True)

    os.makedirs(os.path.dirname(CSV_SAIDA), exist_ok=True)
    out.to_csv(CSV_SAIDA, index=False)
    print(f"\nCSV de validacao salvo em: {CSV_SAIDA}")

    print("\n=== Checagem: IPIA == (1+premium)*100 ===")
    print(f"  max |delta|: {out['ipia_check_delta'].abs().max():.10f}")
    assert out["ipia_check_delta"].abs().max() < 1e-6, "IPIA != (1+premium)*100 - formula quebrada"
    assert out["ppi_reconstruido_delta_pct"].abs().max() < 1e-6, (
        "PPI reconstruido por media ponderada diverge do PPI publicado - decomposicao incorreta")

    print("\n=== Decomposicao media do PPI (R$/t, media simples entre os meses calculaveis) ===")
    for col in ("cif_brl_t", "ii_brl_t", "afrmm_brl_t", "antidumping_brl_t",
                "despesas_porto_rs_t", "frete_interno_rs_t"):
        print(f"  {col}: {out[col].mean():.2f}")
    print(f"  margem_importador_pct (constante): {out['margem_importador_pct'].iloc[0]:.4f}")
    print(f"  PPI medio: {out['ppi_rs_t'].mean():.2f}")
    print(f"  preco domestico medio: {out['preco_domestico_rs_t'].mean():.2f}")
    print(f"  IPIA medio: {out['ipia_hrc_v2'].mean():.2f}")

    print("\n=== Benchmark legado (media entre os meses calculaveis) ===")
    print(f"  PPI V2 vs legado: delta abs medio = {out['ppi_legacy_delta_abs'].mean():.2f}, "
          f"delta % medio = {out['ppi_legacy_delta_pct'].mean() * 100:.2f}%")
    print(f"  Domestico V2 vs legado: delta abs medio = {out['domestic_legacy_delta_abs'].mean():.2f}, "
          f"delta % medio = {out['domestic_legacy_delta_pct'].mean() * 100:.2f}%")


if __name__ == "__main__":
    main()
