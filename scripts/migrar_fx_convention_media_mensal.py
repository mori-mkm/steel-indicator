#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ADR 0014 - migracao da convencao cambial do PPI para media mensal
(FX Convention Sprint; decisao aprovada pelo usuario: MIGRATE TO MONTHLY
MEAN, ver docs/validation/fx_convention_validation.md).

Diferente de `scripts/gerar_ipia_hrc_v2_pia.py` (fluxo ROTINEIRO, que
sempre congela os meses OFFICIAL da vintage anterior via `congelado_df`
dentro de `executar_pipeline_ipia_hrc` - protecao correta contra revisao
SILENCIOSA de historico por uma atualizacao normal de fonte), este script
roda UMA UNICA VEZ, deliberadamente, o recalculo COMPLETO da serie sob a
nova regra de cambio (`calcular_fx_mensal`, ADR 0014) SEM aplicar
`congelado_df` - e exatamente a excecao que o proprio docstring de
`calcular_ipia_hrc_v2_pia` ja documentava como nao implementada
("nao resolve as duas excecoes futuras de revisao de fonte/mudanca
metodologica - decisao explicita de nao implementar isso ainda"). Este
script E essa excecao, feita uma vez, fora do fluxo rotineiro de
`executar_pipeline_ipia_hrc` - NAO modifica essa funcao nem o mecanismo
de congelamento em si, que continua protegendo corretamente contra
revisoes rotineiras dai em diante (agora com A VINTAGE PRODUZIDA AQUI
como nova base congelavel).

Nunca sobrescreve a vintage anterior (permanece imutavel em
data/processed/vintages/ipia_hrc_v2/<vintage_id_antiga>/, totalmente
reproduzivel). Persiste uma NOVA vintage via
`indices_setoriais.salvar_vintage_ipia_hrc_v2` (mesmo mecanismo append-
only de sempre, ADR 0012) e SO ENTAO sobrescreve os LATEST
(ipia_hrc_v2_official.csv/provisional.csv) a partir da vintage recem-
persistida - mesma garantia de `executar_pipeline_ipia_hrc`.

Faz chamadas de rede reais (Comex Stat, BCB/SGS, IBGE/SIDRA).

Uso:
    python scripts/migrar_fx_convention_media_mensal.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m

OUT_DIR = "data/processed/validation/fx_convention"
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
    # _pipeline_import_side_hrc -> agregar_ipia_hrc_multi_ncm_mensal ja usa
    # calcular_fx_mensal (ADR 0014) internamente - nada a mudar aqui.
    ppi_mensal_df = m._pipeline_import_side_hrc(df_bruto, ANO_INI, ANO_FIM)
    fetch_at_utc["pia_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    pia_anual = m.ibge_sidra_pia_hrc_anual()
    fetch_at_utc["ipp_fetch_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    ipp_mensal = m.ibge_sidra_ipp_siderurgia()
    pia_domestico_df = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia_anual, ipp_mensal=ipp_mensal)

    secao("3. Recalculando a serie COMPLETA sob a nova convencao - SEM congelado_df (deliberado)")
    serie_nova = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_mensal_df, pia_domestico_df=pia_domestico_df,
                                             congelado_df=None)
    oficial_novo, provisional_novo = m.separar_ipia_hrc_v2_oficial_provisional(serie_nova)
    print(f"  OFFICIAL novo: {len(oficial_novo)} meses")
    print(f"  PROVISIONAL novo: {len(provisional_novo)} meses")

    secao("3b. Sanity check - o lado domestico mudou por si so (revisao de fonte), fora do escopo do FX?")
    dom_antigo = pd.concat([oficial_antigo, provisional_antigo], ignore_index=True) \
        .set_index("reference_period")["preco_domestico_rs_t"].sort_index()
    dom_novo = pd.concat([oficial_novo, provisional_novo], ignore_index=True) \
        .set_index("reference_period")["preco_domestico_rs_t"].sort_index()
    idx_dom_comum = dom_antigo.index.intersection(dom_novo.index)
    diff_dom = (dom_antigo.loc[idx_dom_comum] - dom_novo.loc[idx_dom_comum]).abs()
    meses_dom_mudou = diff_dom[diff_dom > 1e-6]
    if len(meses_dom_mudou) > 0:
        print(f"  [ATENCAO] preco_domestico_rs_t mudou em {len(meses_dom_mudou)} mes(es) fora do FX "
              f"(revisao de fonte upstream - IBGE/SIDRA - nao causada por este script):")
        print(meses_dom_mudou.sort_values(ascending=False).head(10).to_string())
    else:
        print("  [OK] preco_domestico_rs_t identico ao da vintage anterior em todos os meses comuns - "
              "toda diferenca de IPIA abaixo vem exclusivamente do PPI/FX.")

    secao("4. Persistindo NOVA vintage (append-only - a anterior nao e tocada)")
    manifest = m.salvar_vintage_ipia_hrc_v2(
        serie_nova, import_side_df=ppi_mensal_df, domestic_price_df=pia_domestico_df,
        vintage_anterior=vintage_anterior, sources_fetch_at_utc=fetch_at_utc)
    vintage_id_nova = manifest["vintage_id"]
    print(f"  nova vintage: {vintage_id_nova}  (previous_vintage_id={vintage_id_antiga})")

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
        "ipia_old": old_full.loc[idx_comum, "ipia_hrc_v2"],
        "ipia_new": new_full.loc[idx_comum, "ipia_hrc_v2"],
        "old_status": old_full.loc[idx_comum, "publication_status"],
        "new_status": new_full.loc[idx_comum, "publication_status"],
    })
    comp["delta_pts"] = comp["ipia_new"] - comp["ipia_old"]
    comp["delta_pct"] = comp["delta_pts"] / comp["ipia_old"] * 100.0
    comp["interpretation_changed"] = (
        ((comp["ipia_old"] > 100) & (comp["ipia_new"] < 100))
        | ((comp["ipia_old"] < 100) & (comp["ipia_new"] > 100)))

    validos = comp["ipia_old"].notna() & comp["ipia_new"].notna()
    c = comp[validos]
    print(f"  meses comparaveis: {len(c)} de {len(idx_comum)}")
    print(f"  media Delta = {c['delta_pts'].mean():+.4f} pts   mediana = {c['delta_pts'].median():+.4f} pts")
    print(f"  max |Delta| = {c['delta_pts'].abs().max():.4f} pts em {c['delta_pts'].abs().idxmax():%Y-%m}")
    print(f"  threshold crossings (100): {int(c['interpretation_changed'].sum())}")
    print(f"  status mudou (old_status != new_status): {int((c['old_status'] != c['new_status']).sum())} mes(es)")

    mom_old = old_full.loc[idx_comum, "ipia_hrc_v2"].diff()
    mom_new = new_full.loc[idx_comum, "ipia_hrc_v2"].diff()
    mom_validos = mom_old.notna() & mom_new.notna() & (mom_old != 0) & (mom_new != 0)
    reversoes = np.sign(mom_old[mom_validos]) != np.sign(mom_new[mom_validos])
    print(f"  MoM reversals: {int(reversoes.sum())} / {int(mom_validos.sum())}")
    if reversoes.any():
        print(f"    meses: {reversoes.index[reversoes].strftime('%Y-%m').tolist()}")

    print("\n  Top 10 maiores |Delta| (pts):")
    top10 = c.reindex(c["delta_pts"].abs().sort_values(ascending=False).index).head(10)
    print(top10.to_string(float_format=lambda v: f"{v:,.4f}"))

    comp.insert(0, "label", "OLD_VS_NEW_FX_MONTHLY_MEAN_MIGRATION")
    caminho = f"{OUT_DIR}/fx_convention_migration_old_vs_new.csv"
    comp.to_csv(caminho)
    print(f"\n  escrito: {caminho}")

    secao("FIM")
    print(f"  vintage antiga (intacta, reproduzivel): {vintage_id_antiga}")
    print(f"  vintage nova (persistida):              {vintage_id_nova}")
    print("  Nenhum arquivo da vintage antiga foi sobrescrito.")


if __name__ == "__main__":
    main()
