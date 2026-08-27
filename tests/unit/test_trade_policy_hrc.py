"""Unit tests for the Historical Import Policy Model
(steel_indicator/parameters/trade_policy.py). Deterministic, no network, no
dependency on indices_setoriais or calcular_ipia_mensal (not wired yet).

Covers: II lookup by NCM/period, the 72083910 exception, AFRMM before/after
its rate change, antidumping suspended-vs-effective, absence of a measure,
the 2026/27 quota returning explicit UNKNOWN instead of guessing, the
PUBLICATION_GRADE/EXPERIMENTAL/UNKNOWN split, and no look-ahead at exact
temporal boundaries.
"""
import pandas as pd
import pytest

from steel_indicator.parameters.trade_policy import (
    STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN,
    resolver_ii, resolver_afrmm, resolver_antidumping, status_efetivo,
    _TABELA_II, _JANELAS_COTA,
)


# --- II: lookup por NCM e periodo, incluindo a excecao 72083910 -------------

def test_ii_periodo_experimental_ncm_confirmado():
    r = resolver_ii("72083700", pd.Timestamp("2015-06-01"))
    assert r.aliquota == pytest.approx(0.12)
    assert r.status == STATUS_EXPERIMENTAL
    assert r.legal_basis is not None


def test_ii_periodo_publication_grade_ncm_confirmado():
    r = resolver_ii("72083700", pd.Timestamp("2023-01-01"))
    assert r.aliquota == pytest.approx(0.108)
    assert r.status == STATUS_PUBLICATION_GRADE


def test_ii_excecao_72083910_experimental():
    r = resolver_ii("72083910", pd.Timestamp("2015-06-01"))
    assert r.aliquota == pytest.approx(0.10)
    assert r.status == STATUS_EXPERIMENTAL


def test_ii_excecao_72083910_publication_grade():
    r = resolver_ii("72083910", pd.Timestamp("2023-01-01"))
    assert r.aliquota == pytest.approx(0.09)
    assert r.status == STATUS_PUBLICATION_GRADE


def test_ii_ncm_nao_comprovado_no_periodo_experimental_e_unknown():
    r = resolver_ii("72081000", pd.Timestamp("2015-06-01"))
    assert r.aliquota is None
    assert r.status == STATUS_UNKNOWN
    assert "nao comprovado" in r.nota


def test_ii_ncm_nao_comprovado_no_periodo_publication_grade_tem_valor():
    r = resolver_ii("72081000", pd.Timestamp("2023-01-01"))
    assert r.aliquota == pytest.approx(0.108)
    assert r.status == STATUS_PUBLICATION_GRADE


# --- II: fronteira temporal exata, sem look-ahead ---------------------------

def test_ii_fronteira_2022_04_sem_look_ahead():
    antes = resolver_ii("72083700", pd.Timestamp("2022-03-31"))
    depois = resolver_ii("72083700", pd.Timestamp("2022-04-01"))
    assert antes.aliquota == pytest.approx(0.12)
    assert antes.status == STATUS_EXPERIMENTAL
    assert depois.aliquota == pytest.approx(0.108)
    assert depois.status == STATUS_PUBLICATION_GRADE


# --- II: cota 2026/27 - UNKNOWN explicito, nunca escolha silenciosa --------

def test_ii_cota_2026_2027_retorna_unknown_explicito():
    r = resolver_ii("72083910", pd.Timestamp("2026-07-01"))
    assert r.aliquota is None
    assert r.status == STATUS_UNKNOWN
    assert "cota" in r.nota
    assert "9.0%" in r.nota or "9%" in r.nota
    assert "25.0%" in r.nota or "25%" in r.nota


def test_ii_apos_fim_da_cota_volta_ao_normal():
    r = resolver_ii("72083910", pd.Timestamp("2027-06-26"))
    assert r.aliquota == pytest.approx(0.09)
    assert r.status == STATUS_PUBLICATION_GRADE


def test_ii_ncm_sem_cota_nao_e_afetado_na_janela_929_2026():
    # 72081000 nao esta na lista da Res. GECEX 929/2026 - deve resolver normalmente.
    r = resolver_ii("72081000", pd.Timestamp("2026-07-01"))
    assert r.aliquota == pytest.approx(0.108)
    assert r.status == STATUS_PUBLICATION_GRADE


# --- AFRMM: antes/depois da mudanca, fronteira exata ------------------------

def test_afrmm_antes_da_mudanca():
    r = resolver_afrmm(pd.Timestamp("2022-03-24"))
    assert r.aliquota == pytest.approx(0.25)


def test_afrmm_depois_da_mudanca_sem_look_ahead():
    r = resolver_afrmm(pd.Timestamp("2022-03-25"))
    assert r.aliquota == pytest.approx(0.08)


