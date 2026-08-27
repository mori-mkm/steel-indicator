#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage E11: gera a serie IPIA-HRC V2 PIA-based, integrando o import side
bottom-up multi-NCM (Stage E7, ja aprovado) com o Domestic Price V2 caminho
PIA (Stage E10/ADR 0010, ja aprovado) via
`indices_setoriais.calcular_ipia_hrc_v2_pia()` (Stage E11/ADR 0011),
incluindo o quarto status PROVISIONAL e a separacao explicita entre saida
oficial e provisional (`separar_ipia_hrc_v2_oficial_provisional`).

NAO e codigo de producao/publicacao: gera artefatos analiticos de
VALIDACAO (2 CSVs + grafico), nao o relatorio PDF oficial. Nao altera
`--selftest`, a CLI principal, `report_builder.py` nem nenhum caminho
legado - mesmo status dos demais scripts scripts/gerar_*.py.

Uso:
    python scripts/gerar_ipia_hrc_v2_pia.py

Produz:
    data/processed/ipia_hrc_v2_official.csv
    data/processed/ipia_hrc_v2_provisional.csv
    data/processed/ipia_hrc_v2_pia_validation.png

Faz chamadas de rede reais (Comex Stat, BCB/SGS, IBGE/SIDRA). Mesmo
workaround de janela segura do BCB SGS (<=10 anos por pedaco) ja usado em
scripts/gerar_serie_ipia_hrc_v2.py, reaproveitado aqui sem alteracao.
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

STATUS_PROVISIONAL = m.STATUS_PROVISIONAL

ANO_INI, ANO_FIM = 2012, 2026
CSV_OFICIAL = "data/processed/ipia_hrc_v2_official.csv"
CSV_PROVISIONAL = "data/processed/ipia_hrc_v2_provisional.csv"
PNG_SAIDA = "data/processed/ipia_hrc_v2_pia_validation.png"


def _buscar_comex_bruto_com_retry(tentativas: int = 4, espera_s: float = 20.0) -> pd.DataFrame:
    """Identico em espirito a scripts/gerar_serie_ipia_hrc_v2.py::
    _buscar_comex_bruto_com_retry - a Comex Stat aplica rate limit (429)
    real; espera mais longa entre tentativas resolveu na pratica."""
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
    """Identico a scripts/gerar_serie_ipia_hrc_v2.py::_cambio_historico_seguro_10anos."""
    url = m.SGS_URL.format(cod=m.SGS["cambio_venda"])
    corte = ano_ini + 6
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
    """Identico em tecnica a scripts/gerar_serie_ipia_hrc_v2.py::
    gerar_import_side_2012_2026 - troca `sgs` por cambio ja buscado em
    pedacos seguros so durante a chamada, e usa domestico "curinga" para
    nao deixar `agregar_ipia_hrc_multi_ncm_mensal` recortar o import side
    pelo preco domestico legado antes do merge real com a PIA."""
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
    + provisional) com o IPIA-HRC V2 corporate antigo
    (`calcular_serie_ipia_hrc_v2`, ancora Usiminas+CSN) nos meses
    sobrepostos - quantifica quanto a correcao de product-mix (PIA
    especifica de HRC vs. ancora corporativa "Siderurgia") altera o nivel.
    Comparacao/diagnostico, nunca recalibracao.

    Reaproveita `ppi_mensal` (ja calculado acima, import side 2012-2026)
    em vez de deixar `calcular_serie_ipia_hrc_v2()` recalcula-lo sozinho -
    isso evitaria o mesmo problema de janela do BCB SGS (>10 anos) que
    `gerar_import_side_2012_2026` ja contorna acima; passar o import side
    pronto pula esse caminho por completo (mesmo padrao de injecao de
    dado ja pronto usado no resto do modulo)."""
    print("\n=== Comparacao: novo IPIA PIA-based vs. IPIA-HRC V2 corporate (ancora antiga) ===")
    try:
        corporate = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi_mensal)
    except Exception as e:
        print(f"  nao foi possivel calcular o IPIA corporate ao vivo ({e}) - pulando comparacao")
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
    print(f"  delta_pct medio (PIA vs corporate): {comp['delta_pct'].mean() * 100:+.2f}%")
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
    ax.set_ylabel("IPIA-HRC V2 (PIA-based)")
    ax.set_title("IPIA-HRC V2 PIA-based - OFFICIAL (solido) vs PROVISIONAL (tracejado) - VALIDACAO ANALITICA")
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

    print("\n=== Domestic Price V2 - caminho PIA ===")
    pia = m.ibge_sidra_pia_hrc_anual()
    ipp = m.ibge_sidra_ipp_siderurgia()
    preco_domestico_pia = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)
    print(f"  {len(preco_domestico_pia)} meses "
          f"({int((~preco_domestico_pia['is_provisional']).sum())} benchmarked, "
          f"{int(preco_domestico_pia['is_provisional'].sum())} provisional)")

    print("\n=== Integrando IPIA-HRC V2 PIA-based ===")
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_mensal, pia_domestico_df=preco_domestico_pia)
    print(f"  {len(serie)} meses no output completo (todos os 4 status, antes de separar oficial/provisional)")

    oficial, provisional = m.separar_ipia_hrc_v2_oficial_provisional(serie)

    os.makedirs(os.path.dirname(CSV_OFICIAL), exist_ok=True)
    oficial.to_csv(CSV_OFICIAL, index=False)
    provisional.to_csv(CSV_PROVISIONAL, index=False)
    print(f"\nCSV oficial salvo em:      {CSV_OFICIAL}")
    print(f"CSV provisional salvo em:  {CSV_PROVISIONAL}")

    gerar_grafico_validacao(serie, PNG_SAIDA)
    print(f"Grafico de validacao salvo em: {PNG_SAIDA}")

    reportar_oficial(oficial)
    reportar_provisional(provisional)
    comparar_com_ipia_corporate(serie, ppi_mensal)


if __name__ == "__main__":
    main()
