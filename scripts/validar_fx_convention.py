#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATION / NON-PUBLISHED / COUNTERFACTUAL - Level 3 decision support for
the FX convention used in the IPIA-HRC PPI (docs/METODOLOGIA.md 9.6).

HISTORICAL NOTE (post-ADR 0014): this script was written BEFORE the FX
Convention Sprint decision and is preserved unmodified in its calculation
logic - it is the artifact that made the decision possible
(docs/validation/fx_convention_validation.md) and must not be destroyed.
Production (`indices_setoriais.agregar_ipia_hrc_multi_ncm_mensal`) no
longer uses convention A (`reindex(freq="MS", method="ffill")`) - it now
uses `calcular_fx_mensal` (convention B, monthly mean), per ADR 0014
(`docs/adr/0014-ppi-fx-convention-media-mensal.md`). So what this script
labels "A - CURRENT" is, after the migration
(`scripts/migrar_fx_convention_media_mensal.py`,
`docs/validation/fx_convention_migration.md`), the LEGACY convention
(still used, deliberately, only by the V1 engine -
`calcular_ipia_mensal`/`custo_importacao_detalhado_mensal`), and what it
labels "B - MEAN" is now what production actually computes for the V2
engine. Re-running this script still works exactly as before (nothing
here reads or depends on `agregar_ipia_hrc_multi_ncm_mensal`) and still
correctly reproduces the LEGACY-vs-MEAN comparison that justified the
decision - it just no longer describes "current production" for A.

Does NOT alter any official vintage, the published official/provisional
CSVs, or any production code. Purely analytical: builds two counterfactual
FX series alongside the legacy one, recomputes PPI/IPIA with each
(reusing the exact production formula, `indices_setoriais._ppi_brl_t`/
`ipia`, never a reimplementation), and reports comparison statistics.

Reuses `data/processed/validation/ipia_hrc_v2_import_decomposition_panel.csv`
(produced by `scripts/validar_ipia_hrc_v2_final.py`, Stage G3) as the source
of the FX-independent PPI components (cif_usd_t, frete_usd_t, aliquotas,
antidumping) - avoids a second live Comex Stat fetch for the same data. The
only live network call this script makes is the BCB/SGS daily FX fetch
itself (série 1, cambio_venda), the actual object under study, via the
same `indices_setoriais._pipeline_cambio_historico_seguro` chunked
retrieval production already uses (never `/ultimos/N`).

Conventions compared:
  A. CURRENT  - exactly what production does today: `cambio_mes` column of
     the decomposition panel (daily PTAX venda reindexed onto month-start
     timestamps with `method="ffill"` - see docs/METODOLOGIA.md 9.6 for the
     corrected description: this resolves to the closing PTAX of the last
     business day AT OR BEFORE day 1 of the month, i.e. effectively a
     start-of-month snapshot, not an end-of-month or average rate).
  B. MEAN     - arithmetic mean of all daily PTAX venda observations whose
     calendar date falls within month t.
  C. EOM      - PTAX venda of the last business day WITHIN month t (true
     end-of-month closing rate) - added because convention A turned out to
     be a start-of-month snapshot, not the end-of-month rate the original
     research/most readers would assume "current" means; EOM isolates
     "wrong point in time" from "point vs average" as separate questions.

Produces (all under data/processed/validation/fx_convention/, clearly
separate from data/curated and from any vintage/official CSV):
  fx_convention_counterfactual_panel.csv  - one row per month, all three FX
      conventions and the resulting PPI/IPIA for each, where computable.
  fx_convention_timing_bias.csv           - top-N months by intramonth FX
      volatility, with start/mean/end/current FX and resulting deltas.
  fx_convention_extreme_months.csv        - top-N months by |PPI_current -
      PPI_mean| and by |IPIA_current - IPIA_mean|.

Usage:
    python scripts/validar_fx_convention.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m

PANEL_PATH = "data/processed/validation/ipia_hrc_v2_import_decomposition_panel.csv"
OFFICIAL_PATH = "data/processed/ipia_hrc_v2_official.csv"
PROVISIONAL_PATH = "data/processed/ipia_hrc_v2_provisional.csv"
OUT_DIR = "data/processed/validation/fx_convention"
ANO_INI, ANO_FIM = 2012, 2026

# Thresholds bespoke to THIS analysis only (section 16 of the sprint brief) -
# not an existing project policy. Unit: IPIA points (IPIA is a ratio x100).
LIMIARES_IMPACTO_VINTAGE = {
    "IMMATERIAL": 0.5,
    "LOW": 2.0,
    "MODERATE": 5.0,
    # > 5.0 pts => HIGH
}


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


