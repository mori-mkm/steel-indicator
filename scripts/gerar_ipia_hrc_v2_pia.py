#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage E11/G2/G5: gera a serie IPIA-HRC PIA-based e persiste cada
execucao como uma vintage append-only/imutavel, chamando a orquestracao
CANONICA `indices_setoriais.executar_pipeline_ipia_hrc()` (Stage G5) - o
MESMO caminho que a CLI oficial (`python src/indices_setoriais.py --ipia`)
usa. Este script nao reimplementa fetch, freeze, calculo, separacao
oficial/provisional nem persistencia de vintage - so orquestra a chamada e
adiciona relatorios/artefatos ANALITICOS extras (grafico de validacao,
comparacao com a ancora corporativa) que nao fazem parte do contrato de
publicacao em si.

NAO e codigo de producao/publicacao por conta propria - e um consumidor do
mesmo pipeline que a CLI usa, com extras de validacao. Nao altera
`--selftest`, `report_builder.py` nem nenhum caminho legado.

Fluxo normal (Stage G2/G5): se ja existir uma vintage anterior, o
pipeline canonico carrega automaticamente o official.csv dela e usa como
`congelado_df` - meses ja publicados como oficiais permanecem congelados.
A PRIMEIRA execucao (sem vintage anterior) roda sem congelado_df.

Uso:
    python scripts/gerar_ipia_hrc_v2_pia.py

Produz:
    data/processed/ipia_hrc_v2_official.csv       (LATEST - sobrescrito a cada execucao)
    data/processed/ipia_hrc_v2_provisional.csv    (LATEST - sobrescrito a cada execucao)
    data/processed/ipia_hrc_v2_pia_validation.png (LATEST - sobrescrito a cada execucao)
    data/processed/vintages/ipia_hrc_v2/<vintage_id>/  (IMUTAVEL - nunca sobrescrito)

Faz chamadas de rede reais (Comex Stat, BCB/SGS, IBGE/SIDRA).
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import (
    STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN,
)

STATUS_PROVISIONAL = m.STATUS_PROVISIONAL

PNG_SAIDA = "data/processed/ipia_hrc_v2_pia_validation.png"


def reportar_oficial(oficial: pd.DataFrame) -> None:
    print("\n=== OFFICIAL (EXPERIMENTAL + PUBLICATION_GRADE, nunca PROVISIONAL) ===")
    if oficial.empty:
        print("  vazio")
        return
    print(f"  primeiro mes: {oficial['reference_period'].min():%Y-%m}")
    print(f"  ultimo mes:   {oficial['reference_period'].max():%Y-%m}")
    contagem = oficial["publication_status"].value_counts()
    for status in (STATUS_EXPERIMENTAL, STATUS_PUBLICATION_GRADE):
        print(f"  meses {status}: {int(contagem.get(status, 0))}")
    valido = oficial["ipia_hrc_v2"].dropna()
    if not valido.empty:
        print(f"  IPIA minimo:   {valido.min():.2f}")
        print(f"  IPIA mediana:  {valido.median():.2f}")
        print(f"  IPIA maximo:   {valido.max():.2f}")


def reportar_provisional(provisional: pd.DataFrame) -> None:
    print("\n=== PROVISIONAL ===")
    if provisional.empty:
        print("  vazio (nenhum mes provisional - IPP nao vai alem do ultimo ano PIA)")
        return
    print(f"  primeiro mes: {provisional['reference_period'].min():%Y-%m}")
    print(f"  ultimo mes:   {provisional['reference_period'].max():%Y-%m}")
    print(f"  numero de meses: {len(provisional)}")
    valido = provisional["ipia_hrc_v2"].dropna()
    if not valido.empty:
        print(f"  IPIA minimo:   {valido.min():.2f}")
        print(f"  IPIA mediana:  {valido.median():.2f}")
        print(f"  IPIA maximo:   {valido.max():.2f}")
        ultimo = provisional.sort_values("reference_period").iloc[-1]
        print(f"  ultimo valor corrente (PROVISIONAL, {ultimo['reference_period']:%Y-%m}): "
              f"{ultimo['ipia_hrc_v2']:.2f}")


