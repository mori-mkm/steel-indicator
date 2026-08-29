#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sprint "IPIA-HRC - IMPORT PARITY SCOPE: COST vs OFFER/TRADER PRICE",
decisao aprovada pelo usuario: C - DUAL ARCHITECTURE (core = PPI_COST,
PPI_OFFER = camada analitica opcional). Motivo de revisao: MUDANCA
METODOLOGICA DELIBERADA (nao correcao de fonte) - a serie oficial passa a
usar PPI_COST (CIF+II+AFRMM+AD+D_porto+D_interno, SEM margem comercial)
em vez do PPI antigo (mesma soma x (1+margem)). Ver
docs/validation/ipia_hrc_import_parity_scope.md e
docs/adr/0015-ipia-hrc-import-parity-scope-cost-core-offer-layer.md.

Mesmo padrao de `scripts/migrar_hrc_import_policy_correction.py` (que por
sua vez seguiu `scripts/migrar_fx_convention_media_mensal.py`, ADR 0014):
roda UMA UNICA VEZ o recalculo COMPLETO da serie sob a formula corrigida
(`_ppi_cost_brl_t`/`custo_importacao_bottom_up_mensal`/
`agregar_ipia_hrc_multi_ncm_mensal`, ja editados nesta stage) SEM aplicar
`congelado_df` - excecao deliberada ao fluxo rotineiro de
`executar_pipeline_ipia_hrc` (que sempre congela o OFFICIAL da vintage
anterior), autorizada explicitamente para esta mudanca metodologica
(secao 12 da decisao aprovada: "Nao use o freeze normal para impedir a
revisao deliberadamente aprovada"). Nunca sobrescreve a vintage anterior
(permanece imutavel e byte-identical em
data/processed/vintages/ipia_hrc_v2/<vintage_id_antiga>/). Persiste uma
NOVA vintage via `indices_setoriais.salvar_vintage_ipia_hrc_v2` (mesmo
mecanismo append-only, ADR 0012) e so entao atualiza os LATEST
(ipia_hrc_v2_official.csv/provisional.csv) a partir da vintage recem-
persistida.

Faz chamadas de rede reais (Comex Stat, BCB/SGS, IBGE/SIDRA).

Uso:
    python scripts/migrar_ipia_hrc_cost_offer.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m

OUT_DIR = "data/processed/validation/ipia_hrc_cost_offer_migration"
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
    print(f"  methodology_version anterior: {vintage_anterior['manifest']['methodology_version']}")
    print(f"  OFFICIAL antigo: {len(oficial_antigo)} meses "
          f"({oficial_antigo['reference_period'].min():%Y-%m} a {oficial_antigo['reference_period'].max():%Y-%m})")
    print(f"  PROVISIONAL antigo: {len(provisional_antigo)} meses")

    secao("2. Buscando dado fresco (Comex Stat + BCB/SGS + IBGE/SIDRA) - rede real")
    fetch_at_utc: dict[str, str] = {}
    fetch_at_utc["comex_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    df_bruto = m._pipeline_comex_bruto_com_retry(ANO_INI, ANO_FIM)
    fetch_at_utc["bcb_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    # _pipeline_import_side_hrc -> agregar_ipia_hrc_multi_ncm_mensal ->
    # custo_importacao_bottom_up_mensal -> _ppi_cost_brl_t: PPI_COST
    # (sem margem) desde esta stage - nada a mudar aqui alem do que ja foi
    # editado em src/indices_setoriais.py.
    ppi_mensal_df = m._pipeline_import_side_hrc(df_bruto, ANO_INI, ANO_FIM)
    fetch_at_utc["pia_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    pia_anual = m.ibge_sidra_pia_hrc_anual()
    fetch_at_utc["ipp_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    ipp_mensal = m.ibge_sidra_ipp_siderurgia()
    pia_domestico_df = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia_anual, ipp_mensal=ipp_mensal)

    secao("3. Recalculando a serie COMPLETA sob PPI_COST - SEM congelado_df (deliberado, decisao aprovada)")
    serie_nova = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_mensal_df, pia_domestico_df=pia_domestico_df,
                                             congelado_df=None)
    oficial_novo, provisional_novo = m.separar_ipia_hrc_v2_oficial_provisional(serie_nova)
    print(f"  OFFICIAL novo: {len(oficial_novo)} meses")
    print(f"  PROVISIONAL novo: {len(provisional_novo)} meses")

    secao("3b. Sanity check - preco domestico nao deveria mudar (fora do escopo desta decisao)")
    dom_antigo = pd.concat([oficial_antigo, provisional_antigo], ignore_index=True) \
        .set_index("reference_period")["preco_domestico_rs_t"].sort_index()
    dom_novo = pd.concat([oficial_novo, provisional_novo], ignore_index=True) \
        .set_index("reference_period")["preco_domestico_rs_t"].sort_index()
    idx_dom_comum = dom_antigo.index.intersection(dom_novo.index)
    diff_dom = (dom_antigo.loc[idx_dom_comum] - dom_novo.loc[idx_dom_comum]).abs()
    meses_dom_mudou = diff_dom[diff_dom > 1e-6]
    if len(meses_dom_mudou) > 0:
        print(f"  [ATENCAO] preco_domestico_rs_t mudou em {len(meses_dom_mudou)} mes(es) fora desta decisao "
              f"(revisao de fonte upstream - IBGE/SIDRA - nao causada por esta migracao):")
        print(meses_dom_mudou.sort_values(ascending=False).head(10).to_string())
    else:
        print("  [OK] preco_domestico_rs_t identico ao da vintage anterior em todos os meses comuns - "
              "toda diferenca de PPI/IPIA abaixo vem exclusivamente da remocao da margem do core.")

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

    secao("6. Comparativo OLD (PPI_OFFER, margem 3%) vs NEW (PPI_COST, sem margem)")
    old_full = pd.concat([oficial_antigo, provisional_antigo], ignore_index=True) \
        .set_index("reference_period").sort_index()
    new_full = pd.concat([vintage_nova["official"], vintage_nova["provisional"]], ignore_index=True) \
        .set_index("reference_period").sort_index()
    idx_comum = old_full.index.intersection(new_full.index)

    comp = pd.DataFrame({
        "ppi_offer_old": old_full.loc[idx_comum, "ppi_rs_t"],  # PPI oficial da vintage anterior (pre-1.5) = Offer
        "ppi_cost_new": new_full.loc[idx_comum, "ppi_rs_t"],   # PPI oficial da vintage nova (1.5+) = Cost
        "ipia_old": old_full.loc[idx_comum, "ipia_hrc_v2"],
        "ipia_new": new_full.loc[idx_comum, "ipia_hrc_v2"],
        "old_status": old_full.loc[idx_comum, "publication_status"],
        "new_status": new_full.loc[idx_comum, "publication_status"],
    })
    comp["ppi_delta_pct"] = (comp["ppi_cost_new"] / comp["ppi_offer_old"] - 1) * 100.0
    comp["ipia_delta_pts"] = comp["ipia_new"] - comp["ipia_old"]
    comp["old_side_100"] = np.where(comp["ipia_old"].isna(), "N/A", np.where(comp["ipia_old"] > 100, ">100", "<=100"))
    comp["new_side_100"] = np.where(comp["ipia_new"].isna(), "N/A", np.where(comp["ipia_new"] > 100, ">100", "<=100"))
    comp["threshold_100_crossing"] = (
        ((comp["ipia_old"] > 100) & (comp["ipia_new"] <= 100))
        | ((comp["ipia_old"] <= 100) & (comp["ipia_new"] > 100)))

    validos = comp["ipia_old"].notna() & comp["ipia_new"].notna()
    c = comp[validos].copy()
    print(f"  meses comparaveis: {len(c)} de {len(idx_comum)}")
    print(f"  PPI delta%% - media={c['ppi_delta_pct'].mean():+.4f}  "
          f"min={c['ppi_delta_pct'].min():+.4f}  max={c['ppi_delta_pct'].max():+.4f}")
    print(f"  IPIA delta pts - media={c['ipia_delta_pts'].mean():+.4f}  "
          f"min={c['ipia_delta_pts'].min():+.4f}  max={c['ipia_delta_pts'].max():+.4f}")
    crossings = c[c["threshold_100_crossing"]]
    print(f"  threshold crossings (100): {len(crossings)}")
    if len(crossings):
        print(crossings[["ppi_offer_old", "ppi_cost_new", "ipia_old", "ipia_new",
                         "old_side_100", "new_side_100", "old_status", "new_status"]]
              .to_string(float_format=lambda v: f"{v:,.4f}"))
    print(f"  publication_status mudou (old_status != new_status): "
          f"{int((c['old_status'] != c['new_status']).sum())} mes(es) - esperado 0 (Sec.17 da decisao)")

    secao("7. MoM reversals (IPIA)")
    mom_old = old_full.loc[idx_comum, "ipia_hrc_v2"].diff()
    mom_new = new_full.loc[idx_comum, "ipia_hrc_v2"].diff()
    mom_validos = mom_old.notna() & mom_new.notna() & (mom_old != 0) & (mom_new != 0)
    reversoes = np.sign(mom_old[mom_validos]) != np.sign(mom_new[mom_validos])
    print(f"  MoM reversals: {int(reversoes.sum())} / {int(mom_validos.sum())}")
    if reversoes.any():
        datas_reversao = reversoes.index[reversoes]
        print(f"    meses: {datas_reversao.strftime('%Y-%m').tolist()}")
        print(f"    magnitude (old -> new, pontos):")
        for d in datas_reversao:
            print(f"      {d:%Y-%m}: mom_old={mom_old.loc[d]:+.4f}  mom_new={mom_new.loc[d]:+.4f}")

    secao("8. Valor corrente (mes mais recente calculavel, Cost vs Offer)")
    ultimo_mes_comum = c.index.max()
    ultimo = c.loc[ultimo_mes_comum]
    ppi_cost_atual = new_full.loc[ultimo_mes_comum, "ppi_rs_t"]
    ppi_offer_atual_3pct = new_full.loc[ultimo_mes_comum, "ppi_offer_rs_t"]
    preco_domestico_atual = new_full.loc[ultimo_mes_comum, "preco_domestico_rs_t"]
    ipia_cost_atual = new_full.loc[ultimo_mes_comum, "ipia_hrc_v2"]
    ipia_offer_atual = preco_domestico_atual / ppi_offer_atual_3pct * 100.0
    print(f"  mes de referencia: {ultimo_mes_comum:%Y-%m}")
    print(f"  PPI_COST (oficial, 1.5+):            R$ {ppi_cost_atual:,.2f}/t")
    print(f"  PPI_OFFER (analitico, margem 3%%):     R$ {ppi_offer_atual_3pct:,.2f}/t")
    print(f"  preco domestico:                     R$ {preco_domestico_atual:,.2f}/t")
    print(f"  IPIA_HRC (oficial, usa PPI_COST):    {ipia_cost_atual:.2f}")
    print(f"  IPIA equivalente se usasse PPI_OFFER: {ipia_offer_atual:.2f}")

    secao("9. Top 15 maiores |PPI delta%|")
    top15 = c.reindex(c["ppi_delta_pct"].abs().sort_values(ascending=False).index).head(15)
    print(top15[["ppi_offer_old", "ppi_cost_new", "ppi_delta_pct", "ipia_old", "ipia_new",
                 "ipia_delta_pts", "old_status", "new_status"]].to_string(float_format=lambda v: f"{v:,.4f}"))

    comp.insert(0, "label", "OLD_OFFER_VS_NEW_COST_IMPORT_PARITY_SCOPE")
    comp.insert(1, "revision_reason", "METHODOLOGICAL_SCOPE_DECISION_COST_CORE_OFFER_LAYER")
    caminho = f"{OUT_DIR}/cost_offer_migration_old_vs_new.csv"
    comp.to_csv(caminho)
    print(f"\n  escrito: {caminho}")

    secao("FIM")
    print(f"  vintage antiga (intacta, reproduzivel, PPI_OFFER/margem 3%%): {vintage_id_antiga}")
    print(f"  vintage nova (persistida, PPI_COST/sem margem):              {vintage_id_nova}")
    print("  Nenhum arquivo da vintage antiga foi sobrescrito.")


if __name__ == "__main__":
    main()
