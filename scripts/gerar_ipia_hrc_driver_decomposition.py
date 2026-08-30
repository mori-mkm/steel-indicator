#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sprint "IPIA-HRC - DRIVER DECOMPOSITION ENGINE" (Stage H1). Gera a
decomposicao de Shapley (`indices_setoriais.decompor_variacao_ipia_hrc`)
para toda a serie oficial/provisional ja publicada na ULTIMA vintage.

NAO altera PPI_COST, PPI_OFFER, IPIA, parametros, vintages ou
publication_status - carrega a vintage existente (nunca cria uma nova) e
so DERIVA um artefato analitico a partir dela. Faz chamadas de rede reais
(Comex Stat, BCB/SGS) SEPARADAS da vintage congelada, apenas para obter a
granularidade mes x NCM x pais necessaria para decompor FOB/frete/
seguro/FX/II/AFRMM/antidumping individualmente (a vintage persiste so o
PPI_COST/PPI_OFFER ja agregados por mes - mesmo padrao ja usado por
`scripts/validar_ipia_hrc_v2_final.py`/`scripts/migrar_ipia_hrc_cost_offer.py`).

Nunca chama `salvar_vintage_ipia_hrc_v2`/`vintage_store.criar_vintage` -
nenhuma vintage nova e criada por este script.

Uso:
    python scripts/gerar_ipia_hrc_driver_decomposition.py

Produz (gitignored):
    data/processed/validation/ipia_hrc_driver_decomposition/
        decomposicao_mensal.csv       (transicoes t-1 -> t, contribuicoes Shapley)
        componentes_mensais.csv       (NIVEIS absolutos por mes - composicao do
                                       PPI_COST, consumido por Reporting V3 pag.2)
        diagnostico_importacao_mensal.csv (composicao atipica FOB/frete/seguro,
                                       ADR 0018 - consumido por Reporting V3 pag.2
                                       e pelo scaffold de narrativa mensal)
        resumo_series.csv
        resumo_anual.csv
        threshold_crossings.csv
        cost_vs_offer_mes_atual.csv
