"""Characterization tests for the generic index-engine math.

Externalizes selftest() sections 1-7, 9 and 10 (z-score window, winsorization,
anchor at 50, orientation, missing-weight redistribution, coverage cutoff,
specification validation, forward-looking diagnostic and PCA validation).
Mirrors the exact assertions in src/indices_setoriais.py::selftest() so both
protections coexist during the migration (see docs/specs/0002).
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m


def test_janela_fixa_nao_reescreve_passado():
    s = m._serie_sintetica(seed=1)
    z1 = m.zscore_janela_fixa(s, m.JANELA_REF)
    s2 = pd.concat([s, m._serie_sintetica(n=12, seed=99, nivel=40.0).set_axis(
        pd.date_range(s.index[-1] + pd.offsets.MonthBegin(), periods=12, freq="MS"))])
    z2 = m.zscore_janela_fixa(s2, m.JANELA_REF)
    dif = float((z2.loc[z1.index] - z1).abs().max())
    assert dif < 1e-10


def test_contraprova_amostra_cheia_reescreve_passado():
    s = m._serie_sintetica(seed=1)
    z1 = m.zscore_janela_fixa(s, m.JANELA_REF)
    s2 = pd.concat([s, m._serie_sintetica(n=12, seed=99, nivel=40.0).set_axis(
        pd.date_range(s.index[-1] + pd.offsets.MonthBegin(), periods=12, freq="MS"))])

    def z_amostra_cheia(x):
        return (x - x.mean()) / x.std(ddof=1)

    d_exp = float((z_amostra_cheia(s2).loc[z1.index] - z_amostra_cheia(s)).abs().max())
    assert d_exp > 1e-3


def test_winsorizacao_respeita_limite():
    z = m.zscore_janela_fixa(m._serie_sintetica(seed=2), m.JANELA_REF)
    assert float(z.abs().max()) <= m.WINSOR_Z + 1e-9


def test_indice_medio_na_janela_referencia_eh_50():
    espec_min = m.EspecIndice("T", "teste", [m.Pilar("p", 1.0)], [m.Variavel("v", "p", 1.0, +1)])
    zz = pd.DataFrame({"v": m.zscore_janela_fixa(m._serie_sintetica(seed=3), m.JANELA_REF)})
    out = m.agregar(zz, espec_min)
    ini, fim = m.JANELA_REF
    media = out.loc[(out.index >= ini) & (out.index <= fim), "indice"].mean()
    assert abs(media - 50) < 0.6


def test_orientacao_negativa_espelha_indice():
    zz = pd.DataFrame({"v": m.zscore_janela_fixa(m._serie_sintetica(seed=3), m.JANELA_REF)})
    e_pos = m.EspecIndice("A", "a", [m.Pilar("p", 1.0)], [m.Variavel("v", "p", 1.0, +1)])
    e_neg = m.EspecIndice("B", "b", [m.Pilar("p", 1.0)], [m.Variavel("v", "p", 1.0, -1)])
    a = m.agregar(zz, e_pos)["indice"]
    b = m.agregar(zz, e_neg)["indice"]
    assert float(((a - 50) + (b - 50)).abs().max()) < 1e-9


def _espec2():
    return m.EspecIndice("C", "c", [m.Pilar("p", 1.0)],
                          [m.Variavel("v1", "p", 0.7, +1), m.Variavel("v2", "p", 0.3, +1)])


def _z2df():
    return pd.DataFrame({
        "v1": m.zscore_janela_fixa(m._serie_sintetica(seed=4), m.JANELA_REF),
        "v2": m.zscore_janela_fixa(m._serie_sintetica(seed=5), m.JANELA_REF)})


def test_dado_faltante_redistribui_peso_para_variavel_restante():
    espec2 = _espec2()
    z_falta = _z2df()
    z_falta.loc[z_falta.index[-6:], "v2"] = np.nan
    parcial = m.agregar(z_falta, espec2)
    esperado = m.ESCALA_A + m.ESCALA_B * z_falta["v1"].iloc[-1]
    assert abs(float(parcial["indice"].iloc[-1]) - float(esperado)) < 1e-9


def test_cobertura_cai_quando_falta_variavel_de_peso():
    espec2 = _espec2()
    z_falta = _z2df()
    z_falta.loc[z_falta.index[-6:], "v2"] = np.nan
    parcial = m.agregar(z_falta, espec2)
    assert abs(float(parcial["cobertura"].iloc[-1]) - 0.70) < 1e-9


def test_cobertura_cheia_eh_um():
    cheio = m.agregar(_z2df(), _espec2())
    assert abs(float(cheio["cobertura"].iloc[-1]) - 1.0) < 1e-9


def test_setor_abaixo_da_cobertura_minima_nao_e_publicado():
    espec3 = m.EspecIndice("D", "d", [m.Pilar("p1", 0.5), m.Pilar("p2", 0.5)],
                            [m.Variavel("v1", "p1", 1.0, +1), m.Variavel("v2", "p2", 1.0, +1)])
    z3 = _z2df()
    z3.loc[z3.index[-3:], "v2"] = np.nan
    o3 = m.agregar(z3, espec3)
    assert bool(o3["indice"].iloc[-3:].isna().all())


def test_especificacao_com_pesos_de_pilar_invalidos_e_rejeitada():
    with pytest.raises(ValueError):
        m.EspecIndice("E", "e", [m.Pilar("p", 0.9)], [m.Variavel("v", "p", 1.0)]).validar()


def test_especificacao_do_iccs_e_consistente():
    m.ICCS.validar()  # nao deve levantar ValueError


def test_correlacao_a_frente_supera_a_contemporanea_em_sinal_antecedente():
    base = m._serie_sintetica(n=160, seed=7, ruido=0.5)
    alvo = (-base).shift(6).cumsum()
    ind = 50 + 10 * m.zscore_janela_fixa(base, m.JANELA_REF)
    diag = m.diagnostico_antecedencia(ind, alvo)
    melhor = float(diag["correlacao"].abs().max())
    contemp = abs(diag.attrs["correlacao_contemporanea"])
    assert melhor > contemp


def test_ruido_branco_nao_gera_antecedencia_espuria_forte():
    base = m._serie_sintetica(n=160, seed=7, ruido=0.5)
    rng = np.random.default_rng(11)
    puro = pd.Series(rng.normal(0, 1, 160), index=base.index)
    d2 = m.diagnostico_antecedencia(
        50 + 10 * m.zscore_janela_fixa(puro, m.JANELA_REF),
        pd.Series(rng.normal(0, 1, 160), index=base.index).cumsum())
    assert float(d2["correlacao"].abs().max()) < 0.45


def test_validacao_por_pca_executa_e_reporta_variancia_explicada():
    v = m.validar_com_pca(_z2df())
    assert v.get("ok")
    assert "var_explicada_pc1" in v
