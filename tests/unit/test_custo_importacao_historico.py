"""Unit tests for custo_importacao_historico_mensal() - wiring do Historical
Import Policy Model (steel_indicator.parameters.trade_policy) ao calculo de
custo de importacao do IPIA-HRC (Stage E5, ADR 0009). Deterministic, no
network, no dependency on Comex/BCB.

Prova: regras historicas substituem parametros fixos quando aplicavel;
UNKNOWN nunca vira publication-grade nem e preenchido com zero/fallback;
antidumping usa effective_value (nunca nominal_value) no custo; legacy
(custo_importacao_rs_t/ParamsIPIA) permanece intacto; sem look-ahead.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import (
    STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN,
)


def _series_mes(data: str, fob=600.0, frete=20.0, seguro=2.0, cambio=5.0):
    idx = pd.DatetimeIndex([pd.Timestamp(data)])
    return (pd.Series([fob], index=idx), pd.Series([frete], index=idx),
            pd.Series([seguro], index=idx), pd.Series([cambio], index=idx))


# --- 1. 2024, NCM conhecido: II/AFRMM/AD historicos corretos, PUBLICATION_GRADE

def test_2024_ncm_conhecido_usa_regras_historicas_e_e_publication_grade():
    fob, frete, seguro, cambio = _series_mes("2024-06-01")
    r = m.custo_importacao_historico_mensal(fob, frete, seguro, cambio, ncm="72083700", origin="China")
    linha = r.iloc[0]
    assert linha["status"] == STATUS_PUBLICATION_GRADE
    assert linha["aliquota_ii"] == pytest.approx(0.108)
    assert linha["aliquota_afrmm"] == pytest.approx(0.08)
    assert linha["antidumping_usd_t"] == 0.0  # sem medida em 2024
    assert not np.isnan(linha["ppi_brl_t"])

    cif_usd = 600.0 + 20.0 + 2.0
    cif_brl = cif_usd * 5.0
    ii_esperado = cif_brl * 0.108
    afrmm_esperado = (20.0 * 5.0) * 0.08
    base_esperada = cif_brl + ii_esperado + afrmm_esperado + 0.0 + m.ParamsIPIA().despesas_porto_rs_t + m.ParamsIPIA().frete_interno_rs_t
    total_esperado = base_esperada * (1 + m.ParamsIPIA().margem_importador)
    assert linha["ii_brl_t"] == pytest.approx(ii_esperado)
    assert linha["afrmm_brl_t"] == pytest.approx(afrmm_esperado)
    assert linha["ppi_brl_t"] == pytest.approx(total_esperado)


# --- 2. 2018, NCM com II desconhecido: sem fallback para tarifa atual, nao publication-grade

def test_2018_ncm_com_ii_desconhecido_nao_usa_fallback_nem_e_publication_grade():
    fob, frete, seguro, cambio = _series_mes("2018-06-01")
    r = m.custo_importacao_historico_mensal(fob, frete, seguro, cambio, ncm="72081000", origin="China")
    linha = r.iloc[0]
    assert linha["status"] == STATUS_UNKNOWN
    assert linha["status"] != STATUS_PUBLICATION_GRADE
    assert pd.isna(linha["aliquota_ii"])
    assert linha["aliquota_ii"] != m.ParamsIPIA().aliquota_ii  # nunca usa 0.108 (tarifa atual) como fallback
    assert np.isnan(linha["ppi_brl_t"])
    assert np.isnan(linha["ii_brl_t"])


# --- 3. 2018/2019, antidumping nominal porem suspenso: custo efetivo zero ---

def test_antidumping_suspenso_usa_effective_value_zero_nao_nominal():
    fob, frete, seguro, cambio = _series_mes("2019-01-01")
    r = m.custo_importacao_historico_mensal(
        fob, frete, seguro, cambio, ncm="72083700", origin="China",
        exporter="Maanshan Iron & Steel Company Ltd.")
    linha = r.iloc[0]
    assert linha["status"] == STATUS_EXPERIMENTAL  # antes de 2022-04, mas todos os parametros conhecidos
    assert linha["antidumping_nominal_usd_t"] == pytest.approx(154.68)  # provenance preservada
    assert linha["antidumping_usd_t"] == 0.0  # efetivo usado no custo - suspenso
    assert linha["antidumping_brl_t"] == 0.0  # nao usa 154.68 * cambio no custo
    assert not np.isnan(linha["ppi_brl_t"])


# --- 4. Fronteira 2022-03-31 / 2022-04-01: mudanca correta de status --------

def test_fronteira_2022_03_31_e_experimental_2022_04_01_e_publication_grade():
    fob_a, frete_a, seguro_a, cambio_a = _series_mes("2022-03-31")
    fob_b, frete_b, seguro_b, cambio_b = _series_mes("2022-04-01")
    antes = m.custo_importacao_historico_mensal(fob_a, frete_a, seguro_a, cambio_a, ncm="72083700").iloc[0]
    depois = m.custo_importacao_historico_mensal(fob_b, frete_b, seguro_b, cambio_b, ncm="72083700").iloc[0]
    assert antes["status"] == STATUS_EXPERIMENTAL
    assert antes["aliquota_ii"] == pytest.approx(0.12)
    assert depois["status"] == STATUS_PUBLICATION_GRADE
    assert depois["aliquota_ii"] == pytest.approx(0.108)


# --- 5. 2026, NCM sujeito a cota com consumo desconhecido: UNKNOWN ---------

def test_2026_ncm_com_cota_e_consumo_desconhecido_fica_unknown():
    fob, frete, seguro, cambio = _series_mes("2026-07-01")
    r = m.custo_importacao_historico_mensal(fob, frete, seguro, cambio, ncm="72083910", origin="China")
    linha = r.iloc[0]
    assert linha["status"] == STATUS_UNKNOWN
    assert pd.isna(linha["aliquota_ii"])
    assert np.isnan(linha["ppi_brl_t"])


# --- 6. 2026, NCM NAO afetado pela cota: continua calculavel ---------------

def test_2026_ncm_sem_cota_continua_calculavel():
    fob, frete, seguro, cambio = _series_mes("2026-07-01")
    r = m.custo_importacao_historico_mensal(fob, frete, seguro, cambio, ncm="72081000", origin="China")
    linha = r.iloc[0]
    assert linha["status"] == STATUS_PUBLICATION_GRADE
    assert linha["aliquota_ii"] == pytest.approx(0.108)
    assert not np.isnan(linha["ppi_brl_t"])


# --- 7. ParamsIPIA legacy continua preservado -------------------------------

def test_legacy_custo_importacao_rs_t_nao_foi_alterado():
    fob, frete, seguro, cambio = _series_mes("2024-06-01")
    p = m.ParamsIPIA()
    r_legacy = m.custo_importacao_rs_t(fob, frete, seguro, cambio, p)
    linha = r_legacy.iloc[0]
    cif_usd = 600.0 + 20.0 + 2.0
    cif_brl = cif_usd * 5.0
    ii_esperado = cif_brl * p.aliquota_ii  # sempre 0.108, independente da data - comportamento antigo intacto
    assert linha["ii_brl_t"] == pytest.approx(ii_esperado)
    assert linha["antidumping_brl_t"] == pytest.approx(p.antidumping_usd_t * 5.0)


# --- 8. Ausencia de look-ahead ------------------------------------------------

def test_sem_look_ahead_2015_nao_usa_regime_2022():
    fob, frete, seguro, cambio = _series_mes("2015-01-01")
    r = m.custo_importacao_historico_mensal(fob, frete, seguro, cambio, ncm="72083700")
    linha = r.iloc[0]
    assert linha["aliquota_ii"] == pytest.approx(0.12)  # regime antigo, nao 0.108
    assert linha["status"] == STATUS_EXPERIMENTAL


# --- 9. Ausencia de fallback silencioso para parametro UNKNOWN -------------

def test_unknown_nunca_vira_zero_nem_usa_parametro_atual():
    fob, frete, seguro, cambio = _series_mes("2015-01-01")
    r = m.custo_importacao_historico_mensal(fob, frete, seguro, cambio, ncm="72082500")  # nao comprovado em 2015
    linha = r.iloc[0]
    assert linha["status"] == STATUS_UNKNOWN
    assert pd.isna(linha["aliquota_ii"])
    assert linha["aliquota_ii"] != m.ParamsIPIA().aliquota_ii
    # nenhuma coluna monetaria dependente do parametro faltante vira 0.0 (seria fallback silencioso) -
    # tem que ser NaN, explicitamente distinto de "custo zero".
    assert np.isnan(linha["ii_brl_t"])
    assert np.isnan(linha["ppi_brl_t"])
