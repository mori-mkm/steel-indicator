#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage E9: gera a primeira serie mensal completa do IPIA-HRC V2, integrando
o agregador bottom-up multi-NCM (import side, Stage E7, ja aprovado) com o
Domestic Price V2 (Stage E8, ja aprovado) via
`indices_setoriais.calcular_serie_ipia_hrc_v2()` (Stage E9, ja aprovado).

NAO e codigo de producao/publicacao: gera um artefato analitico de
VALIDACAO (CSV + grafico de linha), nao o relatorio PDF oficial. Nao altera
`--selftest`, a CLI principal, `report_builder.py` nem nenhum caminho
legado.

Uso:
    python scripts/gerar_serie_ipia_hrc_v2.py

Produz:
    data/processed/ipia_hrc_v2_monthly.csv
    data/processed/ipia_hrc_v2_validation.png

Faz chamadas de rede reais (Comex Stat, BCB/SGS, IBGE/SIDRA, CSV curado
local). O BCB SGS rejeita (406) janela de consulta de serie diaria
(cambio_venda/PTAX) acima de 10 anos; como este script pede o periodo
2012-2026 (15 anos), o cambio e buscado em dois pedacos <=10 anos e
`indices_setoriais.sgs` e temporariamente substituido durante a chamada de
`agregar_ipia_hrc_multi_ncm_mensal` - mesmo workaround ja usado por
`scripts/research/ipia_hrc_ncm_coverage.py` e documentado em
`calcular_ipia_mensal`, nao uma decisao nova. `sgs` e restaurado logo em
seguida - nenhum outro consumidor deste modulo e afetado.
"""
from __future__ import annotations
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import (
    STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN,
)

ANO_INI, ANO_FIM = 2012, 2026
CSV_SAIDA = "data/processed/ipia_hrc_v2_monthly.csv"
PNG_SAIDA = "data/processed/ipia_hrc_v2_validation.png"


def _buscar_comex_bruto_com_retry(tentativas: int = 4, espera_s: float = 20.0) -> pd.DataFrame:
    """`_comex_bobina_bruto` ja tem retry embutido (`_post_json`, 3
    tentativas com backoff curto), mas a API da Comex Stat aplicou rate
    limit (429) real durante esta stage mesmo apos esse backoff - uma
    espera mais longa entre tentativas aqui resolveu na pratica. Nao e uma
    politica de retry nova para o adapter (isso mudaria comportamento ja
    aprovado do adapter) - so paciencia adicional no chamador."""
    ultimo_erro = None
    for tentativa in range(tentativas):
        try:
            return m._comex_bobina_bruto(ANO_INI, ANO_FIM)
        except Exception as e:
            ultimo_erro = e
            print(f"  tentativa {tentativa + 1}/{tentativas} falhou ({e}); aguardando {espera_s:.0f}s...")
            time.sleep(espera_s)
    raise RuntimeError(f"Nao foi possivel buscar dado bruto do Comex Stat apos {tentativas} tentativas") from ultimo_erro


def _cambio_historico_seguro_10anos(ano_ini: int, ano_fim: int) -> pd.Series:
    """Busca PTAX (cambio_venda) de `ano_ini` a `ano_fim` em pedacos
    <=10 anos (limite do BCB SGS para series diarias) e concatena.
    Identico em espirito ao workaround ja usado em
    `scripts/research/ipia_hrc_ncm_coverage.py::sensibilidade_ii`."""
    url = m.SGS_URL.format(cod=m.SGS["cambio_venda"])
    corte = ano_ini + 6  # dois pedacos de ate 7 e ate 9 anos, ambos < 10
    janelas = [(f"01/01/{ano_ini}", f"31/12/{corte}"), (f"01/01/{corte + 1}", f"31/12/{ano_fim}")]
    pedacos = []
    for ini, fim in janelas:
        dados = m._get_json(url, {"dataInicial": ini, "dataFinal": fim})
        pdf = pd.DataFrame(dados)
        pdf["data"] = pd.to_datetime(pdf["data"], format="%d/%m/%Y")
        pdf["valor"] = pd.to_numeric(pdf["valor"], errors="coerce")
        pedacos.append(pdf.set_index("data")["valor"])
    cambio = pd.concat(pedacos).sort_index()
    return cambio[~cambio.index.duplicated(keep="last")]


def gerar_import_side_2012_2026(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """`agregar_ipia_hrc_multi_ncm_mensal` busca cambio via `sgs()` sem
    data final (sempre ate "hoje") - para ano_ini=2012 isso excede a
    janela de 10 anos do BCB. Sem tocar `agregar_ipia_hrc_multi_ncm_mensal`
    (Stage E7, ja aprovado), troca `indices_setoriais.sgs` por uma versao
    que devolve o cambio ja buscado em pedacos seguros, so durante esta
    chamada.

    Tambem passa um `domestico_df` "curinga" com cobertura mensal total
    (2012-2026): sem isso, `agregar_ipia_hrc_multi_ncm_mensal` faria seu
    PROPRIO merge interno contra o preco domestico LEGADO (CSV curado, so
    2025Q2 em diante hoje), recortando o import side inteiro para so os
    poucos meses onde o legado tem cobertura - antes mesmo do merge real
    com o Domestic Price V2 mais adiante neste script. O preco_rs_t desse
    curinga nunca e usado (`calcular_serie_ipia_hrc_v2` descarta as colunas
    preco_domestico_rs_t/ipia que essa chamada devolveria) - mesma tecnica
    ja documentada dentro de `calcular_serie_ipia_hrc_v2`."""
    cambio_completo = _cambio_historico_seguro_10anos(ANO_INI, ANO_FIM)
    domestico_curinga = pd.DataFrame(
        {"preco_rs_t": 1.0}, index=pd.date_range(f"{ANO_INI}-01-01", f"{ANO_FIM}-12-01", freq="MS"))
    sgs_original = m.sgs
    m.sgs = lambda codigo, inicio="01/01/2010": cambio_completo
    try:
        return m.agregar_ipia_hrc_multi_ncm_mensal(
            ano_ini=ANO_INI, ano_fim=ANO_FIM, df_bruto=df_bruto, domestico_df=domestico_curinga)
    finally:
        m.sgs = sgs_original


def sanity_checks(serie: pd.DataFrame) -> None:
    print("\n=== SANITY CHECKS ===")
    if serie.empty:
        print("  serie vazia - nada a checar")
        return
    print(f"  primeiro mes: {serie['reference_period'].min():%Y-%m}")
    print(f"  ultimo mes:   {serie['reference_period'].max():%Y-%m}")
    print(f"  total de meses no output: {len(serie)}")
    contagem_status = serie["publication_status"].value_counts()
    for status in (STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN):
        print(f"  meses {status}: {int(contagem_status.get(status, 0))}")

    calculaveis = serie["ipia_hrc_v2"].dropna()
    if calculaveis.empty:
        print("  nenhum mes com IPIA calculado - sem estatisticas de nivel")
    else:
        idx_min, idx_max = calculaveis.idxmin(), calculaveis.idxmax()
        print(f"  minimo do IPIA: {calculaveis.min():.2f} ({serie.loc[idx_min, 'reference_period']:%Y-%m})")
        print(f"  mediana do IPIA: {calculaveis.median():.2f}")
        print(f"  maximo do IPIA: {calculaveis.max():.2f} ({serie.loc[idx_max, 'reference_period']:%Y-%m})")
        print(f"  % meses IPIA < 100: {(calculaveis < 100).mean() * 100:.1f}%")
        print(f"  % meses IPIA >= 100: {(calculaveis >= 100).mean() * 100:.1f}%")

        variacao = calculaveis.diff().abs().sort_values(ascending=False)
        print("  5 maiores movimentos mes-a-mes (|delta| absoluto):")
        for idx, delta in variacao.head(5).items():
            print(f"    {serie.loc[idx, 'reference_period']:%Y-%m}: delta={delta:+.2f} "
                  f"(ipia={calculaveis.loc[idx]:.2f})")


def investigar_outliers(serie: pd.DataFrame) -> list[str]:
    """Verificacoes automaticas de bugs/anomalias tecnicas (nao economicas)
    - ver secao 10 da task. Retorna a lista de achados (vazia = nada
    encontrado)."""
    achados = []
    if serie.empty:
        return achados

    if serie["reference_period"].duplicated().any():
        achados.append("reference_period duplicado no output")
    if not serie["reference_period"].is_monotonic_increasing:
        achados.append("reference_period fora de ordem")

    calculaveis = serie.dropna(subset=["ipia_hrc_v2"])
    if (calculaveis["ipia_hrc_v2"] <= 0).any():
        achados.append(f"IPIA <= 0 em {int((calculaveis['ipia_hrc_v2'] <= 0).sum())} mes(es)")
    if (calculaveis["preco_domestico_rs_t"] <= 0).any():
        achados.append("preco domestico <= 0 em algum mes calculavel")
    if (calculaveis["ppi_rs_t"] <= 0).any():
        achados.append("PPI <= 0 em algum mes calculavel")

    cov = serie["policy_coverage"].dropna()
    if ((cov < 0) | (cov > 1)).any():
        achados.append("policy_coverage fora de [0, 1]")

    rng = serie["ppi_uncertainty_range_pct"].dropna()
    if (rng < 0).any():
        achados.append("ppi_uncertainty_range_pct negativo")

    # status incompativel com NaN/valor: UNKNOWN deve ter ipia NaN;
    # PUBLICATION_GRADE/EXPERIMENTAL devem ter ipia nao-NaN.
    unk_com_valor = serie[(serie["publication_status"] == STATUS_UNKNOWN) & serie["ipia_hrc_v2"].notna()]
    if not unk_com_valor.empty:
        achados.append(f"{len(unk_com_valor)} mes(es) UNKNOWN com ipia_hrc_v2 preenchido (deveria ser NaN)")
    valido_sem_valor = serie[serie["publication_status"].isin([STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL])
                             & serie["ipia_hrc_v2"].isna()]
    if not valido_sem_valor.empty:
        achados.append(f"{len(valido_sem_valor)} mes(es) PUBLICATION_GRADE/EXPERIMENTAL com ipia_hrc_v2 ausente")

    if len(calculaveis) >= 2:
        variacao_pct = calculaveis["ipia_hrc_v2"].pct_change().abs()
        extremos = variacao_pct[variacao_pct > 0.30]
        if not extremos.empty:
            for idx in extremos.index:
                achados.append(
                    f"variacao mensal extrema em {calculaveis.loc[idx, 'reference_period']:%Y-%m} "
                    f"({variacao_pct.loc[idx] * 100:.1f}%) - investigar antes de publicar")

    print("\n=== INVESTIGACAO DE OUTLIERS ===")
    if not achados:
        print("  nenhuma anomalia tecnica encontrada")
    else:
        for a in achados:
            print(f"  [ACHADO] {a}")
    return achados


def gerar_grafico_validacao(serie: pd.DataFrame, caminho_png: str) -> None:
    """Grafico de linha de VALIDACAO ANALITICA (nao o design system do PDF
    oficial): ipia_hrc_v2 x mes, referencia horizontal em 100, cores por
    publication_status, gaps (meses ausentes) nunca conectados por reta -
    matplotlib so liga pontos consecutivos que existem na serie; um mes
    ausente vira um buraco real no eixo X, nunca interpolado."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 5))
    cores = {STATUS_PUBLICATION_GRADE: "#1a7f37", STATUS_EXPERIMENTAL: "#b8860b", STATUS_UNKNOWN: "#c0c0c0"}

    calculaveis = serie.dropna(subset=["ipia_hrc_v2"]).sort_values("reference_period")
    ax.plot(calculaveis["reference_period"], calculaveis["ipia_hrc_v2"], "-", color="#444444",
            linewidth=1.0, zorder=1)
    for status, cor in cores.items():
        if status == STATUS_UNKNOWN:
            continue
        recorte = calculaveis[calculaveis["publication_status"] == status]
        if recorte.empty:
            continue
        ax.scatter(recorte["reference_period"], recorte["ipia_hrc_v2"], s=14, color=cor, label=status, zorder=2)

    # meses UNKNOWN (gap real): marca no eixo X, sem valor no eixo Y - nunca inventa um ponto
    unknown_meses = serie.loc[serie["publication_status"] == STATUS_UNKNOWN, "reference_period"]
    if not unknown_meses.empty and not calculaveis.empty:
        y0 = calculaveis["ipia_hrc_v2"].min()
        ax.scatter(unknown_meses, [y0] * len(unknown_meses), marker="|", color=cores[STATUS_UNKNOWN],
                   s=40, label=f"{STATUS_UNKNOWN} (gap/nao calculavel)", zorder=0, alpha=0.6)

    ax.axhline(100.0, color="black", linewidth=0.8, linestyle="--", label="paridade (100)")
    ax.set_xlabel("Mes (reference_period)")
    ax.set_ylabel("IPIA-HRC V2")
    ax.set_title("IPIA-HRC V2 - serie mensal (VALIDACAO ANALITICA, nao publication-grade)")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(caminho_png, dpi=120)
    plt.close(fig)