def comparar_com_ipia_corporate(serie: pd.DataFrame, ppi_mensal: pd.DataFrame) -> None:
    """Compara o novo IPIA PIA-based (todos os status calculaveis, oficial
    + provisional) com o IPIA-HRC Corporate Benchmark antigo
    (`calcular_serie_ipia_hrc_v2`, ancora Usiminas+CSN, interno/deprecated
    - ADR 0013) nos meses sobrepostos - quantifica quanto a correcao de
    product-mix (PIA especifica de HRC vs. ancora corporativa
    "Siderurgia") altera o nivel. Comparacao/diagnostico, nunca
    recalibracao - nunca entra no calculo oficial."""
    print("\n=== Comparacao: IPIA-HRC PIA-based vs. IPIA-HRC Corporate Benchmark (interno/deprecated) ===")
    try:
        corporate = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi_mensal)
    except Exception as e:
        print(f"  nao foi possivel calcular o benchmark corporativo ao vivo ({e}) - pulando comparacao")
        return
    corp_valido = corporate.dropna(subset=["ipia_hrc_v2"])
    pia_valido = serie.dropna(subset=["ipia_hrc_v2"])
    if corp_valido.empty or pia_valido.empty:
        print("  um dos dois lados nao tem nenhum mes calculavel - sem sobreposicao para comparar")
        return
    comp = pia_valido.merge(
        corp_valido[["reference_period", "ipia_hrc_v2"]].rename(columns={"ipia_hrc_v2": "ipia_corporate"}),
        on="reference_period", how="inner")
    if comp.empty:
        print("  nenhum mes em comum entre as duas series - sem sobreposicao para comparar")
        return
    comp["delta_pct"] = comp["ipia_hrc_v2"] / comp["ipia_corporate"] - 1.0
    print(f"  meses sobrepostos: {len(comp)}")
    print(f"  delta_pct medio (PIA-based vs corporate): {comp['delta_pct'].mean() * 100:+.2f}%")
    print(f"  delta_pct desvio-padrao: {comp['delta_pct'].std() * 100:.2f}pp")
    print(comp[["reference_period", "ipia_hrc_v2", "ipia_corporate", "delta_pct"]].to_string(index=False))


