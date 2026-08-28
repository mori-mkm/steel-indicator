#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATION ONLY - nao altera PPI, cesta NCM, landed cost, vintages,
publicacao, VERSAO_METODOLOGIA, pesos, thresholds nem reporting.

Sprint "COMEX UNIT VALUE x EXTERNAL HRC BENCHMARK": testa empiricamente a
materialidade do unit value bias ja documentado em docs/METODOLOGIA.md
Sec.9.7 - o FOB/kg observado pelo Comex Stat (`metricFOB / metricKG`, por
`mes x NCM x pais de origem`, Sec.9.5.2) acompanha um benchmark externo
independente de preco FOB de HRC?

Reusa a funcao de producao `_comex_bobina_bruto` (mesma cesta de 13 NCMs,
`NCM_BOBINA_QUENTE`) para o lado Comex - nunca reimplementa a busca nem
muda a cesta. O benchmark externo e construido aqui (nao existe em
producao): Tier 1 (Platts/Fastmarkets/Argus/Kallanish) confirmado
DATA ACCESS BLOCKED (paywalled) nesta etapa - ver
docs/validation/comex_unit_value_external_hrc_validation.md Sec. "Benchmark
inventory". Usa UN Comtrade (exportacao da China, mesmos codigos HS6 que
compoem a cesta HRC do projeto, reportado pela China, nao pelo Brasil) como
PRIMARY VALIDATION BENCHMARK gratuito e sistematico - com a mesma limitacao
conceitual de unit value que o proprio Comex Stat (nao e um price
assessment), disclosure explicito no artefato de validacao.

Faz chamadas de rede reais (Comex Stat, UN Comtrade publico) e cacheia os
resultados brutos em data/processed/validation_cache/ (gitignored, nunca
versionado) para nao repetir chamadas custosas durante iteracao - use
force=True nas funcoes de busca para re-buscar. Toda saida analitica vai
para data/processed/validation/comex_unit_value_hrc/ (validation artifact).

Uso:
    python scripts/validar_comex_unit_value_hrc.py
"""
from __future__ import annotations
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd
import requests

import indices_setoriais as m

OUT_DIR = "data/processed/validation/comex_unit_value_hrc"
CACHE_DIR = "data/processed/validation_cache"
CACHE_COMEX = f"{CACHE_DIR}/comex_hrc_bruto_2012_2026.csv"
CACHE_COMTRADE = f"{CACHE_DIR}/comtrade_china_export_hrc_2019_2026.csv"

# Prefixo HS6 dos 13 NCMs de 8 digitos em NCM_BOBINA_QUENTE (src/indices_setoriais.py) -
# mesma cesta conceitual ("em rolos", nao ligado, largura >=600mm), um nivel
# de agregacao acima (HS6 em vez de NCM de 8 digitos), porque a UN Comtrade
# nao expoe o desdobramento nacional de 8 digitos do Brasil para a China.
HS6_CODES = ["720810", "720825", "720826", "720827", "720836", "720837", "720838", "720839"]

JANELA_INI = "2019-01-01"  # overlap real: janela de publicacao do IPIA-HRC V2 (ADR 0013)

# Janelas de evento de politica comercial ja documentadas (trade_policy.py) -
# usadas so para anotar outliers, nunca para filtrar/excluir observacoes.
EVENTOS_POLITICA = [
    ("2018-01-19", "2020-01-17", "China: medida antidumping HRC suspensa (Res. CAMEX 2/2018 -> GECEX 5/2020)"),
    ("2025-06-03", None, "China: nova investigacao antidumping aberta (Circular SECEX 39/2025), sem direito provisorio"),
]


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


def pearson(x: pd.Series, y: pd.Series) -> float:
    """Pearson via numpy puro - evita dependencia nova (scipy) so por causa
    de `.corr(method=...)`, mesma convencao ja usada em
    scripts/validar_ipp242_pia_hrc.py."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x: pd.Series, y: pd.Series) -> float:
    if len(x) < 2:
        return float("nan")
    rx = pd.Series(np.asarray(x, dtype=float)).rank().to_numpy()
    ry = pd.Series(np.asarray(y, dtype=float)).rank().to_numpy()
    return pearson(rx, ry)


