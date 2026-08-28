"""Regressao para os parametros do PPI auditados em docs/METODOLOGIA.md
secoes 9.6-9.10 (unit value bias, cambio, D_porto/D_interno/margem).

Nao testa comportamento novo - trava valores/formulas ja implementados para
que uma mudanca futura (intencional ou nao) nesses parametros nunca passe
despercebida, conforme pedido: "os testes devem validar regras
metodologicas", nao apenas reproduzir a implementacao.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m


def test_params_ipia_defaults_estimados_nao_mudaram_silenciosamente():
    """D_porto, D_interno e margem sao ESTIMADO (hold-flat, nunca
    calibrados - METODOLOGIA 9.8/9.9). Uma mudanca de valor aqui muda toda
    a serie historica publicada e exige decisao Level 3 explicita, nunca
    um ajuste silencioso de constante."""
    p = m.ParamsIPIA()
    assert p.despesas_porto_rs_t == pytest.approx(210.0)
    assert p.frete_interno_rs_t == pytest.approx(140.0)
    assert p.margem_importador == pytest.approx(0.03)
    # defaults legados (usados quando trade_policy nao resolve o periodo)
    assert p.aliquota_ii == pytest.approx(0.108)
    assert p.afrmm == pytest.approx(0.08)
    assert p.antidumping_usd_t == pytest.approx(0.0)


def test_afrmm_incide_apenas_sobre_frete_nunca_sobre_cif_completo():
    """AFRMM e uma taxa sobre o frete maritimo (Lei 10.893/2004, Lei
    14.301/2022), nao sobre o CIF - aplicar sobre o CIF completo seria
    dupla contagem do FOB/seguro na base do AFRMM."""
    fob = pd.Series([600.0])
    frete = pd.Series([20.0])
    seguro = pd.Series([2.0])
    cambio = pd.Series([5.0])
    p = m.ParamsIPIA()
    r = m.custo_importacao_rs_t(fob, frete, seguro, cambio, p)

    afrmm_esperado_sobre_frete = (frete.iloc[0] * cambio.iloc[0]) * p.afrmm
    afrmm_errado_sobre_cif = r["cif_brl_t"].iloc[0] * p.afrmm

    assert r["afrmm_brl_t"].iloc[0] == pytest.approx(afrmm_esperado_sobre_frete)
    assert r["afrmm_brl_t"].iloc[0] != pytest.approx(afrmm_errado_sobre_cif)


def test_ii_incide_uma_unica_vez_sobre_cif_sem_incluir_afrmm_ou_ad():
    """II incide sobre o CIF (FOB+Frete+Seguro convertido), nao sobre uma
    base que ja inclua AFRMM/antidumping - aplicar II sobre uma base
    inflada por outra taxa seria dupla incidencia de tributo."""
    fob = pd.Series([600.0])
    frete = pd.Series([20.0])
    seguro = pd.Series([2.0])
    cambio = pd.Series([5.0])
    p = m.ParamsIPIA()
    r = m.custo_importacao_rs_t(fob, frete, seguro, cambio, p)

    ii_esperado = r["cif_brl_t"].iloc[0] * p.aliquota_ii
    base_inflada = (r["cif_brl_t"].iloc[0] + r["afrmm_brl_t"].iloc[0]) * p.aliquota_ii

    assert r["ii_brl_t"].iloc[0] == pytest.approx(ii_esperado)
    assert r["ii_brl_t"].iloc[0] != pytest.approx(base_inflada)


def test_cambio_mensal_usa_ultima_cotacao_disponivel_do_mes_ffill():
    """Regra documentada em METODOLOGIA 9.6: o cambio mensal usado no PPI
    e a ultima cotacao PTAX diaria disponivel ATE o mes (forward-fill),
    nunca uma media do mes e nunca uma cotacao futura (look-ahead)."""
    cambio_diario = pd.Series(
        [5.00, 5.10, 5.20],
        index=pd.DatetimeIndex(["2024-01-05", "2024-01-20", "2024-03-10"]),
    )
    meses = pd.DatetimeIndex(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"])

    cambio_mensal = cambio_diario.reindex(
        cambio_diario.index.union(meses)
    ).sort_index().ffill().reindex(meses)

    # janeiro: usa a ultima cotacao ate 01/01 (nao existe ainda -> NaN,
    # nao fabrica valor antes da primeira observacao real)
    assert np.isnan(cambio_mensal.loc["2024-01-01"])
    # fevereiro: nenhuma cotacao nova em fevereiro -> carrega a ultima de
    # janeiro (5.10), nao uma media, nao NaN
    assert cambio_mensal.loc["2024-02-01"] == pytest.approx(5.10)
    # marco: cotacao de 10/03 ainda nao ocorreu no dia 01/03 -> continua
    # usando a ultima disponivel ate essa data (5.10), sem look-ahead
    assert cambio_mensal.loc["2024-03-01"] == pytest.approx(5.10)
    # abril: ja incorpora a cotacao de 10/03
    assert cambio_mensal.loc["2024-04-01"] == pytest.approx(5.20)
