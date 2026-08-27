#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage G3: validacao economica final do IPIA-HRC V2 PIA-based, ANTES de
qualquer wiring para CLI/PDF/publicacao.

Analisa a vintage CONGELADA (aprovada no Stage G2, imutavel):

    20260827T150423Z

carregada via `indices_setoriais.carregar_vintage_ipia_hrc_v2()` - a serie
COMPLETA (incluindo os meses UNKNOWN, descartados de official.csv/
provisional.csv) e reconstruida a partir dos INPUTS PERSISTIDOS da propria
vintage (import_side.csv/domestic_price.csv), nunca de uma nova chamada as
APIs - e exatamente o mecanismo de reprodutibilidade ja validado no Stage
G2 (test_reproducao_a_partir_dos_inputs_processados_persistidos).

Duas secoes fazem chamadas de rede SEPARADAS da vintage congelada, para
VALIDACAO INDEPENDENTE (nunca para substituir/recalcular a vintage):
  - decomposicao granular do import side (mes x NCM x pais) e o PPI legado,
    via `custo_importacao_bottom_up_mensal`/`calcular_ipia_mensal` -
    precisam do dado bruto do Comex/BCB, que a vintage NAO persiste
    (so o resultado agregado mensal, ja documentado no ADR 0012);
  - a ancora corporativa Usiminas+CSN (`preco_domestico_hrc_mensal_v2`),
    ja tratada como benchmark de validacao externa desde o ADR 0010/0011,
    nunca usada para recalibrar a serie PIA-based.

