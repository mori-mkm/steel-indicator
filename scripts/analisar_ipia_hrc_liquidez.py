#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATION + DIAGNOSTICS ONLY - nao cria threshold de liquidez, nao
exclui NCM/pais/mes, nao altera weighting, nao imputa dado, nao muda PPI/
IPIA/publication status/VERSAO_METODOLOGIA.

Sprint "IPIA-HRC - LIQUIDITY / CONCENTRATION HARDENING", Pergunta A: quao
representativo e estavel e o unit value mensal do Comex Stat em funcao de
volume, numero de NCMs, origens e concentracao? Continuacao direta do
sprint anterior (docs/validation/comex_unit_value_external_hrc_validation.md)
- reusa as funcoes de coleta/agregacao de la (`validar_comex_unit_value_hrc`)
em vez de reimplementar.

Faz chamadas de rede reais (Comex Stat; UN Comtrade so se o cache do
sprint anterior nao existir) e reusa os caches gitignored em
data/processed/validation_cache/. Toda saida vai para
data/processed/validation/ipia_hrc_liquidity_concentration/.

Uso:
    python scripts/analisar_ipia_hrc_liquidez.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd

import validar_comex_unit_value_hrc as vcuv  # reusa carregar_comex_bruto, uv_*, comtrade, pearson/spearman

OUT_DIR = "data/processed/validation/ipia_hrc_liquidity_concentration"
JANELA_INI = vcuv.JANELA_INI  # 2019-01-01, mesma janela do sprint anterior

PERCENTIS = [0, .05, .10, .25, .50, .75, .90, .95, 1.0]


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


# =============================================================================
# 1. Diagnosticos mensais (dado bruto pre-agregacao, todas as origens -
#    a mesma base que alimenta o PPI oficial bottom-up, nao so China)
# =============================================================================

