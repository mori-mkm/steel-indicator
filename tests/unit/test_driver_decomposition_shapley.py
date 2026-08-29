"""Unit tests for the generic Shapley decomposition engine
(steel_indicator.domain.driver_decomposition) - NAO especifico de IPIA/
PPI. Deterministic, no network, no I/O.

Prova: additivity exata (residual ~0, efficiency property de Shapley);
independencia de ordem; equivalencia entre a formula fechada de
subconjuntos (2^n) e a definicao original por media sobre todas as
ordens (forca bruta, n!); caso analitico conhecido (produto de dois
fatores); guard-rails de custo computacional.
"""
import math
from itertools import permutations

import pytest

from steel_indicator.domain.driver_decomposition import (
    MAX_DRIVERS_EXATO, shapley_contributions, shapley_contributions_forca_bruta,
)


def _produto(**kwargs) -> float:
    resultado = 1.0
    for v in kwargs.values():
        resultado *= v
    return resultado


def _soma(**kwargs) -> float:
    return sum(kwargs.values())


# --- 1. Additivity exata (efficiency property) ------------------------------

def test_additividade_exata_funcao_nao_linear_generica():
    def f(a, b, c):
        return (a * b) / c + a ** 2

    baseline = {"a": 2.0, "b": 3.0, "c": 4.0}
    treatment = {"a": 5.0, "b": 1.0, "c": 2.0}
    r = shapley_contributions(f, baseline, treatment)
    assert sum(r.contribuicoes.values()) == pytest.approx(r.delta_total, abs=1e-9)
    assert abs(r.residual) < 1e-9


def test_delta_total_bate_com_f_direto():
    baseline = {"a": 1.0, "b": 2.0}
    treatment = {"a": 3.0, "b": 5.0}
    r = shapley_contributions(_produto, baseline, treatment)
    assert r.valor_baseline == pytest.approx(1.0 * 2.0)
    assert r.valor_treatment == pytest.approx(3.0 * 5.0)
    assert r.delta_total == pytest.approx(3.0 * 5.0 - 1.0 * 2.0)


# --- 2. Caso analitico conhecido: produto de dois fatores -------------------
# Para f(a,b)=a*b, o valor de Shapley tem forma fechada conhecida
# (decomposicao Bennet/Shapley-Owen de 2 fatores):
#   phi_a = (a2-a1)*(b1+b2)/2 ; phi_b = (b2-b1)*(a1+a2)/2

def test_produto_de_dois_fatores_forma_fechada_conhecida():
    a1, a2, b1, b2 = 10.0, 15.0, 4.0, 6.0
    r = shapley_contributions(_produto, {"a": a1, "b": b1}, {"a": a2, "b": b2})
    phi_a_esperado = (a2 - a1) * (b1 + b2) / 2
    phi_b_esperado = (b2 - b1) * (a1 + a2) / 2
    assert r.contribuicoes["a"] == pytest.approx(phi_a_esperado, abs=1e-9)
    assert r.contribuicoes["b"] == pytest.approx(phi_b_esperado, abs=1e-9)
    assert r.contribuicoes["a"] + r.contribuicoes["b"] == pytest.approx(a2 * b2 - a1 * b1, abs=1e-9)


# --- 3. Independencia de ordem ------------------------------------------------

def test_independencia_de_ordem_dos_drivers():
    baseline = {"a": 2.0, "b": 3.0, "c": 4.0, "d": 5.0}
    treatment = {"a": 6.0, "b": 1.0, "c": 9.0, "d": 2.0}

    def f(a, b, c, d):
        return a * b - c / d + a * c

    r1 = shapley_contributions(f, baseline, treatment, drivers=["a", "b", "c", "d"])
    r2 = shapley_contributions(f, baseline, treatment, drivers=["d", "c", "b", "a"])
    r3 = shapley_contributions(f, baseline, treatment, drivers=["c", "a", "d", "b"])
    for nome in ("a", "b", "c", "d"):
        assert r1.contribuicoes[nome] == pytest.approx(r2.contribuicoes[nome], abs=1e-9)
        assert r1.contribuicoes[nome] == pytest.approx(r3.contribuicoes[nome], abs=1e-9)


# --- 4. Equivalencia com a definicao original (forca bruta, n!) -------------

def test_formula_de_subconjuntos_bate_com_forca_bruta_permutacoes():
    baseline = {"a": 2.0, "b": 5.0, "c": 3.0}
    treatment = {"a": 4.0, "b": 2.0, "c": 6.0}

    def f(a, b, c):
        return (a + b) * c - a * b

    r_subconjuntos = shapley_contributions(f, baseline, treatment)
    r_forca_bruta = shapley_contributions_forca_bruta(f, baseline, treatment)
    for nome in ("a", "b", "c"):
        assert r_subconjuntos.contribuicoes[nome] == pytest.approx(
            r_forca_bruta.contribuicoes[nome], abs=1e-9)


