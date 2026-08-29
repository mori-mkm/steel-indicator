"""Unit tests for `indices_setoriais.decompor_variacao_ipia_hrc` (Stage H1,
Driver Decomposition Engine) - decompoe `ipia_t - ipia_{t-1}` (pontos de
indice) em contribuicoes exatas por driver via Shapley
(`steel_indicator.domain.driver_decomposition`).

Deterministic, no network. Prova: atribuicao de driver unico (domestic/
FX/FOB isolados); dois drivers simultaneos (ordem/soma/sinais); sinais
economicos coerentes (FX/FOB/freight/insurance up -> IPIA down; domestic
up -> IPIA up); mudanca regulatoria real (II) tem contribuicao != 0 e
sinal correto; parametros constantes (D_porto/D_interno) contribuem
exatamente 0; separacao Cost/Offer (margem nunca aparece no modo Cost);
exatidao da reparametrizacao FX-linear contra a reconstrucao ja validada
de `decompor_mes`; determinismo.
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import indices_setoriais as m  # noqa: E402

_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "validar_ipia_hrc_v2_final.py")
_spec = importlib.util.spec_from_file_location("validar_ipia_hrc_v2_final", _SCRIPT_PATH)
_validar = importlib.util.module_from_spec(_spec)
sys.modules["validar_ipia_hrc_v2_final"] = _validar
_spec.loader.exec_module(_validar)
decompor_mes = _validar.decompor_mes

STATUS_PUBLICATION_GRADE = "PUBLICATION_GRADE"


def _componentes(domestic_price=5000.0, fob=600.0, freight=20.0, insurance=2.0, fx=5.0,
                 ii=64.94, afrmm=8.0, antidumping=0.0, d_porto=210.0, d_interno=140.0, **kw):
    """Componentes-base plausiveis (mesma ordem de grandeza dos testes de
    `test_custo_importacao_historico.py`: fob=600, frete=20, seguro=2,
    cambio=5, aliquota_ii=0.108 -> cif_usd=622, ii_usd_efetivo=622*0.108=67.176;
    aqui aproximado para numeros redondos de teste, o valor exato nao
    importa para os testes de atribuicao/sinal abaixo)."""
    base = dict(domestic_price=domestic_price, fob=fob, freight=freight, insurance=insurance,
               fx=fx, ii=ii, afrmm=afrmm, antidumping=antidumping, d_porto=d_porto, d_interno=d_interno)
    base.update(kw)
    return base


# --- 1. Driver unico: domestic only -----------------------------------------

def test_domestic_only_atribui_100pct_a_domestic():
    t_1 = _componentes(domestic_price=5000.0)
    t = _componentes(domestic_price=5300.0)
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    ipia_t_1 = m.ipia(5000.0, m._ppi_cost_de_drivers(600.0, 20.0, 2.0, 5.0, 64.94, 8.0, 0.0, 210.0, 140.0))
    ipia_t = m.ipia(5300.0, m._ppi_cost_de_drivers(600.0, 20.0, 2.0, 5.0, 64.94, 8.0, 0.0, 210.0, 140.0))
    assert r["delta_ipia"] == pytest.approx(ipia_t - ipia_t_1, abs=1e-9)
    assert r["domestic_price"] == pytest.approx(r["delta_ipia"], abs=1e-9)
    for driver in ("fob", "freight", "insurance", "fx", "ii", "afrmm", "antidumping", "d_porto", "d_interno"):
        assert r[driver] == pytest.approx(0.0, abs=1e-9)
    assert abs(r["residual"]) < 1e-9


# --- 2. Driver unico: FX only ------------------------------------------------

def test_fx_only_atribui_100pct_a_fx_e_reduz_ipia():
    t_1 = _componentes(fx=5.0)
    t = _componentes(fx=5.5)  # BRL deprecia
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert r["fx"] == pytest.approx(r["delta_ipia"], abs=1e-9)
    for driver in ("domestic_price", "fob", "freight", "insurance", "ii", "afrmm",
                   "antidumping", "d_porto", "d_interno"):
        assert r[driver] == pytest.approx(0.0, abs=1e-9)
    assert abs(r["residual"]) < 1e-9
    # BRL depreciando (FX sobe) -> PPI_COST sobe -> IPIA cai (Sec.14)
    assert r["delta_ipia"] < 0
    assert r["fx"] < 0


# --- 3. Driver unico: FOB only -----------------------------------------------

def test_fob_only_atribui_100pct_a_fob_e_reduz_ipia():
    t_1 = _componentes(fob=600.0)
    t = _componentes(fob=750.0)
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert r["fob"] == pytest.approx(r["delta_ipia"], abs=1e-9)
    for driver in ("domestic_price", "freight", "insurance", "fx", "ii", "afrmm",
                   "antidumping", "d_porto", "d_interno"):
        assert r[driver] == pytest.approx(0.0, abs=1e-9)
    assert abs(r["residual"]) < 1e-9
    assert r["delta_ipia"] < 0  # FOB sobe -> PPI_COST sobe -> IPIA cai (Sec.15)
    assert r["fob"] < 0


@pytest.mark.parametrize("driver,valor_t", [("freight", 35.0), ("insurance", 6.0)])
def test_freight_e_insurance_only_reduzem_ipia(driver, valor_t):
    t_1 = _componentes()
    t = _componentes(**{driver: valor_t})
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert r[driver] == pytest.approx(r["delta_ipia"], abs=1e-9)
    assert r["delta_ipia"] < 0  # freight/insurance sobem -> PPI_COST sobe -> IPIA cai (Sec.15)


# --- 4. Dois drivers simultaneos: domestic + FX -----------------------------

def test_dois_drivers_domestic_e_fx_soma_fecha_e_ordem_nao_importa():
    t_1 = _componentes(domestic_price=5000.0, fx=5.0)
    t = _componentes(domestic_price=5300.0, fx=5.5)
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")

    soma = sum(r[d] for d in m.DRIVERS_PPI_COST)
    assert soma == pytest.approx(r["delta_ipia"], abs=1e-9)
    assert abs(r["residual"]) < 1e-9
    # ambos os efeitos sao reais e de sinais opostos (domestic empurra IPIA
    # para cima, FX empurra para baixo) - nenhum dos dois deveria ser
    # exatamente zero so por terem mudado simultaneamente.
    assert r["domestic_price"] > 0
    assert r["fx"] < 0

    # independencia de ordem: passar os drivers em ordem diferente para o
    # motor generico (via um modo "cost" alternativo que so reordena a
    # lista) produz o MESMO resultado - testado diretamente no motor
    # generico (test_driver_decomposition_shapley.py); aqui confirmamos que
    # o WRAPPER do IPIA-HRC tambem e estavel a chamadas repetidas.
    r2 = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert r == r2


# --- 5. Sinal: domestic up -> IPIA up ---------------------------------------

def test_domestic_up_aumenta_ipia():
    t_1 = _componentes(domestic_price=5000.0)
    t = _componentes(domestic_price=5500.0)
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert r["delta_ipia"] > 0
    assert r["domestic_price"] > 0


# --- 6. Parametros constantes: D_porto/D_interno contribuem exatamente 0 ---

def test_d_porto_d_interno_constantes_contribuem_zero_mesmo_com_outros_mudando():
    t_1 = _componentes(domestic_price=5000.0, fx=5.0, fob=600.0)
    t = _componentes(domestic_price=5300.0, fx=5.4, fob=650.0)  # d_porto/d_interno iguais nos dois
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert r["d_porto"] == pytest.approx(0.0, abs=1e-9)
    assert r["d_interno"] == pytest.approx(0.0, abs=1e-9)


def test_d_porto_muda_tem_contribuicao_nao_nula_se_no_futuro_variar():
    # prova que o motor JA sabe atribuir contribuicao a D_porto/D_interno
    # caso um dia deixem de ser hold-flat (Sec.12: "se no futuro forem
    # time-varying, o motor deve naturalmente conseguir atribuir
    # contribuicao" - nenhuma mudanca de codigo seria necessaria).
    t_1 = _componentes(d_porto=210.0)
    t = _componentes(d_porto=260.0)
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert r["d_porto"] != pytest.approx(0.0, abs=1e-9)
    assert r["d_porto"] == pytest.approx(r["delta_ipia"], abs=1e-9)
    assert r["d_porto"] < 0  # D_porto sobe -> PPI_COST sobe -> IPIA cai


# --- 7. Mudanca regulatoria real (II) ---------------------------------------

def test_elevacao_de_ii_tem_contribuicao_nao_nula_e_sinal_correto():
    # cenario analogo a uma elevacao tarifaria real (ex.: Res. GECEX
    # 865/2026, 10,8% -> 25% - docs/METODOLOGIA.md Sec.9.5.3): aqui
    # representado diretamente no valor monetario efetivo de II (USD/t),
    # que e como o driver `ii` desta decomposicao e definido (nao uma
    # aliquota) - ver docstring de `_ppi_cost_de_drivers`.
    cif_usd_t = 622.0
    ii_baixo = cif_usd_t * 0.108
    ii_alto = cif_usd_t * 0.25
    t_1 = _componentes(ii=ii_baixo)
    t = _componentes(ii=ii_alto)
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert r["ii"] != pytest.approx(0.0, abs=1e-9)
    assert r["ii"] == pytest.approx(r["delta_ipia"], abs=1e-9)
    assert r["ii"] < 0  # II sobe -> PPI_COST sobe -> IPIA cai


# --- 8. Cost vs Offer --------------------------------------------------------

def test_modo_cost_nunca_inclui_margin():
    t_1 = _componentes()
    t = _componentes(fx=5.4)
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    assert "margin" not in r
    assert set(k for k in m.DRIVERS_PPI_COST) <= set(r.keys())


def test_modo_offer_inclui_margin_com_contribuicao_correta():
    t_1 = _componentes(margin=0.03)
    t = _componentes(margin=0.03)  # so a margem muda, abaixo
    t["margin"] = 0.06
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="offer")
    assert "margin" in r
    assert r["margin"] != pytest.approx(0.0, abs=1e-9)
    assert r["margin"] == pytest.approx(r["delta_ipia"], abs=1e-9)
    assert r["margin"] < 0  # margem sobe -> PPI_OFFER sobe -> IPIA cai
    for driver in m.DRIVERS_PPI_COST:
        assert r[driver] == pytest.approx(0.0, abs=1e-9)


def test_modo_offer_com_margem_constante_drivers_de_custo_escalam_por_1_mais_margem():
    # cross-check independente (achado do code review): com margem
    # constante m, f_offer(drivers) = f_cost(drivers) / (1+m) - uma
    # constante multiplicativa em relacao aos 10 drivers restantes (a
    # margem so entra como divisor comum de TODAS as avaliacoes de
    # subconjunto usadas pelo Shapley). Pela propriedade de LINEARIDADE do
    # valor de Shapley (phi_i(c*f) = c*phi_i(f)), a contribuicao de cada
    # driver fisico/regulatorio no modo Offer deve ser EXATAMENTE a
    # contribuicao do modo Cost dividida por (1+m) - nunca identica em
    # valor absoluto (confirmado numericamente antes de fixar este teste:
    # a igualdade direta falha, a proporcao 1/(1+m) bate exatamente).
    t_1 = _componentes(domestic_price=5000.0, fx=5.0, fob=600.0)
    t = _componentes(domestic_price=5300.0, fx=5.4, fob=650.0)
    r_cost = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")

    margem = 0.03
    t_1_offer = dict(t_1, margin=margem)
    t_offer = dict(t, margin=margem)
    r_offer = m.decompor_variacao_ipia_hrc(t_1_offer, t_offer, modo="offer")

    assert r_offer["margin"] == pytest.approx(0.0, abs=1e-9)
    for driver in m.DRIVERS_PPI_COST:
        assert r_offer[driver] == pytest.approx(r_cost[driver] / (1 + margem), rel=1e-9)


def test_modo_offer_com_margem_constante_margin_contribui_zero():
    # se a margem NAO muda entre t-1 e t, ela e so mais um "driver sem
    # mudanca" (Sec.11/12) - contribuicao exatamente zero, mesmo com
    # outros drivers mudando simultaneamente.
    t_1 = _componentes(margin=0.03)
    t = _componentes(domestic_price=5300.0, fx=5.4, margin=0.03)
    r_offer = m.decompor_variacao_ipia_hrc(t_1, t, modo="offer")
    assert r_offer["margin"] == pytest.approx(0.0, abs=1e-9)


def test_modo_invalido_levanta_erro():
    with pytest.raises(ValueError, match="modo deve ser"):
        m.decompor_variacao_ipia_hrc(_componentes(), _componentes(), modo="invalido")


# --- 9. Exatidao da reparametrizacao FX-linear vs. decompor_mes ------------
# `decompor_mes` (scripts/validar_ipia_hrc_v2_final.py) ja reconstroi
# PPI_COST EXATAMENTE contra o motor de producao
# (test_validar_ipia_hrc_v2_decompor_mes.py::test_reconstrucao_exata_...).
# Aqui provamos que `_ppi_cost_de_drivers`, alimentado pelos MESMOS
# componentes que `decompor_mes` deriva (ii/afrmm convertidos de R$ para
# USD/t efetivo dividindo por cambio_mes), reproduz o MESMO valor -
# ou seja, a reparametrizacao usada pela decomposicao nao e uma
# aproximacao, e a mesma identidade algebrica.

def test_ppi_cost_de_drivers_bate_exatamente_com_decompor_mes_ncms_heterogeneos():
    p = m.ParamsIPIA()
    data = pd.Timestamp("2024-06-01")
    rows = [
        dict(coNcm="72083700", country="China", fob_usd=3_600_000.0, frete_usd=120_000.0, seguro_usd=12_000.0,
            kg=6_000_000.0),
        dict(coNcm="72083910", country="Coreia do Sul", fob_usd=2_400_000.0, frete_usd=80_000.0, seguro_usd=8_000.0,
            kg=4_000_000.0),
    ]
    df_bruto = pd.DataFrame([{
        "year": 2024, "monthNumber": 6, "coNcm": r["coNcm"], "ncm": f"descricao {r['coNcm']}",
        "country": r["country"], "metricFOB": r["fob_usd"], "metricKG": r["kg"],
        "metricFreight": r["frete_usd"], "metricInsurance": r["seguro_usd"],
    } for r in rows])
    cambio = pd.Series([5.0], index=[data])
    grupos = m.custo_importacao_bottom_up_mensal(df_bruto, cambio, p=p)
    grupos["data"] = data
    grupos["status"] = "PUBLICATION_GRADE"

    dec = decompor_mes(grupos, data, p, STATUS_PUBLICATION_GRADE)
    assert dec is not None

    ii_usd_efetivo = dec["ii_brl_t"] / dec["cambio_mes"]
    afrmm_usd_efetivo = dec["afrmm_brl_t"] / dec["cambio_mes"]

    ppi_cost_via_drivers = m._ppi_cost_de_drivers(
        fob=dec["fob_usd_t"], freight=dec["frete_usd_t"], insurance=dec["seguro_usd_t"],
        fx=dec["cambio_mes"], ii=ii_usd_efetivo, afrmm=afrmm_usd_efetivo,
        antidumping=dec["antidumping_usd_t"], d_porto=dec["despesas_porto_rs_t"],
        d_interno=dec["frete_interno_rs_t"])

    assert ppi_cost_via_drivers == pytest.approx(dec["ppi_cost_reconstruido"], abs=1e-9)
    assert ppi_cost_via_drivers == pytest.approx(dec["ppi_cost_via_motor"], abs=1e-9)


# --- 10. Determinismo ---------------------------------------------------------

def test_determinismo_wrapper_ipia_hrc():
    t_1 = _componentes()
    t = _componentes(domestic_price=5300.0, fx=5.4, fob=650.0, ii=70.0)
    r1 = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    r2 = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    for driver in m.DRIVERS_PPI_COST:
        assert r1[driver] == r2[driver]
    assert r1["residual"] == r2["residual"]


# --- 11. Rollup hierarquico (Sec.17) -----------------------------------------

def test_rollup_hierarquico_domestic_vs_import_cost():
    t_1 = _componentes(domestic_price=5000.0, fx=5.0, fob=600.0)
    t = _componentes(domestic_price=5300.0, fx=5.4, fob=650.0)
    r = m.decompor_variacao_ipia_hrc(t_1, t, modo="cost")
    soma_import = sum(r[d] for d in m.DRIVERS_PPI_COST if d != "domestic_price")
    assert r["import_cost_contribution"] == pytest.approx(soma_import, abs=1e-9)
    assert r["domestic_contribution"] == pytest.approx(r["domestic_price"], abs=1e-9)
    assert r["domestic_contribution"] + r["import_cost_contribution"] == pytest.approx(r["delta_ipia"], abs=1e-9)


# --- 12. Metadata (Sec.24) ----------------------------------------------------

def test_nomes_legiveis_cobrem_todos_os_drivers_offer():
    for driver in m.DRIVERS_PPI_OFFER:
        assert driver in m.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC
        assert isinstance(m.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC[driver], str)
        assert m.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC[driver]  # nao vazio


def test_decomposition_method_presente_no_resultado():
    r = m.decompor_variacao_ipia_hrc(_componentes(), _componentes(fx=5.2), modo="cost")
    assert r["decomposition_method"] == m.DECOMPOSITION_METHOD_SHAPLEY_EXATO
    assert r["modo"] == "cost"
