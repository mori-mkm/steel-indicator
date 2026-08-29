#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sprint "IPIA-HRC - Import Policy Evidence Hardening", implementacao
aprovada (decisao do usuario: B - PARTIAL IMPLEMENTATION, VERIFIED policy
only). Motivo de revisao: REGULATORY_SOURCE_CORRECTION - correcao de
parametro/fonte (aliquota de II incorreta para 4 NCMs + elevacao
tarifaria da Res. GECEX 865/2026 nao modelada), nunca uma mudanca da
formula economica do PPI/IPIA. Ver
docs/validation/hrc_import_policy_correction_migration.md.

Mesmo padrao de `scripts/migrar_fx_convention_media_mensal.py` (ADR
0014): roda UMA UNICA VEZ o recalculo COMPLETO da serie sob a policy
table corrigida (`steel_indicator/parameters/trade_policy.py`, ja
editado nesta stage) SEM aplicar `congelado_df` - excecao deliberada ao
fluxo rotineiro de `executar_pipeline_ipia_hrc` (que sempre congela o
OFFICIAL da vintage anterior), autorizada explicitamente para esta
correcao regulatoria. Nunca sobrescreve a vintage anterior (permanece
imutavel e byte-identical em
data/processed/vintages/ipia_hrc_v2/<vintage_id_antiga>/). Persiste uma
NOVA vintage via `indices_setoriais.salvar_vintage_ipia_hrc_v2` (mesmo
mecanismo append-only, ADR 0012) e so entao atualiza os LATEST
(ipia_hrc_v2_official.csv/provisional.csv) a partir da vintage recem-
persistida.

Faz chamadas de rede reais (Comex Stat, BCB/SGS, IBGE/SIDRA).

Uso:
    python scripts/migrar_hrc_import_policy_correction.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m