def diagnosticos_mensais(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por mes: volume, composicao por NCM/origem, HHI, effective
    number. `n_comex_rows` e o numero de combinacoes (NCM x pais) com
    kg>0 devolvidas pelo Comex Stat no mes - NAO e contagem de operacoes
    aduaneiras reais (o endpoint /general com details=[ncm,country] ja
    devolve dado agregado por essas duas dimensoes, sem nivel de
    declaracao/BL individual) - Sec.7 do sprint, nome deliberadamente
    diferente de `n_operations` para nao superclaimar granularidade que a
    fonte nao expoe. Exportador/fornecedor NAO esta entre os `details`
    pedidos ao Comex Stat (`steel_indicator/sources/comex.py`,
    `details=["ncm","country"]`) - EXPORTER CONCENTRATION NOT OBSERVABLE
    neste pipeline, Sec.8 do sprint."""
    d = df[df["data"] >= JANELA_INI].copy()
    d = d[d["metricKG"] > 0]
    linhas = []
    for data, g in d.groupby("data"):
        total_kg = g["metricKG"].sum()
        by_ncm = g.groupby("coNcm")["metricKG"].sum()
        by_country = g.groupby("country")["metricKG"].sum()
        share_ncm = by_ncm / total_kg
        share_country = by_country / total_kg
        hhi_ncm = float((share_ncm ** 2).sum())
        hhi_origin = float((share_country ** 2).sum())
        linhas.append({
            "data": data,
            "total_kg": total_kg, "total_tonnes": total_kg / 1000,
            "n_active_ncm": int((by_ncm > 0).sum()),
            "n_origins": int((by_country > 0).sum()),
            "n_comex_rows": len(g),
            "share_largest_ncm": float(share_ncm.max()),
            "share_top3_ncm": float(share_ncm.sort_values(ascending=False).head(3).sum()),
            "share_largest_origin": float(share_country.max()),
            "share_top3_origins": float(share_country.sort_values(ascending=False).head(3).sum()),
            "china_share": float(share_country.get("China", 0.0)),
            "hhi_ncm_0_1": hhi_ncm, "hhi_ncm_0_10000": hhi_ncm * 10000,
            "hhi_origin_0_1": hhi_origin, "hhi_origin_0_10000": hhi_origin * 10000,
            "effective_ncms": 1.0 / hhi_ncm if hhi_ncm > 0 else np.nan,
            "effective_origins": 1.0 / hhi_origin if hhi_origin > 0 else np.nan,
        })
    return pd.DataFrame(linhas).set_index("data").sort_index()


def distribuicao(serie: pd.Series) -> dict:
    q = serie.quantile(PERCENTIS)
    return {"min": q[0], "p5": q[.05], "p10": q[.10], "p25": q[.25], "mediana": q[.50],
            "p75": q[.75], "p90": q[.90], "p95": q[.95], "max": q[1.0]}


# =============================================================================
# 2. Concentracao x unit value (instabilidade e erro externo)
# =============================================================================

def montar_painel(diag: pd.DataFrame, uv_all: pd.Series, uv_china: pd.Series,
                   uv_bench: pd.Series) -> pd.DataFrame:
    """Junta diagnosticos mensais com |delta UV| (all-origin, base oficial)
    e, quando disponivel, o erro absoluto contra o benchmark externo
    (China-only, unico recorte com comparacao externa - sprint anterior)."""
    painel = diag.copy()
    painel["uv_all"] = uv_all.reindex(painel.index)
    painel["d_uv_all_abs"] = painel["uv_all"].pct_change().abs()
    overlap_china = vcuv.alinhar(uv_china, uv_bench)
    spread_pct_china = (overlap_china["comex"] / overlap_china["benchmark"] - 1).abs()
    painel["abs_external_error_china"] = spread_pct_china.reindex(painel.index)
    return painel


def correlacoes_concentracao(painel: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    pares = [
        ("hhi_origin_0_1", "d_uv_all_abs", "corr(HHI_origin, |delta UV| all-origin)"),
        ("hhi_ncm_0_1", "d_uv_all_abs", "corr(HHI_ncm, |delta UV| all-origin)"),
        ("hhi_origin_0_1", "abs_external_error_china", "corr(HHI_origin, |erro externo| China)"),
        ("hhi_ncm_0_1", "abs_external_error_china", "corr(HHI_ncm, |erro externo| China)"),
    ]
    for xcol, ycol, rotulo in pares:
        sub = painel[[xcol, ycol]].dropna()
        r = vcuv.pearson(sub[xcol], sub[ycol]) if len(sub) >= 3 else np.nan
        linhas.append({"associacao": rotulo, "pearson": r, "n": len(sub)})
    log_vol = np.log(painel["total_kg"].replace(0, np.nan))
    for ycol, rotulo in [("d_uv_all_abs", "corr(log(volume), |delta UV| all-origin)"),
                         ("abs_external_error_china", "corr(log(volume), |erro externo| China)")]:
        sub = pd.DataFrame({"x": log_vol, "y": painel[ycol]}).dropna()
        r = vcuv.pearson(sub["x"], sub["y"]) if len(sub) >= 3 else np.nan
        linhas.append({"associacao": rotulo, "pearson": r, "n": len(sub)})
    return pd.DataFrame(linhas)


def por_quantil(painel: pd.DataFrame, coluna: str, rotulos=("bottom25", "middle50", "top25"),
                 cortes=(0, .25, .75, 1.0)) -> pd.DataFrame:
    grupo = pd.qcut(painel[coluna], cortes, labels=rotulos, duplicates="drop")
    agg = painel.groupby(grupo, observed=True).agg(
        n_meses=("total_kg", "size"),
        d_uv_all_abs_medio=("d_uv_all_abs", "mean"),
        abs_external_error_medio=("abs_external_error_china", "mean"),
        hhi_origin_medio=("hhi_origin_0_1", "mean"),
        hhi_ncm_medio=("hhi_ncm_0_1", "mean"),
        total_kg_medio=("total_kg", "mean"))
    return agg


# =============================================================================
# 3. Outliers (revisita os do sprint anterior + o caso dos 14kg)
# =============================================================================

OUTLIERS_SPRINT_ANTERIOR = ["2020-12", "2019-05", "2021-01", "2021-04", "2022-11",
                             "2022-10", "2021-06", "2021-03", "2021-08", "2022-08"]


def revisar_outliers(painel: pd.DataFrame, meses: list[str]) -> pd.DataFrame:
    linhas = []
    for mes in meses:
        ts = pd.Timestamp(f"{mes}-01")
        if ts not in painel.index:
            linhas.append({"mes": mes, "nota": "fora da janela/sem dado China no mes"})
            continue
        r = painel.loc[ts]
        linhas.append({"mes": mes, "total_kg": r["total_kg"], "n_active_ncm": r["n_active_ncm"],
                        "n_origins": r["n_origins"], "hhi_ncm_0_1": r["hhi_ncm_0_1"],
                        "hhi_origin_0_1": r["hhi_origin_0_1"],
                        "share_largest_ncm": r["share_largest_ncm"],
                        "share_largest_origin": r["share_largest_origin"]})
    return pd.DataFrame(linhas)


def caso_14kg(df: pd.DataFrame) -> pd.DataFrame:
    """Investigacao dedicada do mes de ~14kg identificado no sprint
    anterior (2020-12, origem China) - Sec.17 do sprint. Mostra as linhas
    cruas do Comex Stat para esse mes/origem, e compara contra o total
    ALL-ORIGIN do mesmo mes para medir materialidade real na serie
    oficial (que agrega todas as origens, nao so China)."""
    mes = pd.Timestamp("2020-12-01")
    linhas_china = df[(df["data"] == mes) & (df["country"] == "China") & (df["metricKG"] > 0)]
    total_kg_mes_all = df[(df["data"] == mes) & (df["metricKG"] > 0)]["metricKG"].sum()
    print(linhas_china[["coNcm", "country", "metricFOB", "metricKG"]].to_string(index=False))
    if len(linhas_china):
        kg_china = linhas_china["metricKG"].sum()
        print(f"\nkg_china_no_mes={kg_china:.0f}  kg_total_all_origin_no_mes={total_kg_mes_all:.0f}  "
              f"participacao_china_no_total={kg_china / total_kg_mes_all:.6%}" if total_kg_mes_all else "sem total")
    return linhas_china


# =============================================================================
# 4. Regimes
# =============================================================================

def por_regime(painel: pd.DataFrame) -> pd.DataFrame:
    d = painel.copy()
    d["ano"] = d.index.year
    agg = d.groupby("ano").agg(
        n_meses=("total_kg", "size"),
        total_kg_medio=("total_kg", "mean"),
        n_active_ncm_medio=("n_active_ncm", "mean"),
        n_origins_medio=("n_origins", "mean"),
        hhi_ncm_medio=("hhi_ncm_0_1", "mean"),
        hhi_origin_medio=("hhi_origin_0_1", "mean"),
        china_share_medio=("china_share", "mean"),
        d_uv_all_abs_medio=("d_uv_all_abs", "mean"))
    return agg


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    secao("0. CARREGAR DADO (reusa scripts/validar_comex_unit_value_hrc.py)")
    df_comex = vcuv.carregar_comex_bruto()
    uv_all = vcuv.uv_agregado_mensal(df_comex, country=None)
    uv_all = uv_all[uv_all.index >= JANELA_INI]
    uv_china = vcuv.uv_agregado_mensal(df_comex, country="China")
    uv_china = uv_china[uv_china.index >= JANELA_INI]
    df_comtrade = vcuv.buscar_comtrade_china_export(ano_ini=2019)
    uv_bench = vcuv.uv_comtrade_agregado_mensal(df_comtrade)

    secao("1. DIAGNOSTICOS MENSAIS (todas as origens - base do PPI oficial)")
    diag = diagnosticos_mensais(df_comex)
    print(f"{len(diag)} meses, {diag.index.min():%Y-%m} a {diag.index.max():%Y-%m}")
    print(diag.tail(6).to_string())
    diag.to_csv(f"{OUT_DIR}/diagnosticos_mensais.csv")

    secao("2. DISTRIBUICAO HISTORICA (volume, NCMs, origens)")
    for col in ("total_kg", "n_active_ncm", "n_origins", "share_largest_ncm",
                "share_top3_ncm", "share_largest_origin", "share_top3_origins", "china_share"):
        dist = distribuicao(diag[col])
        print(f"{col}: " + "  ".join(f"{k}={v:,.4g}" for k, v in dist.items()))

    secao("3. HHI ORIGIN")
    dist_hhi_o = distribuicao(diag["hhi_origin_0_1"])
    print("HHI_origin (0-1): " + "  ".join(f"{k}={v:.4f}" for k, v in dist_hhi_o.items()))
    dist_hhi_o10k = distribuicao(diag["hhi_origin_0_10000"])
    print("HHI_origin (0-10000): " + "  ".join(f"{k}={v:.1f}" for k, v in dist_hhi_o10k.items()))

    secao("4. HHI NCM")
    dist_hhi_n = distribuicao(diag["hhi_ncm_0_1"])
    print("HHI_ncm (0-1): " + "  ".join(f"{k}={v:.4f}" for k, v in dist_hhi_n.items()))
    dist_hhi_n10k = distribuicao(diag["hhi_ncm_0_10000"])
    print("HHI_ncm (0-10000): " + "  ".join(f"{k}={v:.1f}" for k, v in dist_hhi_n10k.items()))

    secao("5. EFFECTIVE NUMBERS")
    print("effective_origins: " + "  ".join(f"{k}={v:.2f}" for k, v in distribuicao(diag["effective_origins"]).items()))
    print("effective_ncms:    " + "  ".join(f"{k}={v:.2f}" for k, v in distribuicao(diag["effective_ncms"]).items()))

    secao("6. VOLUME DIAGNOSTICS x INSTABILIDADE")
    painel = montar_painel(diag, uv_all, uv_china, uv_bench)
    painel.to_csv(f"{OUT_DIR}/painel_completo.csv")
    corr = correlacoes_concentracao(painel)
    print(corr.to_string(index=False))
    corr.to_csv(f"{OUT_DIR}/correlacoes_concentracao.csv", index=False)

    secao("7. CONCENTRACAO x UNIT VALUE - QUANTIS DE VOLUME")
    qv = por_quantil(painel, "total_kg")
    print(qv.to_string())
    qv.to_csv(f"{OUT_DIR}/quantis_volume.csv")

    secao("8. QUANTIS DE CONCENTRACAO (HHI origin)")
    qh = por_quantil(painel, "hhi_origin_0_1")
    print(qh.to_string())
    qh.to_csv(f"{OUT_DIR}/quantis_hhi_origin.csv")

    secao("9. OUTLIERS (revisitando o sprint anterior)")
    out = revisar_outliers(painel, OUTLIERS_SPRINT_ANTERIOR)
    print(out.to_string(index=False))
    out.to_csv(f"{OUT_DIR}/outliers_revisitados.csv", index=False)

    secao("10. CASO DOS 14KG (2020-12, origem China)")
    caso_14kg(df_comex)

    secao("11. REGIMES (por ano)")
    regime = por_regime(painel)
    print(regime.to_string())
    regime.to_csv(f"{OUT_DIR}/regimes.csv")

    secao("FIM - artefatos salvos em " + OUT_DIR)


if __name__ == "__main__":
    main()