def gerar_grafico_validacao(serie: pd.DataFrame, caminho_png: str) -> None:
    """Grafico de linha de VALIDACAO ANALITICA: ipia_hrc_v2 x mes,
    referencia horizontal em 100, cores por publication_status (os quatro
    - EXPERIMENTAL, PUBLICATION_GRADE, PROVISIONAL claramente distinto,
    UNKNOWN como gap real no eixo X), nunca interpolando um gap."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(13, 5))
    cores = {STATUS_PUBLICATION_GRADE: "#1a7f37", STATUS_EXPERIMENTAL: "#b8860b",
             STATUS_PROVISIONAL: "#7c3aed", STATUS_UNKNOWN: "#c0c0c0"}

    # linha continua so entre pontos OFICIAIS (nunca liga oficial->provisional
    # como se fosse a mesma serie continua sem selo).
    oficial_calc = serie[serie["publication_status"].isin([STATUS_EXPERIMENTAL, STATUS_PUBLICATION_GRADE])]
    oficial_calc = oficial_calc.dropna(subset=["ipia_hrc_v2"]).sort_values("reference_period")
    ax.plot(oficial_calc["reference_period"], oficial_calc["ipia_hrc_v2"], "-", color="#444444",
            linewidth=1.0, zorder=1, label="_nolegend_")

    prov = serie[serie["publication_status"] == STATUS_PROVISIONAL].dropna(
        subset=["ipia_hrc_v2"]).sort_values("reference_period")
    if not prov.empty:
        ax.plot(prov["reference_period"], prov["ipia_hrc_v2"], "--", color=cores[STATUS_PROVISIONAL],
                linewidth=1.2, zorder=1, label="_nolegend_")

    for status in (STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_PROVISIONAL):
        recorte = serie[(serie["publication_status"] == status) & serie["ipia_hrc_v2"].notna()]
        if recorte.empty:
            continue
        marker = "^" if status == STATUS_PROVISIONAL else "o"
        ax.scatter(recorte["reference_period"], recorte["ipia_hrc_v2"], s=16, color=cores[status],
                   marker=marker, label=status, zorder=2)

    calculaveis = serie.dropna(subset=["ipia_hrc_v2"])
    unknown_meses = serie.loc[serie["publication_status"] == STATUS_UNKNOWN, "reference_period"]
    if not unknown_meses.empty and not calculaveis.empty:
        y0 = calculaveis["ipia_hrc_v2"].min()
        ax.scatter(unknown_meses, [y0] * len(unknown_meses), marker="|", color=cores[STATUS_UNKNOWN],
                   s=40, label=f"{STATUS_UNKNOWN} (gap/nao calculavel)", zorder=0, alpha=0.6)

    ax.axhline(100.0, color="black", linewidth=0.8, linestyle="--", label="paridade (100)")
    ax.set_xlabel("Mes (reference_period)")
    ax.set_ylabel("IPIA-HRC (PIA-based)")
    ax.set_title("IPIA-HRC - OFFICIAL (solido) vs PROVISIONAL (tracejado) - VALIDACAO ANALITICA")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(caminho_png, dpi=120)
    plt.close(fig)


def reportar_vintage(manifest: dict, vintage_anterior: dict | None,
                     oficial_final: pd.DataFrame, provisional_final: pd.DataFrame) -> None:
    print("\n=== VINTAGE ===")
    print(f"  vintage_id:          {manifest['vintage_id']}")
    print(f"  previous_vintage_id: {manifest['previous_vintage_id']}")
    print(f"  methodology_version: {manifest['methodology_version']}")
    print(f"  last_pia_year:       {manifest['sources']['pia_last_observed_year']}")
    print(f"  official coverage:    {manifest['coverage']['official_first_period']} -> "
          f"{manifest['coverage']['official_last_period']}")
    print(f"  provisional coverage: {manifest['coverage']['provisional_first_period']} -> "
          f"{manifest['coverage']['provisional_last_period']}")

    revisados = int(oficial_final["revised"].sum()) + int(provisional_final["revised"].sum())
    print(f"  revised rows (official+provisional): {revisados}")

    if vintage_anterior is None:
        print("  new rows: n/a (primeira vintage)")
        print("  promoted provisional -> official: n/a (primeira vintage)")
        return

    meses_anteriores = (set(vintage_anterior["official"]["reference_period"])
                        | set(vintage_anterior["provisional"]["reference_period"]))
    meses_provisional_anterior = set(vintage_anterior["provisional"]["reference_period"])
    meses_novos_agora = set(oficial_final["reference_period"]) | set(provisional_final["reference_period"])
    meses_realmente_novos = meses_novos_agora - meses_anteriores
    promovidos = meses_provisional_anterior & set(oficial_final["reference_period"])

    print(f"  new rows: {len(meses_realmente_novos)}")
    print(f"  promoted provisional -> official: {len(promovidos)}")
    if promovidos:
        for mes in sorted(promovidos):
            print(f"    {mes:%Y-%m}")


def main() -> None:
    vintage_anterior_id = m.ultima_vintage_ipia_hrc_v2()
    if vintage_anterior_id is not None:
        print(f"=== Vintage anterior encontrada: {vintage_anterior_id} ===")
    else:
        print("=== Nenhuma vintage anterior - esta sera a PRIMEIRA vintage ===")

    print("\n=== Executando pipeline canonico do IPIA-HRC (fetch + calculo + persistencia) ===")
    resultado = m.executar_pipeline_ipia_hrc()
    serie = resultado["serie"]
    oficial = resultado["oficial"]
    provisional = resultado["provisional"]
    manifest = resultado["manifest"]

    print(f"  {len(serie)} meses no output completo (todos os 4 status, antes de separar oficial/provisional)")
    print(f"\nCSV oficial (latest) salvo em:      {resultado['csv_oficial']}")
    print(f"CSV provisional (latest) salvo em:  {resultado['csv_provisional']}")
    print(f"  vintage criada em: {m.VINTAGE_BASE_DIR_PADRAO}/{m.VINTAGE_PRODUTO_IPIA_HRC_V2}/{manifest['vintage_id']}")
    print(f"  hashes: OK ({len(manifest['hashes'])} arquivo(s))")

    gerar_grafico_validacao(serie, PNG_SAIDA)
    print(f"Grafico de validacao (latest) salvo em: {PNG_SAIDA}")

    reportar_oficial(oficial)
    reportar_provisional(provisional)
    reportar_vintage(manifest, resultado["vintage_anterior"], oficial, provisional)

    # comparacao com o benchmark corporativo reusa o import side ja
    # calculado no pipeline (evitando recalcula-lo/rebuscar Comex/BCB) -
    # `resultado["ppi_mensal_df"]` e devolvido diretamente pelo pipeline,
    # nunca recarregado da vintage via base_dir default (evitaria um
    # descasamento se o pipeline tivesse rodado contra um base_dir
    # diferente do default).
    comparar_com_ipia_corporate(serie, resultado["ppi_mensal_df"])


if __name__ == "__main__":
    main()