OUT_DIR = "data/processed/validation/hrc_import_policy_correction"
ANO_INI, ANO_FIM = m._PIPELINE_ANO_INI_PADRAO, m._PIPELINE_ANO_FIM_PADRAO


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    secao("1. Carregando vintage anterior (lineage + comparacao)")
    vintage_id_antiga = m.ultima_vintage_ipia_hrc_v2()
    if vintage_id_antiga is None:
        raise RuntimeError("Nenhuma vintage anterior encontrada em "
                            f"{m.VINTAGE_BASE_DIR_PADRAO} - nada para migrar.")
    vintage_anterior = m.carregar_vintage_ipia_hrc_v2(vintage_id_antiga)
    oficial_antigo = vintage_anterior["official"]
    provisional_antigo = vintage_anterior["provisional"]
    print(f"  vintage anterior: {vintage_id_antiga}")
    print(f"  OFFICIAL antigo: {len(oficial_antigo)} meses "
          f"({oficial_antigo['reference_period'].min():%Y-%m} a {oficial_antigo['reference_period'].max():%Y-%m})")
    print(f"  PROVISIONAL antigo: {len(provisional_antigo)} meses")

    secao("2. Buscando dado fresco (Comex Stat + BCB/SGS + IBGE/SIDRA) - rede real")
    fetch_at_utc: dict[str, str] = {}
    fetch_at_utc["comex_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    df_bruto = m._pipeline_comex_bruto_com_retry(ANO_INI, ANO_FIM)
    fetch_at_utc["bcb_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    # _pipeline_import_side_hrc -> agregar_ipia_hrc_multi_ncm_mensal ->
    # resolver_ii (steel_indicator/parameters/trade_policy.py) ja usa a
    # policy table CORRIGIDA nesta stage - nada a mudar aqui.
    ppi_mensal_df = m._pipeline_import_side_hrc(df_bruto, ANO_INI, ANO_FIM)
    fetch_at_utc["pia_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    pia_anual = m.ibge_sidra_pia_hrc_anual()
    fetch_at_utc["ipp_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    ipp_mensal = m.ibge_sidra_ipp_siderurgia()
    pia_domestico_df = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia_anual, ipp_mensal=ipp_mensal)

    secao("3. Recalculando a serie COMPLETA sob a policy corrigida - SEM congelado_df (deliberado)")
    serie_nova = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_mensal_df, pia_domestico_df=pia_domestico_df,
                                             congelado_df=None)
    oficial_novo, provisional_novo = m.separar_ipia_hrc_v2_oficial_provisional(serie_nova)
    print(f"  OFFICIAL novo: {len(oficial_novo)} meses")
    print(f"  PROVISIONAL novo: {len(provisional_novo)} meses")

    secao("3b. Sanity check - preco domestico nao deveria mudar (fora do escopo desta correcao)")
    dom_antigo = pd.concat([oficial_antigo, provisional_antigo], ignore_index=True) \
        .set_index("reference_period")["preco_domestico_rs_t"].sort_index()
    dom_novo = pd.concat([oficial_novo, provisional_novo], ignore_index=True) \
        .set_index("reference_period")["preco_domestico_rs_t"].sort_index()
    idx_dom_comum = dom_antigo.index.intersection(dom_novo.index)
    diff_dom = (dom_antigo.loc[idx_dom_comum] - dom_novo.loc[idx_dom_comum]).abs()
    meses_dom_mudou = diff_dom[diff_dom > 1e-6]
    if len(meses_dom_mudou) > 0:
        print(f"  [ATENCAO] preco_domestico_rs_t mudou em {len(meses_dom_mudou)} mes(es) fora desta correcao "
              f"(revisao de fonte upstream - IBGE/SIDRA - nao causada por este script):")
        print(meses_dom_mudou.sort_values(ascending=False).head(10).to_string())
    else:
        print("  [OK] preco_domestico_rs_t identico ao da vintage anterior em todos os meses comuns - "
              "toda diferenca de PPI/IPIA abaixo vem exclusivamente da correcao de policy de II.")

    secao("4. Persistindo NOVA vintage (append-only - a anterior nao e tocada)")
    manifest = m.salvar_vintage_ipia_hrc_v2(
        serie_nova, import_side_df=ppi_mensal_df, domestic_price_df=pia_domestico_df,
        vintage_anterior=vintage_anterior, sources_fetch_at_utc=fetch_at_utc)
    vintage_id_nova = manifest["vintage_id"]
    print(f"  nova vintage: {vintage_id_nova}  (previous_vintage_id={vintage_id_antiga})")
    print(f"  methodology_version: {manifest['methodology_version']}")

    secao("5. Atualizando LATEST a partir da vintage recem-persistida")
    vintage_nova = m.carregar_vintage_ipia_hrc_v2(vintage_id_nova)
    vintage_nova["official"].to_csv("data/processed/ipia_hrc_v2_official.csv", index=False)
    vintage_nova["provisional"].to_csv("data/processed/ipia_hrc_v2_provisional.csv", index=False)
    print("  data/processed/ipia_hrc_v2_official.csv atualizado")
    print("  data/processed/ipia_hrc_v2_provisional.csv atualizado")

    secao("6. Comparativo OLD vs NEW (todos os meses comuns, oficiais + provisorios)")
    old_full = pd.concat([oficial_antigo, provisional_antigo], ignore_index=True) \
        .set_index("reference_period").sort_index()
    new_full = pd.concat([vintage_nova["official"], vintage_nova["provisional"]], ignore_index=True) \
        .set_index("reference_period").sort_index()
    idx_comum = old_full.index.intersection(new_full.index)

    comp = pd.DataFrame({
        "ppi_old": old_full.loc[idx_comum, "ppi_rs_t"],
        "ppi_new": new_full.loc[idx_comum, "ppi_rs_t"],
        "ipia_old": old_full.loc[idx_comum, "ipia_hrc_v2"],
        "ipia_new": new_full.loc[idx_comum, "ipia_hrc_v2"],
        "old_status": old_full.loc[idx_comum, "publication_status"],
        "new_status": new_full.loc[idx_comum, "publication_status"],
    })
    comp["ppi_delta_rs_t"] = comp["ppi_new"] - comp["ppi_old"]
    comp["ppi_delta_pct"] = comp["ppi_delta_rs_t"] / comp["ppi_old"] * 100.0
    comp["ipia_delta_pts"] = comp["ipia_new"] - comp["ipia_old"]
    comp["threshold_100_crossing"] = (
        ((comp["ipia_old"] > 100) & (comp["ipia_new"] < 100))
        | ((comp["ipia_old"] < 100) & (comp["ipia_new"] > 100)))

    validos = comp["ipia_old"].notna() & comp["ipia_new"].notna()
    c = comp[validos]
    print(f"  meses comparaveis: {len(c)} de {len(idx_comum)}")
    mudaram = c[c["ppi_delta_pct"].abs() > 1e-9]
    print(f"  meses com PPI alterado: {len(mudaram)}")
    if len(mudaram):
        print(f"  PPI delta%% - media={mudaram['ppi_delta_pct'].mean():+.4f}  "
              f"min={mudaram['ppi_delta_pct'].min():+.4f}  max={mudaram['ppi_delta_pct'].max():+.4f}")
        print(f"  IPIA delta pts - media={mudaram['ipia_delta_pts'].mean():+.4f}  "
              f"min={mudaram['ipia_delta_pts'].min():+.4f}  max={mudaram['ipia_delta_pts'].max():+.4f}")
    print(f"  threshold crossings (100): {int(c['threshold_100_crossing'].sum())}")
    print(f"  status mudou (old_status != new_status): {int((c['old_status'] != c['new_status']).sum())} mes(es)")

    oficial_idx = pd.to_datetime(oficial_antigo["reference_period"])
    oficial_afetado = mudaram[mudaram.index.isin(oficial_idx)] if len(mudaram) else mudaram
    print(f"  meses OFFICIAL (congelados na vintage antiga) afetados: {len(oficial_afetado)}")

    mom_old = old_full.loc[idx_comum, "ipia_hrc_v2"].diff()
    mom_new = new_full.loc[idx_comum, "ipia_hrc_v2"].diff()
    mom_validos = mom_old.notna() & mom_new.notna() & (mom_old != 0) & (mom_new != 0)
    reversoes = np.sign(mom_old[mom_validos]) != np.sign(mom_new[mom_validos])
    print(f"  MoM reversals: {int(reversoes.sum())} / {int(mom_validos.sum())}")
    if reversoes.any():
        print(f"    meses: {reversoes.index[reversoes].strftime('%Y-%m').tolist()}")

    print("\n  Top 15 maiores |PPI delta%|:")
    top15 = mudaram.reindex(mudaram["ppi_delta_pct"].abs().sort_values(ascending=False).index).head(15)
    print(top15[["ppi_old", "ppi_new", "ppi_delta_rs_t", "ppi_delta_pct", "ipia_old", "ipia_new",
                 "ipia_delta_pts", "old_status", "new_status"]].to_string(float_format=lambda v: f"{v:,.4f}"))

    comp.insert(0, "label", "OLD_VS_NEW_IMPORT_POLICY_CORRECTION")
    comp.insert(1, "revision_reason", "REGULATORY_SOURCE_CORRECTION")
    caminho = f"{OUT_DIR}/import_policy_correction_old_vs_new.csv"
    comp.to_csv(caminho)
    print(f"\n  escrito: {caminho}")

    secao("FIM")
    print(f"  vintage antiga (intacta, reproduzivel): {vintage_id_antiga}")
    print(f"  vintage nova (persistida):              {vintage_id_nova}")
    print("  Nenhum arquivo da vintage antiga foi sobrescrito.")


if __name__ == "__main__":
    main()
