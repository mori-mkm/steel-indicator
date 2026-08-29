"""Testes puros e deterministicos (sem rede) para
scripts/validar_comex_unit_value_hrc.py - sprint "COMEX UNIT VALUE x
EXTERNAL HRC BENCHMARK". VALIDATION ONLY: nao testa nenhuma decisao
metodologica (isso e Level 3, do usuario) - so garante que as
transformacoes/metricas reutilizaveis usadas no artefato de validacao
estao matematicamente corretas.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import numpy as np
import pandas as pd
import pytest

import validar_comex_unit_value_hrc as v


def test_out_dir_e_cache_nunca_sao_curated_nem_vintage():
    assert "curated" not in v.OUT_DIR
    assert "vintages" not in v.OUT_DIR
    assert v.OUT_DIR.startswith("data/processed/validation/")
    assert "curated" not in v.CACHE_COMEX
    assert "vintages" not in v.CACHE_COMEX


def _df_bruto(linhas):
    """Monta um df no formato de _comex_bobina_bruto ja com 'data'/'hs6'
    calculados (mesmo que carregar_comex_bruto produz)."""
    df = pd.DataFrame(linhas)
    df["data"] = pd.to_datetime(df["data"])
    df["hs6"] = df["coNcm"].str[:6]
    return df


def test_uv_agregado_mensal_e_ponderado_por_volume_nao_media_simples():
    # dois NCMs no mesmo mes/pais: preco medio ponderado != media simples dos UVs individuais
    df = _df_bruto([
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 100_000, "metricKG": 200_000},
        {"data": "2023-01-01", "coNcm": "72083990", "country": "China", "metricFOB": 900_000, "metricKG": 900_000},
    ])
    uv = v.uv_agregado_mensal(df, country="China")
    esperado = 1000 * (100_000 + 900_000) / (200_000 + 900_000)
    assert uv.loc[pd.Timestamp("2023-01-01")] == pytest.approx(esperado)
    media_simples_errada = (500.0 + 1000.0) / 2
    assert uv.loc[pd.Timestamp("2023-01-01")] != pytest.approx(media_simples_errada)


def test_uv_agregado_mensal_descarta_kg_zero_nunca_fabrica_preco():
    df = _df_bruto([
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 100_000, "metricKG": 0},
        {"data": "2023-02-01", "coNcm": "72083700", "country": "China", "metricFOB": 50_000, "metricKG": 100_000},
    ])
    uv = v.uv_agregado_mensal(df, country="China")
    assert pd.Timestamp("2023-01-01") not in uv.index  # kg=0 nunca vira ponto de dado
    assert uv.loc[pd.Timestamp("2023-02-01")] == pytest.approx(500.0)


def test_uv_grupo_mensal_uma_linha_por_mes_ncm_pais():
    df = _df_bruto([
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 100_000, "metricKG": 200_000},
        {"data": "2023-01-01", "coNcm": "72083990", "country": "China", "metricFOB": 50_000, "metricKG": 100_000},
        {"data": "2023-01-01", "coNcm": "72083700", "country": "Coreia do Sul", "metricFOB": 30_000, "metricKG": 60_000},
    ])
    g = v.uv_grupo_mensal(df, country="China")
    assert len(g) == 2  # China: 2 NCMs, Coreia do Sul filtrada fora
    assert set(g["coNcm"]) == {"72083700", "72083990"}


def test_alinhar_faz_inner_join_por_data_dropna():
    comex = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01"]))
    benchmark = pd.Series([10.0, np.nan, 30.0], index=pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01"]))
    df = v.alinhar(comex, benchmark)
    assert list(df.index) == [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-03-01")]  # fev descartado (NaN)


def test_metricas_nivel_spread_e_spread_pct():
    df = pd.DataFrame({"comex": [110.0, 90.0], "benchmark": [100.0, 100.0]},
                       index=pd.to_datetime(["2023-01-01", "2023-02-01"]))
    metricas, spread, spread_pct = v.metricas_nivel(df)
    assert spread.tolist() == pytest.approx([10.0, -10.0])
    assert spread_pct.tolist() == pytest.approx([0.10, -0.10])
    assert metricas["spread_mean"] == pytest.approx(0.0)


def test_directional_accuracy_conta_mesmo_sinal():
    d = pd.DataFrame({"d_comex": [0.05, -0.03, 0.02], "d_benchmark": [0.04, 0.01, -0.01]})
    da = v.directional_accuracy(d)
    # mesmo sinal: linha0 (+/+) sim, linha1 (-/+) nao, linha2 (+/-) nao -> 1/3
    assert da["directional_accuracy"] == pytest.approx(1 / 3)
    assert da["n"] == 3


def test_directional_accuracy_grandes_usa_limiar_analitico():
    d = pd.DataFrame({"d_comex": [0.05, -0.01], "d_benchmark": [0.04, 0.01]})
    da = v.directional_accuracy(d, limiar_abs=0.03)
    assert da["n_grandes"] == 1  # so a primeira linha tem |d_benchmark|>=3%
    assert da["directional_accuracy_grandes"] == pytest.approx(1.0)


def test_analise_lags_recupera_correlacao_no_lag_correto():
    # benchmark antecipa comex em 1 mes: comex(t) = benchmark(t-1)
    idx = pd.date_range("2023-01-01", periods=8, freq="MS")
    benchmark = pd.Series(np.linspace(100, 170, 8), index=idx)
    comex = benchmark.shift(1).dropna()
    comex = pd.concat([pd.Series([90.0], index=[idx[0]]), comex])  # completa o primeiro mes
    lags = v.analise_lags(comex, benchmark, lags=(0, 1, 2))
    melhor = lags.loc[lags["pearson"].idxmax(), "lag_meses"]
    assert melhor == 1


def test_pearson_e_spearman_sem_scipy_casos_conhecidos():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([2.0, 4.0, 6.0, 8.0])
    assert v.pearson(x, y) == pytest.approx(1.0)
    assert v.spearman(x, y) == pytest.approx(1.0)
    y_constante = np.array([5.0, 5.0, 5.0, 5.0])
    assert np.isnan(v.pearson(x, y_constante))  # variancia zero -> nao definido, nunca 0 fabricado


def test_decomposicao_mix_soma_within_mais_mix_mais_interacao_bate_com_delta_dos_codigos_comuns():
    # dois HS6, dois meses, ambos presentes nos dois meses (n_hs6_comuns=2)
    grupo = pd.DataFrame([
        {"data": pd.Timestamp("2023-01-01"), "hs6": "720837", "kg": 100.0, "fob_usd": 50_000.0},
        {"data": pd.Timestamp("2023-01-01"), "hs6": "720839", "kg": 100.0, "fob_usd": 60_000.0},
        {"data": pd.Timestamp("2023-02-01"), "hs6": "720837", "kg": 150.0, "fob_usd": 82_500.0},
        {"data": pd.Timestamp("2023-02-01"), "hs6": "720839", "kg": 50.0, "fob_usd": 27_500.0},
    ])
    out = v.decomposicao_mix(grupo)
    linha = out.loc[pd.Timestamp("2023-02-01")]
    assert linha["n_hs6_comuns"] == 2
    soma = linha["within_price"] + linha["mix_between"] + linha["interacao"]
    # com os dois codigos comuns aos dois meses, within+mix+interacao reconstroi
    # exatamente a variacao do UV total ponderado (identidade shift-share)
    w0 = pd.Series({"720837": 0.5, "720839": 0.5})
    w1 = pd.Series({"720837": 0.75, "720839": 0.25})
    p0 = pd.Series({"720837": 500.0, "720839": 600.0})
    p1 = pd.Series({"720837": 550.0, "720839": 550.0})
    delta_ponderado = (w1 * p1).sum() - (w0 * p0).sum()
    assert soma == pytest.approx(delta_ponderado)


def test_decomposicao_mix_marca_menos_de_2_codigos_comuns_como_nao_computavel():
    grupo = pd.DataFrame([
        {"data": pd.Timestamp("2023-01-01"), "hs6": "720837", "kg": 100.0, "fob_usd": 50_000.0},
        {"data": pd.Timestamp("2023-02-01"), "hs6": "720839", "kg": 100.0, "fob_usd": 60_000.0},  # codigo diferente
    ])
    out = v.decomposicao_mix(grupo)
    linha = out.loc[pd.Timestamp("2023-02-01")]
    assert linha["n_hs6_comuns"] == 0
    assert np.isnan(linha["within_price"])
    assert "nao decomposto" in linha["nota"]