# =============================================================================
# 1. Carrega o painel de decomposicao (FX-independent components + FX_current)
# =============================================================================

def carregar_panel() -> pd.DataFrame:
    df = pd.read_csv(PANEL_PATH, parse_dates=["reference_period"])
    df = df.set_index("reference_period").sort_index()
    return df


def carregar_domestico_oficial() -> pd.DataFrame:
    off = pd.read_csv(OFFICIAL_PATH, parse_dates=["reference_period"])
    prov = pd.read_csv(PROVISIONAL_PATH, parse_dates=["reference_period"])
    full = pd.concat([off, prov], ignore_index=True)
    full = full.sort_values("reference_period").set_index("reference_period")
    return full


# =============================================================================
# 2. Cambio diario (BCB/SGS serie 1) - unica chamada de rede deste script
# =============================================================================

def buscar_cambio_diario(ano_ini: int, ano_fim: int) -> pd.Series:
    """Reusa o mesmo coletor chunked de producao (respeita o limite de 10
    anos por requisicao do BCB/SGS, nunca usa /ultimos/N)."""
    return m._pipeline_cambio_historico_seguro(ano_ini, ano_fim)


def construir_convencoes_fx(cambio_diario: pd.Series, meses_idx: pd.DatetimeIndex):
    """A partir da serie diaria, constroi FX_mean (media aritmetica dos dias
    uteis do mes) e FX_eom (cotacao do ultimo dia util DENTRO do mes) - a
    granularidade de agrupamento e o mes-calendario de cada observacao
    diaria, nunca um reindex/ffill (isso e exatamente a convencao A, ja
    dada pelo painel)."""
    diario = cambio_diario.copy()
    diario.index = pd.to_datetime(diario.index)
    diario = diario.sort_index()
    por_mes = diario.groupby(diario.index.to_period("M"))

    fx_mean = por_mes.mean()
    fx_mean.index = fx_mean.index.to_timestamp()

    fx_first = por_mes.first()
    fx_first.index = fx_first.index.to_timestamp()

    fx_eom = por_mes.last()
    fx_eom.index = fx_eom.index.to_timestamp()

    fx_vol_intra = (por_mes.max() - por_mes.min()) / por_mes.mean()
    fx_vol_intra.index = fx_vol_intra.index.to_timestamp()

    return (fx_mean.reindex(meses_idx), fx_first.reindex(meses_idx),
            fx_eom.reindex(meses_idx), fx_vol_intra.reindex(meses_idx))


# =============================================================================
# 3. Recomputa PPI para uma convencao de FX alternativa (formula de producao)
# =============================================================================

def recompute_ppi(panel: pd.DataFrame, fx_alt: pd.Series) -> pd.Series:
    """Reusa `indices_setoriais._ppi_brl_t` (mesma funcao que produz
    `ppi_via_motor` no painel oficial) - nunca reimplementa a formula.
    Os componentes FX-independentes (cif_usd_t, frete_usd_t, aliquotas,
    antidumping, D_porto/D_interno/margem via ParamsIPIA) vem do painel;
    so o cambio muda."""
    p = m.ParamsIPIA()
    cif_brl_alt = panel["cif_usd_t"] * fx_alt
    return m._ppi_brl_t(cif_brl_alt, panel["aliquota_ii"], panel["frete_usd_t"],
                         fx_alt, panel["aliquota_afrmm"], panel["antidumping_usd_t"], p)


# =============================================================================
# 4. Estatisticas de comparacao
# =============================================================================

def estatisticas_diferenca(a: pd.Series, b: pd.Series, label_a: str, label_b: str) -> dict:
    """a - b, com a/b ja alinhados (mesmo indice, sem NaN)."""
    diff = a - b
    diff_pct = diff / b * 100.0
    return {
        "n": int(diff.notna().sum()),
        "mean_diff": diff.mean(),
        "median_diff": diff.median(),
        "mae": diff.abs().mean(),
        "rmse": float(np.sqrt((diff ** 2).mean())),
        "mape_pct": diff_pct.abs().mean(),
        "mean_diff_pct": diff_pct.mean(),
        "max_abs_diff": diff.abs().max(),
        "p5": diff.quantile(0.05), "p25": diff.quantile(0.25),
        "p50": diff.quantile(0.50), "p75": diff.quantile(0.75),
        "p95": diff.quantile(0.95),
        "corr": a.corr(b),
        f"mean_{label_a}": a.mean(), f"mean_{label_b}": b.mean(),
    }