# =============================================================================
# 1. Comex Stat (Brasil) - reusa a funcao de producao, nunca reimplementa
# =============================================================================

def carregar_comex_bruto(ano_ini: int = 2012, ano_fim: int = 2026,
                          cache: str = CACHE_COMEX, force: bool = False) -> pd.DataFrame:
    if not force and os.path.exists(cache):
        df = pd.read_csv(cache, dtype={"coNcm": str})
    else:
        df = m._comex_bobina_bruto(ano_ini, ano_fim)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        df.to_csv(cache, index=False)
    for c in ("metricFOB", "metricKG", "metricFreight", "metricInsurance"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["data"] = pd.to_datetime(df["year"].astype(str) + "-"
                                 + df["monthNumber"].astype(str).str.zfill(2) + "-01")
    df["hs6"] = df["coNcm"].str[:6]
    return df


def uv_grupo_mensal(df: pd.DataFrame, country: str | None = None) -> pd.DataFrame:
    """UV_(ncm,country,t) = 1000 * fob_usd / kg, uma linha por (mes, NCM[8d], pais).
    country=None agrega todas as origens (mantem a coluna country por linha)."""
    d = df if country is None else df[df["country"] == country]
    g = (d.groupby(["data", "coNcm", "hs6", "country"], as_index=False)
           .agg(fob_usd=("metricFOB", "sum"), kg=("metricKG", "sum")))
    g = g[g["kg"] > 0].reset_index(drop=True)
    g["uv_usd_t"] = 1000 * g["fob_usd"] / g["kg"]
    return g


def uv_agregado_mensal(df: pd.DataFrame, country: str | None = None) -> pd.Series:
    """UV_HRC_t agregado (China-only se country='China'; all-origin se None) -
    mesma formula ja usada em producao por `serie_mensal_preco_bobina`
    (soma FOB / soma KG do mes, ponderado por volume, nao media simples)."""
    d = df if country is None else df[df["country"] == country]
    g = d.groupby("data").agg(fob_usd=("metricFOB", "sum"), kg=("metricKG", "sum")).reset_index()
    g = g[g["kg"] > 0]
    g["uv_usd_t"] = 1000 * g["fob_usd"] / g["kg"]
    return g.set_index("data")["uv_usd_t"].sort_index()


def volume_mensal(df: pd.DataFrame, country: str | None = None) -> pd.Series:
    d = df if country is None else df[df["country"] == country]
    return d.groupby("data")["metricKG"].sum().sort_index()


# =============================================================================
# 2. UN Comtrade (China, lado exportador) - PRIMARY VALIDATION BENCHMARK
# =============================================================================

COMTRADE_URL = "https://comtradeapi.un.org/public/v1/preview/C/M/HS"


def _comtrade_mes(periodo_yyyymm: str, tentativas: int = 5) -> list[dict]:
    """Um mes, todos os HS6_CODES numa unica chamada (endpoint preview aceita
    varios cmdCode separados por virgula, mas so 1 periodo por chamada -
    confirmado ao vivo nesta etapa). Sem chave de API (endpoint publico,
    tier gratuito de preview: max 500 registros/consulta, rate-limited)."""
    params = {"reporterCode": "156", "period": periodo_yyyymm, "partnerCode": "0",
              "flowCode": "X", "cmdCode": ",".join(HS6_CODES)}
    for i in range(tentativas):
        r = requests.get(COMTRADE_URL, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(3 + i * 2)
            continue
        r.raise_for_status()
        return r.json().get("data", [])
    raise RuntimeError(f"UN Comtrade rate-limited apos {tentativas} tentativas, periodo={periodo_yyyymm}")


def buscar_comtrade_china_export(ano_ini: int = 2019, cache: str = CACHE_COMTRADE,
                                  force: bool = False) -> pd.DataFrame:
    """Exportacao da China (reporterCode=156, flowCode=X, partnerCode=0=Mundo)
    dos mesmos codigos HS6 da cesta HRC do projeto - fonte independente
    (administracao aduaneira chinesa, nao brasileira), gratuita, sem chave.
    `fobvalue`/`netWgt` sao os campos nativos da API - China ja reporta
    exportacao em base FOB (mesma base conceitual do metricFOB do Comex
    Stat), confirmado ao vivo (cifvalue vem None para flow=X)."""
    if not force and os.path.exists(cache):
        return pd.read_csv(cache, parse_dates=["data"])
    hoje = pd.Timestamp.today().normalize().replace(day=1)
    meses = pd.date_range(f"{ano_ini}-01-01", hoje, freq="MS")
    linhas = []
    for i, dt in enumerate(meses):
        periodo = dt.strftime("%Y%m")
        try:
            dados = _comtrade_mes(periodo)
        except Exception as e:
            print(f"  [WARN] {periodo}: {e}")
            continue
        for row in dados:
            linhas.append({"data": dt, "hs6": row["cmdCode"],
                            "fob_usd": row.get("fobvalue"), "kg": row.get("netWgt")})
        if (i + 1) % 12 == 0:
            print(f"  ... UN Comtrade: {i + 1}/{len(meses)} meses buscados")
        time.sleep(1.2)
    df = pd.DataFrame(linhas)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    df.to_csv(cache, index=False)
    return df


def uv_comtrade_agregado_mensal(df_comtrade: pd.DataFrame) -> pd.Series:
    g = df_comtrade.groupby("data").agg(fob_usd=("fob_usd", "sum"), kg=("kg", "sum")).reset_index()
    g = g[g["kg"] > 0]
    g["uv_usd_t"] = 1000 * g["fob_usd"] / g["kg"]
    return g.set_index("data")["uv_usd_t"].sort_index()


# =============================================================================
# 3. Alinhamento e cobertura
# =============================================================================

def alinhar(comex: pd.Series, benchmark: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"comex": comex, "benchmark": benchmark}).dropna().sort_index()
    return df


def tabela_cobertura(comex: pd.Series, benchmark: pd.Series, overlap: pd.DataFrame) -> pd.DataFrame:
    def linha(nome, s):
        return {"serie": nome, "first_month": s.index.min().strftime("%Y-%m") if len(s) else None,
                "last_month": s.index.max().strftime("%Y-%m") if len(s) else None, "n_months": len(s)}
    return pd.DataFrame([
        linha("Comex China (import, Brasil)", comex),
        linha("UN Comtrade China (export, mundo)", benchmark),
        linha("Overlap (analise principal)", overlap["comex"] if len(overlap) else pd.Series(dtype=float)),
    ])


# =============================================================================
# 4. Level e change comparison
# =============================================================================

def metricas_nivel(df: pd.DataFrame) -> dict:
    spread = df["comex"] - df["benchmark"]
    spread_pct = df["comex"] / df["benchmark"] - 1
    return {"spread_mean": spread.mean(), "spread_median": spread.median(), "spread_std": spread.std(),
            "spread_p5": spread.quantile(.05), "spread_p25": spread.quantile(.25),
            "spread_p75": spread.quantile(.75), "spread_p95": spread.quantile(.95),
            "spread_min": spread.min(), "spread_max": spread.max(),
            "spread_pct_mean": spread_pct.mean(), "spread_pct_std": spread_pct.std(),
            "pearson_nivel": pearson(df["comex"], df["benchmark"]),
            "spearman_nivel": spearman(df["comex"], df["benchmark"])}, spread, spread_pct


def metricas_variacao(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    d = df.copy()
    d["d_comex"] = d["comex"].pct_change()
    d["d_benchmark"] = d["benchmark"].pct_change()
    d = d.dropna(subset=["d_comex", "d_benchmark"])
    pearson_mom = pearson(d["d_comex"], d["d_benchmark"])
    spearman_mom = spearman(d["d_comex"], d["d_benchmark"])
    return d, {"pearson_mom": pearson_mom, "spearman_mom": spearman_mom, "n_mom": len(d)}


def directional_accuracy(d: pd.DataFrame, limiar_abs: float | None = None) -> dict:
    mesmo_sinal = np.sign(d["d_comex"]) == np.sign(d["d_benchmark"])
    resultado = {"directional_accuracy": mesmo_sinal.mean(), "n": len(d)}
    if limiar_abs is not None:
        grandes = d[d["d_benchmark"].abs() >= limiar_abs]
        if len(grandes):
            resultado["directional_accuracy_grandes"] = (
                np.sign(grandes["d_comex"]) == np.sign(grandes["d_benchmark"])).mean()
            resultado["n_grandes"] = len(grandes)
            resultado["limiar_grandes"] = limiar_abs
    return resultado


def regressao_diagnostica(d: pd.DataFrame) -> dict:
    x = d["d_benchmark"].to_numpy()
    y = d["d_comex"].to_numpy()
    beta, alpha = np.polyfit(x, y, 1)
    pred = alpha + beta * x
    resid = y - pred
    ss_res = (resid ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot else np.nan
    return {"alpha": alpha, "beta": beta, "r2": r2, "resid_std": resid.std(), "n": len(d)}


# =============================================================================
# 5. Lags
# =============================================================================

def analise_lags(comex: pd.Series, benchmark: pd.Series, lags=(0, 1, 2)) -> pd.DataFrame:
    d_comex = comex.pct_change()
    linhas = []
    for lag in lags:
        d_bench = benchmark.shift(lag).pct_change()
        aligned = pd.DataFrame({"d_comex": d_comex, "d_bench": d_bench}).dropna()
        if len(aligned) < 3:
            linhas.append({"lag_meses": lag, "n": len(aligned), "pearson": np.nan})
            continue
        linhas.append({"lag_meses": lag, "n": len(aligned),
                        "pearson": aligned["d_comex"].corr(aligned["d_bench"])})
    return pd.DataFrame(linhas)


# =============================================================================
# 6. Rolling stability
# =============================================================================

def correlacao_rolling(d: pd.DataFrame, janela: int = 12) -> pd.Series:
    if len(d) < janela:
        return pd.Series(dtype=float)
    return d["d_comex"].rolling(janela).corr(d["d_benchmark"])


# =============================================================================
# 7. Analise por regime
# =============================================================================

REGIMES = [
    ("2019-01-01", "2019-12-31", "pre-choque (2019)"),
    ("2020-01-01", "2020-12-31", "2020 (choque COVID)"),
    ("2021-01-01", "2021-12-31", "2021 (supercycle)"),
    ("2022-01-01", "2023-12-31", "2022-2023 (normalizacao)"),
    ("2024-01-01", "2099-12-31", "2024+ (recente)"),
]


def analise_por_regime(d: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for ini, fim, nome in REGIMES:
        sub = d[(d.index >= ini) & (d.index <= fim)]
        if len(sub) < 3:
            linhas.append({"regime": nome, "n": len(sub), "pearson_mom": np.nan,
                            "directional_accuracy": np.nan, "nota": "N insuficiente (<3)"})
            continue
        da = (np.sign(sub["d_comex"]) == np.sign(sub["d_benchmark"])).mean()
        linhas.append({"regime": nome, "n": len(sub), "pearson_mom": sub["d_comex"].corr(sub["d_benchmark"]),
                        "directional_accuracy": da, "nota": ""})
    return pd.DataFrame(linhas)


# =============================================================================
# 8. Analise por NCM (dentro do HS6, granularidade real do Comex Stat)
# =============================================================================

def analise_por_ncm(grupo_china: pd.DataFrame, benchmark: pd.Series) -> pd.DataFrame:
    """Para cada NCM (8 digitos) com volume de origem China: share, UV medio,
    spread medio vs. benchmark (agregado, unico nivel disponivel do
    benchmark), volatilidade (desvio-padrao MoM %) e correlacao MoM com o
    benchmark - Sec.23 do sprint."""
    total_kg = grupo_china["kg"].sum()
    linhas = []
    for ncm, g in grupo_china.groupby("coNcm"):
        serie = g.set_index("data")["uv_usd_t"].sort_index()
        aligned = pd.DataFrame({"uv": serie, "bench": benchmark}).dropna()
        vol = serie.pct_change().std()
        corr_delta = np.nan
        if len(aligned) >= 6:
            d_uv = aligned["uv"].pct_change().dropna()
            d_bench = aligned["bench"].pct_change().dropna()
            comuns = d_uv.index.intersection(d_bench.index)
            if len(comuns) >= 4:
                corr_delta = d_uv.loc[comuns].corr(d_bench.loc[comuns])
        linhas.append({"ncm": ncm, "share_volume": g["kg"].sum() / total_kg,
                        "n_meses": len(g), "mean_uv_usd_t": serie.mean(),
                        "mean_spread_benchmark": (aligned["uv"] - aligned["bench"]).mean() if len(aligned) else np.nan,
                        "volatilidade_mom_std": vol, "corr_delta_benchmark": corr_delta})
    return pd.DataFrame(linhas).sort_values("share_volume", ascending=False)


# =============================================================================
# 9. Decomposicao within/between (shift-share) do mix de HS6
# =============================================================================

def decomposicao_mix(grupo_china: pd.DataFrame) -> pd.DataFrame:
    """d(UV_total) ~= efeito 'within' (preco, peso do periodo anterior fixo)
    + efeito 'mix/between' (mudanca de peso, preco do periodo anterior fixo)
    + interacao residual. So calculado sobre HS6 com volume>0 em AMBOS os
    meses do par (nunca inventa preco para um codigo que sumiu do mes) -
    Sec.24-25 do sprint."""
    pivot_kg = grupo_china.pivot_table(index="data", columns="hs6", values="kg", aggfunc="sum").fillna(0)
    pivot_fob = grupo_china.pivot_table(index="data", columns="hs6", values="fob_usd", aggfunc="sum").fillna(0)
    uv = 1000 * pivot_fob / pivot_kg.replace(0, np.nan)
    total_kg = pivot_kg.sum(axis=1)
    share = pivot_kg.div(total_kg, axis=0)
    uv_total = 1000 * pivot_fob.sum(axis=1) / total_kg

    meses = uv_total.index
    linhas = []
    for i in range(1, len(meses)):
        t0, t1 = meses[i - 1], meses[i]
        comuns = [c for c in pivot_kg.columns if pivot_kg.loc[t0, c] > 0 and pivot_kg.loc[t1, c] > 0]
        if len(comuns) < 2:
            linhas.append({"data": t1, "d_uv_total": uv_total[t1] - uv_total[t0],
                            "within_price": np.nan, "mix_between": np.nan, "interacao": np.nan,
                            "n_hs6_comuns": len(comuns), "nota": "menos de 2 HS6 comuns - nao decomposto"})
            continue
        w0 = share.loc[t0, comuns]
        w1 = share.loc[t1, comuns]
        p0 = uv.loc[t0, comuns]
        p1 = uv.loc[t1, comuns]
        within = (w0 * (p1 - p0)).sum()
        mix = ((w1 - w0) * p0).sum()
        d_total_comuns = (w1 * p1).sum() - (w0 * p0).sum()
        interacao = d_total_comuns - within - mix
        linhas.append({"data": t1, "d_uv_total": uv_total[t1] - uv_total[t0],
                        "within_price": within, "mix_between": mix, "interacao": interacao,
                        "n_hs6_comuns": len(comuns), "nota": ""})
    return pd.DataFrame(linhas).set_index("data")


# =============================================================================
# 10. Origem (composicao por pais)
# =============================================================================

def composicao_origem(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["data"] >= JANELA_INI]
    por_ano_pais = d.groupby([d["data"].dt.year, "country"])["metricKG"].sum().reset_index()
    por_ano_pais.columns = ["ano", "country", "kg"]
    total_ano = por_ano_pais.groupby("ano")["kg"].transform("sum")
    por_ano_pais["share"] = por_ano_pais["kg"] / total_ano
    linhas = []
    for ano, g in por_ano_pais.groupby("ano"):
        g = g.sort_values("share", ascending=False)
        china_share = g.loc[g["country"] == "China", "share"].sum()
        top3 = g.head(3)[["country", "share"]].to_dict("records")
        hhi = (g["share"] ** 2).sum()
        linhas.append({"ano": ano, "china_share": china_share, "hhi_paises": hhi,
                        "top3": "; ".join(f"{r['country']}={r['share']:.1%}" for r in top3)})
    return pd.DataFrame(linhas)


# =============================================================================
# 11. Outliers
# =============================================================================

def anotar_evento(data: pd.Timestamp) -> str:
    notas = []
    for ini, fim, nome in EVENTOS_POLITICA:
        ini_ts = pd.Timestamp(ini)
        fim_ts = pd.Timestamp(fim) if fim else pd.Timestamp("2099-12-31")
        if ini_ts <= data <= fim_ts:
            notas.append(nome)
    return "; ".join(notas)


def outliers(df_nivel: pd.DataFrame, spread: pd.Series, d_var: pd.DataFrame,
             grupo_china: pd.DataFrame, top_n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
    def contexto(data):
        mes = grupo_china[grupo_china["data"] == data]
        total_kg = mes["kg"].sum()
        n_hs6 = mes["hs6"].nunique()
        dominante = ""
        if len(mes):
            por_hs6 = mes.groupby("hs6")["kg"].sum().sort_values(ascending=False)
            dominante = f"{por_hs6.index[0]}={por_hs6.iloc[0] / total_kg:.1%}" if total_kg else ""
        return total_kg, n_hs6, dominante, anotar_evento(data)

    top_spread = spread.abs().sort_values(ascending=False).head(top_n)
    linhas_a = []
    for data, val in top_spread.items():
        total_kg, n_hs6, dominante, evento = contexto(data)
        linhas_a.append({"data": data.strftime("%Y-%m"), "spread_abs": spread[data],
                          "total_kg": total_kg, "n_hs6_ativos": n_hs6,
                          "hs6_dominante": dominante, "evento_politica": evento})

    d_var = d_var.copy()
    d_var["delta_diff"] = d_var["d_comex"] - d_var["d_benchmark"]
    top_delta = d_var["delta_diff"].abs().sort_values(ascending=False).head(top_n)
    linhas_b = []
    for data, val in top_delta.items():
        total_kg, n_hs6, dominante, evento = contexto(data)
        linhas_b.append({"data": data.strftime("%Y-%m"), "delta_diff_abs": val,
                          "d_comex_pct": d_var.loc[data, "d_comex"], "d_benchmark_pct": d_var.loc[data, "d_benchmark"],
                          "total_kg": total_kg, "n_hs6_ativos": n_hs6,
                          "hs6_dominante": dominante, "evento_politica": evento})
    return pd.DataFrame(linhas_a), pd.DataFrame(linhas_b)


# =============================================================================
# 12. Diagnostico de liquidez (sem threshold - so correlacao)
# =============================================================================

def diagnostico_liquidez(df_nivel: pd.DataFrame, spread_pct: pd.Series,
                          volume: pd.Series, grupo_china: pd.DataFrame) -> dict:
    erro_abs = spread_pct.abs()
    n_hs6_mes = grupo_china.groupby("data")["hs6"].nunique()
    vol_aligned = volume.reindex(erro_abs.index)
    nhs6_aligned = n_hs6_mes.reindex(erro_abs.index)
    return {"corr_volume_erro_abs": vol_aligned.corr(erro_abs),
            "corr_n_hs6_erro_abs": nhs6_aligned.corr(erro_abs),
            "n": len(erro_abs)}


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    secao("1. COMEX STAT (BRASIL) - cesta HRC bottom-up, NCM_BOBINA_QUENTE")
    df_comex = carregar_comex_bruto()
    grupo_china = uv_grupo_mensal(df_comex, country="China")
    grupo_china = grupo_china[grupo_china["data"] >= JANELA_INI]
    uv_china = uv_agregado_mensal(df_comex, country="China")
    uv_china = uv_china[uv_china.index >= JANELA_INI]
    uv_all = uv_agregado_mensal(df_comex, country=None)
    uv_all = uv_all[uv_all.index >= JANELA_INI]
    vol_china = volume_mensal(df_comex, country="China")
    vol_china = vol_china[vol_china.index >= JANELA_INI]
    print(f"UV_China_HRC_t: {len(uv_china)} meses, {uv_china.index.min():%Y-%m} a {uv_china.index.max():%Y-%m}")
    print(uv_china.tail(6))

    secao("2. UN COMTRADE (CHINA, EXPORTACAO) - PRIMARY VALIDATION BENCHMARK")
    df_comtrade = buscar_comtrade_china_export(ano_ini=2019)
    uv_bench = uv_comtrade_agregado_mensal(df_comtrade)
    print(f"UV_Comtrade_China_export_t: {len(uv_bench)} meses, "
          f"{uv_bench.index.min():%Y-%m} a {uv_bench.index.max():%Y-%m}" if len(uv_bench) else "VAZIO")
    print(uv_bench.tail(6))

    secao("3. COBERTURA E ALINHAMENTO")
    overlap = alinhar(uv_china, uv_bench)
    cobertura = tabela_cobertura(uv_china, uv_bench, overlap)
    print(cobertura.to_string(index=False))
    cobertura.to_csv(f"{OUT_DIR}/cobertura.csv", index=False)
    overlap.to_csv(f"{OUT_DIR}/serie_alinhada.csv")

    secao("4. LEVEL COMPARISON")
    m_nivel, spread, spread_pct = metricas_nivel(overlap)
    for k, v in m_nivel.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    secao("5. CHANGE COMPARISON (MoM)")
    d_var, m_var = metricas_variacao(overlap)
    for k, v in m_var.items():
        print(f"  {k}: {v}")
    d_var.to_csv(f"{OUT_DIR}/variacao_mensal.csv")

    secao("6. DIRECTIONAL ACCURACY")
    da = directional_accuracy(d_var, limiar_abs=0.03)
    for k, v in da.items():
        print(f"  {k}: {v}")

    secao("7. REGRESSAO DIAGNOSTICA (MoM)")
    reg = regressao_diagnostica(d_var)
    for k, v in reg.items():
        print(f"  {k}: {v}")

    secao("8. LAGS")
    lags = analise_lags(uv_china, uv_bench)
    print(lags.to_string(index=False))
    lags.to_csv(f"{OUT_DIR}/lags.csv", index=False)

    secao("9. ROLLING CORRELATION (12m)")
    roll = correlacao_rolling(d_var, janela=12)
    if len(roll.dropna()):
        print(roll.describe())
        roll.to_csv(f"{OUT_DIR}/rolling_corr_12m.csv")
    else:
        print("  N insuficiente para rolling de 12 meses")

    secao("10. ANALISE POR REGIME")
    regime = analise_por_regime(d_var)
    print(regime.to_string(index=False))
    regime.to_csv(f"{OUT_DIR}/regime.csv", index=False)

    secao("11. ANALISE POR NCM")
    ncm_tab = analise_por_ncm(grupo_china, uv_bench)
    print(ncm_tab.to_string(index=False))
    ncm_tab.to_csv(f"{OUT_DIR}/ncm_analysis.csv", index=False)

    secao("12. DECOMPOSICAO MIX (within/between)")
    mix = decomposicao_mix(grupo_china)
    print(mix.to_string())
    mix.to_csv(f"{OUT_DIR}/mix_decomposicao.csv")

    secao("13. ORIGEM (composicao por pais)")
    origem = composicao_origem(df_comex)
    print(origem.to_string(index=False))
    origem.to_csv(f"{OUT_DIR}/origem.csv", index=False)

    secao("14. AGREGADO ALL-ORIGIN vs BENCHMARK (SECUNDARIO)")
    overlap_all = alinhar(uv_all, uv_bench)
    m_nivel_all, spread_all, spread_pct_all = metricas_nivel(overlap_all)
    d_var_all, m_var_all = metricas_variacao(overlap_all)
    da_all = directional_accuracy(d_var_all)
    print(f"  N overlap all-origin: {len(overlap_all)}")
    print(f"  pearson nivel: {m_nivel_all['pearson_nivel']:.4f}  pearson MoM: {m_var_all['pearson_mom']:.4f}")
    print(f"  directional accuracy: {da_all['directional_accuracy']:.4f}")
    print(f"  spread_pct medio: {m_nivel_all['spread_pct_mean']:.4f}")

    secao("15. OUTLIERS")
    out_a, out_b = outliers(overlap, spread, d_var, grupo_china)
    print("-- Top |spread| (nivel) --")
    print(out_a.to_string(index=False))
    print("-- Top |delta_diff| (MoM) --")
    print(out_b.to_string(index=False))
    out_a.to_csv(f"{OUT_DIR}/outliers_nivel.csv", index=False)
    out_b.to_csv(f"{OUT_DIR}/outliers_variacao.csv", index=False)

    secao("16. DIAGNOSTICO DE LIQUIDEZ")
    liq = diagnostico_liquidez(overlap, spread_pct, vol_china, grupo_china)
    for k, v in liq.items():
        print(f"  {k}: {v}")

    secao("FIM - artefatos salvos em " + OUT_DIR)


if __name__ == "__main__":
    main()
