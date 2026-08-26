"""Characterization tests for vintage/cutoff validation and provenance badges.

Externalizes selftest() sections 21b and 22 (validar_report_cutoff look-ahead
detection, and end-to-end classification -> selo_dado_texto badge rendering
for PROXY/ESTIMADO/OBSERVADO/formula_alternativa).
"""
import pandas as pd

import indices_setoriais as m
from reporting import components as rep_components


def _tabela_vintage_teste():
    idx_reconc = pd.date_range("2026-05-01", periods=2, freq="MS")
    df_ipia_reconc = pd.DataFrame({
        "preco_domestico_rs_t": [5000.0, 5236.0],
        "ppi_rs_t": [3600.0, 3728.0],
        "ipia": [138.9, 140.4],
        "tipo_dado_domestico": ["proxy_segmento_aco", "proxy_segmento_aco"],
        "metodo_domestico": ["nivel_trimestral", "nivel_trimestral"],
    }, index=idx_reconc)
    idx_custo_reconc = pd.date_range("2026-05-01", periods=3, freq="MS")
    df_custo_reconc = pd.DataFrame({
        "ppi_brl_t": [3600.0, 3728.0, 3806.0],
    }, index=idx_custo_reconc)
    return m.montar_tabela_vintage(df_ipia_reconc, df_custo_reconc)


def test_validar_report_cutoff_sem_problemas_quando_reference_period_no_prazo():
    tabela_vintage_teste = _tabela_vintage_teste()
    cutoff_valido = pd.Timestamp("2026-07-15")  # cobre o mes mais recente (df_custo vai ate julho)
    assert len(m.validar_report_cutoff(tabela_vintage_teste, cutoff_valido)) == 0


def test_validar_report_cutoff_detecta_look_ahead():
    tabela_vintage_teste = _tabela_vintage_teste()
    cutoff_anterior = pd.Timestamp("2026-05-15")  # anterior ao mes de df_ipia (2026-06)
    problemas_cutoff = m.validar_report_cutoff(tabela_vintage_teste, cutoff_anterior)
    assert len(problemas_cutoff) > 0


def test_selo_nunca_omite_proxy_quando_tipo_dado_domestico_e_proxy_segmento_aco():
    linha_proxy_teste = pd.Series(
        {"tipo_dado_domestico": "proxy_segmento_aco", "metodo_domestico": "nivel_trimestral"},
        name=pd.Timestamp("2026-06-01"))
    v_proxy = m.classificar_preco_domestico(linha_proxy_teste)
    assert "PROXY" in rep_components.selo_dado_texto(v_proxy.nivel, v_proxy.proxy)


def test_selo_nunca_omite_estimado_quando_metodo_domestico_e_hold_flat_fallback():
    linha_estimado_teste = pd.Series(
        {"tipo_dado_domestico": "especifico_laminado_quente", "metodo_domestico": "hold_flat_fallback"},
        name=pd.Timestamp("2026-07-01"))
    v_estimado = m.classificar_preco_domestico(linha_estimado_teste)
    assert "ESTIMADO" in rep_components.selo_dado_texto(v_estimado.nivel, v_estimado.proxy)


def test_selo_vazio_para_observado_puro_sem_proxy():
    linha_observado_teste = pd.Series({"tipo_dado_penetracao": "oficial_mensal"},
                                       name=pd.Timestamp("2026-07-01"))
    v_observado = m.classificar_penetracao(linha_observado_teste)
    assert rep_components.selo_dado_texto(v_observado.nivel, v_observado.proxy) == ""


def test_formula_alternativa_classifica_como_calculado_nao_estimado_nem_proxy():
    linha_formula_alt_teste = pd.Series({"tipo_dado_penetracao": "aproximado_consumo_aparente"},
                                         name=pd.Timestamp("2026-06-01"))
    v_formula_alt = m.classificar_penetracao(linha_formula_alt_teste)
    assert v_formula_alt.nivel == m.NIVEL_CALCULADO
    assert not v_formula_alt.proxy
    assert v_formula_alt.metodo == m.METODO_FORMULA_ALTERNATIVA
