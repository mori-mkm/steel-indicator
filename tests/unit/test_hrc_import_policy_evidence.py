"""Testes puros e deterministicos (sem rede) para
scripts/validar_hrc_import_policy_evidence.py - sprint "IPIA-HRC - IMPORT
POLICY EVIDENCE HARDENING". VALIDATION ONLY: nao testa disponibilidade
online corrente (Sec.25 do sprint) - so a logica de vigencia/candidate
classification/contrafactual que e determinstica. Nao promove nenhuma
decisao metodologica (Level 3, do usuario); so garante que o script nao
altera producao e que a logica candidata esta correta.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pandas as pd
import pytest

import validar_hrc_import_policy_evidence as v
import indices_setoriais as m
import steel_indicator.parameters.trade_policy as tp


# =============================================================================
# Correcao de aliquota 2022+ (VERIFIED) - nunca aplicada fora de vigencia
# =============================================================================

def test_correcao_aliquota_so_se_aplica_dentro_da_janela_publication_grade():
    # antes de 2022-04-01, o NCM corrigido continua UNKNOWN (nao vira 9% cedo demais)
    antes = v.resolver_ii_candidato("72082610", pd.Timestamp("2022-03-31"))
    assert antes.status == tp.STATUS_UNKNOWN
    assert antes.aliquota is None


def test_correcao_aliquota_aplica_9_pct_a_partir_de_2022_04_01():
    depois = v.resolver_ii_candidato("72082610", pd.Timestamp("2022-04-01"))
    assert depois.aliquota == pytest.approx(0.09)
    assert depois.status == tp.STATUS_PUBLICATION_GRADE
    assert "VERIFIED" in depois.nota


def test_correcao_aliquota_cobre_exatamente_os_4_codigos_encontrados():
    data = pd.Timestamp("2023-01-01")
    for ncm in ("72082610", "72082710", "72083610", "72083810"):
        r = v.resolver_ii_candidato(ncm, data)
        assert r.aliquota == pytest.approx(0.09), f"{ncm} deveria corrigir para 9%"
    # 72083910 ja estava certo em producao (nao e "correcao", so preserva)
    r_ja_certo = v.resolver_ii_candidato("72083910", data)
    assert r_ja_certo.aliquota == pytest.approx(0.09)
    # codigos NAO afetados continuam iguais a producao (10.8%)
    for ncm in ("72081000", "72082500", "72082690", "72082790", "72083690", "72083700", "72083890", "72083990"):
        candidato = v.resolver_ii_candidato(ncm, data)
        atual = tp.resolver_ii(ncm, data)
        assert candidato.aliquota == atual.aliquota, f"{ncm} nao deveria mudar"


def test_correcao_aliquota_nunca_promove_ncm_desconhecido():
    # um NCM fora da cesta HRC continua UNKNOWN no candidato tambem
    r = v.resolver_ii_candidato("99999999", pd.Timestamp("2023-01-01"))
    assert r.status == tp.STATUS_UNKNOWN


# =============================================================================
# Elevacao DCC (Res. GECEX 865/2026) - vigencia exata, nunca vaza pra fora
# =============================================================================

def test_elevacao_dcc_so_dentro_da_janela_865_2026():
    ncm = "72082690"
    antes = v.resolver_ii_candidato(ncm, pd.Timestamp("2026-02-25"))
    dentro_inicio = v.resolver_ii_candidato(ncm, pd.Timestamp("2026-02-26"))
    dentro_fim = v.resolver_ii_candidato(ncm, pd.Timestamp("2027-02-25"))
    depois = v.resolver_ii_candidato(ncm, pd.Timestamp("2027-02-26"))

    assert antes.aliquota == pytest.approx(0.108)  # antes da elevacao, TEC normal
    assert dentro_inicio.aliquota == pytest.approx(0.25)
    assert dentro_fim.aliquota == pytest.approx(0.25)
    assert depois.aliquota == pytest.approx(0.108)  # volta ao normal apos o fim da vigencia


def test_elevacao_dcc_cobre_so_os_2_codigos_sem_cota():
    # 2026-07-01 esta dentro do 1o sub-periodo da cota 929/2026 (2026-06-26 a
    # 2026-10-25) E dentro da vigencia da elevacao 865/2026 (2026-02-26+)
    data = pd.Timestamp("2026-07-01")
    for ncm in ("72082690", "72082790"):
        r = v.resolver_ii_candidato(ncm, data)
        assert r.aliquota == pytest.approx(0.25)
    # os 4 codigos com cota 929/2026 NAO sao afetados pela elevacao 865/2026
    # (mecanismos diferentes) - continuam UNKNOWN dentro do sub-periodo da
    # cota (producao ja resolve isso, candidato reusa sem alteracao)
    for ncm in ("72083700", "72083890", "72083910", "72083990"):
        r = v.resolver_ii_candidato(ncm, data)
        atual = tp.resolver_ii(ncm, data)
        assert r.status == atual.status == tp.STATUS_UNKNOWN


# =============================================================================
# Contrafactual: monkeypatch nunca vaza para o modulo de producao
# =============================================================================

def test_rodar_contrafactual_restaura_resolver_ii_mesmo_apos_excecao(monkeypatch):
    original = m.resolver_ii
    vazio = pd.DataFrame({"year": [], "monthNumber": [], "coNcm": [], "country": [],
                           "metricFOB": [], "metricKG": []})
    monkeypatch.setattr(m, "_comex_bobina_bruto", lambda ano_ini, ano_fim: vazio.copy())

    chamadas = {"n": 0}

    def primeira_ok_segunda_quebra(*a, **kw):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return pd.DataFrame({"reference_period": [], "publication_status": [],
                                  "ppi_rs_t": [], "total_kg": []})
        raise RuntimeError("falha proposital dentro do bloco com resolver_ii ja trocado")

    monkeypatch.setattr(m, "agregar_ipia_hrc_multi_ncm_mensal", primeira_ok_segunda_quebra)
    with pytest.raises(RuntimeError):
        v.rodar_contrafactual(ano_ini=2023, ano_fim=2023)
    assert chamadas["n"] == 2  # confirma que a excecao ocorreu DEPOIS do resolver_ii ja trocado
    assert m.resolver_ii is original  # nunca fica com o candidato ativo em producao


def test_resolver_ii_candidato_nunca_e_o_mesmo_objeto_que_producao_apos_rodar():
    # rodar_contrafactual troca e restaura m.resolver_ii - garantimos que a
    # funcao candidata em si nao É a funcao de producao (nomes diferentes)
    assert v.resolver_ii_candidato is not tp.resolver_ii


# =============================================================================
# Comparacao current vs candidate - status/valor
# =============================================================================

def test_comparar_current_candidate_detecta_mudanca_de_status():
    atual = pd.DataFrame({"reference_period": ["2023-01-01"], "publication_status": ["UNKNOWN"],
                           "ppi_rs_t": [float("nan")], "total_kg": [1000]})
    candidato = pd.DataFrame({"reference_period": ["2023-01-01"], "publication_status": ["EXPERIMENTAL"],
                               "ppi_rs_t": [2500.0]})
    out = v.comparar_current_candidate(atual, candidato)
    linha = out.iloc[0]
    assert linha["status_mudou"]
    assert linha["publication_status_current"] == "UNKNOWN"
    assert linha["publication_status_candidate"] == "EXPERIMENTAL"


def test_comparar_current_candidate_calcula_delta_pct_quando_status_igual():
    atual = pd.DataFrame({"reference_period": ["2023-01-01"], "publication_status": ["PUBLICATION_GRADE"],
                           "ppi_rs_t": [1000.0], "total_kg": [1000]})
    candidato = pd.DataFrame({"reference_period": ["2023-01-01"], "publication_status": ["PUBLICATION_GRADE"],
                               "ppi_rs_t": [1050.0]})
    out = v.comparar_current_candidate(atual, candidato)
    linha = out.iloc[0]
    assert not linha["status_mudou"]
    assert linha["ppi_delta_pct"] == pytest.approx(0.05)


# =============================================================================
# Investigacao 2020-11 - classificacao correta a partir de consultas repetidas
# =============================================================================

def test_investigar_2020_11_classifica_true_zero_quando_reproduzivel(monkeypatch):
    vazio = pd.DataFrame({"year": [], "monthNumber": [], "coNcm": [], "country": [],
                           "metricFOB": [], "metricKG": []})

    def fake_bobina_bruto(ano_ini, ano_fim):
        return vazio.copy()

    monkeypatch.setattr(m, "_comex_bobina_bruto", fake_bobina_bruto)
    resultado = v.investigar_2020_11()
    assert resultado["classificacao"] == "TRUE_ZERO"
    assert resultado["consultas_identicas"]
    assert resultado["n_linhas_consulta_a"] == 0


def test_investigar_2020_11_classifica_api_instability_quando_consultas_divergem(monkeypatch):
    chamadas = {"n": 0}

    def fake_bobina_bruto(ano_ini, ano_fim):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return pd.DataFrame({"year": [2020], "monthNumber": ["11"], "coNcm": ["72083700"],
                                  "country": ["China"], "metricFOB": [1000], "metricKG": [2000]})
        return pd.DataFrame({"year": [], "monthNumber": [], "coNcm": [], "country": [],
                              "metricFOB": [], "metricKG": []})

    monkeypatch.setattr(m, "_comex_bobina_bruto", fake_bobina_bruto)
    resultado = v.investigar_2020_11()
    assert resultado["classificacao"] == "API_INSTABILITY"
    assert resultado["n_linhas_consulta_a"] != resultado["n_linhas_consulta_b"]


# =============================================================================
# Inventario / cota - nunca inventa NCM ou codigo alem do que ja existe
# =============================================================================

def test_inventario_ncm_cobre_exatamente_os_13_codigos_de_producao():
    inv = v.inventario_ncm()
    esperado = set(sum(m.NCM_BOBINA_QUENTE.values(), []))
    assert set(inv["ncm"]) == esperado
    assert len(inv) == 13


def test_cota_929_2026_volumes_tem_3_subperiodos_para_cada_um_dos_4_codigos():
    tab = v.COTA_929_2026_VOLUMES_KG
    contagem = tab.groupby("ncm").size()
    assert set(contagem.index) == {"72083700", "72083890", "72083910", "72083990"}
    assert (contagem == 3).all()
    assert (tab["quota_kg"] > 0).all()  # nenhuma cota zero/negativa fabricada
