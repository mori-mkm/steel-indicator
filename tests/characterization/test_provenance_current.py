"""Characterization tests for vintage/cutoff validation and provenance badges.

Externalizes selftest() sections 21b and 22 (validar_report_cutoff look-ahead
detection, and end-to-end classification -> selo_dado_texto badge rendering
for PROXY/ESTIMADO/OBSERVADO/formula_alternativa).

Also freezes the full row assembly of montar_tabela_vintage() (columns, order,
and per-variable values) ahead of Spec 0003 batch 2, which extracts the
generic list-of-VintageInfo -> DataFrame serialization into
steel_indicator/domain/provenance.py. classificar_* stay IPIA-V1-specific and
are not part of that extraction.
"""
import pandas as pd

import indices_setoriais as m
from reporting import components as rep_components


def _tabela_vintage_completa_teste():
    """Cobre as 6 linhas possiveis de montar_tabela_vintage() num unico
    cenario deterministico: ipia + preco_domestico + penetracao (via
    df_ipia), ppi_brl_t + cambio (via df_custo, um mes a mais que df_ipia,
    como no uso real) e origem_importacao_pct (via df_origem)."""
    idx_ipia = pd.date_range("2026-05-01", periods=2, freq="MS")
    df_ipia = pd.DataFrame({
        "tipo_dado_domestico": ["especifico_laminado_quente", "proxy_segmento_aco"],
        "metodo_domestico": ["nivel_trimestral", "encadeado_ipp"],
        "tipo_dado_penetracao": ["oficial_mensal", "aproximado_consumo_aparente"],
    }, index=idx_ipia)

    idx_custo = pd.date_range("2026-05-01", periods=3, freq="MS")
    df_custo = pd.DataFrame({"ppi_brl_t": [3600.0, 3728.0, 3806.0]}, index=idx_custo)

    df_origem = pd.DataFrame({"pct": [60.0, 40.0]}, index=["China", "Coreia"])
    df_origem.attrs["mes_inicio"] = pd.Timestamp("2026-01-01")
    df_origem.attrs["mes_fim"] = pd.Timestamp("2026-06-01")

    return m.montar_tabela_vintage(df_ipia, df_custo, df_origem)


_PROXY_MOTIVO_DOMESTICO_CONGELADO = (
    'Ancora domestica e proxy do segmento "Siderurgia", nao especifica '
    "de bobina a quente (ver docs/adr/0003)."
)


def test_montar_tabela_vintage_congela_colunas_e_ordem():
    tabela = _tabela_vintage_completa_teste()
    assert list(tabela.columns) == [
        "variavel", "reference_period", "fonte", "nivel", "proxy",
        "proxy_motivo", "metodo", "metodo_motivo", "periodo_texto",
    ]
    assert tabela["variavel"].tolist() == [
        "ipia", "preco_domestico_rs_t", "penetracao_importacao_planos_pct",
        "ppi_brl_t", "cambio", "origem_importacao_pct",
    ]


def test_montar_tabela_vintage_congela_linha_ipia():
    linha = _tabela_vintage_completa_teste().set_index("variavel").loc["ipia"]
    assert linha["reference_period"] == pd.Timestamp("2026-06-01")
    assert linha["fonte"] == "Comex Stat + BCB/SGS + CSV curado (Usiminas/CSN) + IBGE/SIDRA IPP"
    assert linha["nivel"] == m.NIVEL_ESTIMADO
    assert bool(linha["proxy"]) is True
    assert linha["proxy_motivo"] == _PROXY_MOTIVO_DOMESTICO_CONGELADO
    assert linha["metodo"] == "encadeado_ipp"
    assert pd.isna(linha["metodo_motivo"])
    assert pd.isna(linha["periodo_texto"])


def test_montar_tabela_vintage_congela_linha_preco_domestico():
    linha = _tabela_vintage_completa_teste().set_index("variavel").loc["preco_domestico_rs_t"]
    assert linha["reference_period"] == pd.Timestamp("2026-06-01")
    assert linha["fonte"] == "Releases trimestrais Usiminas/CSN + IBGE/SIDRA IPP (encadeamento mensal)"
    assert linha["nivel"] == m.NIVEL_ESTIMADO
    assert bool(linha["proxy"]) is True
    assert linha["proxy_motivo"] == _PROXY_MOTIVO_DOMESTICO_CONGELADO
    assert linha["metodo"] == "encadeado_ipp"


def test_montar_tabela_vintage_congela_linha_penetracao():
    linha = _tabela_vintage_completa_teste().set_index("variavel").loc["penetracao_importacao_planos_pct"]
    assert linha["reference_period"] == pd.Timestamp("2026-06-01")
    assert linha["fonte"] == 'Instituto Aço Brasil (Excel "Performance Mensal", cálculo próprio)'
    assert linha["nivel"] == m.NIVEL_CALCULADO
    assert bool(linha["proxy"]) is False
    assert pd.isna(linha["proxy_motivo"])
    assert linha["metodo"] == m.METODO_FORMULA_ALTERNATIVA
    assert "docs/adr/0007" in linha["metodo_motivo"]


def test_montar_tabela_vintage_congela_linha_custo_internacao_e_cambio():
    tabela = _tabela_vintage_completa_teste().set_index("variavel")

    linha_ppi = tabela.loc["ppi_brl_t"]
    assert linha_ppi["reference_period"] == pd.Timestamp("2026-07-01")
    assert linha_ppi["fonte"] == "Comex Stat (FOB/frete/seguro) + BCB/SGS (cambio)"
    assert linha_ppi["nivel"] == m.NIVEL_CALCULADO
    assert bool(linha_ppi["proxy"]) is False

    linha_cambio = tabela.loc["cambio"]
    assert linha_cambio["reference_period"] == pd.Timestamp("2026-07-01")
    assert linha_cambio["fonte"] == "BCB/SGS (PTAX venda)"
    assert linha_cambio["nivel"] == m.NIVEL_OBSERVADO
    assert bool(linha_cambio["proxy"]) is False


def test_montar_tabela_vintage_congela_linha_origem_importacao():
    linha = _tabela_vintage_completa_teste().set_index("variavel").loc["origem_importacao_pct"]
    assert linha["reference_period"] == pd.Timestamp("2026-06-01")
    assert linha["fonte"] == "Comex Stat (agregado por país)"
    assert linha["nivel"] == m.NIVEL_CALCULADO
    assert bool(linha["proxy"]) is False
    assert linha["periodo_texto"] == "2026-01 a 2026-06"


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
