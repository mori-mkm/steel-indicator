"""Testes puros e deterministicos (sem rede) para o script de analise
contrafactual de convencao cambial (scripts/validar_fx_convention.py,
sprint metodologico "FX convention" - docs/validation/fx_convention_validation.md).

Nao testa a decisao metodologica em si (isso e Level 3, do usuario) - so
garante que a MECANICA da comparacao (construcao das convencoes FX,
reuso da formula de PPI de producao, aritmetica das estatisticas) esta
correta. Reproduzir esses calculos errado invalidaria a analise inteira
sem que ninguem percebesse.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import numpy as np
import pandas as pd
import pytest

import validar_fx_convention as fx
import indices_setoriais as m


def test_construir_convencoes_fx_media_primeiro_e_ultimo_dia_do_mes():
    diario = pd.Series(
        [5.00, 5.10, 5.20, 6.00, 6.40],
        index=pd.DatetimeIndex(["2024-01-05", "2024-01-10", "2024-01-31",
                                 "2024-02-01", "2024-02-15"]),
    )
    meses = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"])
    fx_mean, fx_first, fx_eom, fx_vol = fx.construir_convencoes_fx(diario, meses)

    assert fx_mean.loc["2024-01-01"] == pytest.approx((5.00 + 5.10 + 5.20) / 3)
    assert fx_first.loc["2024-01-01"] == pytest.approx(5.00)
    assert fx_eom.loc["2024-01-01"] == pytest.approx(5.20)

    assert fx_mean.loc["2024-02-01"] == pytest.approx((6.00 + 6.40) / 2)
    assert fx_first.loc["2024-02-01"] == pytest.approx(6.00)
    assert fx_eom.loc["2024-02-01"] == pytest.approx(6.40)

    # mes sem nenhuma observacao diaria: NaN explicito, nunca fabricado
    assert np.isnan(fx_mean.loc["2024-03-01"])
    assert np.isnan(fx_eom.loc["2024-03-01"])


def test_recompute_ppi_reproduz_formula_de_producao_exatamente():
    """Mesmo caso de test_custo_importacao_historico.py (fob=600, frete=20,
    seguro=2, cambio=5, ii=0.108, afrmm=0.08) - garante que
    `recompute_ppi` (reuso de `_ppi_brl_t`) bate com o calculo manual, nao
    so com a propria producao (que ja usa `_ppi_brl_t` internamente - um
    teste que so chamasse a mesma funcao dos dois lados nao provaria nada)."""
    panel = pd.DataFrame({
        "cif_usd_t": [622.0], "frete_usd_t": [20.0],
        "aliquota_ii": [0.108], "aliquota_afrmm": [0.08], "antidumping_usd_t": [0.0],
    }, index=pd.to_datetime(["2024-06-01"]))
    fx_alt = pd.Series([5.0], index=panel.index)

    resultado = fx.recompute_ppi(panel, fx_alt)

    cif_brl = 622.0 * 5.0
    ii = cif_brl * 0.108
    afrmm = (20.0 * 5.0) * 0.08
    base = cif_brl + ii + afrmm + 0.0 + m.ParamsIPIA().despesas_porto_rs_t + m.ParamsIPIA().frete_interno_rs_t
    esperado = base * (1 + m.ParamsIPIA().margem_importador)

    assert resultado.iloc[0] == pytest.approx(esperado)


def test_recompute_ppi_e_afim_em_fx():
    """Para os demais componentes fixos, PPI(FX) e uma funcao AFIM de FX
    (o cambio multiplica CIF/AFRMM/antidumping mas D_porto/D_interno/margem
    nao dependem dele) - propriedade usada no relatorio para argumentar que
    o residuo de reconstrucao do painel agregado (que nao afeta FX) nao
    contamina a DIFERENCA entre convencoes. Se isso quebrar, a formula de
    `_ppi_brl_t` deixou de ser afim em cambio e o argumento do relatorio
    (docs/validation/fx_convention_validation.md) precisa ser revisto."""
    panel = pd.DataFrame({
        "cif_usd_t": [700.0], "frete_usd_t": [30.0],
        "aliquota_ii": [0.12], "aliquota_afrmm": [0.25], "antidumping_usd_t": [10.0],
    }, index=pd.to_datetime(["2019-06-01"]))

    fx_a = pd.Series([4.0], index=panel.index)
    fx_b = pd.Series([6.0], index=panel.index)
    fx_meio = pd.Series([5.0], index=panel.index)

    ppi_a = fx.recompute_ppi(panel, fx_a).iloc[0]
    ppi_b = fx.recompute_ppi(panel, fx_b).iloc[0]
    ppi_meio = fx.recompute_ppi(panel, fx_meio).iloc[0]

    assert ppi_meio == pytest.approx((ppi_a + ppi_b) / 2)


def test_estatisticas_diferenca_aritmetica_correta():
    a = pd.Series([10.0, 12.0, 8.0], index=pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]))
    b = pd.Series([9.0, 12.0, 10.0], index=a.index)

    stats = fx.estatisticas_diferenca(a, b, "a", "b")

    diffs = [1.0, 0.0, -2.0]
    assert stats["n"] == 3
    assert stats["mean_diff"] == pytest.approx(np.mean(diffs))
    assert stats["median_diff"] == pytest.approx(np.median(diffs))
    assert stats["mae"] == pytest.approx(np.mean(np.abs(diffs)))
    assert stats["rmse"] == pytest.approx(np.sqrt(np.mean(np.square(diffs))))
    assert stats["max_abs_diff"] == pytest.approx(2.0)
    assert stats["corr"] == pytest.approx(a.corr(b))