def test_forca_bruta_usa_media_sobre_todas_as_ordens():
    # prova independente de que shapley_contributions_forca_bruta de fato
    # usa TODAS as n! ordens (nao um subconjunto/amostra) - reimplementa a
    # media aqui, fora da funcao testada, e compara.
    baseline = {"x": 1.0, "y": 2.0}
    treatment = {"x": 3.0, "y": 7.0}

    def f(x, y):
        return x ** 2 * y

    contrib_manual = {"x": 0.0, "y": 0.0}
    n_ordens = 0
    for ordem in permutations(["x", "y"]):
        n_ordens += 1
        atual = dict(baseline)
        valor = f(**atual)
        for nome in ordem:
            atual[nome] = treatment[nome]
            novo = f(**atual)
            contrib_manual[nome] += novo - valor
            valor = novo
    contrib_manual = {k: v / n_ordens for k, v in contrib_manual.items()}

    r = shapley_contributions_forca_bruta(f, baseline, treatment)
    assert r.contribuicoes["x"] == pytest.approx(contrib_manual["x"], abs=1e-9)
    assert r.contribuicoes["y"] == pytest.approx(contrib_manual["y"], abs=1e-9)


# --- 5. Casos-limite ---------------------------------------------------------

def test_um_unico_driver_contribuicao_igual_ao_delta():
    r = shapley_contributions(lambda a: a * 2, {"a": 3.0}, {"a": 10.0})
    assert r.contribuicoes["a"] == pytest.approx(r.delta_total, abs=1e-9)
    assert r.residual == pytest.approx(0.0, abs=1e-9)


def test_driver_sem_mudanca_contribui_exatamente_zero():
    def f(a, b):
        return a * b

    r = shapley_contributions(f, {"a": 5.0, "b": 100.0}, {"a": 9.0, "b": 100.0})
    assert r.contribuicoes["b"] == pytest.approx(0.0, abs=1e-12)
    assert r.contribuicoes["a"] == pytest.approx(r.delta_total, abs=1e-9)


def test_guard_rail_excede_max_drivers_exato():
    baseline = {f"d{i}": 1.0 for i in range(MAX_DRIVERS_EXATO + 1)}
    treatment = {f"d{i}": 2.0 for i in range(MAX_DRIVERS_EXATO + 1)}
    with pytest.raises(ValueError, match="MAX_DRIVERS_EXATO"):
        shapley_contributions(_soma, baseline, treatment)


def test_driver_faltando_em_baseline_ou_treatment_levanta_erro():
    with pytest.raises(ValueError, match="drivers sem valor"):
        shapley_contributions(_soma, {"a": 1.0}, {"a": 1.0, "b": 2.0}, drivers=["a", "b"])


def test_nenhum_driver_levanta_erro():
    with pytest.raises(ValueError, match="nenhum driver"):
        shapley_contributions(_soma, {}, {}, drivers=[])


# --- 6. Determinismo ----------------------------------------------------------

def test_determinismo_mesma_entrada_mesmo_resultado():
    baseline = {"a": 3.0, "b": 7.0, "c": 2.0}
    treatment = {"a": 4.5, "b": 6.0, "c": 9.0}

    def f(a, b, c):
        return a * b / c

    r1 = shapley_contributions(f, baseline, treatment)
    r2 = shapley_contributions(f, baseline, treatment)
    assert r1.contribuicoes == r2.contribuicoes
    assert r1.residual == r2.residual


# --- 7. Helpers do ResultadoShapley ------------------------------------------

def test_abs_contribution_share_soma_um():
    def f(a, b, c):
        return a + b - c

    r = shapley_contributions(f, {"a": 1.0, "b": 1.0, "c": 1.0}, {"a": 5.0, "b": 3.0, "c": 10.0})
    share = r.abs_contribution_share()
    assert sum(share.values()) == pytest.approx(1.0, abs=1e-9)


def test_top_positive_negative_dominant_driver():
    def f(a, b, c):
        return a + b + c

    r = shapley_contributions(f, {"a": 0.0, "b": 0.0, "c": 0.0}, {"a": 10.0, "b": -3.0, "c": 1.0})
    assert r.top_positive_driver() == "a"
    assert r.top_negative_driver() == "b"
    assert r.dominant_driver() == "a"


def test_abs_contribution_share_com_delta_zero_nao_quebra():
    def f(a, b):
        return a - b

    r = shapley_contributions(f, {"a": 1.0, "b": 1.0}, {"a": 1.0, "b": 1.0})
    share = r.abs_contribution_share()
    assert share == {"a": 0.0, "b": 0.0}
    assert r.top_positive_driver() is None
    assert r.top_negative_driver() is None