def test_afrmm_2023_inteiro_e_8_pct_stf_tema_1368():
    r = resolver_afrmm(pd.Timestamp("2023-06-15"))
    assert r.aliquota == pytest.approx(0.08)


# --- Antidumping: nominal vs. efetivo --------------------------------------

def test_antidumping_suspenso_tem_nominal_mas_efetivo_zero():
    r = resolver_antidumping("China", pd.Timestamp("2019-01-01"), exporter="Maanshan Iron & Steel Company Ltd.")
    assert r.nominal_value == pytest.approx(154.68)
    assert r.suspended is True
    assert r.effective_value == 0.0


def test_antidumping_periodo_sem_medida_e_zero():
    r = resolver_antidumping("China", pd.Timestamp("2021-06-01"))
    assert r.nominal_value is None
    assert r.effective_value == 0.0
    assert r.suspended is False


def test_antidumping_investigacao_2025_sem_direito_provisorio_e_zero():
    r = resolver_antidumping("China", pd.Timestamp("2026-01-01"))
    assert r.nominal_value is None
    assert r.effective_value == 0.0
    assert "investigacao" in r.nota


def test_antidumping_residual_quando_exportador_nao_informado():
    # "Russia" em ingles (sem acento) nunca daria match aqui - o campo
    # `country` real do Comex Stat vem em portugues, "Rússia" com acento.
    # Fix em trade_policy.py (Stage E7): _MEDIDAS_ANTIDUMPING passou a usar
    # "Rússia" para bater com o dado real (confirmado ao vivo na API).
    r = resolver_antidumping("Rússia", pd.Timestamp("2019-01-01"))
    assert r.nominal_value == pytest.approx(207.43)
    assert r.effective_value == 0.0


# --- Publication status geral ------------------------------------------------

def test_periodo_publication_grade_generico():
    assert resolver_ii("72083910", pd.Timestamp("2022-04-01")).status == STATUS_PUBLICATION_GRADE
    assert resolver_afrmm(pd.Timestamp("2022-04-01")).status == STATUS_PUBLICATION_GRADE


def test_periodo_experimental_generico():
    assert resolver_ii("72083910", pd.Timestamp("2022-03-31")).status == STATUS_EXPERIMENTAL
    assert resolver_afrmm(pd.Timestamp("2012-01-01")).status == STATUS_EXPERIMENTAL


def test_parametro_realmente_desconhecido_e_unknown():
    r = resolver_ii("72082610", pd.Timestamp("2018-01-01"))
    assert r.status == STATUS_UNKNOWN
    assert r.aliquota is None


# --- status_efetivo: PUBLICATION_GRADE nunca coexiste com parametro UNKNOWN -

def test_status_efetivo_a_2024_ncm_normal_parametros_conhecidos_e_publication_grade():
    data = pd.Timestamp("2024-01-01")
    ii = resolver_ii("72083700", data)
    afrmm = resolver_afrmm(data)
    ad = resolver_antidumping("China", data)
    assert status_efetivo(ii.status, afrmm.status, ad.status) == STATUS_PUBLICATION_GRADE


def test_status_efetivo_b_2018_ncm_com_ii_desconhecido_nunca_e_publication_grade():
    data = pd.Timestamp("2018-01-01")
    ii = resolver_ii("72081000", data)  # um dos 9 NCMs sem II comprovado no periodo experimental
    afrmm = resolver_afrmm(data)
    assert ii.status == STATUS_UNKNOWN
    assert status_efetivo(ii.status, afrmm.status) == STATUS_UNKNOWN
    assert status_efetivo(ii.status, afrmm.status) != STATUS_PUBLICATION_GRADE


def test_status_efetivo_c_cota_2026_consumo_desconhecido_e_unknown():
    data = pd.Timestamp("2026-07-01")
    ii = resolver_ii("72083910", data)  # NCM afetado pela cota GECEX 929/2026
    afrmm = resolver_afrmm(data)
    assert ii.aliquota is None
    assert ii.status == STATUS_UNKNOWN
    assert status_efetivo(ii.status, afrmm.status) == STATUS_UNKNOWN


def test_status_efetivo_d_cota_2026_ncm_nao_afetado_e_publication_grade():
    data = pd.Timestamp("2026-07-01")
    ii = resolver_ii("72081000", data)  # NCM fora da lista da Res. GECEX 929/2026
    afrmm = resolver_afrmm(data)
    assert status_efetivo(ii.status, afrmm.status) == STATUS_PUBLICATION_GRADE


