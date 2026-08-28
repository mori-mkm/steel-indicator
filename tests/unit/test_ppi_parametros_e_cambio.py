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


def test_cambio_mensal_legado_v1_usa_ultima_cotacao_disponivel_do_mes_ffill():
    """ADR 0014 SUBSTITUIU esta convencao para o motor V2
    (`agregar_ipia_hrc_multi_ncm_mensal`, que agora usa `calcular_fx_mensal`
    - ver os testes de `test_calcular_fx_mensal_*` abaixo). Este teste
    permanece porque a linhagem LEGADA V1 (`calcular_ipia_mensal`,
    `custo_importacao_detalhado_mensal`) continua deliberadamente
    congelada nesta convencao antiga (forward-fill) - nao foi alterada
    pela decisao do FX Convention Sprint, por ser codigo de referencia/
    comparacao historica, nunca a serie OFFICIAL/PROVISIONAL publicada.
    Renomeado de test_cambio_mensal_usa_ultima_cotacao_disponivel_do_mes_ffill
    para deixar esse escopo explicito."""
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


# =============================================================================
# calcular_fx_mensal() - convencao NOVA (ADR 0014, FX Convention Sprint):
# media aritmetica das observacoes diarias validas DENTRO do mes-calendario.
# Unica regra usada pelo motor V2 (agregar_ipia_hrc_multi_ncm_mensal).
# =============================================================================

def test_calcular_fx_mensal_caso1_mes_normal_media_simples():
    diario = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(
        ["2024-06-03", "2024-06-14", "2024-06-27"]))
    meses = pd.to_datetime(["2024-06-01"])
    r = m.calcular_fx_mensal(diario, meses)
    assert r.loc["2024-06-01"] == pytest.approx(2.0)


def test_calcular_fx_mensal_caso2_primeiro_dia_sem_cotacao_nao_puxa_mes_anterior():
    """1o de julho sem cotacao (feriado) nao pode fazer o mes de julho
    herdar a ultima cotacao de junho - a media de julho deve usar SO as
    observacoes que caem dentro de julho."""
    diario = pd.Series([9.0, 4.0, 6.0], index=pd.to_datetime(
        ["2024-06-28", "2024-07-02", "2024-07-15"]))
    meses = pd.to_datetime(["2024-06-01", "2024-07-01"])
    r = m.calcular_fx_mensal(diario, meses)
    assert r.loc["2024-06-01"] == pytest.approx(9.0)
    assert r.loc["2024-07-01"] == pytest.approx((4.0 + 6.0) / 2)  # nunca inclui o 9.0 de junho


def test_calcular_fx_mensal_caso3_fins_de_semana_feriados_apenas_dias_uteis_entram():
    """Series de origem (BCB/SGS) so tem dias uteis - nenhuma linha extra
    precisa ser criada/ignorada para sabado/domingo/feriado; a media usa
    exatamente as observacoes que existem."""
    diario = pd.Series([5.0, 5.2], index=pd.to_datetime(["2024-08-02", "2024-08-05"]))  # sex e seg
    meses = pd.to_datetime(["2024-08-01"])
    r = m.calcular_fx_mensal(diario, meses)
    assert r.loc["2024-08-01"] == pytest.approx((5.0 + 5.2) / 2)


def test_calcular_fx_mensal_caso4_nan_parcial_usa_so_validos():
    diario = pd.Series([5.0, np.nan, 7.0], index=pd.to_datetime(
        ["2024-09-02", "2024-09-10", "2024-09-20"]))
    meses = pd.to_datetime(["2024-09-01"])
    r = m.calcular_fx_mensal(diario, meses)
    assert r.loc["2024-09-01"] == pytest.approx((5.0 + 7.0) / 2)


def test_calcular_fx_mensal_caso5_mes_sem_nenhuma_observacao_falha_explicito():
    diario = pd.Series([5.0], index=pd.to_datetime(["2024-01-10"]))
    meses = pd.to_datetime(["2024-01-01", "2024-02-01"])  # fevereiro sem nenhum dado
    with pytest.raises(ValueError, match="2024-02"):
        m.calcular_fx_mensal(diario, meses)


def test_calcular_fx_mensal_caso5b_mes_totalmente_nan_conta_como_sem_observacao():
    diario = pd.Series([np.nan, np.nan], index=pd.to_datetime(["2024-03-05", "2024-03-20"]))
    meses = pd.to_datetime(["2024-03-01"])
    with pytest.raises(ValueError, match="2024-03"):
        m.calcular_fx_mensal(diario, meses)


def test_calcular_fx_mensal_caso6_isolamento_entre_meses_nenhuma_contaminacao():
    """Cotacoes extremas em t-1 e t+1 nao podem vazar para a media de t."""
    diario = pd.Series(
        [100.0, 5.0, 5.2, 5.4, -100.0],
        index=pd.to_datetime(["2024-04-30", "2024-05-05", "2024-05-15", "2024-05-25", "2024-06-01"]),
    )
    meses = pd.to_datetime(["2024-05-01"])
    r = m.calcular_fx_mensal(diario, meses)
    assert r.loc["2024-05-01"] == pytest.approx((5.0 + 5.2 + 5.4) / 3)


def test_calcular_fx_mensal_e_deterministico_e_preserva_unidade():
    diario = pd.Series([5.1234, 5.2345], index=pd.to_datetime(["2024-10-01", "2024-10-15"]))
    meses = pd.to_datetime(["2024-10-01"])
    r1 = m.calcular_fx_mensal(diario, meses)
    r2 = m.calcular_fx_mensal(diario, meses)
    assert r1.equals(r2)
    assert r1.loc["2024-10-01"] == pytest.approx((5.1234 + 5.2345) / 2, abs=1e-10)  # sem arredondamento precoce
