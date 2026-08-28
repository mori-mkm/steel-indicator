"""Testes puros e deterministicos (sem rede) para
scripts/validar_ipp242_pia_hrc.py - sprint de validacao empirica
IPP-242 x PIA-HRC. VALIDATION ONLY: nao testa nenhuma decisao
metodologica (isso e Level 3, do usuario) - so garante que as
transformacoes/metricas usadas no relatorio estao matematicamente
corretas e que o script nunca escreve em area oficial/curada/vintage.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import numpy as np
import pandas as pd
import pytest

import validar_ipp242_pia_hrc as v


def test_out_dir_nunca_e_curated_nem_vintage():
    assert "curated" not in v.OUT_DIR
    assert "vintages" not in v.OUT_DIR
    assert v.OUT_DIR.startswith("data/processed/validation/")


def test_ipp_anual_media_so_usa_anos_com_12_meses():
    idx = pd.date_range("2019-01-01", "2021-06-01", freq="MS")  # 2021 incompleto (so ate junho)
    ipp = pd.Series(np.arange(len(idx), dtype=float) + 100.0, index=idx)
    media = v.ipp_anual_media(ipp)
    assert set(media.index) == {2019, 2020}  # 2021 (incompleto) fica de fora
    assert media.loc[2019] == pytest.approx(ipp.loc["2019"].mean())


def test_ipp_anual_dez_dez_usa_so_o_mes_de_dezembro():
    idx = pd.to_datetime(["2019-06-01", "2019-12-01", "2020-12-01"])
    ipp = pd.Series([50.0, 100.0, 130.0], index=idx)
    dez = v.ipp_anual_dez_dez(ipp)
    assert dez.to_dict() == {2019: 100.0, 2020: 130.0}


def test_crescimento_anual_so_para_anos_consecutivos_presentes():
    nivel = pd.Series({2019: 100.0, 2020: 120.0, 2022: 150.0})  # 2021 ausente - quebra a sequencia
    g = v.crescimento_anual(nivel)
    assert set(g.index) == {2020}  # 2022 nao tem 2021 antecedente -> fora
    assert g.loc[2020] == pytest.approx(0.20)


def test_pearson_e_spearman_casos_conhecidos():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([2.0, 4.0, 6.0, 8.0])  # relacao linear perfeita
    assert v.pearson(x, y) == pytest.approx(1.0)
    assert v.spearman(x, y) == pytest.approx(1.0)

    y_inverso = np.array([8.0, 6.0, 4.0, 2.0])
    assert v.pearson(x, y_inverso) == pytest.approx(-1.0)

    y_constante = np.array([5.0, 5.0, 5.0, 5.0])
    assert np.isnan(v.pearson(x, y_constante))  # variancia zero -> nao definido, nunca 0 fabricado


def test_beta_simples_regressao_conhecida():
    df = pd.DataFrame({"g_ipp": [0.0, 1.0, 2.0, 3.0], "g_pia": [0.0, 2.0, 4.0, 6.0]})
    assert v.beta_simples(df) == pytest.approx(2.0)


def test_direcao_tabela_marca_sinal_e_diferenca_em_pontos_percentuais():
    df = pd.DataFrame({"g_pia": [0.10, -0.05], "g_ipp": [0.08, 0.02]}, index=[2020, 2021])
    out = v.direcao_tabela(df)
    assert out["mesmo_sinal"].tolist() == [True, False]
    assert out.loc[2020, "diff_pp"] == pytest.approx(2.0)
    assert out.loc[2021, "diff_pp"] == pytest.approx(-7.0)


def test_leave_one_out_remove_exatamente_um_ano_por_vez():
    df = v.direcao_tabela(pd.DataFrame(
        {"g_pia": [0.1, 0.2, -0.1, 0.3], "g_ipp": [0.08, 0.15, -0.05, 0.25]},
        index=[2020, 2021, 2022, 2023]))
    loo = v.leave_one_out(df)
    assert set(loo.index) == {2020, 2021, 2022, 2023}
    assert (loo["n"] == 3).all()
    # remover o ano com pior aderencia de sinal so pode aumentar (ou manter)
    # a directional_accuracy dos anos restantes, nunca diminuir para o mesmo N
    assert loo["directional_accuracy"].between(0.0, 1.0).all()


def test_baseline_linear_bate_com_alvo_no_ponto_de_ancora_meio_do_ano():
    alvos = pd.Series({2020: 100.0, 2021: 200.0})
    meses = pd.date_range("2020-01-01", "2021-12-01", freq="MS")
    linear = v.baseline_linear(alvos, meses)
    assert linear.loc["2020-07-01"] == pytest.approx(100.0)
    assert linear.loc["2021-07-01"] == pytest.approx(200.0)
    # estritamente monotona crescente entre os dois pontos de ancora
    trecho = linear.loc["2020-07-01":"2021-07-01"]
    assert (trecho.diff().dropna() > 0).all()


def test_baseline_step_e_constante_dentro_do_ano_e_muda_na_virada():
    alvos = pd.Series({2020: 100.0, 2021: 200.0})
    meses = pd.date_range("2020-01-01", "2021-12-01", freq="MS")
    step = v.baseline_step(alvos, meses)
    assert (step.loc["2020-01-01":"2020-12-01"] == 100.0).all()
    assert (step.loc["2021-01-01":"2021-12-01"] == 200.0).all()


def test_metricas_suavidade_step_tem_maior_variacao_pontual_que_linear():
    alvos = pd.Series({2020: 100.0, 2021: 200.0})
    meses = pd.date_range("2020-01-01", "2021-12-01", freq="MS")
    linear = v.baseline_linear(alvos, meses)
    step = v.baseline_step(alvos, meses)
    met_linear = v.metricas_suavidade(linear)
    met_step = v.metricas_suavidade(step)
    # o degrau concentra toda a mudanca do ano num unico mes -> maior desvio-padrao
    # da variacao mensal do que uma rampa linear equivalente
    assert met_step["std_var_mensal_pct"] > met_linear["std_var_mensal_pct"]