"""
from __future__ import annotations
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m

OUT_DIR = "data/processed/validation/ipia_hrc_driver_decomposition"
ANO_INI, ANO_FIM = m._PIPELINE_ANO_INI_PADRAO, m._PIPELINE_ANO_FIM_PADRAO

_SCRIPT_DECOMPOR_MES = os.path.join(os.path.dirname(__file__), "validar_ipia_hrc_v2_final.py")
_spec = importlib.util.spec_from_file_location("validar_ipia_hrc_v2_final", _SCRIPT_DECOMPOR_MES)
_validar = importlib.util.module_from_spec(_spec)
sys.modules["validar_ipia_hrc_v2_final"] = _validar
_spec.loader.exec_module(_validar)
decompor_mes = _validar.decompor_mes


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


def _componentes_do_mes(dec: dict, preco_domestico_rs_t: float) -> dict:
    """Traduz a saida de `decompor_mes` (fob/frete/seguro em USD/t, cambio,
    ii_brl_t/afrmm_brl_t/antidumping_usd_t ja reconciliados) para o dict de
    drivers que `decompor_variacao_ipia_hrc` espera - `ii`/`afrmm` viram
    valores monetarios efetivos em USD/t (dividindo por `cambio_mes`), NAO
    aliquotas (ver docstring de `indices_setoriais._ppi_cost_de_drivers`
    para a prova de que essa reparametrizacao preserva reconstrucao exata)."""
    cambio_mes = dec["cambio_mes"]
    return {
        "domestic_price": preco_domestico_rs_t,
        "fob": dec["fob_usd_t"], "freight": dec["frete_usd_t"], "insurance": dec["seguro_usd_t"],
        "fx": cambio_mes,
        "ii": dec["ii_brl_t"] / cambio_mes, "afrmm": dec["afrmm_brl_t"] / cambio_mes,
        "antidumping": dec["antidumping_usd_t"],
        "d_porto": dec["despesas_porto_rs_t"], "d_interno": dec["frete_interno_rs_t"],
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    secao("1. Carregando a ULTIMA vintage persistida (nao cria nenhuma vintage nova)")
    vintage_id = m.ultima_vintage_ipia_hrc_v2()
    if vintage_id is None:
        raise RuntimeError("Nenhuma vintage encontrada - rode --ipia antes deste script.")
    vintage = m.carregar_vintage_ipia_hrc_v2(vintage_id)
    manifest = vintage["manifest"]
    print(f"  vintage: {vintage_id}  methodology_version: {manifest['methodology_version']}")
    serie = pd.concat([vintage["official"], vintage["provisional"]], ignore_index=True)
    serie = serie.sort_values("reference_period").reset_index(drop=True)
    calculavel = serie[serie["ipia_hrc_v2"].notna()].copy()
    print(f"  meses calculaveis (OFFICIAL+PROVISIONAL): {len(calculavel)} "
          f"({calculavel['reference_period'].min():%Y-%m} a {calculavel['reference_period'].max():%Y-%m})")

    secao("2. Buscando dado granular fresco (Comex Stat + BCB/SGS) - rede real, SEPARADA da vintage")
    df_bruto = m._pipeline_comex_bruto_com_retry(ANO_INI, ANO_FIM)
    datas = pd.to_datetime(df_bruto["year"].astype(str) + "-"
                           + df_bruto["monthNumber"].astype(str).str.zfill(2) + "-01")
    idx_mensal = pd.date_range(datas.min(), datas.max(), freq="MS")
    cambio = m.calcular_fx_mensal(m._pipeline_cambio_historico_seguro(ANO_INI, ANO_FIM), idx_mensal)
    p = m.ParamsIPIA()
    grupos = m.custo_importacao_bottom_up_mensal(df_bruto, cambio, p=p)
    print(f"  {len(grupos)} linhas (mes x NCM x pais)")

    secao("3. Decompondo componentes por mes calculavel (decompor_mes, reusado sem alteracao)")
    componentes_por_mes: dict[pd.Timestamp, dict] = {}
    for _, linha in calculavel.iterrows():
        data = linha["reference_period"]
        dec = decompor_mes(grupos, data, p, linha["import_status"])
        if dec is None:
            continue  # import_status calculavel na serie oficial mas grupos indisponiveis nesta busca fresca
        componentes_por_mes[data] = _componentes_do_mes(dec, linha["preco_domestico_rs_t"])
    print(f"  {len(componentes_por_mes)} meses com componentes granulares reconstruidos")

    secao("3b. Persistindo NIVEIS absolutos por mes (composicao do PPI_COST, Sec.11 do Reporting V3)")
    linhas_niveis = []
    for data, comp in componentes_por_mes.items():
        fx = comp["fx"]
        cif_brl_t = (comp["fob"] + comp["freight"] + comp["insurance"]) * fx
        ii_brl_t = comp["ii"] * fx
        afrmm_brl_t = comp["afrmm"] * fx
        antidumping_brl_t = comp["antidumping"] * fx
        ppi_cost_rs_t = m._ppi_cost_de_drivers(**{k: v for k, v in comp.items() if k != "domestic_price"})
        linhas_niveis.append({
            "reference_period": data, "vintage_id": vintage_id,
            "methodology_version": manifest["methodology_version"],
            "domestic_price_rs_t": comp["domestic_price"],
            "fob_usd_t": comp["fob"], "freight_usd_t": comp["freight"], "insurance_usd_t": comp["insurance"],
            "fx": fx, "cif_brl_t": cif_brl_t,
            "ii_brl_t": ii_brl_t, "afrmm_brl_t": afrmm_brl_t, "antidumping_brl_t": antidumping_brl_t,
            "d_porto_rs_t": comp["d_porto"], "d_interno_rs_t": comp["d_interno"],
            "ppi_cost_rs_t": ppi_cost_rs_t,
        })
    componentes_niveis = pd.DataFrame(linhas_niveis).sort_values("reference_period").reset_index(drop=True)
    caminho_niveis = f"{OUT_DIR}/componentes_mensais.csv"
    componentes_niveis.to_csv(caminho_niveis, index=False)
    print(f"  escrito: {caminho_niveis} ({len(componentes_niveis)} meses)")

    secao("3c. Diagnostico de composicao atipica na importacao (ADR 0018)")
    linhas_diagnostico = []
    for data in sorted(componentes_por_mes.keys()):
        diag = m.detectar_composicao_atipica_importacao(data, ANO_INI, ANO_FIM, df_bruto=df_bruto)
        linhas_diagnostico.append({
            "reference_period": data, "vintage_id": vintage_id,
            "methodology_version": manifest["methodology_version"],
            "status": diag["status"], "razao_volume": diag["razao_volume"],
            "volume_atual_t": diag["volume_atual_t"], "mediana_trailing_t": diag["mediana_trailing_t"],
            "n_meses_trailing": diag["n_meses_trailing"], "limiar": diag["limiar"],
            "top_pais": diag["top_pais"], "top_pais_pct": diag["top_pais_pct"],
            "top_pais_mes_anterior": diag["top_pais_mes_anterior"],
            "top_pais_pct_mes_anterior": diag["top_pais_pct_mes_anterior"],
            "motivos": " | ".join(diag["motivos"]),
        })
    diagnostico_importacao = pd.DataFrame(linhas_diagnostico).sort_values("reference_period").reset_index(drop=True)
    n_atipicos = (diagnostico_importacao["status"] == m.STATUS_COMPOSICAO_ATIPICO).sum()
    print(f"  {len(diagnostico_importacao)} meses avaliados, {n_atipicos} marcados '{m.STATUS_COMPOSICAO_ATIPICO}'")
    caminho_diagnostico = f"{OUT_DIR}/diagnostico_importacao_mensal.csv"
    diagnostico_importacao.to_csv(caminho_diagnostico, index=False)
    print(f"  escrito: {caminho_diagnostico}")

    secao("4. Decompondo transicoes MES-A-MES (t-1 -> t, so meses CALENDARIO consecutivos)")
    linhas_decomp = []
    datas_ordenadas = sorted(componentes_por_mes.keys())
    for data_t in datas_ordenadas:
        data_t_1 = data_t - pd.DateOffset(months=1)
        if data_t_1 not in componentes_por_mes:
            continue  # primeiro mes da serie, ou gap (mes UNKNOWN entre os dois) - sem decomposicao MoM
        r = m.decompor_variacao_ipia_hrc(componentes_por_mes[data_t_1], componentes_por_mes[data_t], modo="cost")
        linha = {
            "reference_period": data_t, "previous_reference_period": data_t_1,
            "vintage_id": vintage_id, "methodology_version": manifest["methodology_version"],
        }
        linha.update(r)
        linha["abs_contribution_share"] = str(r["abs_contribution_share"])  # dict -> string p/ CSV
        linhas_decomp.append(linha)
    decomposicao = pd.DataFrame(linhas_decomp).sort_values("reference_period").reset_index(drop=True)
    print(f"  {len(decomposicao)} transicoes decompostas")

    caminho_mensal = f"{OUT_DIR}/decomposicao_mensal.csv"
    decomposicao.to_csv(caminho_mensal, index=False)
    print(f"  escrito: {caminho_mensal}")

    secao("5. Resumo da serie completa (Sec.31)")
    residual_abs = decomposicao["residual"].abs()
    print(f"  N transicoes: {len(decomposicao)}")
    print(f"  residual maximo: {residual_abs.max():.2e}")
    print(f"  residual medio:  {residual_abs.mean():.2e}")
    print("\n  driver medio (pontos de IPIA, media sobre todas as transicoes):")
    for driver in m.DRIVERS_PPI_COST:
        print(f"    {driver:16s} {decomposicao[driver].mean():+.4f}")

    print("\n  top drivers por FREQUENCIA de dominancia (dominant_driver):")
    freq_dominante = decomposicao["dominant_driver"].value_counts()
    print(freq_dominante.to_string())

    print("\n  top drivers por CONTRIBUICAO ABSOLUTA MEDIA:")
    contrib_abs_media = decomposicao[list(m.DRIVERS_PPI_COST)].abs().mean().sort_values(ascending=False)
    print(contrib_abs_media.to_string())

    resumo_series = pd.DataFrame({
        "metric": ["n_transicoes", "residual_max", "residual_mean"],
        "value": [len(decomposicao), residual_abs.max(), residual_abs.mean()],
    })
    resumo_series.to_csv(f"{OUT_DIR}/resumo_series.csv", index=False)

    secao("6. Resumo por ano/regime (Sec.32) - mathematically dominant contribution, sem causalidade externa")
    decomposicao["ano"] = decomposicao["reference_period"].dt.year
    linhas_ano = []
    for ano, grupo in decomposicao.groupby("ano"):
        dominante_do_ano = grupo["dominant_driver"].value_counts()
        linhas_ano.append({
            "ano": ano, "n_transicoes": len(grupo),
            "driver_mais_frequente": dominante_do_ano.index[0] if len(dominante_do_ano) else None,
            "freq_driver_mais_frequente": int(dominante_do_ano.iloc[0]) if len(dominante_do_ano) else 0,
            "mean_delta_ipia": grupo["delta_ipia"].mean(),
        })
    resumo_anual = pd.DataFrame(linhas_ano)
    print(resumo_anual.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
    resumo_anual.to_csv(f"{OUT_DIR}/resumo_anual.csv", index=False)

    secao("7. Threshold crossings (100) - decomposicao de cada cruzamento (Sec.33)")
    serie_idx = calculavel.set_index("reference_period")["ipia_hrc_v2"]
    decomposicao_idx = decomposicao.set_index("reference_period")
    crossings = []
    for data_t in decomposicao_idx.index:
        data_t_1 = data_t - pd.DateOffset(months=1)
        if data_t_1 not in serie_idx.index or data_t not in serie_idx.index:
            continue
        antes, depois = serie_idx.loc[data_t_1], serie_idx.loc[data_t]
        if (antes > 100) != (depois > 100):
            linha = decomposicao_idx.loc[data_t].to_dict()
            linha["reference_period"] = data_t
            linha["ipia_antes"] = antes
            linha["ipia_depois"] = depois
            crossings.append(linha)
    if crossings:
        df_crossings = pd.DataFrame(crossings)
        cols_print = ["reference_period", "ipia_antes", "ipia_depois", "delta_ipia",
                     "top_positive_driver", "top_negative_driver", "dominant_driver", "residual"]
        print(df_crossings[cols_print].to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
        df_crossings.to_csv(f"{OUT_DIR}/threshold_crossings.csv", index=False)
    else:
        print("  nenhum cruzamento de threshold 100 encontrado nas transicoes decompostas")

    secao("8. Decomposicao do mes mais recente calculavel (Sec.14 da entrega)")
    ultima_data = datas_ordenadas[-1]
    penultima_data = ultima_data - pd.DateOffset(months=1)
    if penultima_data in componentes_por_mes:
        r_atual = m.decompor_variacao_ipia_hrc(
            componentes_por_mes[penultima_data], componentes_por_mes[ultima_data], modo="cost")
        print(f"  {penultima_data:%Y-%m} -> {ultima_data:%Y-%m}: delta_ipia={r_atual['delta_ipia']:+.4f} pts")
        for driver in m.DRIVERS_PPI_COST:
            nome_legivel = m.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC[driver]
            print(f"    {nome_legivel:24s} {r_atual[driver]:+.4f} pts")
        print(f"    {'Residual':24s} {r_atual['residual']:+.2e} pts")
        print(f"    dominant_driver: {r_atual['dominant_driver']} "
              f"({m.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC[r_atual['dominant_driver']]})")

    secao("9. Cost vs Offer - mesma transicao, margem so aparece no modo Offer (Sec.30)")
    if penultima_data in componentes_por_mes:
        comp_t_1_offer = dict(componentes_por_mes[penultima_data], margin=p.margem_importador)
        comp_t_offer = dict(componentes_por_mes[ultima_data], margin=p.margem_importador)
        r_offer = m.decompor_variacao_ipia_hrc(comp_t_1_offer, comp_t_offer, modo="offer")
        print(f"  modo=cost   delta_ipia={r_atual['delta_ipia']:+.4f}  'margin' in resultado: "
              f"{'margin' in r_atual}")
        print(f"  modo=offer  delta_ipia={r_offer['delta_ipia']:+.4f}  margin_contribution="
              f"{r_offer['margin']:+.4f}  (margem constante nesta transicao -> 0 esperado)")
        pd.DataFrame([
            {"modo": "cost", **{k: r_atual.get(k) for k in m.DRIVERS_PPI_OFFER}, "delta_ipia": r_atual["delta_ipia"]},
            {"modo": "offer", **{k: r_offer.get(k) for k in m.DRIVERS_PPI_OFFER}, "delta_ipia": r_offer["delta_ipia"]},
        ]).to_csv(f"{OUT_DIR}/cost_vs_offer_mes_atual.csv", index=False)

    secao("FIM")
    print(f"  Nenhuma vintage foi criada ou alterada - artefatos derivados em {OUT_DIR}/")


if __name__ == "__main__":
    main()
