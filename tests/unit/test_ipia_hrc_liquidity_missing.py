"""Testes puros e deterministicos (sem rede) para
scripts/analisar_ipia_hrc_liquidez.py e scripts/auditar_ipia_hrc_missing.py -
sprint "IPIA-HRC - LIQUIDITY/CONCENTRATION HARDENING + MISSING DATA AUDIT".
VALIDATION ONLY: nao testa nenhuma decisao metodologica (isso e Level 3, do
usuario) - so garante que HHI/effective number/shares/coverage/classificacao
estao matematicamente corretos e que nenhuma funcao muta o dado de entrada.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import numpy as np
import pandas as pd
import pytest

import analisar_ipia_hrc_liquidez as lq
import auditar_ipia_hrc_missing as aud


def _df_bruto(linhas):
    df = pd.DataFrame(linhas)
    df["data"] = pd.to_datetime(df["data"])
    return df


# =============================================================================
# HHI / effective number / concentration shares
# =============================================================================

def test_hhi_e_1_0_quando_uma_unica_origem_domina_o_mes():
    df = _df_bruto([
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 100_000, "metricKG": 200_000},
    ])
    diag = lq.diagnosticos_mensais(df)
    linha = diag.loc[pd.Timestamp("2023-01-01")]
    assert linha["hhi_origin_0_1"] == pytest.approx(1.0)
    assert linha["hhi_origin_0_10000"] == pytest.approx(10000.0)
    assert linha["effective_origins"] == pytest.approx(1.0)
    assert linha["n_origins"] == 1
    assert linha["share_largest_origin"] == pytest.approx(1.0)


def test_hhi_com_duas_origens_iguais_da_05_e_effective_number_2():
    df = _df_bruto([
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 50_000, "metricKG": 100_000},
        {"data": "2023-01-01", "coNcm": "72083700", "country": "Coreia do Sul", "metricFOB": 50_000, "metricKG": 100_000},
    ])
    diag = lq.diagnosticos_mensais(df)
    linha = diag.loc[pd.Timestamp("2023-01-01")]
    assert linha["hhi_origin_0_1"] == pytest.approx(0.5)
    assert linha["effective_origins"] == pytest.approx(2.0)
    assert linha["n_origins"] == 2
    assert linha["share_largest_origin"] == pytest.approx(0.5)


def test_hhi_ncm_e_shares_top3_calculados_sobre_participacao_em_kg():
    # 3 NCMs com kg 500/300/200 (mesmo pais) - shares 0.5/0.3/0.2
    df = _df_bruto([
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 1, "metricKG": 500},
        {"data": "2023-01-01", "coNcm": "72083990", "country": "China", "metricFOB": 1, "metricKG": 300},
        {"data": "2023-01-01", "coNcm": "72083910", "country": "China", "metricFOB": 1, "metricKG": 200},
    ])
    diag = lq.diagnosticos_mensais(df)
    linha = diag.loc[pd.Timestamp("2023-01-01")]
    assert linha["share_largest_ncm"] == pytest.approx(0.5)
    assert linha["share_top3_ncm"] == pytest.approx(1.0)  # os 3 juntos = 100%
    hhi_esperado = 0.5 ** 2 + 0.3 ** 2 + 0.2 ** 2
    assert linha["hhi_ncm_0_1"] == pytest.approx(hhi_esperado)
    assert linha["effective_ncms"] == pytest.approx(1 / hhi_esperado)
    assert linha["n_active_ncm"] == 3


def test_diagnosticos_mensais_descarta_kg_zero_e_ignora_meses_fora_da_janela():
    df = _df_bruto([
        {"data": "2018-12-01", "coNcm": "72083700", "country": "China", "metricFOB": 100, "metricKG": 100},  # antes da janela
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 100, "metricKG": 0},   # kg=0
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 100, "metricKG": 100},
    ])
    diag = lq.diagnosticos_mensais(df)
    assert pd.Timestamp("2018-12-01") not in diag.index  # fora da janela (Sec.3 do sprint: >= JANELA_INI)
    assert diag.loc[pd.Timestamp("2023-01-01"), "total_kg"] == pytest.approx(100)  # so a linha com kg>0


def test_diagnosticos_mensais_nao_muta_o_dataframe_de_entrada():
    df = _df_bruto([
        {"data": "2023-01-01", "coNcm": "72083700", "country": "China", "metricFOB": 100, "metricKG": 200},
    ])
    original = df.copy(deep=True)
    lq.diagnosticos_mensais(df)
    pd.testing.assert_frame_equal(df, original)


def test_china_share_e_zero_quando_china_nao_importou_no_mes():
    df = _df_bruto([
        {"data": "2023-01-01", "coNcm": "72083700", "country": "Coreia do Sul", "metricFOB": 100, "metricKG": 200},
    ])
    diag = lq.diagnosticos_mensais(df)
    assert diag.loc[pd.Timestamp("2023-01-01"), "china_share"] == pytest.approx(0.0)


# =============================================================================
# por_quantil - grupos analiticos, nunca threshold de producao
# =============================================================================

def test_por_quantil_agrupa_em_bottom25_middle50_top25():
    idx = pd.date_range("2023-01-01", periods=8, freq="MS")
    painel = pd.DataFrame({
        "total_kg": [10, 20, 30, 40, 50, 60, 70, 80],
        "d_uv_all_abs": [0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05, 0.02],
        "abs_external_error_china": [np.nan] * 8,
        "hhi_origin_0_1": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2],
        "hhi_ncm_0_1": [0.5] * 8,
    }, index=idx)
    agg = lq.por_quantil(painel, "total_kg")
    assert set(agg.index.astype(str)) == {"bottom25", "middle50", "top25"}
    assert agg.loc["bottom25", "n_meses"] == 2  # 25% de 8 = 2
    assert agg.loc["top25", "n_meses"] == 2
    assert agg.loc["middle50", "n_meses"] == 4
    # instabilidade media cai com volume (dado construido deliberadamente assim)
    assert agg.loc["bottom25", "d_uv_all_abs_medio"] > agg.loc["top25", "d_uv_all_abs_medio"]


# =============================================================================
# Missing-data taxonomy / coverage (auditar_ipia_hrc_missing)
# =============================================================================

def test_coverage_pct_casos_basicos():
    assert aud.coverage_pct(91, 91) == pytest.approx(1.0)
    assert aud.coverage_pct(78, 91) == pytest.approx(78 / 91)
    assert aud.coverage_pct(0, 91) == pytest.approx(0.0)


def test_coverage_pct_nunca_fabrica_numero_quando_esperado_e_zero():
    assert np.isnan(aud.coverage_pct(0, 0))


def test_linha_cobertura_calcula_missing_e_coverage_corretamente():
    linha = aud.linha_cobertura("componente teste", "2019-01", "2020-12", "mensal", 20, 24, aud.TECHNICAL_MISSING)
    assert linha["missing"] == 4
    assert linha["coverage_pct"] == pytest.approx(20 / 24)
    assert linha["missing_type"] == aud.TECHNICAL_MISSING


def test_linha_cobertura_aceita_n_expected_none_sem_fabricar_percentual():
    linha = aud.linha_cobertura("parametro estrutural", "n/a", "n/a", "n/a (constante)", 0, None,
                                 aud.STRUCTURAL_PARAMETER)
    assert linha["missing"] is None
    assert np.isnan(linha["coverage_pct"])


def test_candidatos_imputacao_cobre_toda_a_taxonomia_e_nunca_recomenda_yes_direto():
    cand = aud.candidatos_imputacao()
    tipos_cobertos = set(cand["tipo"])
    assert tipos_cobertos == set(aud.TAXONOMIA)  # as 6 categorias, todas representadas
    # nenhum candidato desta etapa deve ser YES puro (Sec.28: "somente identifique
    # candidatos, NAO implemente" - YES direto seria prescricao de implementacao)
    assert "YES" not in cand["model_imputation_suitable"].tolist()


def test_montar_matriz_mensal_marca_estrutural_como_not_applicable_sempre():
    idx_original = aud.JANELA_INI, aud.JANELA_FIM
    serie_import = pd.DataFrame({
        "reference_period": pd.date_range("2019-01-01", "2019-03-01", freq="MS"),
        "publication_status": ["UNKNOWN", "EXPERIMENTAL", "PUBLICATION_GRADE"],
    })
    pia = pd.Series([1000.0], index=pd.Index([2019], name="ano"))
    ipp = pd.Series([100.0, 101.0, 102.0], index=pd.date_range("2019-01-01", "2019-03-01", freq="MS"))
    # restringe a janela do teste sem depender da janela real do sprint (2019-2026)
    aud.JANELA_INI, aud.JANELA_FIM = "2019-01-01", "2019-03-01"
    try:
        matriz = aud.montar_matriz_mensal(serie_import, pia, ipp)
    finally:
        aud.JANELA_INI, aud.JANELA_FIM = idx_original
    assert (matriz["structural_params"] == "NOT_APPLICABLE").all()
    assert matriz.loc[pd.Timestamp("2019-01-01"), "import_side"] == "MISSING"
    assert matriz.loc[pd.Timestamp("2019-02-01"), "import_side"] == "ESTIMATED"
    assert matriz.loc[pd.Timestamp("2019-03-01"), "import_side"] == "OBSERVED"