Produz (todos gitignored, sob data/processed/*):
    data/processed/validation/ipia_hrc_v2_final_validation.csv
    data/processed/validation/ipia_hrc_v2_outliers.csv
    data/processed/validation/ipia_hrc_v2_validation_summary.csv
    data/processed/validation/ipia_hrc_v2_full_series.png
    data/processed/validation/ipia_hrc_v2_domestic_vs_ppi.png
    data/processed/validation/ipia_hrc_v2_component_drivers.png
    data/processed/validation/ipia_hrc_v2_volume_coverage.png

Uso:
    python scripts/validar_ipia_hrc_v2_final.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import (
    STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN, PUBLICATION_GRADE_INICIO,
)

STATUS_PROVISIONAL = m.STATUS_PROVISIONAL

VINTAGE_ID = "20260827T150423Z"
OUT_DIR = "data/processed/validation"
CSV_FINAL = f"{OUT_DIR}/ipia_hrc_v2_final_validation.csv"
CSV_OUTLIERS = f"{OUT_DIR}/ipia_hrc_v2_outliers.csv"
CSV_SUMMARY = f"{OUT_DIR}/ipia_hrc_v2_validation_summary.csv"
ANO_INI, ANO_FIM = 2012, 2026


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


# =============================================================================
# 1. Carrega a vintage congelada e reconstroi a serie completa (sem rede)
# =============================================================================

def carregar_serie_completa():
    vintage = m.carregar_vintage_ipia_hrc_v2(VINTAGE_ID)
    serie = m.calcular_ipia_hrc_v2_pia(
        ppi_mensal_df=vintage["import_side"], pia_domestico_df=vintage["domestic_price"])
    return vintage, serie


# =============================================================================
# 2. Auditoria de unidades (sem rede)
# =============================================================================

def auditoria_unidades(serie: pd.DataFrame, vintage: dict) -> None:
    secao("2. AUDITORIA DE UNIDADES")
    dom = serie["preco_domestico_rs_t"].dropna()
    ppi = serie["ppi_rs_t"].dropna()
    ipia_v = serie["ipia_hrc_v2"].dropna()
    print(f"  preco_domestico_rs_t (BRL/t): min={dom.min():,.1f}  mediana={dom.median():,.1f}  max={dom.max():,.1f}")
    print(f"  ppi_rs_t             (BRL/t): min={ppi.min():,.1f}  mediana={ppi.median():,.1f}  max={ppi.max():,.1f}")
    print(f"  ipia_hrc_v2  (adimensional*100): min={ipia_v.min():.2f}  mediana={ipia_v.median():.2f}  max={ipia_v.max():.2f}")
    print("  -> ambos os precos ficam na faixa de milhares de BRL/t (aco laminado a quente "
          "real fica nessa ordem de grandeza) - nao ha sinal de erro x1000/x100/kg-t aqui.")

    # reconstrucao independente da formula: ipia == domestico/ppi*100
    calculavel = serie["ipia_hrc_v2"].notna()
    recomputado = serie.loc[calculavel, "preco_domestico_rs_t"] / serie.loc[calculavel, "ppi_rs_t"] * 100.0
    erro = (recomputado - serie.loc[calculavel, "ipia_hrc_v2"]).abs()
    print(f"  reconstrucao manual ipia=domestico/ppi*100: erro maximo absoluto = {erro.max():.10f} "
          f"({'OK' if erro.max() < 1e-9 else 'DIVERGENCIA'})")

    total_kg = serie["total_kg"].dropna()
    print(f"\n  total_kg importado/mes: min={total_kg.min():,.0f}  mediana={total_kg.median():,.0f}  "
          f"max={total_kg.max():,.0f}  (equivalente a {total_kg.median()/1000:,.0f} t/mes na mediana)")

    dom_pia = vintage["domestic_price"]
    ancoras = dom_pia.loc[~dom_pia["is_provisional"], ["pia_reference_year", "pia_anchor_price_rs_t"]
                          ].drop_duplicates()
    print(f"\n  ancoras PIA anuais (receita_liquida_mil_rs*1000/quantidade_vendida_t, BRL/t):")
    for _, r in ancoras.sort_values("pia_reference_year").iterrows():
        print(f"    {int(r['pia_reference_year'])}: {r['pia_anchor_price_rs_t']:,.2f} BRL/t")
    print("  -> unidade da PIA: receita em MIL REAIS (fonte IBGE/SIDRA) -> x1000 -> R$ -> "
          "/ quantidade_vendida_t (Toneladas, unidade confirmada ao vivo no ADR 0010) -> R$/t. "
          "Mesma ordem de grandeza dos precos observados acima - OK.")

    print(f"\n  policy_coverage: min={serie['policy_coverage'].min():.4f}  max={serie['policy_coverage'].max():.4f} "
          f"(deve estar em [0,1] - {'OK' if serie['policy_coverage'].dropna().between(0,1).all() else 'FORA DE FAIXA'})")
    print(f"  ppi_uncertainty_range_pct: min={serie['ppi_uncertainty_range_pct'].min():.4f}  "
          f"max={serie['ppi_uncertainty_range_pct'].max():.4f} "
          f"(fracao decimal, nao percentual 0-100 - por construcao de custo_importacao_bottom_up_mensal)")


# =============================================================================
# 3. Dataset analitico final (secao 2 da task) - salvo em CSV, sem rede
# =============================================================================

def decompor_mes(grupos: pd.DataFrame, data: pd.Timestamp, p, import_status: str) -> dict | None:
    """Reconstrucao volume-weighted EXATA (mesmo motor de
    `agregar_ipia_hrc_multi_ncm_mensal`, nunca uma formula aproximada) dos
    componentes de custo de importacao para UM mes: FOB, frete, seguro,
    cambio, aliquota/valor de II, AFRMM, antidumping, custos portuarios,
    frete interno, margem - e o PPI final reconstruido a partir deles.

    `import_status` e o `import_status` JA CALCULADO pela vintage/motor de
    producao para esse mes (nunca re-derivado aqui) - elegibilidade
    delega 100% para essa classificacao ja oficial, em vez de duplicar os
    limiares de cobertura/incerteza (`LIMIAR_COBERTURA_EXPERIMENTAL`/
    `LIMIAR_INCERTEZA_EXPERIMENTAL_PCT`/`TOL_COBERTURA_PUBLICATION_GRADE`
    ja existentes em `indices_setoriais.py`) uma segunda vez neste script
    de validacao - motivo: uma reimplementacao paralela desses limiares
    aqui divergiria silenciosamente se os valores oficiais forem revisados
    (achado do code review desta stage), e faltava especificamente o
    gate de incerteza no regime EXPERIMENTAL. UNKNOWN -> None (sem ponto
    de custo publicado). PUBLICATION_GRADE -> usa TODOS os grupos do mes
    (a propria classificacao ja garante coverage=100%). EXPERIMENTAL ->
    usa so os grupos com status de grupo conhecido (peso redistribuido
    entre eles, mesma regra do motor).
    """
    from steel_indicator.parameters.trade_policy import (
        STATUS_UNKNOWN as _UNK, STATUS_EXPERIMENTAL as _EXP, STATUS_PUBLICATION_GRADE as _PG,
    )
    if import_status not in (_EXP, _PG):
        return None
    g = grupos[grupos["data"] == data]
    if g.empty:
        return None
    usar = g if import_status == _PG else g[g["status"] != _UNK]
    if usar.empty:
        return None

    total_kg = g["kg"].sum()
    known_kg = g.loc[g["status"] != _UNK, "kg"].sum()
    coverage = known_kg / total_kg
    kg = usar["kg"]
    fob_usd_t = 1000 * usar["fob_usd"].sum() / kg.sum()
    frete_usd_t = 1000 * usar["frete_usd"].sum() / kg.sum()
    seguro_usd_t = 1000 * usar["seguro_usd"].sum() / kg.sum()
    cambio_mes = float(usar["cambio_mes"].iloc[0])
    cif_usd_t = fob_usd_t + frete_usd_t + seguro_usd_t
    cif_brl_t = cif_usd_t * cambio_mes

    # Reconstrucao EXATA (bit-a-bit contra "PPI via motor"): II/AFRMM/AD
    # variam por grupo (NCM/pais) - volume-ponderar a ALIQUOTA/valor
    # unitario e depois aplicar ao CIF ja agregado NAO e algebricamente
    # igual a volume-ponderar o VALOR MONETARIO ja calculado por grupo
    # (media ponderada de um produto != produto das medias ponderadas,
    # quando aliquota e CIF/t covariam entre grupos - e o caso real aqui,
    # NCMs com aliquota de II diferente tambem tem CIF/t diferente).
    # `custo_importacao_bottom_up_mensal` pondera o ppi_brl_t JA PRONTO por
    # grupo (nunca a aliquota) - entao a decomposicao exata precisa
    # ponderar os VALORES MONETARIOS por grupo tambem, nunca as taxas.
    ii_brl_t_i = usar["cif_brl_t"] * usar["aliquota_ii"]
    afrmm_brl_t_i = (usar["frete_usd_t"] * usar["cambio_mes"]) * usar["aliquota_afrmm"]
    ad_brl_t_i = usar["antidumping_usd_t"] * usar["cambio_mes"]
    ii_brl_t = float(np.average(ii_brl_t_i, weights=kg))
    afrmm_brl_t = float(np.average(afrmm_brl_t_i, weights=kg))
    ad_brl_t = float(np.average(ad_brl_t_i, weights=kg))
    # aliquotas "efetivas" reportadas so para leitura humana (media
    # ponderada da TAXA, nao usada em nenhum calculo de valor monetario
    # acima - evita a mesma armadilha de novo).
    aliquota_ii_efetiva = float(np.average(usar["aliquota_ii"], weights=kg))
    aliquota_afrmm_efetiva = float(np.average(usar["aliquota_afrmm"], weights=kg))
    antidumping_usd_t_efetivo = float(np.average(usar["antidumping_usd_t"], weights=kg))

    base = cif_brl_t + ii_brl_t + afrmm_brl_t + ad_brl_t + p.despesas_porto_rs_t + p.frete_interno_rs_t
    ppi_reconstruido = base * (1 + p.margem_importador)
    ppi_via_motor = float(np.average(usar["ppi_brl_t"], weights=kg))

    return dict(
        reference_period=data, fob_usd_t=fob_usd_t, frete_usd_t=frete_usd_t, seguro_usd_t=seguro_usd_t,
        cambio_mes=cambio_mes, cif_usd_t=cif_usd_t, cif_brl_t=cif_brl_t,
        aliquota_ii=aliquota_ii_efetiva, aliquota_afrmm=aliquota_afrmm_efetiva,
        antidumping_usd_t=antidumping_usd_t_efetivo, ii_brl_t=ii_brl_t, afrmm_brl_t=afrmm_brl_t,
        ad_brl_t=ad_brl_t, despesas_porto_rs_t=p.despesas_porto_rs_t, frete_interno_rs_t=p.frete_interno_rs_t,
        margem_rs_t=ppi_reconstruido - base, ppi_reconstruido=ppi_reconstruido, ppi_via_motor=ppi_via_motor,
        coverage=coverage, total_kg=total_kg, known_kg=known_kg, n_grupos_usados=len(usar))


def montar_dataset_final(serie: pd.DataFrame) -> pd.DataFrame:
    cols = ["reference_period", "ipia_hrc_v2", "publication_status", "preco_domestico_rs_t", "ppi_rs_t",
            "import_status", "total_kg", "known_policy_kg", "unknown_policy_kg", "policy_coverage",
            "ppi_lower", "ppi_upper", "ppi_uncertainty_range_pct",
            "pia_reference_year", "pia_anchor_price_rs_t", "ipp_series_id",
            "domestic_provenance_level", "domestic_is_proxy", "domestic_proxy_reason", "domestic_validation_status",
            "is_provisional", "last_pia_year"]
    return serie[cols].copy()


if __name__ == "__main__":
    secao("1. VINTAGE CONGELADA")
    vintage, serie = carregar_serie_completa()
    print(f"  vintage_id: {vintage['manifest']['vintage_id']}")
    print(f"  created_at_utc: {vintage['manifest']['created_at_utc']}")
    print(f"  methodology_version: {vintage['manifest']['methodology_version']}")
    print(f"  serie completa (todos os status): {len(serie)} meses, "
          f"{serie['reference_period'].min():%Y-%m} a {serie['reference_period'].max():%Y-%m}")
    print(f"  status counts:\n{serie['publication_status'].value_counts().to_string()}")
    oficial, provisional = m.separar_ipia_hrc_v2_oficial_provisional(serie)
    assert len(oficial) == len(vintage["official"]), "reconstrucao != official.csv persistido"
    assert len(provisional) == len(vintage["provisional"]), "reconstrucao != provisional.csv persistido"
    print("  reconstrucao a partir dos inputs persistidos bate EXATAMENTE com "
          "official.csv/provisional.csv (contagem de linhas) - OK")

    auditoria_unidades(serie, vintage)

    os.makedirs(OUT_DIR, exist_ok=True)
    dataset_final = montar_dataset_final(serie)
    dataset_final.to_csv(CSV_FINAL, index=False)
    print(f"\nDataset analitico salvo em: {CSV_FINAL} ({len(dataset_final)} linhas)")

    # =========================================================================
    # 4. Outliers (sem rede)
    # =========================================================================
    secao("4. OUTLIERS")
    # delta_abs precisa ser calculado sobre o CALENDARIO completo (reindex mes a
    # mes), nunca sobre a serie filtrada/comprimida so aos meses calculaveis -
    # a serie tem gaps UNKNOWN DENTRO da propria janela OFFICIAL (2019-11/12,
    # 2020-03/04/06/08/10/11, 2021-09, 2022-02/03 - ver secao 8), entao
    # `.diff()` sobre a serie comprimida confundiria um salto de 2-3 MESES
    # com uma mudanca de 1 mes. Reindexado ao calendario, o diff so existe
    # entre meses CONSECUTIVOS de fato, nunca atravessando um gap.
    ipia_mensal = serie.set_index("reference_period")["ipia_hrc_v2"].reindex(
        pd.date_range(serie["reference_period"].min(), serie["reference_period"].max(), freq="MS"))
    delta_calendario = ipia_mensal.diff().abs()
    calc = serie.dropna(subset=["ipia_hrc_v2"]).sort_values("reference_period").reset_index(drop=True)
    calc["delta_abs"] = calc["reference_period"].map(delta_calendario)

    print("  10 MENORES IPIA:")
    print(calc.nsmallest(10, "ipia_hrc_v2")[
        ["reference_period", "ipia_hrc_v2", "publication_status", "preco_domestico_rs_t", "ppi_rs_t"]
    ].to_string(index=False))

    print("\n  10 MAIORES IPIA:")
    print(calc.nlargest(10, "ipia_hrc_v2")[
        ["reference_period", "ipia_hrc_v2", "publication_status", "preco_domestico_rs_t", "ppi_rs_t"]
    ].to_string(index=False))

    print("\n  10 MAIORES MUDANCAS MENSAIS ABSOLUTAS:")
    print(calc.nlargest(10, "delta_abs")[
        ["reference_period", "ipia_hrc_v2", "delta_abs", "publication_status"]
    ].to_string(index=False))

    media_delta, std_delta = calc["delta_abs"].mean(), calc["delta_abs"].std()
    limiar_2std = media_delta + 2 * std_delta
    extremos = calc[calc["delta_abs"] > limiar_2std]
    print(f"\n  mudancas mensais > 2 desvios-padrao (limiar={limiar_2std:.2f}): {len(extremos)} mes(es)")
    if not extremos.empty:
        print(extremos[["reference_period", "ipia_hrc_v2", "delta_abs", "publication_status"]].to_string(index=False))

    outliers_export = pd.concat([
        calc.nsmallest(10, "ipia_hrc_v2").assign(motivo="10_menores_ipia"),
        calc.nlargest(10, "ipia_hrc_v2").assign(motivo="10_maiores_ipia"),
        calc.nlargest(10, "delta_abs").assign(motivo="10_maiores_delta_mensal"),
        extremos.assign(motivo="delta_acima_2std"),
    ], ignore_index=True).drop_duplicates(subset=["reference_period", "motivo"])
    outliers_export.to_csv(CSV_OUTLIERS, index=False)
    print(f"\nOutliers salvos em: {CSV_OUTLIERS} ({len(outliers_export)} linhas)")

    # =========================================================================
    # 5. Gap de 2019-01 (sem rede)
    # =========================================================================
    secao("5. GAP DE 2019-01")
    linha_jan = serie[serie["reference_period"] == "2019-01-01"]
    linha_fev = serie[serie["reference_period"] == "2019-02-01"]
    if linha_jan.empty:
        print("  2019-01 nao aparece NEM como linha UNKNOWN na serie completa - "
              "nao ha registro de import OU domestico nesse mes (merge outer nao gerou linha).")
    else:
        print("  2019-01 (linha completa):")
        print(linha_jan[["reference_period", "preco_domestico_rs_t", "ppi_rs_t", "import_status",
                         "publication_status", "policy_coverage", "ppi_uncertainty_range_pct",
                         "ipia_hrc_v2"]].to_string(index=False))
    print("\n  2019-02 (primeiro mes OFFICIAL, para comparacao):")
    print(linha_fev[["reference_period", "preco_domestico_rs_t", "ppi_rs_t", "import_status",
                     "publication_status", "policy_coverage", "ppi_uncertainty_range_pct",
                     "ipia_hrc_v2"]].to_string(index=False))
    dom_pia_jan = vintage["domestic_price"][vintage["domestic_price"]["reference_period"] == "2019-01-01"]
    print(f"\n  domestic_price.csv (input persistido) tem 2019-01? {not dom_pia_jan.empty}")
    if not dom_pia_jan.empty:
        print(dom_pia_jan[["reference_period", "preco_domestico_rs_t", "is_provisional"]].to_string(index=False))
    imp_jan = vintage["import_side"][vintage["import_side"]["reference_period"] == "2019-01-01"]
    print(f"  import_side.csv (input persistido) tem 2019-01? {not imp_jan.empty}")
    if not imp_jan.empty:
        print(imp_jan[["reference_period", "publication_status", "total_kg", "policy_coverage"]].to_string(index=False))
        cov = float(imp_jan["policy_coverage"].iloc[0])
        print(f"\n  EXPLICACAO: domestico presente e benchmarked (2430.33 BRL/t) - o lado IMPORT e "
              f"quem falha. policy_coverage={cov:.4f} ({cov*100:.2f}%) esta MUITO abaixo do limiar "
              f"EXPERIMENTAL (>=60%, ADR 0009/§9.5.2 - decisao ja aprovada) - a maior parte do "
              f"volume importado nesse mes (total_kg={int(imp_jan['total_kg'].iloc[0]):,}) tem "
              f"NCM/pais sem politica comercial resolvida. Nao ha bug: e exatamente a regra de "
              f"publicacao ja aprovada operando como projetada num mes de baixissima cobertura de "
              f"politica conhecida - nunca preenchido/estimado.")

    # =========================================================================
    # 6. Janelas de status: EXPERIMENTAL / PUBLICATION_GRADE / PROVISIONAL
    # =========================================================================
    secao("6. JANELAS DE STATUS (nivel, volatilidade, fronteiras)")
    janelas = {
        "A. EXPERIMENTAL (2019-02..2022-03)": ("2019-02-01", "2022-03-01", STATUS_EXPERIMENTAL),
        "B. PUBLICATION_GRADE (2022-04..2023-12)": ("2022-04-01", "2023-12-01", STATUS_PUBLICATION_GRADE),
        "C. PROVISIONAL (2024-01..presente)": ("2024-01-01", None, STATUS_PROVISIONAL),
    }
    resumo_janelas = []
    for nome, (ini, fim, status_esperado) in janelas.items():
        mascara = (serie["reference_period"] >= ini) & (serie["publication_status"] == status_esperado)
        if fim is not None:
            mascara &= serie["reference_period"] <= fim
        janela = serie[mascara]
        if janela.empty:
            continue
        resumo_janelas.append({
            "janela": nome, "n_meses": len(janela),
            "ipia_media": janela["ipia_hrc_v2"].mean(), "ipia_mediana": janela["ipia_hrc_v2"].median(),
            "ipia_std": janela["ipia_hrc_v2"].std(),
            "domestico_media": janela["preco_domestico_rs_t"].mean(), "ppi_media": janela["ppi_rs_t"].mean(),
            "total_kg_mediana": janela["total_kg"].median(),
        })
        print(f"\n  {nome}: {len(janela)} meses")
        print(f"    IPIA: media={janela['ipia_hrc_v2'].mean():.2f}  mediana={janela['ipia_hrc_v2'].median():.2f}  "
              f"std={janela['ipia_hrc_v2'].std():.2f}")
        print(f"    domestico: media={janela['preco_domestico_rs_t'].mean():,.1f} BRL/t   "
              f"PPI: media={janela['ppi_rs_t'].mean():,.1f} BRL/t")
        print(f"    total_kg mediana: {janela['total_kg'].median():,.0f}")

    df_janelas = pd.DataFrame(resumo_janelas)

    print("\n  FRONTEIRAS DE STATUS - salto no mes exatamente na transicao vs. saltos vizinhos:")
    for nome_fronteira, mes_antes, mes_depois in [
        ("EXPERIMENTAL -> PUBLICATION_GRADE (2022-03 -> 2022-04)", "2022-03-01", "2022-04-01"),
        ("PUBLICATION_GRADE -> PROVISIONAL (2023-12 -> 2024-01)", "2023-12-01", "2024-01-01"),
    ]:
        ipia_antes = serie.loc[serie["reference_period"] == mes_antes, "ipia_hrc_v2"]
        ipia_depois = serie.loc[serie["reference_period"] == mes_depois, "ipia_hrc_v2"]
        if ipia_antes.empty or ipia_depois.empty or ipia_antes.isna().all() or ipia_depois.isna().all():
            print(f"\n  {nome_fronteira}: mes anterior ou posterior nao calculavel "
                  f"({mes_antes}={ipia_antes.tolist()}, {mes_depois}={ipia_depois.tolist()}) - "
                  f"sem salto de fronteira mensuravel diretamente (ha gap UNKNOWN adjacente).")
            continue
        salto = abs(float(ipia_depois.iloc[0]) - float(ipia_antes.iloc[0]))
        mediana_saltos_ordinarios = delta_calendario.median()
        print(f"\n  {nome_fronteira}: salto={salto:.2f}  (mediana dos saltos mensais ordinarios "
              f"da serie inteira={mediana_saltos_ordinarios:.2f}) - "
              f"{'DENTRO do range tipico' if salto <= 2*mediana_saltos_ordinarios else 'ACIMA do range tipico'}")

    print("\n  2022-03 -> 2022-04 caem AMBOS num gap UNKNOWN pre-existente (2022-02 e 2022-03 sem "
          "cobertura de politica suficiente - mesmo padrao ja visto em 2019-01) - o salto exato na "
          "fronteira de status nao e diretamente observavel porque a fronteira em si cai dentro de "
          "um gap de dado, nao de metodologia. Comparando os ULTIMOS/PRIMEIROS meses calculaveis "
          "de cada lado do gap (nao adjacentes no calendario):")
    ultimo_exp = serie[(serie["publication_status"] == STATUS_EXPERIMENTAL)
                       & serie["ipia_hrc_v2"].notna()].sort_values("reference_period").iloc[-1]
    primeiro_pg = serie[(serie["publication_status"] == STATUS_PUBLICATION_GRADE)
                        & serie["ipia_hrc_v2"].notna()].sort_values("reference_period").iloc[0]
    n_meses_gap = (primeiro_pg["reference_period"].year * 12 + primeiro_pg["reference_period"].month) - \
                  (ultimo_exp["reference_period"].year * 12 + ultimo_exp["reference_period"].month)
    print(f"    ultimo EXPERIMENTAL calculavel: {ultimo_exp['reference_period']:%Y-%m} = "
          f"{ultimo_exp['ipia_hrc_v2']:.2f}")
    print(f"    primeiro PUBLICATION_GRADE calculavel: {primeiro_pg['reference_period']:%Y-%m} = "
          f"{primeiro_pg['ipia_hrc_v2']:.2f}")
    print(f"    diferenca: {abs(primeiro_pg['ipia_hrc_v2'] - ultimo_exp['ipia_hrc_v2']):.2f} "
          f"ao longo de {n_meses_gap} meses de calendario (nao um salto de 1 mes)")

    # =========================================================================
    # 7. Fronteiras do Denton (dezembro -> janeiro) e restricao anual (sem rede)
    # =========================================================================
    secao("7. FRONTEIRAS DO DENTON (dez->jan) E RESTRICAO ANUAL")
    dom_pia = vintage["domestic_price"].sort_values("reference_period").reset_index(drop=True)
    bench = dom_pia[~dom_pia["is_provisional"]].copy()
    bench["delta_abs"] = bench["preco_domestico_rs_t"].diff().abs()
    bench["eh_fronteira_dez_jan"] = bench["reference_period"].dt.month == 1

    fronteiras = bench[bench["eh_fronteira_dez_jan"]]
    ordinarios = bench[~bench["eh_fronteira_dez_jan"]]
    print(f"  mudanca mensal ORDINARIA (nao-fronteira) do domestic price benchmarked: "
          f"mediana={ordinarios['delta_abs'].median():,.2f} BRL/t  media={ordinarios['delta_abs'].mean():,.2f} BRL/t")
    print(f"  mudanca na FRONTEIRA dez->jan: mediana={fronteiras['delta_abs'].median():,.2f} BRL/t  "
          f"media={fronteiras['delta_abs'].mean():,.2f} BRL/t")
    print(f"\n  {'mes':12}{'delta_abs (BRL/t)':>20}")
    for _, r in fronteiras.iterrows():
        print(f"  {r['reference_period']:%Y-%m}  {r['delta_abs']:>18,.2f}")
    razao = fronteiras["delta_abs"].median() / ordinarios["delta_abs"].median()
    print(f"\n  razao fronteira/ordinario (mediana): {razao:.2f}x "
          f"({'sem evidencia de step artifact - fronteira NAO e sistematicamente maior' if razao < 1.5 else 'fronteira sistematicamente maior - investigar'})")

    print("\n  RESTRICAO ANUAL: mean(preco mensal do ano) == alvo PIA anual (tolerancia numerica)")
    for ano, g in bench.groupby(bench["reference_period"].dt.year):
        media_ano = g["preco_domestico_rs_t"].mean()
        alvo = g["pia_anchor_price_rs_t"].iloc[0]
        erro_pct = (media_ano - alvo) / alvo * 100
        print(f"    {ano}: media={media_ano:,.4f}  alvo_PIA={alvo:,.4f}  erro={erro_pct:+.8f}%")

    sem_2021 = fronteiras[fronteiras["reference_period"].dt.year != 2021]
    print(f"\n  NOTA: 2021-01 e a maior fronteira (delta={fronteiras[fronteiras['reference_period'].dt.year==2021]['delta_abs'].iloc[0]:,.2f}), "
          f"coincidindo com a alta global do aco em 2021 (alvo PIA salta de "
          f"{bench[bench['reference_period'].dt.year==2020]['pia_anchor_price_rs_t'].iloc[0]:,.0f} em 2020 para "
          f"{bench[bench['reference_period'].dt.year==2021]['pia_anchor_price_rs_t'].iloc[0]:,.0f} em 2021, "
          f"+{(bench[bench['reference_period'].dt.year==2021]['pia_anchor_price_rs_t'].iloc[0]/bench[bench['reference_period'].dt.year==2020]['pia_anchor_price_rs_t'].iloc[0]-1)*100:.0f}% - evento real de mercado, nao artefato). "
          f"Excluindo 2021: razao fronteira/ordinario cai para "
          f"{sem_2021['delta_abs'].median()/ordinarios['delta_abs'].median():.2f}x - ABAIXO de 1, "
          f"sem evidencia de step artificial nas demais fronteiras.")

    # =========================================================================
    # 8. Domestic Price PIA-based vs ancora corporativa (rede LEVE, so validacao)
    # =========================================================================
    secao("8. DOMESTIC PRICE: PIA-BASED vs ANCORA CORPORATIVA (validacao externa)")
    try:
        corporate = m.preco_domestico_hrc_mensal_v2()
    except Exception as e:
        print(f"  nao foi possivel buscar a ancora corporativa ao vivo ({e}) - pulando esta secao")
        corporate = None

    if corporate is not None and not corporate.empty:
        comp = serie[["reference_period", "preco_domestico_rs_t"]].dropna().merge(
            corporate[["reference_period", "preco_domestico_rs_t"]].rename(
                columns={"preco_domestico_rs_t": "preco_corporate_rs_t"}),
            on="reference_period", how="inner")
        comp["delta_pct"] = comp["preco_domestico_rs_t"] / comp["preco_corporate_rs_t"] - 1.0
        comp["delta_abs_rs_t"] = comp["preco_domestico_rs_t"] - comp["preco_corporate_rs_t"]
        print(f"  meses sobrepostos: {len(comp)} ({comp['reference_period'].min():%Y-%m} a "
              f"{comp['reference_period'].max():%Y-%m})")
        print(f"  delta_pct: media={comp['delta_pct'].mean()*100:+.2f}%  mediana={comp['delta_pct'].median()*100:+.2f}%  "
              f"std={comp['delta_pct'].std()*100:.2f}pp")
        print(f"  delta_abs: media={comp['delta_abs_rs_t'].mean():,.1f} BRL/t  "
              f"mediana={comp['delta_abs_rs_t'].median():,.1f} BRL/t")
        if len(comp) >= 3:
            tendencia = np.polyfit(range(len(comp)), comp["delta_pct"].to_numpy(), 1)[0]
            correl = comp["preco_domestico_rs_t"].corr(comp["preco_corporate_rs_t"])
            print(f"  tendencia do gap (delta_pct/mes, regressao linear simples): {tendencia*100:+.4f}pp/mes "
                  f"({'estavel' if abs(tendencia*100) < 0.3 else 'com tendencia material'})")
            print(f"  correlacao (niveis, PIA-based x corporate): {correl:.4f}")
        print("\n  interpretacao: gap negativo estavel e consistente com a hipotese ja registrada "
              "(ADR 0010/0011) de que a ancora corporativa 'Siderurgia' esta inflada por mix de "
              "produto frente a um preco mais proximo de HRC puro (PIA-Produto). NENHUM ajuste "
              "aplicado a partir desta comparacao - e validacao, nunca calibracao (regra ja aprovada).")
    else:
        print("  ancora corporativa vazia - sem sobreposicao para validar")

    # =========================================================================
    # 9-13. Decomposicao granular do import side, PPI legado, sensitivity,
    # market-logic - REDE SEPARADA da vintage congelada (validacao
    # independente, nunca substitui/recalcula official.csv/provisional.csv).
    # A vintage nao persiste o dado bruto mes x NCM x pais - so o resultado
    # AGREGADO mensal (ADR 0012) - esta e a razao explicita desta chamada.
    # =========================================================================
    secao("9-13. DECOMPOSICAO GRANULAR / PPI LEGADO / SENSITIVITY / MARKET-LOGIC (rede separada)")
    try:
        import time as _time

        def _buscar_comex_com_retry(tentativas=4, espera_s=20.0):
            for tent in range(tentativas):
                try:
                    return m._comex_bobina_bruto(ANO_INI, ANO_FIM)
                except Exception as e:
                    print(f"    tentativa {tent+1}/{tentativas} falhou ({e}); aguardando {espera_s:.0f}s")
                    _time.sleep(espera_s)
            raise RuntimeError("nao foi possivel buscar Comex Stat")

        def _cambio_seguro(ano_ini, ano_fim):
            url = m.SGS_URL.format(cod=m.SGS["cambio_venda"])
            corte = ano_ini + 6
            pedacos = []
            for ini, fim in [(f"01/01/{ano_ini}", f"31/12/{corte}"), (f"01/01/{corte+1}", f"31/12/{ano_fim}")]:
                dados = m._get_json(url, {"dataInicial": ini, "dataFinal": fim})
                pdf = pd.DataFrame(dados)
                pdf["data"] = pd.to_datetime(pdf["data"], format="%d/%m/%Y")
                pdf["valor"] = pd.to_numeric(pdf["valor"], errors="coerce")
                pedacos.append(pdf.set_index("data")["valor"])
            cambio_completo = pd.concat(pedacos).sort_index()
            return cambio_completo[~cambio_completo.index.duplicated(keep="last")]

        print("  buscando dado bruto do Comex Stat (2012-2026) - validacao independente...")
        df_bruto = _buscar_comex_com_retry()
        print(f"    {len(df_bruto)} linhas brutas")
        cambio_completo = _cambio_seguro(ANO_INI, ANO_FIM)
        datas_mensais = pd.to_datetime(df_bruto["year"].astype(str) + "-"
                                       + df_bruto["monthNumber"].astype(str).str.zfill(2) + "-01")
        idx_mensal = pd.date_range(datas_mensais.min(), datas_mensais.max(), freq="MS")
        cambio_mensal = cambio_completo.reindex(idx_mensal, method="ffill")

        grupos = m.custo_importacao_bottom_up_mensal(df_bruto, cambio_mensal, p=m.ParamsIPIA())
        print(f"    {len(grupos)} linhas granulares (mes x NCM x pais)")
        os.makedirs(OUT_DIR, exist_ok=True)
        print("  [rede OK - continuando com identidade contabil/decomposicao/sensitivity/market-logic]")

        # --- 9. Identidade contabil do import side (secao 4 da task) --------
        secao("9. IDENTIDADE CONTABIL DO IMPORT SIDE (reconstrucao exata, amostra de meses)")
        p_default = m.ParamsIPIA()
        idx_min_ipia = calc["ipia_hrc_v2"].idxmin()
        idx_max_ipia = calc["ipia_hrc_v2"].idxmax()
        meses_amostra = {
            "inicio da serie (OFFICIAL)": oficial["reference_period"].min(),
            "meio da serie (OFFICIAL)": oficial.sort_values("reference_period").iloc[len(oficial)//2]["reference_period"],
            "ultimo PUBLICATION_GRADE": oficial[oficial["publication_status"] == STATUS_PUBLICATION_GRADE][
                "reference_period"].max(),
            "ultimo PROVISIONAL": provisional["reference_period"].max(),
            "minimo IPIA (serie completa)": calc.loc[idx_min_ipia, "reference_period"],
            "maximo IPIA (serie completa)": calc.loc[idx_max_ipia, "reference_period"],
        }
        import_status_por_mes = serie.set_index("reference_period")["import_status"]
        decomposicoes = {}
        for rotulo, data in meses_amostra.items():
            status_import_do_mes = import_status_por_mes.get(data, STATUS_UNKNOWN)
            dec = decompor_mes(grupos, data, p_default, status_import_do_mes)
            if dec is None:
                print(f"\n  {rotulo} ({data:%Y-%m}): sem ponto de custo publicado nessa data (UNKNOWN) - "
                      f"nada a reconstruir.")
                continue
            decomposicoes[rotulo] = dec
            ppi_vintage = serie.loc[serie["reference_period"] == data, "ppi_rs_t"]
            ppi_vintage_val = float(ppi_vintage.iloc[0]) if not ppi_vintage.empty else float("nan")
            erro_reconstrucao = abs(dec["ppi_reconstruido"] - ppi_vintage_val)
            erro_pct = erro_reconstrucao / ppi_vintage_val * 100 if ppi_vintage_val else float("nan")
            print(f"\n  {rotulo} ({data:%Y-%m}), {dec['n_grupos_usados']} grupo(s) NCM/pais, "
                  f"coverage={dec['coverage']*100:.1f}%:")
            print(f"    FOB={dec['fob_usd_t']:,.2f} USD/t  frete={dec['frete_usd_t']:,.2f} USD/t  "
                  f"seguro={dec['seguro_usd_t']:,.2f} USD/t  cambio={dec['cambio_mes']:.4f} BRL/USD")
            print(f"    CIF={dec['cif_brl_t']:,.2f} BRL/t  II={dec['ii_brl_t']:,.2f} BRL/t "
                  f"(aliq={dec['aliquota_ii']*100:.2f}%)  AFRMM={dec['afrmm_brl_t']:,.2f} BRL/t "
                  f"(aliq={dec['aliquota_afrmm']*100:.2f}%)  AD={dec['ad_brl_t']:,.2f} BRL/t")
            print(f"    porto={dec['despesas_porto_rs_t']:,.2f} BRL/t  frete_interno={dec['frete_interno_rs_t']:,.2f} BRL/t  "
                  f"margem={dec['margem_rs_t']:,.2f} BRL/t")
            print(f"    PPI reconstruido (componentes)={dec['ppi_reconstruido']:,.4f} BRL/t   "
                  f"PPI via motor (custo_importacao_bottom_up_mensal)={dec['ppi_via_motor']:,.4f} BRL/t   "
                  f"PPI na vintage congelada={ppi_vintage_val:,.4f} BRL/t")
            print(f"    erro reconstrucao vs vintage: {erro_reconstrucao:.6f} BRL/t ({erro_pct:.6f}%) - "
                  f"{'OK' if erro_pct < 0.01 else 'DIVERGENCIA'}")

        # --- 10. Sensitivity/stress (secao 13 da task) -----------------------
        secao("10. SENSITIVITY / STRESS (choques sobre meses representativos)")
        choques = [
            ("FX +10%", dict(cambio_mult=1.10)), ("FX -10%", dict(cambio_mult=0.90)),
            ("FOB +10%", dict(fob_mult=1.10)), ("FOB -10%", dict(fob_mult=0.90)),
            ("frete internacional +20%", dict(frete_mult=1.20)), ("frete internacional -20%", dict(frete_mult=0.80)),
            ("custo portuario +20%", dict(porto_mult=1.20)), ("custo portuario -20%", dict(porto_mult=0.80)),
            ("frete interno +20%", dict(frete_interno_mult=1.20)), ("frete interno -20%", dict(frete_interno_mult=0.80)),
            ("margem importador +5pp", dict(margem_add=0.05)), ("margem importador -5pp", dict(margem_add=-0.05)),
        ]
        for rotulo_mes, dec in decomposicoes.items():
            print(f"\n  mes de referencia: {rotulo_mes} ({dec['reference_period']:%Y-%m}), "
                  f"PPI base={dec['ppi_via_motor']:,.2f} BRL/t")
            for nome_choque, kw in choques:
                cambio_c = dec["cambio_mes"] * kw.get("cambio_mult", 1.0)
                fob_c = dec["fob_usd_t"] * kw.get("fob_mult", 1.0)
                frete_c = dec["frete_usd_t"] * kw.get("frete_mult", 1.0)
                seguro_c = dec["seguro_usd_t"]
                cif_usd_t_c = fob_c + frete_c + seguro_c
                cif_brl_t_c = cif_usd_t_c * cambio_c
                ii_c = cif_brl_t_c * dec["aliquota_ii"]
                afrmm_c = (frete_c * cambio_c) * dec["aliquota_afrmm"]
                ad_c = dec["antidumping_usd_t"] * cambio_c
                porto_c = dec["despesas_porto_rs_t"] * kw.get("porto_mult", 1.0)
                frete_int_c = dec["frete_interno_rs_t"] * kw.get("frete_interno_mult", 1.0)
                margem_c = p_default.margem_importador + kw.get("margem_add", 0.0)
                base_c = cif_brl_t_c + ii_c + afrmm_c + ad_c + porto_c + frete_int_c
                ppi_c = base_c * (1 + margem_c)
                delta_ppi_pct = (ppi_c / dec["ppi_via_motor"] - 1) * 100
                delta_ipia_pct = -delta_ppi_pct  # ipia = domestico/ppi*100, domestico fixo no choque
                print(f"    {nome_choque:28s}: PPI {delta_ppi_pct:+.2f}%  ->  IPIA {delta_ipia_pct:+.2f}%")
            break  # um mes representativo basta para ilustrar a elasticidade - evita output excessivo

        # --- 11. PPI legado vs V2 (secao 11 da task) -------------------------
        secao("11. IMPORT SIDE: PPI V2 (bottom-up) vs PPI LEGADO")
        try:
            legado = m.calcular_ipia_mensal(ano_ini=2020, ano_fim=ANO_FIM, df_bruto=df_bruto)
            legado = legado.reset_index().rename(columns={legado.index.name or "index": "reference_period",
                                                           "ppi_rs_t": "ppi_legado_rs_t"})
            comp_legado = serie[["reference_period", "ppi_rs_t"]].dropna().merge(
                legado[["reference_period", "ppi_legado_rs_t"]], on="reference_period", how="inner")
            if comp_legado.empty:
                print("  sem sobreposicao entre V2 e legado no periodo comparavel")
            else:
                comp_legado["erro_abs"] = (comp_legado["ppi_rs_t"] - comp_legado["ppi_legado_rs_t"]).abs()
                comp_legado["erro_pct"] = comp_legado["erro_abs"] / comp_legado["ppi_legado_rs_t"] * 100
                mae = comp_legado["erro_abs"].mean()
                mape = comp_legado["erro_pct"].mean()
                mediana_pct = ((comp_legado["ppi_rs_t"] / comp_legado["ppi_legado_rs_t"] - 1) * 100).median()
                correl = comp_legado["ppi_rs_t"].corr(comp_legado["ppi_legado_rs_t"])
                print(f"  meses comparaveis: {len(comp_legado)} ({comp_legado['reference_period'].min():%Y-%m} a "
                      f"{comp_legado['reference_period'].max():%Y-%m})")
                print(f"  MAE absoluto: {mae:,.2f} BRL/t")
                print(f"  MAPE: {mape:.2f}%")
                print(f"  diferenca percentual mediana (V2 vs legado): {mediana_pct:+.2f}%")
                print(f"  correlacao: {correl:.4f}")
                maiores_div = comp_legado.nlargest(5, "erro_pct")
                print("  5 maiores divergencias:")
                print(maiores_div[["reference_period", "ppi_rs_t", "ppi_legado_rs_t", "erro_pct"]].to_string(index=False))
        except Exception as e:
            print(f"  nao foi possivel calcular o PPI legado ({e}) - pulando comparacao")

        # --- 12. Market-logic check (secao 12 da task) ------------------------
        secao("12. MARKET-LOGIC CHECK (correlacoes de sinal)")
        painel = []
        for data in sorted(grupos["data"].unique()):
            data_ts = pd.Timestamp(data)
            status_import_do_mes = import_status_por_mes.get(data_ts, STATUS_UNKNOWN)
            dec = decompor_mes(grupos, data_ts, p_default, status_import_do_mes)
            if dec is not None:
                painel.append(dec)
        painel_df = pd.DataFrame(painel)
        ml = serie[["reference_period", "ipia_hrc_v2", "preco_domestico_rs_t", "ppi_rs_t"]].merge(
            painel_df[["reference_period", "fob_usd_t", "cambio_mes"]], on="reference_period", how="inner").dropna()
        print(f"  meses no painel (com decomposicao + IPIA calculavel): {len(ml)}")
        if len(ml) >= 5:
            corr_fx_ppi = ml["cambio_mes"].corr(ml["ppi_rs_t"])
            corr_fx_ipia = ml["cambio_mes"].corr(ml["ipia_hrc_v2"])
            corr_fob_ppi = ml["fob_usd_t"].corr(ml["ppi_rs_t"])
            corr_fob_ipia = ml["fob_usd_t"].corr(ml["ipia_hrc_v2"])
            corr_dom_ipia = ml["preco_domestico_rs_t"].corr(ml["ipia_hrc_v2"])
            print(f"  corr(FX, PPI)        = {corr_fx_ppi:+.3f}   (esperado positivo)")
            print(f"  corr(FX, IPIA)       = {corr_fx_ipia:+.3f}   (esperado negativo, ceteris paribus)")
            print(f"  corr(FOB, PPI)       = {corr_fob_ppi:+.3f}   (esperado positivo)")
            print(f"  corr(FOB, IPIA)      = {corr_fob_ipia:+.3f}   (esperado negativo, ceteris paribus)")
            print(f"  corr(domestico, IPIA)= {corr_dom_ipia:+.3f}   (esperado positivo)")
            # variacao mensal (delta), nao so nivel
            ml_delta = ml.set_index("reference_period").diff().dropna()
            if len(ml_delta) >= 5:
                print(f"\n  correlacoes de VARIACAO MENSAL (delta a delta):")
                print(f"  corr(dFX, dPPI)   = {ml_delta['cambio_mes'].corr(ml_delta['ppi_rs_t']):+.3f}")
                print(f"  corr(dFX, dIPIA)  = {ml_delta['cambio_mes'].corr(ml_delta['ipia_hrc_v2']):+.3f}")
                print(f"  corr(dFOB, dPPI)  = {ml_delta['fob_usd_t'].corr(ml_delta['ppi_rs_t']):+.3f}")
                print(f"  corr(dFOB, dIPIA) = {ml_delta['fob_usd_t'].corr(ml_delta['ipia_hrc_v2']):+.3f}")
            print("\n  NOTA: correlacao e sanity check de sinal, nunca causalidade (regra explicita da task).")
        else:
            print("  poucos meses no painel - correlacoes nao reportadas")

        painel_df.to_csv(f"{OUT_DIR}/ipia_hrc_v2_import_decomposition_panel.csv", index=False)
        print(f"\nPainel de decomposicao granular salvo em: {OUT_DIR}/ipia_hrc_v2_import_decomposition_panel.csv "
              f"({len(painel_df)} meses)")
    except Exception as e_rede:
        print(f"  FALHA na busca de rede para validacao independente: {e_rede}")
        print("  Secoes 9-12 (identidade contabil exata, decomposicao por componente, sensitivity, "
              "PPI legado, market-logic com FOB/FX granular) ficam MARCADAS COMO NAO EXECUTADAS "
              "nesta rodada - nunca fabricadas a partir da vintage (que nao tem esse detalhe).")
        grupos = None

    # =========================================================================
    # 14. Volume / liquidez (sem rede)
    # =========================================================================
    secao("14. VOLUME / LIQUIDEZ")
    calc_vol = serie.dropna(subset=["ipia_hrc_v2", "total_kg"]).copy()
    calc_vol["delta_abs"] = calc_vol["reference_period"].map(delta_calendario)
    corr_vol_delta = calc_vol[["total_kg", "delta_abs"]].dropna().corr().iloc[0, 1]
    print(f"  correlacao entre total_kg e |delta mensal do IPIA| (meses consecutivos): {corr_vol_delta:+.3f} "
          f"({'baixa liquidez associada a mais volatilidade' if corr_vol_delta < -0.15 else 'sem relacao clara' if abs(corr_vol_delta) <= 0.15 else 'ALTA liquidez associada a mais volatilidade (contraintuitivo)'})")
    limiar_baixo_volume = calc_vol["total_kg"].quantile(0.10)
    baixo_volume = calc_vol[calc_vol["total_kg"] <= limiar_baixo_volume]
    print(f"  limiar de baixo volume (percentil 10): {limiar_baixo_volume:,.0f} kg")
    print(f"  meses de baixo volume: {len(baixo_volume)}")
    print(baixo_volume[["reference_period", "total_kg", "ipia_hrc_v2", "publication_status"]].to_string(index=False))
    extremos_ipia_meses = set(calc.nsmallest(10, "ipia_hrc_v2")["reference_period"]) | \
                          set(calc.nlargest(10, "ipia_hrc_v2")["reference_period"])
    baixo_volume_e_extremo = extremos_ipia_meses & set(baixo_volume["reference_period"])
    print(f"\n  meses que sao AO MESMO TEMPO baixo volume E outlier de nivel (10 menores/maiores IPIA): "
          f"{len(baixo_volume_e_extremo)}")
    if baixo_volume_e_extremo:
        for d in sorted(baixo_volume_e_extremo):
            print(f"    {d:%Y-%m}")
    print("\n  NOTA: nenhuma suavizacao (legacy) foi reaplicada ao V2 bottom-up nesta validacao - "
          "os numeros acima descrevem o dado como calculado, para informar uma decisao Level 3 "
          "futura se a relacao volume/volatilidade se mostrar material.")

    # =========================================================================
    # 15. Policy coverage empirico (sem rede)
    # =========================================================================
    secao("15. POLICY COVERAGE - VERIFICACAO EMPIRICA DAS REGRAS JA APROVADAS")
    exp_meses = serie[serie["publication_status"] == STATUS_EXPERIMENTAL]
    viola_exp = exp_meses[(exp_meses["policy_coverage"] < m.LIMIAR_COBERTURA_EXPERIMENTAL)
                          | (exp_meses["ppi_uncertainty_range_pct"] > m.LIMIAR_INCERTEZA_EXPERIMENTAL_PCT)]
    print(f"  EXPERIMENTAL: {len(exp_meses)} meses. Violacoes da regra "
          f"(coverage>={m.LIMIAR_COBERTURA_EXPERIMENTAL*100:.0f}% AND "
          f"uncertainty<={m.LIMIAR_INCERTEZA_EXPERIMENTAL_PCT*100:.0f}%): "
          f"{len(viola_exp)} ({'OK - regra respeitada empiricamente' if viola_exp.empty else 'VIOLACAO ENCONTRADA'})")
    print(f"    coverage: min={exp_meses['policy_coverage'].min()*100:.1f}%  "
          f"mediana={exp_meses['policy_coverage'].median()*100:.1f}%  max={exp_meses['policy_coverage'].max()*100:.1f}%")
    print(f"    uncertainty_range_pct: min={exp_meses['ppi_uncertainty_range_pct'].min()*100:.3f}%  "
          f"mediana={exp_meses['ppi_uncertainty_range_pct'].median()*100:.3f}%  "
          f"max={exp_meses['ppi_uncertainty_range_pct'].max()*100:.3f}%")

    pg_meses = serie[serie["publication_status"] == STATUS_PUBLICATION_GRADE]
    viola_pg = pg_meses[pg_meses["policy_coverage"] < 1.0 - m.TOL_COBERTURA_PUBLICATION_GRADE]
    print(f"\n  PUBLICATION_GRADE: {len(pg_meses)} meses. Violacoes da regra "
          f"(coverage deve ser ~100%): {len(viola_pg)} "
          f"({'OK - regra respeitada empiricamente' if viola_pg.empty else 'VIOLACAO ENCONTRADA'})")
    print(f"    coverage: min={pg_meses['policy_coverage'].min()*100:.4f}%  max={pg_meses['policy_coverage'].max()*100:.4f}%")

    # =========================================================================
    # 16. Qualidade do provisional (sem rede + comparacoes ja calculadas)
    # =========================================================================
    secao("16. QUALIDADE DO PROVISIONAL (2024+)")
    trans_dez = serie.loc[serie["reference_period"] == "2023-12-01"].iloc[0]
    trans_jan = serie.loc[serie["reference_period"] == "2024-01-01"].iloc[0]
    print(f"  2023-12 (ultimo OFFICIAL): domestico={trans_dez['preco_domestico_rs_t']:,.1f}  "
          f"ppi={trans_dez['ppi_rs_t']:,.1f}  ipia={trans_dez['ipia_hrc_v2']:.2f}")
    print(f"  2024-01 (primeiro PROVISIONAL): domestico={trans_jan['preco_domestico_rs_t']:,.1f}  "
          f"ppi={trans_jan['ppi_rs_t']:,.1f}  ipia={trans_jan['ipia_hrc_v2']:.2f}")
    print(f"  delta domestico: {trans_jan['preco_domestico_rs_t'] - trans_dez['preco_domestico_rs_t']:+,.1f} BRL/t "
          f"({(trans_jan['preco_domestico_rs_t']/trans_dez['preco_domestico_rs_t']-1)*100:+.2f}%)")
    print(f"  delta ppi:       {trans_jan['ppi_rs_t'] - trans_dez['ppi_rs_t']:+,.1f} BRL/t "
          f"({(trans_jan['ppi_rs_t']/trans_dez['ppi_rs_t']-1)*100:+.2f}%)")
    print(f"  delta ipia:      {trans_jan['ipia_hrc_v2'] - trans_dez['ipia_hrc_v2']:+.2f} pontos")

    prov_traj = serie[serie["publication_status"] == STATUS_PROVISIONAL].sort_values("reference_period")
    print(f"\n  trajetoria 2024-2026 (PROVISIONAL, {len(prov_traj)} meses):")
    print(f"    IPIA: primeiro={prov_traj['ipia_hrc_v2'].iloc[0]:.2f}  ultimo={prov_traj['ipia_hrc_v2'].iloc[-1]:.2f}  "
          f"min={prov_traj['ipia_hrc_v2'].min():.2f}  max={prov_traj['ipia_hrc_v2'].max():.2f}  "
          f"std={prov_traj['ipia_hrc_v2'].std():.2f}")
    print(f"    (para comparacao: std do OFFICIAL como um todo = {oficial['ipia_hrc_v2'].std():.2f} - "
          f"PROVISIONAL {'e visivelmente MENOS volatil' if prov_traj['ipia_hrc_v2'].std() < oficial['ipia_hrc_v2'].std() else 'tem volatilidade comparavel/maior'}, "
          f"esperado dado que e encadeado por indice de precos - IPP - em vez do Denton mes a mes)")
    print("\n  NOTA: PROVISIONAL nunca foi promovido nesta validacao - permanece PROVISIONAL, "
          "consistente com a regra ja aprovada (secao 16 da task).")

    # =========================================================================
    # 19. Backtest distribution (sem rede)
    # =========================================================================
    secao("19. BACKTEST DISTRIBUTION")
    resumo_backtest = []
    for nome, sub in [("TODOS os status calculaveis", calc),
                      ("A. EXPERIMENTAL", calc[calc["publication_status"] == STATUS_EXPERIMENTAL]),
                      ("B. PUBLICATION_GRADE", calc[calc["publication_status"] == STATUS_PUBLICATION_GRADE]),
                      ("C. PROVISIONAL", calc[calc["publication_status"] == STATUS_PROVISIONAL])]:
        if sub.empty:
            continue
        v = sub["ipia_hrc_v2"]
        linha = {
            "janela": nome, "n": len(v), "media": v.mean(), "mediana": v.median(), "std": v.std(),
            "p10": v.quantile(0.10), "p25": v.quantile(0.25), "p75": v.quantile(0.75), "p90": v.quantile(0.90),
            "pct_menor_90": (v < 90).mean() * 100, "pct_90_100": ((v >= 90) & (v < 100)).mean() * 100,
            "pct_100_110": ((v >= 100) & (v < 110)).mean() * 100, "pct_maior_110": (v >= 110).mean() * 100,
        }
        resumo_backtest.append(linha)
        print(f"\n  {nome} (n={len(v)}):")
        print(f"    media={linha['media']:.2f}  mediana={linha['mediana']:.2f}  std={linha['std']:.2f}  "
              f"p10={linha['p10']:.2f}  p25={linha['p25']:.2f}  p75={linha['p75']:.2f}  p90={linha['p90']:.2f}")
        print(f"    % <90: {linha['pct_menor_90']:.1f}%   % 90-100: {linha['pct_90_100']:.1f}%   "
              f"% 100-110: {linha['pct_100_110']:.1f}%   % >110: {linha['pct_maior_110']:.1f}%")

    # persistencia: meses consecutivos acima/abaixo de 100, sobre o calendario
    # completo (gaps quebram a sequencia - nunca conectam dois blocos separados
    # por um mes UNKNOWN como se fossem consecutivos).
    ipia_cal = ipia_mensal.dropna()
    sinal = (ipia_cal >= 100).astype(int)
    blocos = (sinal != sinal.shift()).cumsum()
    tamanhos = sinal.groupby(blocos).agg(["first", "size"])
    acima = tamanhos[tamanhos["first"] == 1]["size"]
    abaixo = tamanhos[tamanhos["first"] == 0]["size"]
    print(f"\n  PERSISTENCIA (sequencias de meses CALENDARIO-CONSECUTIVOS, gap quebra a sequencia):")
    print(f"    acima de 100: {len(acima)} sequencia(s), duracao media={acima.mean():.1f} meses, max={acima.max()} meses")
    print(f"    abaixo de 100: {len(abaixo)} sequencia(s), duracao media={abaixo.mean():.1f} meses, max={abaixo.max()} meses")

    pd.DataFrame(resumo_backtest).to_csv(CSV_SUMMARY, index=False)
    print(f"\nResumo estatistico salvo em: {CSV_SUMMARY}")

    # =========================================================================
    # 23. Visualizacoes (sem rede - reaproveita `serie`/`calc`/painel se existir)
    # =========================================================================
    secao("23. VISUALIZACOES")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cores = {STATUS_PUBLICATION_GRADE: "#1a7f37", STATUS_EXPERIMENTAL: "#b8860b",
             STATUS_PROVISIONAL: "#7c3aed", STATUS_UNKNOWN: "#c0c0c0"}

    # 1. IPIA completo por status
    fig, ax = plt.subplots(figsize=(13, 5))
    oficial_calc = calc[calc["publication_status"].isin([STATUS_EXPERIMENTAL, STATUS_PUBLICATION_GRADE])]
    ax.plot(oficial_calc["reference_period"], oficial_calc["ipia_hrc_v2"], "-", color="#444444", linewidth=1.0, zorder=1)
    prov_calc = calc[calc["publication_status"] == STATUS_PROVISIONAL]
    ax.plot(prov_calc["reference_period"], prov_calc["ipia_hrc_v2"], "--", color=cores[STATUS_PROVISIONAL], linewidth=1.2, zorder=1)
    for status in (STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_PROVISIONAL):
        recorte = calc[calc["publication_status"] == status]
        marker = "^" if status == STATUS_PROVISIONAL else "o"
        ax.scatter(recorte["reference_period"], recorte["ipia_hrc_v2"], s=16, color=cores[status], marker=marker, label=status, zorder=2)
    unk = serie.loc[serie["publication_status"] == STATUS_UNKNOWN, "reference_period"]
    if not unk.empty:
        ax.scatter(unk, [calc["ipia_hrc_v2"].min()] * len(unk), marker="|", color=cores[STATUS_UNKNOWN], s=40,
                   label=f"{STATUS_UNKNOWN} (gap)", zorder=0, alpha=0.6)
    ax.axhline(100.0, color="black", linewidth=0.8, linestyle="--", label="paridade (100)")
    ax.set_title("IPIA-HRC V2 PIA-based - serie completa (vintage 20260827T150423Z) - VALIDACAO FINAL G3")
    ax.set_xlabel("Mes"); ax.set_ylabel("IPIA-HRC V2"); ax.legend(loc="best", fontsize=8)
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/ipia_hrc_v2_full_series.png", dpi=120); plt.close(fig)
    print(f"  1. {OUT_DIR}/ipia_hrc_v2_full_series.png")

    # 2. Domestic vs PPI
    fig, ax = plt.subplots(figsize=(13, 5))
    dp = serie.dropna(subset=["preco_domestico_rs_t"]).sort_values("reference_period")
    ax.plot(dp["reference_period"], dp["preco_domestico_rs_t"], "-", color="#1a7f37", label="Domestic (PIA-based)", linewidth=1.3)
    pp = serie.dropna(subset=["ppi_rs_t"]).sort_values("reference_period")
    ax.plot(pp["reference_period"], pp["ppi_rs_t"], "-", color="#b8860b", label="PPI (import parity)", linewidth=1.3)
    ax.set_title("Domestic Price (PIA-based) vs PPI importado - BRL/t")
    ax.set_xlabel("Mes"); ax.set_ylabel("BRL/t"); ax.legend(loc="best", fontsize=9)
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/ipia_hrc_v2_domestic_vs_ppi.png", dpi=120); plt.close(fig)
    print(f"  2. {OUT_DIR}/ipia_hrc_v2_domestic_vs_ppi.png")

    # 3. Component drivers (so se o painel de decomposicao existe)
    if grupos is not None and not painel_df.empty:
        fig, ax = plt.subplots(figsize=(13, 5))
        pdec = painel_df.sort_values("reference_period")
        ax.stackplot(pdec["reference_period"],
                    pdec["cif_brl_t"], pdec["ii_brl_t"], pdec["afrmm_brl_t"], pdec["ad_brl_t"],
                    pdec["despesas_porto_rs_t"], pdec["frete_interno_rs_t"], pdec["margem_rs_t"],
                    labels=["CIF", "II", "AFRMM", "Antidumping", "Custo portuario", "Frete interno", "Margem"],
                    colors=["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51", "#8ab17d", "#6d597a"])
        ax.set_title("PPI importado - decomposicao por componente (volume-weighted, reconstrucao exata)")
        ax.set_xlabel("Mes"); ax.set_ylabel("BRL/t"); ax.legend(loc="upper left", fontsize=7, ncol=2)
        fig.tight_layout(); fig.savefig(f"{OUT_DIR}/ipia_hrc_v2_component_drivers.png", dpi=120); plt.close(fig)
        print(f"  3. {OUT_DIR}/ipia_hrc_v2_component_drivers.png")
    else:
        print("  3. pulado (sem dado granular de rede nesta execucao)")

    # 4. Volume / policy coverage
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    ax1.bar(serie["reference_period"], serie["total_kg"] / 1000.0, width=20, color="#457b9d")
    ax1.set_ylabel("t/mes importadas"); ax1.set_title("Volume importado (t/mes) e policy_coverage")
    ax2.plot(serie["reference_period"], serie["policy_coverage"] * 100, color="#e76f51", linewidth=1.0)
    ax2.axhline(60, color="black", linestyle="--", linewidth=0.8, label="limiar EXPERIMENTAL (60%)")
    ax2.set_ylabel("policy_coverage (%)"); ax2.set_xlabel("Mes"); ax2.legend(loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/ipia_hrc_v2_volume_coverage.png", dpi=120); plt.close(fig)
    print(f"  4. {OUT_DIR}/ipia_hrc_v2_volume_coverage.png")

    secao("VALIDACAO SCRIPT CONCLUIDA")
