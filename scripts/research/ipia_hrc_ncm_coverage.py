#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage E7 research: cobertura de politica comercial por volume (KG) e
sensibilidade economica do II desconhecido, para fechar LIMIAR_COBERTURA e
a regra de UNKNOWN do IPIA-HRC (Level 3, ainda pendente).

NAO e codigo de producao. Faz chamadas de rede reais - execucao
explicitamente opt-in:

    python scripts/research/ipia_hrc_ncm_coverage.py

Usa steel_indicator.sources.comex (adapter ja aprovado) e
steel_indicator.parameters.trade_policy (ja aprovado) - nao reimplementa
nem altera nenhum dos dois. Nao altera calcular_ipia_hrc_v2 nem nenhum
codigo de producao.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np
import pandas as pd

from steel_indicator.sources.comex import COMEX_URL, _post_json
from steel_indicator.parameters.trade_policy import resolver_ii, resolver_afrmm, STATUS_UNKNOWN
import indices_setoriais as m

NCMS = sorted(sum(m.NCM_BOBINA_QUENTE.values(), []))
NCMS_CONFIRMADOS_2012 = {"72083700", "72083890", "72083990", "72083910"}
NCMS_COTA_2026 = {"72083700", "72083890", "72083910", "72083990"}
METRICAS = ["metricFOB", "metricKG", "metricFreight", "metricInsurance"]


def _consulta(ano_ini: int, ano_fim: int) -> list:
    payload = {
        "flow": "import", "monthDetail": True,
        "period": {"from": f"{ano_ini}-01", "to": f"{ano_fim}-12"},
        "filters": [{"filter": "ncm", "values": NCMS}],
        "details": ["ncm", "country"],
        "metrics": METRICAS,
    }
    dados = _post_json(COMEX_URL, payload)
    return dados.get("data", {}).get("list", [])


def coletar_tudo() -> pd.DataFrame:
    janelas = [(2012, 2015), (2016, 2019), (2020, 2022), (2023, 2025), (2026, 2026)]
    linhas = []
    for ini, fim in janelas:
        lote = _consulta(ini, fim)
        print(f"  janela {ini}-{fim}: {len(lote)} registros")
        linhas.extend(lote)
    df = pd.DataFrame(linhas)
    for col in METRICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["data"] = pd.to_datetime(df["year"].astype(str) + "-" + df["monthNumber"].astype(str).str.zfill(2) + "-01")
    return df


