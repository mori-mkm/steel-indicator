"""Unit tests for agregar_ipia_hrc_multi_ncm_mensal() / custo_importacao_bottom_up_mensal()
- agregador bottom-up multi-NCM do IPIA-HRC V2 (Stage E7, ADR 0009, decisao
  Level 3 aprovada). Deterministic, no network: `sgs` e stubado (cambio) e
  `domestico_df` e injetado direto (mesmo padrao de test_ipia_hrc_v2.py).

Prova: II/AFRMM/antidumping sao resolvidos por (mes, ncm, pais) ANTES de
qualquer soma; a agregacao pondera por KG (nunca NCM representativo, nunca
media simples, nunca aliquota unica sobre CIF ja combinado); as duas
politicas de publicacao (EXPERIMENTAL 60%+2%, PUBLICATION_GRADE 100%) se
comportam exatamente como aprovado; UNKNOWN nunca redistribui peso; o
legado permanece intacto; nao ha look-ahead entre meses.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN


def _linha(ano, mes, ncm, country="China", fob=6_000_000.0, kg=10_000_000.0, frete=200_000.0, seguro=20_000.0):
    return {"year": ano, "monthNumber": mes, "ncm": ncm, "country": country,
            "metricFOB": fob, "metricKG": kg, "metricFreight": frete, "metricInsurance": seguro}


def _dom_df(ano, mes, preco_rs_t=5000.0):
    idx = pd.DatetimeIndex([pd.Timestamp(year=ano, month=mes, day=1)])
    return pd.DataFrame({"preco_rs_t": [preco_rs_t], "metodo": ["nivel_trimestral"],
                         "trimestre_base": ["teste"], "tipo_dado": ["proxy_segmento_aco"]}, index=idx)


def _stub_sgs(cambio=5.0):
    def _sgs(codigo, inicio="01/01/2010"):
        return pd.Series([cambio], index=[pd.Timestamp("2000-01-01")], name=f"sgs_{codigo}")
    return _sgs


def _rodar(ano, mes, rows, preco_dom=5000.0):
    original_sgs = m.sgs
    m.sgs = _stub_sgs()
    try:
        return m.agregar_ipia_hrc_multi_ncm_mensal(
            ano_ini=ano, ano_fim=ano, df_bruto=pd.DataFrame(rows),
            domestico_df=_dom_df(ano, mes, preco_dom))
    finally:
        m.sgs = original_sgs


# --- 1. KG-weighted average entre dois NCMs com aliquota de II diferente ----
# (72083700=12%, 72081000... nao, usar 72083910=10% - excecao ja em 2012)
# prova bottom-up: nao aplica uma unica aliquota ao CIF combinado.

def test_dois_ncms_aliquotas_diferentes_agregam_por_kg():
    rows = [
        _linha(2019, 6, "72083700", kg=6_000_000.0, fob=3_600_000.0, frete=120_000.0, seguro=12_000.0),
        _linha(2019, 6, "72083910", kg=4_000_000.0, fob=2_400_000.0, frete=80_000.0, seguro=8_000.0),
    ]
    out = _rodar(2019, 6, rows).iloc[0]
    assert out["publication_status"] == STATUS_EXPERIMENTAL

    # ppi esperado: media dos dois PPIs individuais (mesma formula ja
    # aprovada de custo_importacao_historico_mensal), ponderada por kg -
    # NUNCA a aliquota de um unico NCM aplicada ao CIF combinado.
    cambio = pd.Series([5.0], index=[pd.Timestamp("2019-06-01")])
    c37 = m.custo_importacao_historico_mensal(
        pd.Series([600.0], index=cambio.index), pd.Series([20.0], index=cambio.index),
        pd.Series([2.0], index=cambio.index), cambio, ncm="72083700")
    c39 = m.custo_importacao_historico_mensal(
        pd.Series([600.0], index=cambio.index), pd.Series([20.0], index=cambio.index),
        pd.Series([2.0], index=cambio.index), cambio, ncm="72083910")
    esperado = (c37["ppi_brl_t"].iloc[0] * 6_000_000.0 + c39["ppi_brl_t"].iloc[0] * 4_000_000.0) / 10_000_000.0
    assert out["ppi_rs_t"] == pytest.approx(esperado)
    # top-down (aplicar 12% ao CIF combinado) daria um numero diferente
    assert out["ppi_rs_t"] != pytest.approx(c37["ppi_brl_t"].iloc[0])


# --- 2. Politica (antidumping) resolvida por PAIS antes de agregar ----------

def test_antidumping_resolvido_por_pais_antes_de_agregar(monkeypatch):
    def _fake_resolver_antidumping(origin, data, exporter=None):
        from steel_indicator.parameters.trade_policy import ResultadoAntidumping, STATUS_PUBLICATION_GRADE as SPG
        valor = 50.0 if origin == "Paisimaginario" else 0.0
        return ResultadoAntidumping(origin=origin, exporter=exporter, data=data, nominal_value=valor,
                                     unit="USD/t", suspended=False, effective_value=valor,
                                     status=SPG, legal_basis="teste", nota=None)

    monkeypatch.setattr(m, "resolver_antidumping", _fake_resolver_antidumping)
    rows = [
        _linha(2024, 6, "72083700", country="China", kg=6_000_000.0, fob=3_600_000.0, frete=120_000.0, seguro=12_000.0),
        _linha(2024, 6, "72083700", country="Paisimaginario", kg=4_000_000.0, fob=2_400_000.0, frete=80_000.0, seguro=8_000.0),
    ]
    out = _rodar(2024, 6, rows).iloc[0]
    assert out["publication_status"] == STATUS_PUBLICATION_GRADE

    cambio = pd.Series([5.0], index=[pd.Timestamp("2024-06-01")])
    china = m.custo_importacao_bottom_up_mensal(pd.DataFrame([rows[0]]), cambio)
    outro = m.custo_importacao_bottom_up_mensal(pd.DataFrame([rows[1]]), cambio)
    esperado = (china["ppi_brl_t"].iloc[0] * 6_000_000.0 + outro["ppi_brl_t"].iloc[0] * 4_000_000.0) / 10_000_000.0
    assert out["ppi_rs_t"] == pytest.approx(esperado)
    assert china["ppi_brl_t"].iloc[0] != outro["ppi_brl_t"].iloc[0]  # antidumping realmente mudou o custo por pais


# --- 3. NCM sem importacao (kg=0) tem peso zero, nao distorce a media ------

def test_ncm_com_kg_zero_nao_distorce_media():
    rows_sem_zero = [
        _linha(2024, 6, "72083700", kg=6_000_000.0, fob=3_600_000.0, frete=120_000.0, seguro=12_000.0),
        _linha(2024, 6, "72083890", kg=4_000_000.0, fob=2_400_000.0, frete=80_000.0, seguro=8_000.0),
    ]
    rows_com_zero = rows_sem_zero + [_linha(2024, 6, "72082500", kg=0.0, fob=0.0, frete=0.0, seguro=0.0)]
    out_sem = _rodar(2024, 6, rows_sem_zero).iloc[0]
    out_com = _rodar(2024, 6, rows_com_zero).iloc[0]
    assert out_com["ppi_rs_t"] == pytest.approx(out_sem["ppi_rs_t"])
    assert out_com["total_kg"] == pytest.approx(out_sem["total_kg"])


# --- 4. EXPERIMENTAL: coverage>=60% + range<=2% -> calculavel ---------------

def test_experimental_coverage_alta_e_range_baixo_e_calculavel():
    rows = [
        _linha(2019, 6, "72083700", kg=9_000_000.0, fob=5_400_000.0, frete=180_000.0, seguro=18_000.0),
        _linha(2019, 6, "72081000", kg=1_000_000.0, fob=600_000.0, frete=20_000.0, seguro=2_000.0),
    ]
    out = _rodar(2019, 6, rows).iloc[0]
    assert out["policy_coverage"] == pytest.approx(0.9)
    assert out["ppi_uncertainty_range_pct"] <= 0.02
    assert out["publication_status"] == STATUS_EXPERIMENTAL
    assert not np.isnan(out["ppi_rs_t"])
    assert not np.isnan(out["ipia"])


# --- 5. EXPERIMENTAL: coverage < 60% -> UNKNOWN (nunca calculado) ----------

def test_experimental_coverage_baixa_e_unknown():
    rows = [
        _linha(2019, 6, "72083910", kg=1_000_000.0, fob=600_000.0, frete=20_000.0, seguro=2_000.0),
        _linha(2019, 6, "72081000", kg=9_000_000.0, fob=5_400_000.0, frete=180_000.0, seguro=18_000.0),
    ]
    out = _rodar(2019, 6, rows).iloc[0]
    assert out["policy_coverage"] == pytest.approx(0.1)
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["ppi_rs_t"])
    assert np.isnan(out["ipia"])


# --- 6. EXPERIMENTAL: coverage>=60% mas range>2% -> UNKNOWN -----------------

def test_experimental_coverage_alta_mas_range_alto_e_unknown():
    rows = [
        _linha(2019, 6, "72083700", kg=6_000_000.0, fob=3_600_000.0, frete=120_000.0, seguro=12_000.0),
        _linha(2019, 6, "72081000", kg=4_000_000.0, fob=10_000_000.0, frete=80_000.0, seguro=8_000.0),  # NCM
        # nao confirmado com preco unitario muito mais alto - amplifica o
        # impacto da faixa 10%-14% de II desconhecido sobre o range%.
    ]
    out = _rodar(2019, 6, rows).iloc[0]
    assert out["policy_coverage"] == pytest.approx(0.6)
    assert out["ppi_uncertainty_range_pct"] > 0.02
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["ppi_rs_t"])
    assert np.isnan(out["ipia"])
    # transparencia: ppi_lower/upper continuam preservados mesmo com status UNKNOWN
    assert not np.isnan(out["ppi_lower"])
    assert not np.isnan(out["ppi_upper"])


# --- 7. PUBLICATION_GRADE: 100% conhecido -> calculado ----------------------

def test_publication_grade_100pct_conhecido_e_calculado():
    rows = [
        _linha(2024, 6, "72083700", kg=6_000_000.0, fob=3_600_000.0, frete=120_000.0, seguro=12_000.0),
        _linha(2024, 6, "72083890", kg=4_000_000.0, fob=2_400_000.0, frete=80_000.0, seguro=8_000.0),
    ]
    out = _rodar(2024, 6, rows).iloc[0]
    assert out["policy_coverage"] == pytest.approx(1.0)
    assert out["publication_status"] == STATUS_PUBLICATION_GRADE
    assert not np.isnan(out["ppi_rs_t"])
    assert not np.isnan(out["ipia"])
    assert out["ppi_uncertainty_range_pct"] == pytest.approx(0.0)


# --- 8. PUBLICATION_GRADE: 99% conhecido -> UNKNOWN, sem redistribuir peso -

def test_publication_grade_99pct_conhecido_e_unknown_sem_redistribuir():
    rows = [
        _linha(2026, 7, "72081000", kg=9_900_000.0, fob=5_940_000.0, frete=198_000.0, seguro=19_800.0),
        _linha(2026, 7, "72083910", kg=100_000.0, fob=60_000.0, frete=2_000.0, seguro=200.0),  # dentro
        # da janela de cota GECEX 929/2026 - consumo de cota nao rastreado, UNKNOWN.
    ]
    out = _rodar(2026, 7, rows).iloc[0]
    assert out["policy_coverage"] == pytest.approx(0.99)
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["ppi_rs_t"])
    assert np.isnan(out["ipia"])


# --- 9. jul/2026-like: maioria do volume sob cota -> UNKNOWN ----------------
# 2026-07 esta na janela PUBLICATION_GRADE (>= 2022-04-01), nao na
# EXPERIMENTAL - este teste prova o mesmo ramo "qualquer kg desconhecido
# torna o mes inteiro UNKNOWN, sem redistribuir peso" do teste 8, so que
# com a maioria (nao so 1%) do volume sob a cota GECEX 929/2026.

def test_maioria_sob_cota_2026_e_unknown():
    rows = [
        _linha(2026, 7, "72083910", kg=9_000_000.0, fob=5_400_000.0, frete=180_000.0, seguro=18_000.0),
        _linha(2026, 7, "72081000", kg=1_000_000.0, fob=600_000.0, frete=20_000.0, seguro=2_000.0),
    ]
    out = _rodar(2026, 7, rows).iloc[0]
    assert out["policy_coverage"] < 0.60
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["ppi_rs_t"])
    assert np.isnan(out["ipia"])


# --- 10. Formula do IPIA preservada -----------------------------------------

def test_formula_ipia_preservada():
    rows = [_linha(2024, 6, "72083700", kg=10_000_000.0, fob=6_000_000.0, frete=200_000.0, seguro=20_000.0)]
    out = _rodar(2024, 6, rows, preco_dom=5236.0).iloc[0]
    assert out["ipia"] == pytest.approx(out["preco_domestico_rs_t"] / out["ppi_rs_t"] * 100.0)


# --- 11. Legado permanece intacto (mesmo dado bruto multi-NCM/pais) --------

def test_legado_serie_mensal_e_calcular_ipia_mensal_nao_alterados():
    rows = [
        _linha(2024, 6, "72083700", country="China", kg=6_000_000.0, fob=3_600_000.0, frete=120_000.0, seguro=12_000.0),
        _linha(2024, 6, "72083890", country="Coreia do Sul", kg=4_000_000.0, fob=2_400_000.0, frete=80_000.0, seguro=8_000.0),
    ]
    df_bruto = pd.DataFrame(rows)
    bobina = m.serie_mensal_preco_bobina(2024, 2024, df_bruto=df_bruto)
    assert "ncm" not in bobina.columns and "country" not in bobina.columns  # legado continua cego a NCM/pais
    esperado_preco = 1000 * (3_600_000.0 + 2_400_000.0) / (6_000_000.0 + 4_000_000.0)
    assert bobina.set_index("data").loc["2024-06-01", "preco_usd_t"] == pytest.approx(esperado_preco)

    original_sgs, original_ibge, original_penet = m.sgs, m.ibge_sidra_ipp_metalurgia, m.taxa_penetracao_importacao_planos_mensal
    m.sgs = _stub_sgs()
    m.ibge_sidra_ipp_metalurgia = lambda periodos="all": pd.Series(dtype=float)
    m.taxa_penetracao_importacao_planos_mensal = lambda **kw: pd.DataFrame(
        {"taxa_penetracao_pct": pd.Series(dtype=float), "tipo_dado_penetracao": pd.Series(dtype=object)})
    try:
        r = m.calcular_ipia_mensal(2024, 2024, df_bruto=df_bruto)
        assert "ipia" in r.columns and "ppi_rs_t" in r.columns
    finally:
        m.sgs, m.ibge_sidra_ipp_metalurgia, m.taxa_penetracao_importacao_planos_mensal = (
            original_sgs, original_ibge, original_penet)


# --- 12. Ausencia de look-ahead: mes seguinte nao afeta o mes anterior -----

def test_sem_look_ahead_entre_meses():
    linha_junho = _linha(2024, 6, "72083700", kg=6_000_000.0, fob=3_600_000.0, frete=120_000.0, seguro=12_000.0)
    linha_julho = _linha(2024, 7, "72083910", kg=1_000_000.0, fob=1_400_000.0, frete=30_000.0, seguro=3_000.0)

    def _rodar_multi(rows, dom_meses):
        original_sgs = m.sgs
        m.sgs = _stub_sgs()
        try:
            dom = pd.concat([_dom_df(a, mm) for a, mm in dom_meses])
            return m.agregar_ipia_hrc_multi_ncm_mensal(
                ano_ini=2024, ano_fim=2024, df_bruto=pd.DataFrame(rows), domestico_df=dom)
        finally:
            m.sgs = original_sgs

    so_junho = _rodar_multi([linha_junho], [(2024, 6)])
    junho_e_julho = _rodar_multi([linha_junho, linha_julho], [(2024, 6), (2024, 7)])

    linha_so = so_junho.set_index("reference_period").loc["2024-06-01"]
    linha_com_julho = junho_e_julho.set_index("reference_period").loc["2024-06-01"]
    assert linha_so["ppi_rs_t"] == pytest.approx(linha_com_julho["ppi_rs_t"])
    assert linha_so["publication_status"] == linha_com_julho["publication_status"]
