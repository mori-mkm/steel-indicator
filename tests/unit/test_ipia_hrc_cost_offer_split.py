"""Unit tests for the IPIA-HRC Cost/Offer scope split (decisao Level 3
aprovada, docs/validation/ipia_hrc_import_parity_scope.md, ADR 0015,
VERSAO_METODOLOGIA 1.5): a serie oficial (`agregar_ipia_hrc_multi_ncm_mensal`
-> `ipia`) passa a usar PPI_COST (CIF+II+AFRMM+AD+D_porto+D_interno, SEM
margem comercial) em vez do PPI antigo (mesma soma x (1+margem)). A margem
vira camada analitica opcional (`calcular_ppi_offer`), nunca embutida
silenciosamente no core.

Deterministic, no network - mesmo padrao de stub/injecao de
test_ipia_hrc_multi_ncm.py.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import STATUS_PUBLICATION_GRADE


def _linha(ano, mes, ncm, country="China", fob=6_000_000.0, kg=10_000_000.0, frete=200_000.0, seguro=20_000.0):
    return {"year": ano, "monthNumber": mes, "coNcm": ncm, "ncm": f"descricao textual do NCM {ncm}",
            "country": country, "metricFOB": fob, "metricKG": kg, "metricFreight": frete,
            "metricInsurance": seguro}


def _dom_df(ano, mes, preco_rs_t=5000.0):
    idx = pd.DatetimeIndex([pd.Timestamp(year=ano, month=mes, day=1)])
    return pd.DataFrame({"preco_rs_t": [preco_rs_t], "metodo": ["nivel_trimestral"],
                         "trimestre_base": ["teste"], "tipo_dado": ["proxy_segmento_aco"]}, index=idx)


def _stub_sgs(cambio=5.0):
    def _sgs(codigo, inicio="01/01/2010"):
        dias = pd.date_range("2010-01-01", "2030-12-31", freq="D")
        return pd.Series(cambio, index=dias, name=f"sgs_{codigo}")
    return _sgs


def _rodar(ano, mes, rows, p=None, preco_dom=5000.0):
    original_sgs = m.sgs
    m.sgs = _stub_sgs()
    try:
        return m.agregar_ipia_hrc_multi_ncm_mensal(
            ano_ini=ano, ano_fim=ano, df_bruto=pd.DataFrame(rows),
            domestico_df=_dom_df(ano, mes, preco_dom), p=p)
    finally:
        m.sgs = original_sgs


_ROWS_2024_06 = [_linha(2024, 6, "72083700", kg=10_000_000.0, fob=6_000_000.0, frete=200_000.0, seguro=20_000.0)]


# --- 1. PPI_COST ignora margem -----------------------------------------

def test_ppi_cost_ignora_margem():
    r_margem_baixa = _rodar(2024, 6, _ROWS_2024_06, p=m.ParamsIPIA(margem_importador=0.0)).iloc[0]
    r_margem_alta = _rodar(2024, 6, _ROWS_2024_06, p=m.ParamsIPIA(margem_importador=0.50)).iloc[0]
    assert r_margem_baixa["ppi_rs_t"] == pytest.approx(r_margem_alta["ppi_rs_t"])


def test_ppi_cost_brl_t_direto_ignora_margem():
    p_baixa = m.ParamsIPIA(margem_importador=0.0)
    p_alta = m.ParamsIPIA(margem_importador=0.50)
    cif, ii, frete_usd_t, cambio, afrmm, ad = 5000.0, 0.108, 100.0, 5.0, 0.08, 0.0
    custo_baixa = m._ppi_cost_brl_t(cif, ii, frete_usd_t, cambio, afrmm, ad, p_baixa)
    custo_alta = m._ppi_cost_brl_t(cif, ii, frete_usd_t, cambio, afrmm, ad, p_alta)
    assert custo_baixa == pytest.approx(custo_alta)


# --- 2. PPI_OFFER = PPI_COST x (1 + margin) -----------------------------

def test_calcular_ppi_offer_formula():
    assert m.calcular_ppi_offer(1000.0, 0.03) == pytest.approx(1030.0)
    assert m.calcular_ppi_offer(pd.Series([1000.0, 2000.0]), 0.10).tolist() == pytest.approx([1100.0, 2200.0])


# --- 3. margem zero: PPI_OFFER(margin=0) == PPI_COST --------------------

def test_calcular_ppi_offer_margem_zero_igual_a_cost():
    r = _rodar(2024, 6, _ROWS_2024_06).iloc[0]
    assert m.calcular_ppi_offer(r["ppi_rs_t"], 0.0) == pytest.approx(r["ppi_rs_t"])


# --- 4. legado: PPI_OFFER(margin=3%) reproduz o comportamento pre-1.5 ---

def test_ppi_offer_com_margem_3pct_reproduz_legado_pre_1_5():
    p = m.ParamsIPIA()  # default: margem_importador == 0.03, mesmo valor de sempre
    r = _rodar(2024, 6, _ROWS_2024_06, p=p).iloc[0]
    ppi_cost = r["ppi_rs_t"]
    ppi_offer = m.calcular_ppi_offer(ppi_cost, p.margem_importador)
    # formula pre-1.5: base * (1 + margem) - reconstruida direto aqui (sem
    # chamar _ppi_cost_brl_t de novo) so para provar a equivalencia
    # numerica com o comportamento antigo, nao para reimplementar producao.
    cif_brl = (6_000_000.0 + 200_000.0 + 20_000.0) / 10_000_000.0 * 1000.0 * 5.0
    ii = cif_brl * p.aliquota_ii
    afrmm = (200_000.0 / 10_000_000.0 * 1000.0 * 5.0) * p.afrmm
    base_legado = cif_brl + ii + afrmm + p.despesas_porto_rs_t + p.frete_interno_rs_t
    ppi_legado_pre_1_5 = base_legado * (1 + p.margem_importador)
    assert ppi_offer == pytest.approx(ppi_legado_pre_1_5, rel=1e-9)
    assert r["ppi_offer_rs_t"] == pytest.approx(ppi_legado_pre_1_5, rel=1e-9)


# --- 5. isolamento: margem nao altera componentes fisicos/regulatorios --

def test_margem_isolamento_nao_altera_ii_afrmm_antidumping_porto_interno():
    grupos_baixa = m.custo_importacao_bottom_up_mensal(
        pd.DataFrame(_ROWS_2024_06), pd.Series([5.0], index=[pd.Timestamp("2024-06-01")]),
        p=m.ParamsIPIA(margem_importador=0.0))
    grupos_alta = m.custo_importacao_bottom_up_mensal(
        pd.DataFrame(_ROWS_2024_06), pd.Series([5.0], index=[pd.Timestamp("2024-06-01")]),
        p=m.ParamsIPIA(margem_importador=0.50))
    for col in ("cif_brl_t", "aliquota_ii", "aliquota_afrmm", "antidumping_usd_t", "ppi_cost_brl_t"):
        assert grupos_baixa[col].iloc[0] == pytest.approx(grupos_alta[col].iloc[0]), col


# --- 6. a serie oficial usa Cost, nao Offer ------------------------------

def test_ipia_usa_ppi_cost_nao_ppi_offer():
    p = m.ParamsIPIA()  # margem default 0.03 - se `ipia` usasse Offer, isto teria efeito mensuravel
    r = _rodar(2024, 6, _ROWS_2024_06, p=p, preco_dom=5236.0).iloc[0]
    assert r["publication_status"] == STATUS_PUBLICATION_GRADE
    assert r["ipia"] == pytest.approx(r["preco_domestico_rs_t"] / r["ppi_rs_t"] * 100.0)
    # o IPIA que a formula usaria se fosse Offer-based seria MENOR (denominador maior)
    ipia_se_fosse_offer = r["preco_domestico_rs_t"] / r["ppi_offer_rs_t"] * 100.0
    assert r["ipia"] != pytest.approx(ipia_se_fosse_offer)
    assert r["ipia"] > ipia_se_fosse_offer


def test_ppi_offer_rs_t_nan_quando_status_unknown():
    # mes com maioria do volume sob cota GECEX 929/2026 (mesmo cenario de
    # test_maioria_sob_cota_2026_e_unknown em test_ipia_hrc_multi_ncm.py) -
    # ppi_rs_t/ppi_offer_rs_t devem ficar NaN juntos, nunca so um deles.
    rows = [
        _linha(2026, 7, "72083910", kg=9_000_000.0, fob=5_400_000.0, frete=180_000.0, seguro=18_000.0),
        _linha(2026, 7, "72081000", kg=1_000_000.0, fob=600_000.0, frete=20_000.0, seguro=2_000.0),
    ]
    r = _rodar(2026, 7, rows).iloc[0]
    assert np.isnan(r["ppi_rs_t"])
    assert np.isnan(r["ppi_offer_rs_t"])