def imprimir_stats(nome: str, stats: dict, unidade: str = "") -> None:
    print(f"  {nome}  (n={stats['n']}{unidade})")
    print(f"    mean diff = {stats['mean_diff']:,.4f}   median diff = {stats['median_diff']:,.4f}")
    print(f"    MAE = {stats['mae']:,.4f}   RMSE = {stats['rmse']:,.4f}")
    print(f"    mean diff% = {stats['mean_diff_pct']:,.3f}%   MAPE = {stats['mape_pct']:,.3f}%")
    print(f"    max |diff| = {stats['max_abs_diff']:,.4f}")
    print(f"    P5={stats['p5']:,.4f}  P25={stats['p25']:,.4f}  P50={stats['p50']:,.4f}  "
          f"P75={stats['p75']:,.4f}  P95={stats['p95']:,.4f}")
    print(f"    correlacao = {stats['corr']:,.5f}")


# =============================================================================
# main
# =============================================================================

def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    secao("0. BASELINE")
    panel = carregar_panel()
    print(f"  painel de decomposicao: {panel.index.min().date()} a {panel.index.max().date()}, "
          f"{len(panel)} meses calculaveis")

    secao("1. BUSCA CAMBIO DIARIO (BCB/SGS serie 1, unica chamada de rede)")
    cambio_diario = buscar_cambio_diario(ANO_INI, ANO_FIM)
    print(f"  {len(cambio_diario)} observacoes diarias, {cambio_diario.index.min().date()} "
          f"a {cambio_diario.index.max().date()}")

    fx_mean, fx_first, fx_eom, fx_vol_intra = construir_convencoes_fx(cambio_diario, panel.index)
    fx_current = panel["cambio_mes"]

    secao("2. SANITY CHECK - reconstrucao de PPI_current bate com o painel oficial?")
    ppi_current_reconstruido = recompute_ppi(panel, fx_current)
    erro_reconstrucao = (ppi_current_reconstruido - panel["ppi_via_motor"]).abs().max()
    print(f"  max |PPI_current reconstruido - ppi_via_motor (painel)| = {erro_reconstrucao:.6f} R$/t")
    if erro_reconstrucao > 1e-6:
        print("  [ALERTA] reconstrucao nao bate exatamente - investigar antes de prosseguir.")
    else:
        print("  [OK] formula recomputada bate exatamente com o motor de producao.")

    faltantes = fx_mean.isna() | fx_eom.isna()
    if faltantes.any():
        print(f"  [AVISO] {int(faltantes.sum())} mes(es) do painel sem cotacao diaria correspondente "
              f"(fora da janela buscada nesta secao): {panel.index[faltantes].tolist()}")

    ppi_current = panel["ppi_via_motor"]
    ppi_mean = recompute_ppi(panel, fx_mean)
    ppi_eom = recompute_ppi(panel, fx_eom)

    secao("3. FX: CURRENT vs MEAN")
    validos = fx_current.notna() & fx_mean.notna()
    stats_fx_mean = estatisticas_diferenca(fx_current[validos], fx_mean[validos], "current", "mean")
    imprimir_stats("FX_current - FX_mean", stats_fx_mean, unidade=" meses")
    print(f"    vies sistematico (mean(current-mean)) = {stats_fx_mean['mean_diff']:+.4f} "
          f"({'SUPERESTIMA' if stats_fx_mean['mean_diff']>0 else 'SUBESTIMA'} current vs mean, em media)")

    secao("3b. FX: CURRENT vs EOM (isola o efeito de timing puro)")
    validos_eom = fx_current.notna() & fx_eom.notna()
    stats_fx_eom = estatisticas_diferenca(fx_current[validos_eom], fx_eom[validos_eom], "current", "eom")
    imprimir_stats("FX_current - FX_eom", stats_fx_eom, unidade=" meses")

    secao("4. PPI: CURRENT vs MEAN")
    validos_ppi = ppi_current.notna() & ppi_mean.notna()
    stats_ppi = estatisticas_diferenca(ppi_current[validos_ppi], ppi_mean[validos_ppi], "current", "mean")
    imprimir_stats("PPI_current - PPI_mean (R$/t)", stats_ppi, unidade=" meses")

    secao("5. Merge com preco domestico oficial (so onde publicado)")
    domestico = carregar_domestico_oficial()
    idx_ipia = panel.index.intersection(domestico.index)
    print(f"  janela com preco domestico publicado: {idx_ipia.min().date()} a {idx_ipia.max().date()}, "
          f"{len(idx_ipia)} meses")

    preco_dom = domestico.loc[idx_ipia, "preco_domestico_rs_t"]
    ipia_current = m.ipia(preco_dom, ppi_current.loc[idx_ipia])
    ipia_mean = m.ipia(preco_dom, ppi_mean.loc[idx_ipia])
    ipia_eom = m.ipia(preco_dom, ppi_eom.loc[idx_ipia])

    erro_ipia_oficial = (ipia_current - domestico.loc[idx_ipia, "ipia_hrc_v2"]).abs().max()
    print(f"  max |IPIA_current reconstruido - ipia_hrc_v2 oficial| = {erro_ipia_oficial:.8f}")

    secao("6. IPIA: CURRENT vs MEAN")
    validos_ipia = ipia_current.notna() & ipia_mean.notna()
    stats_ipia = estatisticas_diferenca(ipia_current[validos_ipia], ipia_mean[validos_ipia], "current", "mean")
    imprimir_stats("IPIA_current - IPIA_mean (pontos)", stats_ipia)

    mom_current = ipia_current.diff()
    mom_mean = ipia_mean.diff()
    mesma_direcao = np.sign(mom_current) == np.sign(mom_mean)
    mesma_direcao = mesma_direcao[mom_current.notna() & mom_mean.notna()]
    print(f"  MoM mesma direcao: {int(mesma_direcao.sum())} / {len(mesma_direcao)} meses "
          f"({100*mesma_direcao.mean():.1f}%)")
    print(f"  MoM direcao DIFERENTE: {int((~mesma_direcao).sum())} meses")

    cruzam_100 = ((ipia_current > 100) & (ipia_mean < 100)) | ((ipia_current < 100) & (ipia_mean > 100))
    print(f"  meses com interpretacao de paridade diferente (um lado de 100, outro do outro): "
          f"{int(cruzam_100.sum())}")
    if cruzam_100.any():
        print(f"    meses: {ipia_current.index[cruzam_100].strftime('%Y-%m').tolist()}")

    yoy_current = ipia_current.diff(12)
    yoy_mean = ipia_mean.diff(12)
    yoy_validos = yoy_current.notna() & yoy_mean.notna()
    if yoy_validos.any():
        yoy_diff = (yoy_current[yoy_validos] - yoy_mean[yoy_validos]).abs()
        print(f"  YoY: {int(yoy_validos.sum())} meses comparaveis, "
              f"diferenca media |YoY_current - YoY_mean| = {yoy_diff.mean():.3f} pts")
    else:
        print("  YoY: historico insuficiente para nenhum mes comparavel.")

    secao("7. Volatilidade (MoM, nivel-a-nivel)")
    print(f"  std(delta FX_current)  = {fx_current.diff().std():.5f}   "
          f"std(delta FX_mean) = {fx_mean.diff().std():.5f}")
    print(f"  std(delta PPI_current) = {ppi_current.diff().std():,.3f}   "
          f"std(delta PPI_mean) = {ppi_mean.diff().std():,.3f}")
    print(f"  std(delta IPIA_current)= {ipia_current.diff().std():.4f}   "
          f"std(delta IPIA_mean) = {ipia_mean.diff().std():.4f}")

    secao("8. Timing bias - top 10 meses por volatilidade intramensal do FX")
    top_vol = fx_vol_intra.dropna().sort_values(ascending=False).head(10).index
    timing = pd.DataFrame({
        "fx_inicio_mes": fx_first.loc[top_vol], "fx_medio_mes": fx_mean.loc[top_vol],
        "fx_fim_mes": fx_eom.loc[top_vol], "fx_current_producao": fx_current.loc[top_vol],
        "vol_intramensal_pct": fx_vol_intra.loc[top_vol] * 100,
        "diff_current_menos_mean": (fx_current - fx_mean).loc[top_vol],
        "delta_ppi_current_menos_mean": (ppi_current - ppi_mean).loc[top_vol],
    })
    timing["delta_ipia_current_menos_mean"] = (ipia_current - ipia_mean).reindex(top_vol)
    timing = timing.sort_values("vol_intramensal_pct", ascending=False)
    print(timing.to_string(float_format=lambda v: f"{v:,.4f}"))
    timing.to_csv(f"{OUT_DIR}/fx_convention_timing_bias.csv")

    secao("9. Meses extremos - maior |PPI_current - PPI_mean|")
    delta_ppi = (ppi_current - ppi_mean).dropna()
    extremos_ppi = delta_ppi.abs().sort_values(ascending=False).head(10).index
    tab_ppi = pd.DataFrame({
        "ppi_current": ppi_current.loc[extremos_ppi], "ppi_mean": ppi_mean.loc[extremos_ppi],
        "delta_ppi": delta_ppi.loc[extremos_ppi], "delta_pct": (delta_ppi.loc[extremos_ppi] / ppi_mean.loc[extremos_ppi] * 100),
    }).sort_values("delta_ppi", key=abs, ascending=False)
    print(tab_ppi.to_string(float_format=lambda v: f"{v:,.3f}"))
    tab_ppi.to_csv(f"{OUT_DIR}/fx_convention_extreme_months_ppi.csv")

    secao("10. Meses extremos - maior |IPIA_current - IPIA_mean|")
    delta_ipia = (ipia_current - ipia_mean).dropna()
    extremos_ipia = delta_ipia.abs().sort_values(ascending=False).head(10).index
    tab_ipia = pd.DataFrame({
        "ipia_current": ipia_current.loc[extremos_ipia], "ipia_mean": ipia_mean.loc[extremos_ipia],
        "delta_ipia": delta_ipia.loc[extremos_ipia],
        "publication_status": domestico.loc[extremos_ipia, "publication_status"],
    }).sort_values("delta_ipia", key=abs, ascending=False)
    print(tab_ipia.to_string(float_format=lambda v: f"{v:,.4f}"))
    tab_ipia.to_csv(f"{OUT_DIR}/fx_convention_extreme_months_ipia.csv")

    secao("11. Impacto sobre historico OFICIAL (EXPERIMENTAL/PUBLICATION_GRADE, nao PROVISIONAL)")
    oficial_mask = domestico["publication_status"].isin(["EXPERIMENTAL", "PUBLICATION_GRADE"])
    idx_oficial = idx_ipia[oficial_mask.reindex(idx_ipia).fillna(False)]
    delta_ipia_oficial = (ipia_current.loc[idx_oficial] - ipia_mean.loc[idx_oficial]).abs()
    print(f"  {len(idx_oficial)} meses OFICIAIS (ja congelados) na janela comparavel")

    def classifica(v):
        if pd.isna(v):
            return "N/A"
        if v < LIMIARES_IMPACTO_VINTAGE["IMMATERIAL"]:
            return "IMMATERIAL"
        if v < LIMIARES_IMPACTO_VINTAGE["LOW"]:
            return "LOW"
        if v < LIMIARES_IMPACTO_VINTAGE["MODERATE"]:
            return "MODERATE"
        return "HIGH"

    classes = delta_ipia_oficial.apply(classifica)
    contagem = classes.value_counts().reindex(["IMMATERIAL", "LOW", "MODERATE", "HIGH"], fill_value=0)
    print(f"  limiares desta analise (pts de IPIA, NAO sao politica oficial do projeto): {LIMIARES_IMPACTO_VINTAGE}")
    print(contagem.to_string())

    secao("12. Escrevendo artefatos de validacao")
    contrafactual = pd.DataFrame({
        "fx_current": fx_current, "fx_mean": fx_mean, "fx_eom": fx_eom,
        "ppi_current": ppi_current, "ppi_mean": ppi_mean, "ppi_eom": ppi_eom,
    })
    contrafactual.loc[idx_ipia, "ipia_current"] = ipia_current
    contrafactual.loc[idx_ipia, "ipia_mean"] = ipia_mean
    contrafactual.loc[idx_ipia, "ipia_eom"] = ipia_eom
    contrafactual.loc[idx_ipia, "publication_status"] = domestico.loc[idx_ipia, "publication_status"]
    contrafactual.insert(0, "label", "VALIDATION_NON_PUBLISHED_COUNTERFACTUAL")
    caminho = f"{OUT_DIR}/fx_convention_counterfactual_panel.csv"
    contrafactual.to_csv(caminho)
    print(f"  escrito: {caminho} ({len(contrafactual)} linhas)")
    print(f"  escrito: {OUT_DIR}/fx_convention_timing_bias.csv")
    print(f"  escrito: {OUT_DIR}/fx_convention_extreme_months_ppi.csv")
    print(f"  escrito: {OUT_DIR}/fx_convention_extreme_months_ipia.csv")

    secao("FIM")
    print("  Nenhum vintage oficial, CSV publicado ou serie do PDF foi alterado por este script.")


if __name__ == "__main__":
    main()
