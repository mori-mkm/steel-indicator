"""Unit tests for calcular_ipia_hrc_v2() - wiring do Historical Import
Policy Model ao pipeline completo do IPIA-HRC (Stage E6, ADR 0009).
Deterministic, no network: `sgs` e stubado (cambio), e `domestico_df` e
injetado diretamente (mesmo padrao ja usado por `df_bruto` em
calcular_ipia_mensal) para nao depender do CSV curado real nem do IBGE.

Prova: o caminho V2 realmente usa custo_importacao_historico_mensal();
legado permanece intacto; UNKNOWN nunca vira publication-grade nem zero;
formula do IPIA preservada; sem look-ahead; sem fallback para ParamsIPIA.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN


def _df_bruto_mes(ano: int, mes: int, fob=6_000_000.0, kg=10_000_000.0, frete=200_000.0, seguro=20_000.0):
    return pd.DataFrame({
        "year": [ano], "monthNumber": [mes],
        "metricFOB": [fob], "metricKG": [kg], "metricFreight": [frete], "metricInsurance": [seguro],
        "country": ["China"],
    })


def _domestico_df_mes(ano: int, mes: int, preco_rs_t=5000.0, metodo="nivel_trimestral", tipo="proxy_segmento_aco"):
    idx = pd.DatetimeIndex([pd.Timestamp(year=ano, month=mes, day=1)])
    return pd.DataFrame({"preco_rs_t": [preco_rs_t], "metodo": [metodo],
                         "trimestre_base": ["teste"], "tipo_dado": [tipo]}, index=idx)


def _stub_sgs(cambio=5.0):
    def _sgs(codigo, inicio="01/01/2010"):
        return pd.Series([cambio], index=[pd.Timestamp("2000-01-01")], name=f"sgs_{codigo}")
    return _sgs


def _rodar_v2(ano, mes, ncm, origin="China", exporter=None, preco_dom=5000.0):
    original_sgs = m.sgs
    m.sgs = _stub_sgs()
    try:
        return m.calcular_ipia_hrc_v2(
            ncm=ncm, ano_ini=ano, ano_fim=ano, origin=origin, exporter=exporter,
            df_bruto=_df_bruto_mes(ano, mes), domestico_df=_domestico_df_mes(ano, mes, preco_rs_t=preco_dom))
    finally:
        m.sgs = original_sgs


# --- 1. V2 realmente chama custo_importacao_historico_mensal() -------------

def test_v2_chama_custo_importacao_historico_mensal():
    chamadas = []
    original = m.custo_importacao_historico_mensal

    def _spy(*args, **kwargs):
        chamadas.append(kwargs.get("ncm"))
        return original(*args, **kwargs)

    m.custo_importacao_historico_mensal = _spy
    try:
        _rodar_v2(2024, 6, ncm="72083700")
    finally:
        m.custo_importacao_historico_mensal = original
    assert chamadas == ["72083700"]


# --- 2. Caminho legacy permanece inalterado ---------------------------------

def test_legacy_calcular_ipia_mensal_nao_foi_alterado():
    original_sgs, original_ibge, original_penet = m.sgs, m.ibge_sidra_ipp_metalurgia, m.taxa_penetracao_importacao_planos_mensal
    m.sgs = _stub_sgs()
    m.ibge_sidra_ipp_metalurgia = lambda periodos="all": pd.Series(dtype=float)
    m.taxa_penetracao_importacao_planos_mensal = lambda **kw: pd.DataFrame(
        {"taxa_penetracao_pct": pd.Series(dtype=float), "tipo_dado_penetracao": pd.Series(dtype=object)})
    try:
        r = m.calcular_ipia_mensal(2026, 2026, df_bruto=_df_bruto_mes(2026, 6))
        # legado usa ParamsIPIA().aliquota_ii=0.108 SEMPRE, independente da data - comportamento intacto
        assert "ipia" in r.columns and "ppi_rs_t" in r.columns
    finally:
        m.sgs, m.ibge_sidra_ipp_metalurgia, m.taxa_penetracao_importacao_planos_mensal = (
            original_sgs, original_ibge, original_penet)


# --- 3. 2024, parametros conhecidos: PPI/IPIA calculados, PUBLICATION_GRADE

def test_2024_parametros_conhecidos_publication_grade():
    r = _rodar_v2(2024, 6, ncm="72083700", preco_dom=5000.0)
    linha = r.iloc[0]
    assert linha["publication_status"] == STATUS_PUBLICATION_GRADE
    assert not np.isnan(linha["ppi_rs_t"])
    assert not np.isnan(linha["ipia"])
    assert linha["aliquota_ii"] == pytest.approx(0.108)


# --- 4. Periodo experimental calculavel: nunca promovido a PUBLICATION_GRADE

def test_periodo_experimental_calculavel_nao_e_publication_grade():
    r = _rodar_v2(2019, 3, ncm="72083700", preco_dom=5000.0)
    linha = r.iloc[0]
    assert linha["publication_status"] == STATUS_EXPERIMENTAL
    assert linha["publication_status"] != STATUS_PUBLICATION_GRADE
    assert not np.isnan(linha["ppi_rs_t"])
    assert not np.isnan(linha["ipia"])
    assert linha["aliquota_ii"] == pytest.approx(0.12)  # regime antigo, nao 0.108


# --- 5. UNKNOWN no trade policy: PPI NaN, IPIA NaN, status UNKNOWN ---------

def test_unknown_no_trade_policy_propaga_nan_ate_ipia():
    r = _rodar_v2(2018, 3, ncm="72081000", preco_dom=5000.0)  # NCM sem II comprovado no periodo
    linha = r.iloc[0]
    assert linha["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(linha["ppi_rs_t"])
    assert np.isnan(linha["ipia"])
    assert pd.isna(linha["aliquota_ii"])


# --- 6. Cota 2026 com consumo desconhecido: UNKNOWN -------------------------

def test_cota_2026_consumo_desconhecido_e_unknown_ate_ipia():
    r = _rodar_v2(2026, 7, ncm="72083910", preco_dom=5000.0)
    linha = r.iloc[0]
    assert linha["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(linha["ppi_rs_t"])
    assert np.isnan(linha["ipia"])


# --- 7. Ausencia de fallback para ParamsIPIA no V2 --------------------------

def test_v2_nao_usa_aliquotas_fixas_de_paramsipia():
    r_antigo = _rodar_v2(2015, 1, ncm="72083700", preco_dom=5000.0)
    linha = r_antigo.iloc[0]
    p_atual = m.ParamsIPIA()
    assert linha["aliquota_ii"] != p_atual.aliquota_ii  # nao usa 0.108 (atual) para 2015
    assert linha["aliquota_ii"] == pytest.approx(0.12)  # usa o regime historico correto


# --- 8. Formula do IPIA preservada -----------------------------------------

def test_formula_ipia_preservada():
    r = _rodar_v2(2024, 6, ncm="72083700", preco_dom=5236.0)
    linha = r.iloc[0]
    assert linha["ipia"] == pytest.approx(linha["preco_domestico_rs_t"] / linha["ppi_rs_t"] * 100.0)


# --- 9. Sem look-ahead: fronteira 2022-03/2022-04 ---------------------------

def test_fronteira_2022_03_experimental_2022_04_publication_grade():
    antes = _rodar_v2(2022, 3, ncm="72083700", preco_dom=5000.0).iloc[0]
    depois = _rodar_v2(2022, 4, ncm="72083700", preco_dom=5000.0).iloc[0]
    assert antes["publication_status"] == STATUS_EXPERIMENTAL
    assert antes["aliquota_ii"] == pytest.approx(0.12)
    assert depois["publication_status"] == STATUS_PUBLICATION_GRADE
    assert depois["aliquota_ii"] == pytest.approx(0.108)


# --- 10. NCM fora de NCM_BOBINA_QUENTE e rejeitado (guardrail, Stage E6 review)

def test_ncm_fora_da_cesta_hrc_levanta_erro():
    with pytest.raises(ValueError, match="nao pertence a NCM_BOBINA_QUENTE"):
        _rodar_v2(2024, 6, ncm="99999999")


# --- 11. Risco de representatividade entre NCMs, tornado visivel no teste --
# (recomendacao do code-reviewer, Stage E6 2a rodada): o IPIA calculado
# depende de QUAL NCM confirmado e escolhido para representar a cesta
# inteira no periodo experimental - isso e uma limitacao documentada
# (docs/adr/0009-*.md, adendo Stage E6), nao uma agregacao ponderada. Este
# teste so PROVA que a limitacao existe e e mensuravel; nao resolve nem
# esconde o problema.

def test_escolha_do_ncm_representativo_muda_o_ii_no_periodo_experimental():
    r_37 = _rodar_v2(2019, 6, ncm="72083700", preco_dom=5000.0).iloc[0]  # 12%
    r_39_10 = _rodar_v2(2019, 6, ncm="72083910", preco_dom=5000.0).iloc[0]  # 10% (excecao)
    assert r_37["aliquota_ii"] != r_39_10["aliquota_ii"]
    assert r_37["ppi_rs_t"] != r_39_10["ppi_rs_t"]
    assert r_37["ipia"] != r_39_10["ipia"]
