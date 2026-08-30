"""Unit tests for `indices_setoriais.detectar_composicao_atipica_importacao`
(ADR 0018). Deterministico, sem rede - `df_bruto` sempre injetado.

Cobre: volume estavel -> normal; volume abaixo do limiar vs. mediana
movel de 12 meses -> atipico, com motivos preenchidos; historico
insuficiente -> indeterminado (nunca finge baseline); mes ausente/df
vazio -> indeterminado sem excecao; contexto de origem (top_pais) sempre
calculado, mesmo quando normal, e NUNCA usado para decidir o status
(concentracao de origem foi testada e rejeitada como gatilho - ver
comentario no modulo); regressao com os numeros reais de jun/2026 que
motivaram este diagnostico (congelados aqui, nao lidos do cache
gitignored de validacao).
"""
import pandas as pd
import pytest

import indices_setoriais as m


def _linha(ano, mes, coNcm="72083990", country="China", fob=6_000_000.0, kg=10_000_000.0,
          frete=200_000.0, seguro=20_000.0):
    return {"year": ano, "monthNumber": mes, "coNcm": coNcm, "ncm": f"descricao {coNcm}",
            "country": country, "metricFOB": fob, "metricKG": kg, "metricFreight": frete,
            "metricInsurance": seguro}


def _serie_estavel_12_meses(kg_por_mes=10_000_000.0, ano_ini=2025, mes_ini=1, **kw):
    linhas = []
    ano, mes = ano_ini, mes_ini
    for _ in range(12):
        linhas.append(_linha(ano, mes, kg=kg_por_mes, **kw))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
    return linhas


# --- 1. Volume estável -------------------------------------------------------

def test_volume_estavel_e_normal():
    linhas = _serie_estavel_12_meses()
    # mes avaliado (13o mes), volume igual aos anteriores
    linhas.append(_linha(2026, 1, kg=10_000_000.0))
    df = pd.DataFrame(linhas)
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2026-01-01"), df_bruto=df)
    assert r["status"] == m.STATUS_COMPOSICAO_NORMAL
    assert r["motivos"] == []
    assert r["razao_volume"] == pytest.approx(1.0, abs=0.05)


# --- 2. Volume abaixo do limiar -----------------------------------------------

def test_volume_muito_abaixo_do_limiar_e_atipico_com_motivos():
    linhas = _serie_estavel_12_meses(kg_por_mes=30_000_000.0)
    linhas.append(_linha(2026, 1, kg=5_000_000.0))  # ~17% da mediana trailing - bem abaixo de 0.35
    df = pd.DataFrame(linhas)
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2026-01-01"), df_bruto=df)
    assert r["status"] == m.STATUS_COMPOSICAO_ATIPICO
    assert r["razao_volume"] < m.LIMIAR_RAZAO_VOLUME_ATIPICO
    assert len(r["motivos"]) >= 1
    assert "volume" in r["motivos"][0].lower()


def test_volume_um_pouco_acima_do_limiar_permanece_normal():
    linhas = _serie_estavel_12_meses(kg_por_mes=10_000_000.0)
    linhas.append(_linha(2026, 1, kg=4_000_000.0))  # razao=0.4 > limiar 0.35
    df = pd.DataFrame(linhas)
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2026-01-01"), df_bruto=df)
    assert r["status"] == m.STATUS_COMPOSICAO_NORMAL


# --- 3. Histórico insuficiente nunca finge baseline --------------------------

def test_historico_insuficiente_e_indeterminado():
    linhas = _serie_estavel_12_meses()[:3]  # so 3 meses de trailing, < MIN_MESES_TRAILING_COMPOSICAO
    linhas.append(_linha(2025, 4, kg=1_000_000.0))
    df = pd.DataFrame(linhas)
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2025-04-01"), df_bruto=df)
    assert r["status"] == m.STATUS_COMPOSICAO_INDETERMINADO
    assert r["motivos"] == []


# --- 4. Mês ausente / df vazio nunca lança exceção ---------------------------

def test_mes_ausente_e_indeterminado_sem_excecao():
    df = pd.DataFrame(_serie_estavel_12_meses())
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2030-01-01"), df_bruto=df)
    assert r["status"] == m.STATUS_COMPOSICAO_INDETERMINADO


def test_df_vazio_e_indeterminado_sem_excecao():
    df = pd.DataFrame(columns=["year", "monthNumber", "coNcm", "ncm", "country",
                               "metricFOB", "metricKG", "metricFreight", "metricInsurance"])
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2026-01-01"), df_bruto=df)
    assert r["status"] == m.STATUS_COMPOSICAO_INDETERMINADO


# --- 5. Contexto de origem sempre calculado, nunca decide o status ----------

def test_contexto_de_origem_calculado_mesmo_quando_normal():
    linhas = _serie_estavel_12_meses(country="Coreia do Sul")
    linhas.append(_linha(2026, 1, country="Coreia do Sul", kg=10_000_000.0))
    df = pd.DataFrame(linhas)
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2026-01-01"), df_bruto=df)
    assert r["status"] == m.STATUS_COMPOSICAO_NORMAL
    assert r["top_pais"] == "Coreia do Sul"
    assert r["top_pais_pct"] == pytest.approx(100.0)


def test_concentracao_extrema_sozinha_nao_dispara_atipico():
    """Um so pais responder por 100% do volume NAO deve, sozinho, marcar
    atipico - concentracao de origem foi testada com dado real e
    rejeitada como gatilho (mediana historica de top-1 pais e ~82%,
    disparar em concentracao alta marcaria a maioria dos meses normais).
    So a razao de volume decide o status."""
    linhas = _serie_estavel_12_meses(country="Egito", kg_por_mes=20_000_000.0)
    linhas.append(_linha(2026, 1, country="Egito", kg=20_000_000.0))  # 100% de 1 pais, volume normal
    df = pd.DataFrame(linhas)
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2026-01-01"), df_bruto=df)
    assert r["top_pais_pct"] == pytest.approx(100.0)
    assert r["status"] == m.STATUS_COMPOSICAO_NORMAL


# --- 6. Regressão real: jun/2026 (o incidente que motivou este diagnóstico) --

def test_regressao_junho_2026_e_atipico():
    """Numeros reais (Comex Stat, mesmo dado que gerou o vintage
    20260829T174456Z) congelados aqui - nao le o cache gitignored de
    validacao. mar-mai/2026 com volume normal (~40-72 mil t), jun/2026
    com 16.281 t (queda de 64% vs. maio) - a razao vs. mediana movel dos
    meses anteriores fica bem abaixo do limiar. Trava o comportamento no
    caso real que motivou a ADR 0018."""
    volumes_kg = {  # toneladas reais (mesma base do vintage) * 1000
        (2025, 7): 68767290, (2025, 8): 74987892, (2025, 9): 75609249,
        (2025, 10): 9245138, (2025, 11): 70426224, (2025, 12): 49430205,
        (2026, 1): 34655786, (2026, 2): 71452219, (2026, 3): 72197254,
        (2026, 4): 39663011, (2026, 5): 44843420, (2026, 6): 16281008,
    }
    linhas = [_linha(ano, mes, country="China", kg=float(kg)) for (ano, mes), kg in volumes_kg.items()]
    df = pd.DataFrame(linhas)
    r = m.detectar_composicao_atipica_importacao(pd.Timestamp("2026-06-01"), df_bruto=df)
    assert r["status"] == m.STATUS_COMPOSICAO_ATIPICO
    assert r["razao_volume"] < 0.35
    assert r["n_meses_trailing"] == 11