def montar_por_ncm_mes(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega por (data, coNcm), somando paises - suficiente para II/quota
    (nao variam por origem). Origem e analisada separadamente (secao 7)."""
    g = df.groupby(["data", "coNcm"], as_index=False)[METRICAS].sum()
    g["status_ii"] = [resolver_ii(row.coNcm, row.data).status for row in g.itertuples()]
    g["aliquota_ii"] = [resolver_ii(row.coNcm, row.data).aliquota for row in g.itertuples()]
    g["known"] = g["status_ii"] != STATUS_UNKNOWN
    g["confirmado_individualmente"] = g["coNcm"].isin(NCMS_CONFIRMADOS_2012)
    g["sujeito_a_cota_2026"] = g["coNcm"].isin(NCMS_COTA_2026)
    return g


def montar_resumo_mensal(por_ncm_mes: pd.DataFrame) -> pd.DataFrame:
    def _linha(g):
        total_kg = g["metricKG"].sum()
        known_kg = g.loc[g["known"], "metricKG"].sum()
        return pd.Series({
            "total_kg": total_kg,
            "known_policy_kg": known_kg,
            "unknown_policy_kg": total_kg - known_kg,
            "coverage": (known_kg / total_kg) if total_kg > 0 else np.nan,
            "kg_confirmados_4ncm": g.loc[g["confirmado_individualmente"], "metricKG"].sum(),
            "kg_nao_confirmados_9ncm": g.loc[~g["confirmado_individualmente"], "metricKG"].sum(),
            "kg_sujeito_cota_2026": g.loc[g["sujeito_a_cota_2026"], "metricKG"].sum(),
        })
    resumo = por_ncm_mes.groupby("data").apply(_linha).reset_index()
    return resumo


def relatar_janela(resumo: pd.DataFrame, nome: str, ini: str, fim: str):
    r = resumo[(resumo["data"] >= ini) & (resumo["data"] <= fim)].copy()
    print(f"\n=== Janela {nome}: {ini} a {fim} ({len(r)} meses com dado) ===")
    if r.empty:
        print("  SEM DADOS")
        return r
    cov = r["coverage"].dropna()
    print(f"  total_kg medio/mes: {r['total_kg'].mean():,.0f} kg")
    print(f"  coverage: min={cov.min():.1%} P10={cov.quantile(.10):.1%} mediana={cov.median():.1%} "
          f"P90={cov.quantile(.90):.1%} max={cov.max():.1%}")
    for lim in (0.50, 0.60, 0.75, 0.90, 0.95, 1.00):
        pct = (cov >= lim).mean() if lim < 1.0 else (cov >= 0.999999).mean()
        n_meses = int((cov >= lim).sum()) if lim < 1.0 else int((cov >= 0.999999).sum())
        print(f"    >= {lim:.0%}: {pct:.1%} dos meses ({n_meses}/{len(cov)})")
    piores = r.nsmallest(5, "coverage")[["data", "coverage", "total_kg", "known_policy_kg"]]
    print("  5 piores meses:")
    for _, row in piores.iterrows():
        print(f"    {row['data']:%Y-%m}: coverage={row['coverage']:.1%} "
              f"total_kg={row['total_kg']:,.0f} known_kg={row['known_policy_kg']:,.0f}")
    return r


def sensibilidade_ii(por_ncm_mes: pd.DataFrame, df_bruto: pd.DataFrame, ano_ini="2012-01-01", ano_fim="2022-03-31"):
    """Para meses com unknown_policy_kg > 0 na janela A, calcula PPI_lower/
    upper usando 10%/14% para os NCMs nao confirmados, mantendo a
    aliquota real resolvida para os confirmados - NUNCA um ponto central
    escolhido. Usa cambio real (BCB/SGS)."""
    print("\n=== Sensibilidade economica do II desconhecido (janela A, 2012-2022-03) ===")
    # PTAX (codigo 1) e serie diaria - BCB rejeita (406) janela > 10 anos, e
    # sgs() nao aceita data final (sempre vai ate "hoje") - busca direto via
    # _get_json com dataInicial/dataFinal explicitos, em pedacos <=10 anos
    # (mesmo problema ja documentado em calcular_ipia_mensal).
    url = m.SGS_URL.format(cod=m.SGS["cambio_venda"])
    pedacos = []
    for ini, fim in [("01/01/2012", "31/12/2018"), ("01/01/2019", "31/12/2022")]:
        dados = m._get_json(url, {"dataInicial": ini, "dataFinal": fim})
        pdf = pd.DataFrame(dados)
        pdf["data"] = pd.to_datetime(pdf["data"], format="%d/%m/%Y")
        pdf["valor"] = pd.to_numeric(pdf["valor"], errors="coerce")
        pedacos.append(pdf.set_index("data")["valor"])
    cambio = pd.concat(pedacos).sort_index()
    cambio = cambio[~cambio.index.duplicated(keep="last")]

    p = m.ParamsIPIA()
    linhas_result = []
    meses_a = sorted(por_ncm_mes.loc[
        (por_ncm_mes["data"] >= ano_ini) & (por_ncm_mes["data"] <= ano_fim), "data"].unique())
    for mes in meses_a:
        g = por_ncm_mes[por_ncm_mes["data"] == mes]
        if g["metricKG"].sum() <= 0:
            continue
        if mes not in cambio.index:
            continue
        cbo = cambio.reindex([mes], method="ffill").iloc[0]
        if pd.isna(cbo):
            continue

        def _custo_total_com_ii(aliquota_por_linha):
            total_kg = g["metricKG"].sum()
            soma_ppi_x_kg = 0.0
            for row in g.itertuples():
                if row.metricKG <= 0:
                    continue
                cif_usd_t = 1000 * (row.metricFOB + row.metricFreight + row.metricInsurance) / row.metricKG
                frete_usd_t = 1000 * row.metricFreight / row.metricKG
                cif_brl_t = cif_usd_t * cbo
                r_ii = aliquota_por_linha(row)
                if r_ii is None:
                    continue
                afrmm_res = resolver_afrmm(mes)
                ii = cif_brl_t * r_ii
                afrmm = (frete_usd_t * cbo) * (afrmm_res.aliquota or 0.0)
                base = cif_brl_t + ii + afrmm + p.despesas_porto_rs_t + p.frete_interno_rs_t
                ppi_t = base * (1 + p.margem_importador)
                soma_ppi_x_kg += ppi_t * row.metricKG
            return soma_ppi_x_kg / total_kg if total_kg > 0 else np.nan

        unk_kg = g.loc[~g["known"], "metricKG"].sum()
        total_kg = g["metricKG"].sum()
        if unk_kg <= 0:
            continue  # mes 100% conhecido, nao ha o que sensibilizar

        ppi_lower = _custo_total_com_ii(lambda row: row.aliquota_ii if row.known else 0.10)
        ppi_upper = _custo_total_com_ii(lambda row: row.aliquota_ii if row.known else 0.14)
        if np.isnan(ppi_lower) or np.isnan(ppi_upper):
            continue
        linhas_result.append({
            "data": mes, "unknown_share": unk_kg / total_kg,
            "ppi_lower": ppi_lower, "ppi_upper": ppi_upper,
            "ppi_range_rs_t": ppi_upper - ppi_lower,
            "ppi_range_pct": (ppi_upper - ppi_lower) / ppi_lower if ppi_lower else np.nan,
        })
    res = pd.DataFrame(linhas_result)
    if res.empty:
        print("  Nenhum mes com dado suficiente para sensibilidade (verificar cambio/kg).")
        return res
    print(f"  meses avaliados: {len(res)}")
    print(f"  unknown_share: min={res['unknown_share'].min():.1%} mediana={res['unknown_share'].median():.1%} "
          f"max={res['unknown_share'].max():.1%}")
    print(f"  ppi_range_rs_t: min={res['ppi_range_rs_t'].min():.1f} mediana={res['ppi_range_rs_t'].median():.1f} "
          f"P90={res['ppi_range_rs_t'].quantile(.9):.1f} max={res['ppi_range_rs_t'].max():.1f}")
    print(f"  ppi_range_pct: min={res['ppi_range_pct'].min():.2%} mediana={res['ppi_range_pct'].median():.2%} "
          f"P90={res['ppi_range_pct'].quantile(.9):.2%} max={res['ppi_range_pct'].max():.2%}")
    piores = res.nlargest(5, "ppi_range_pct")
    print("  5 piores meses (maior range %):")
    for _, row in piores.iterrows():
        print(f"    {row['data']:%Y-%m}: unknown_share={row['unknown_share']:.1%} "
              f"ppi=[{row['ppi_lower']:.0f}, {row['ppi_upper']:.0f}] range={row['ppi_range_pct']:.2%}")
    return res


def analisar_origem(df: pd.DataFrame):
    print("\n=== Origem (pais) - participacao no volume total, 2012-presente ===")
    por_pais = df.groupby("country")["metricKG"].sum().sort_values(ascending=False)
    total = por_pais.sum()
    for pais, kg in por_pais.head(10).items():
        print(f"  {pais}: {kg/total:.1%}")


def testar_candidatos_threshold(resumo: pd.DataFrame, sens: pd.DataFrame, ini="2012-01-01", fim="2022-03-31"):
    print("\n=== Candidatos de LIMIAR_COBERTURA (janela A) ===")
    r = resumo[(resumo["data"] >= ini) & (resumo["data"] <= fim)].copy()
    s = sens.set_index("data") if not sens.empty else pd.DataFrame(columns=["ppi_range_pct"])
    for lim in (0.60, 0.75, 0.90, 0.95, 1.00):
        passa = r[r["coverage"] >= (lim - 1e-9)]
        falha = r[r["coverage"] < (lim - 1e-9)]
        kg_descartado = falha["total_kg"].sum()
        kg_total = r["total_kg"].sum()
        piores_no_grupo_que_passa = s.reindex(passa["data"])["ppi_range_pct"].dropna()
        pior_impacto = piores_no_grupo_que_passa.max() if len(piores_no_grupo_que_passa) else 0.0
        print(f"  limiar {lim:.0%}: {len(passa)}/{len(r)} meses calculaveis, "
              f"{len(falha)} UNKNOWN, {kg_descartado/kg_total:.1%} do volume total descartado/redistribuido, "
              f"pior impacto de PPI (%) entre os meses que passariam: {pior_impacto:.2%}")


if __name__ == "__main__":
    print("Coletando dados do Comex Stat (rede real, 5 janelas)...")
    df = coletar_tudo()
    print(f"\nTotal de registros brutos: {len(df)}")

    por_ncm_mes = montar_por_ncm_mes(df)
    resumo = montar_resumo_mensal(por_ncm_mes)

    relatar_janela(resumo, "A", "2012-01-01", "2022-03-31")
    relatar_janela(resumo, "B", "2022-04-01", "2025-12-31")
    relatar_janela(resumo, "C", "2026-01-01", "2026-12-31")

    sens = sensibilidade_ii(por_ncm_mes, df)
    testar_candidatos_threshold(resumo, sens)
    analisar_origem(df)