def test_status_efetivo_e_regra_geral_qualquer_unknown_domina():
    assert status_efetivo(STATUS_PUBLICATION_GRADE, STATUS_UNKNOWN) == STATUS_UNKNOWN
    assert status_efetivo(STATUS_UNKNOWN, STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL) == STATUS_UNKNOWN
    assert status_efetivo(STATUS_PUBLICATION_GRADE, STATUS_PUBLICATION_GRADE) == STATUS_PUBLICATION_GRADE
    assert status_efetivo(STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL) == STATUS_EXPERIMENTAL


def test_status_efetivo_um_unico_status_e_identidade():
    assert status_efetivo(STATUS_EXPERIMENTAL) == STATUS_EXPERIMENTAL
    assert status_efetivo(STATUS_PUBLICATION_GRADE) == STATUS_PUBLICATION_GRADE
    assert status_efetivo(STATUS_UNKNOWN) == STATUS_UNKNOWN


def test_status_efetivo_sem_argumentos_levanta_erro_em_vez_de_publication_grade_por_omissao():
    with pytest.raises(ValueError):
        status_efetivo()


# --- ausencia de sobreposicao de faixas temporais por NCM -------------------

def test_tabela_ii_nao_tem_faixas_sobrepostas_por_ncm():
    por_ncm = {}
    for f in _TABELA_II:
        por_ncm.setdefault(f.ncm, []).append(f)
    for ncm, faixas in por_ncm.items():
        ordenadas = sorted(faixas, key=lambda f: f.valid_from)
        for a, b in zip(ordenadas, ordenadas[1:]):
            fim_a = a.valid_to if a.valid_to is not None else pd.Timestamp.max
            assert fim_a < b.valid_from, f"faixas de II sobrepostas para {ncm}: {a} vs {b}"


def test_janelas_cota_nao_se_sobrepoe_por_ncm():
    por_ncm = {}
    for j in _JANELAS_COTA:
        por_ncm.setdefault(j.ncm, []).append(j)
    for ncm, janelas in por_ncm.items():
        ordenadas = sorted(janelas, key=lambda j: j.sub_periodo_inicio)
        for a, b in zip(ordenadas, ordenadas[1:]):
            assert a.sub_periodo_fim < b.sub_periodo_inicio, f"sub-periodos de cota sobrepostos para {ncm}: {a} vs {b}"


# --- fronteiras adicionais de antidumping (recomendacao do reviewer) -------

def test_antidumping_inicio_exato_da_medida_2018_01_19():
    r = resolver_antidumping("China", pd.Timestamp("2018-01-19"), exporter="Maanshan Iron & Steel Company Ltd.")
    assert r.nominal_value == pytest.approx(154.68)
    assert r.suspended is True
    assert r.effective_value == 0.0


def test_antidumping_dia_anterior_ao_inicio_da_medida_sem_direito():
    r = resolver_antidumping("China", pd.Timestamp("2018-01-18"))
    assert r.nominal_value is None
    assert r.effective_value == 0.0


def test_antidumping_2020_01_17_ainda_dentro_da_medida_suspensa():
    r = resolver_antidumping("China", pd.Timestamp("2020-01-17"), exporter="Maanshan Iron & Steel Company Ltd.")
    assert r.nominal_value == pytest.approx(154.68)
    assert r.suspended is True
    assert r.effective_value == 0.0


def test_antidumping_2020_01_18_ja_extinta_sem_medida():
    r = resolver_antidumping("China", pd.Timestamp("2020-01-18"), exporter="Maanshan Iron & Steel Company Ltd.")
    assert r.nominal_value is None
    assert r.effective_value == 0.0


def test_antidumping_investigacao_inicio_exato_2025_06_03():
    r = resolver_antidumping("China", pd.Timestamp("2025-06-03"))
    assert r.nominal_value is None
    assert r.effective_value == 0.0
    assert "investigacao" in r.nota


def test_antidumping_dia_anterior_a_investigacao_sem_nenhuma_medida():
    r = resolver_antidumping("China", pd.Timestamp("2025-06-02"))
    assert r.nominal_value is None
    assert r.effective_value == 0.0
    assert "nenhuma medida" in r.nota


# --- fronteiras adicionais da cota 2026/27 (recomendacao do reviewer) ------

def test_cota_dia_anterior_ao_inicio_ainda_e_aliquota_normal():
    r = resolver_ii("72083910", pd.Timestamp("2026-06-25"))
    assert r.aliquota == pytest.approx(0.09)
    assert r.status == STATUS_PUBLICATION_GRADE


def test_cota_dia_exato_do_inicio_e_unknown():
    r = resolver_ii("72083910", pd.Timestamp("2026-06-26"))
    assert r.aliquota is None
    assert r.status == STATUS_UNKNOWN