def main() -> None:
    print(f"=== Buscando dado bruto do Comex Stat ({ANO_INI}-{ANO_FIM}) ===")
    df_bruto = _buscar_comex_bruto_com_retry()
    print(f"  {len(df_bruto)} linhas brutas")

    print("\n=== Import side V2 (bottom-up multi-NCM) ===")
    ppi_mensal = gerar_import_side_2012_2026(df_bruto)
    print(f"  {len(ppi_mensal)} meses calculaveis (com dado Comex no periodo)")

    print("\n=== Domestic Price V2 ===")
    preco_domestico = m.preco_domestico_hrc_mensal_v2()
    print(f"  {len(preco_domestico)} meses (ancorados em {preco_domestico['anchor_reference_period'].nunique()} "
          f"trimestre(s) curado(s))")

    print("\n=== Integrando IPIA-HRC V2 ===")
    serie = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi_mensal, preco_domestico_df=preco_domestico)
    print(f"  {len(serie)} meses no output final")

    os.makedirs(os.path.dirname(CSV_SAIDA), exist_ok=True)
    serie.to_csv(CSV_SAIDA, index=False)
    print(f"\nCSV salvo em: {CSV_SAIDA}")

    gerar_grafico_validacao(serie, PNG_SAIDA)
    print(f"Grafico de validacao salvo em: {PNG_SAIDA}")

    sanity_checks(serie)
    achados = investigar_outliers(serie)
    print(f"\n{len(achados)} anomalia(s) tecnica(s) encontrada(s)." if achados
          else "\nNenhuma anomalia tecnica encontrada.")


if __name__ == "__main__":
    main()
