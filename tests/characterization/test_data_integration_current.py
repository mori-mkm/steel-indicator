"""Characterization tests for cross-source integration guarantees.

Externalizes selftest() sections 20 and 21a (calcular_ipia_mensal must not
re-collect Comex Stat data when df_bruto is injected, and spread
reconciliation must compare same-month values, not positional iloc[-1]).
No live network calls: comex_importacao_ncm is monkeypatched to raise if
called, and sgs/ibge/penetracao are replaced with deterministic stubs, exactly
as selftest() does.
"""
import pandas as pd

import indices_setoriais as m


def test_calcular_ipia_mensal_com_df_bruto_nao_chama_comex_de_novo():
    _comex_original = m.comex_importacao_ncm
    _sgs_original = m.sgs
    _ibge_original = m.ibge_sidra_ipp_metalurgia
    _penet_original = m.taxa_penetracao_importacao_planos_mensal
    chamadas_comex = {"n": 0}

    def _comex_bloqueado(ncm, ano_ini, ano_fim):
        chamadas_comex["n"] += 1
        raise AssertionError("comex_importacao_ncm nao deveria ser chamado com df_bruto fornecido")

    def _sgs_stub(codigo, inicio="01/01/2010"):
        return pd.Series([5.10], index=[pd.Timestamp("2020-01-01")], name=f"sgs_{codigo}")

    def _ibge_stub(periodos="all"):
        return pd.Series(dtype=float)

    def _penet_stub(ano_ini=2013, ano_fim=None, df_historico=None, df_oficial=None):
        return pd.DataFrame({"taxa_penetracao_pct": pd.Series(dtype=float),
                              "tipo_dado_penetracao": pd.Series(dtype=object)})

    df_bruto_teste = pd.DataFrame({
        "year": [2026, 2026, 2026],
        "monthNumber": [6, 6, 6],
        "metricFOB": [600000.0, 610000.0, 590000.0],
        "metricKG": [1000000.0, 1020000.0, 980000.0],
        "metricFreight": [40000.0, 41000.0, 39000.0],
        "metricInsurance": [4000.0, 4100.0, 3900.0],
        "country": ["China", "Coreia do Sul", "Egito"],
    })

    m.comex_importacao_ncm = _comex_bloqueado
    m.sgs = _sgs_stub
    m.ibge_sidra_ipp_metalurgia = _ibge_stub
    m.taxa_penetracao_importacao_planos_mensal = _penet_stub
    try:
        resultado_dedup = m.calcular_ipia_mensal(2026, 2026, df_bruto=df_bruto_teste)
    finally:
        m.comex_importacao_ncm = _comex_original
        m.sgs = _sgs_original
        m.ibge_sidra_ipp_metalurgia = _ibge_original
        m.taxa_penetracao_importacao_planos_mensal = _penet_original

    assert chamadas_comex["n"] == 0
    assert not resultado_dedup.empty
    assert pd.Timestamp("2026-06-01") in resultado_dedup.index


def _tabelas_reconciliacao():
    idx_reconc = pd.date_range("2026-05-01", periods=2, freq="MS")
    df_ipia_reconc = pd.DataFrame({
        "preco_domestico_rs_t": [5000.0, 5236.0],
        "ppi_rs_t": [3600.0, 3728.0],
        "ipia": [138.9, 140.4],
        "tipo_dado_domestico": ["proxy_segmento_aco", "proxy_segmento_aco"],
        "metodo_domestico": ["nivel_trimestral", "nivel_trimestral"],
    }, index=idx_reconc)
    idx_custo_reconc = pd.date_range("2026-05-01", periods=3, freq="MS")  # 1 mes a mais que df_ipia
    df_custo_reconc = pd.DataFrame({
        "ppi_brl_t": [3600.0, 3728.0, 3806.0],
    }, index=idx_custo_reconc)
    return df_ipia_reconc, df_custo_reconc


def test_reconciliacao_spread_usa_mesmo_mes_de_df_ipia():
    df_ipia_reconc, df_custo_reconc = _tabelas_reconciliacao()
    assert m.checar_reconciliacao_spread(df_ipia_reconc, df_custo_reconc)


def test_contraprova_padrao_antigo_iloc_menos_um_nao_reconciliava():
    df_ipia_reconc, df_custo_reconc = _tabelas_reconciliacao()
    spread_correto = df_ipia_reconc["preco_domestico_rs_t"].iloc[-1] - df_ipia_reconc["ppi_rs_t"].iloc[-1]
    spread_do_bug_antigo = df_ipia_reconc["preco_domestico_rs_t"].iloc[-1] - df_custo_reconc["ppi_brl_t"].iloc[-1]
    assert abs(spread_correto - spread_do_bug_antigo) > 1.0
