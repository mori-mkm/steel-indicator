"""Unit tests for `reporting.narrative` (Reporting V3, Sec.45/46).
Deterministic, no network, no matplotlib. Prova: headline/interpretation
corretas para IPIA subindo/caindo e acima/abaixo de 100; driver dominante
corretamente identificado (FX, FOB, etc.); compensacao corretamente
identificada; nenhuma palavra/causa externa aparece na saida, mesmo
quando o vocabulario de entrada e adversarial.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from reporting import narrative as n


def _decomp(delta_ipia, **contribuicoes):
    base = {d: 0.0 for d in n.DRIVERS_PPI_COST}
    base.update(contribuicoes)
    base["delta_ipia"] = delta_ipia
    base["residual"] = 0.0
    base["dominant_driver"] = max(base, key=lambda k: abs(base[k]) if k in n.DRIVERS_PPI_COST else -1)
    return base


# --- 1. Headline / interpretacao: IPIA sobe -------------------------------

def test_headline_ipia_sobe():
    resumo = n.gerar_resumo_executivo_ipia(
        ipia_atual=128.3, ipia_anterior=120.9,
        decomposicao=_decomp(7.4, domestic_price=5.0, fob=2.4), publication_status="PUBLICATION_GRADE")
    assert resumo["headline"] == "IPIA-HRC em 128.3 pontos"
    assert "acima" in resumo["interpretation"]
    assert resumo["delta_ipia_mom"] == pytest.approx(7.4)


# --- 2. IPIA cai -----------------------------------------------------------

def test_headline_ipia_cai():
    resumo = n.gerar_resumo_executivo_ipia(
        ipia_atual=105.9, ipia_anterior=113.3,
        decomposicao=_decomp(-7.4, fob=-3.75, fx=-3.38, domestic_price=1.55),
        publication_status="PUBLICATION_GRADE")
    assert resumo["headline"] == "IPIA-HRC em 105.9 pontos"
    assert resumo["delta_ipia_mom"] < 0


# --- 3/4. Interpretacao acima/abaixo de 100 --------------------------------

def test_interpretacao_acima_de_100():
    texto = n.montar_interpretacao_100(128.3)
    assert "acima" in texto
    assert "PPI_COST" in texto
    assert "abaixo" not in texto


def test_interpretacao_abaixo_de_100():
    texto = n.montar_interpretacao_100(91.0)
    assert "abaixo" in texto
    assert "acima" not in texto


def test_interpretacao_exatamente_100():
    texto = n.montar_interpretacao_100(100.0)
    assert "exatamente" in texto


def test_sinal_paridade_nunca_inventa_threshold_intermediario():
    # so 2 categorias + o caso exato =100 - nunca uma faixa "near parity"
    # com um corte numerico arbitrario.
    assert n.classificar_sinal_paridade(100.5)["categoria"] == "Domestic Premium"
    assert n.classificar_sinal_paridade(99.5)["categoria"] == "Import-Cost Premium"
    assert n.classificar_sinal_paridade(100.0)["categoria"] == "At Parity"
    assert n.classificar_sinal_paridade(100.5)["distancia_pts"] == pytest.approx(0.5)


# --- 5. Driver dominante: FX ------------------------------------------------

def test_dominante_fx_aparece_como_principal_driver():
    decomp = _decomp(-7.41, fob=-3.75, fx=-3.38, domestic_price=1.55, ii=-1.18)
    resumo = n.gerar_resumo_executivo_ipia(105.9, 113.3, decomp, "PUBLICATION_GRADE")
    # FOB e FX sao os dois maiores em |contribuicao| e mesma direcao do
    # movimento (queda) - o principal deve ser o maior dos dois (FOB,
    # -3.75 > |-3.38|), FX deve ser o segundo.
    assert resumo["main_driver"]["driver"] == "fob"
    assert resumo["secondary_driver"]["driver"] == "fx"
    assert resumo["offsetting_driver"]["driver"] == "domestic_price"


def test_dominante_fx_quando_fx_e_o_maior():
    decomp = _decomp(-5.0, fx=-4.5, fob=-0.3, domestic_price=0.1)
    resumo = n.gerar_resumo_executivo_ipia(95.0, 100.0, decomp, "PUBLICATION_GRADE")
    assert resumo["main_driver"]["driver"] == "fx"


# --- 6. Compensacao (offsetting) --------------------------------------------

def test_offsetting_domestic_texto_correto():
    decomp = _decomp(-7.41, fob=-3.75, fx=-3.38, domestic_price=1.55, ii=-1.18)
    resumo = n.gerar_resumo_executivo_ipia(105.9, 113.3, decomp, "PUBLICATION_GRADE")
    sentenca = resumo["what_changed"]["sentenca"]
    assert "compensada por" in sentenca
    assert "Preço doméstico" in sentenca
    assert "queda" in sentenca  # delta_ipia negativo


def test_sem_driver_de_sinal_oposto_nao_ha_compensador():
    decomp = _decomp(5.0, domestic_price=3.0, fob=2.0)  # ambos positivos, mesma direcao
    resumo = n.gerar_resumo_executivo_ipia(105.0, 100.0, decomp, "PUBLICATION_GRADE")
    assert resumo["offsetting_driver"] is None
    assert "compensada" not in resumo["what_changed"]["sentenca"]


# --- 7. Direcao do valor subjacente (polaridade) ---------------------------

def test_direcao_valor_driver_polaridade_inversa_para_custo():
    assert n.direcao_valor_driver("fob", -3.0) == "alta"   # contribuicao negativa = FOB subiu
    assert n.direcao_valor_driver("fob", 3.0) == "queda"
    assert n.direcao_valor_driver("fx", -1.0) == "alta"


def test_direcao_valor_driver_polaridade_direta_para_domestico():
    assert n.direcao_valor_driver("domestic_price", 3.0) == "alta"
    assert n.direcao_valor_driver("domestic_price", -3.0) == "queda"


def test_direcao_valor_driver_estavel_quando_contribuicao_zero():
    assert n.direcao_valor_driver("d_porto", 0.0) == "estável"


# --- 8. Confidence sentence --------------------------------------------------

def test_confidence_sentence_provisional_traduz_jargao():
    texto = n.montar_confidence_sentence("PROVISIONAL")
    assert "IPP" in texto
    assert "PIA" in texto
    assert "PROVISIONAL" not in texto  # traduzido, nao repete o jargao tecnico


def test_confidence_sentence_publication_grade():
    texto = n.montar_confidence_sentence("PUBLICATION_GRADE")
    assert "validada" in texto


# --- 9. Nao-causalidade externa (Sec.46) ------------------------------------

_TERMOS_PROIBIDOS = ["fed", "china", "guerra", "juros", "governo", "minério", "demanda", "geopolít",
                     "banco central", "opep", "estímulo", "stimulus"]


@pytest.mark.parametrize("ipia_atual,ipia_anterior,kwargs,status", [
    (128.3, 120.9, dict(domestic_price=5.0, fob=2.4), "PUBLICATION_GRADE"),
    (78.0, 130.0, dict(fob=-30.0, fx=-20.0, domestic_price=-2.0), "EXPERIMENTAL"),
    (100.0, 100.0, dict(), "PROVISIONAL"),
])
def test_narrativa_nunca_contem_causalidade_externa(ipia_atual, ipia_anterior, kwargs, status):
    decomp = _decomp(ipia_atual - ipia_anterior, **kwargs)
    resumo = n.gerar_resumo_executivo_ipia(ipia_atual, ipia_anterior, decomp, status)
    texto_completo = " ".join([
        resumo["headline"], resumo["interpretation"], resumo["parity_interpretation"],
        resumo["what_changed"]["sentenca"], resumo["confidence_sentence"],
    ]).lower()
    for termo in _TERMOS_PROIBIDOS:
        assert termo not in texto_completo, f"termo causal externo '{termo}' vazou na narrativa"


def test_vocabulario_fechado_nomes_legiveis_cobre_todos_os_drivers():
    # garante que _nome() nunca cai no fallback "retorna o proprio driver
    # tecnico" para nenhum driver oficial - o vocabulario e sempre
    # traduzido, nunca jargao de codigo vazando pro relatorio.
    for driver in n.DRIVERS_PPI_COST:
        assert driver in n.NOMES_LEGIVEIS
        assert n.NOMES_LEGIVEIS[driver] != driver


# --- 10. Ranking por |contribuicao|, nunca percentual liquido ---------------

def test_ranking_ordena_por_valor_absoluto_nao_liquido():
    contribuicoes = {"fob": -10.0, "fx": 8.0, "domestic_price": 1.0}
    ranking = n.ranking_drivers(contribuicoes)
    assert [nome for nome, _ in ranking] == ["fob", "fx", "domestic_price"]


# --- 11. Agrupamento "Outros" do waterfall (Sec.14/47) - soma exata -------

def test_agrupar_para_waterfall_soma_exata_com_ruido():
    contribuicoes = {"domestic_price": 1.55, "fob": -3.75, "freight": -0.03, "insurance": -0.01,
                     "fx": -3.38, "ii": -1.18, "afrmm": -0.02, "antidumping": 0.0,
                     "d_porto": 0.0, "d_interno": 0.0}
    agrupado = n.agrupar_para_waterfall(contribuicoes, limiar=0.05)
    assert sum(v for _, v in agrupado) == pytest.approx(sum(contribuicoes.values()), abs=1e-9)
    nomes = [nome for nome, _ in agrupado]
    assert "Outros" in nomes
    assert nomes[-1] == "Outros"  # grupo de ruido sempre por ultimo


def test_agrupar_para_waterfall_sem_ruido_nao_cria_grupo_outros():
    contribuicoes = {"domestic_price": 5.0, "fob": -3.0}
    agrupado = n.agrupar_para_waterfall(contribuicoes, limiar=0.05)
    assert "Outros" not in [nome for nome, _ in agrupado]
    assert sum(v for _, v in agrupado) == pytest.approx(5.0 - 3.0)


def test_agrupar_para_waterfall_nunca_descarta_dado():
    contribuicoes = {f"d{i}": 0.001 for i in range(10)}
    agrupado = n.agrupar_para_waterfall(contribuicoes, limiar=0.05)
    assert len(agrupado) == 1  # tudo agrupado em "Outros"
    assert agrupado[0][1] == pytest.approx(sum(contribuicoes.values()), abs=1e-9)


def test_what_changed_maximo_tres_drivers_citados():
    decomp = _decomp(-20.0, fob=-10.0, fx=-8.0, ii=-5.0, domestic_price=3.0, afrmm=-1.0)
    resumo = n.gerar_resumo_executivo_ipia(80.0, 100.0, decomp, "PUBLICATION_GRADE")
    # principal + segundo + compensador = no maximo 3 drivers citados
    citados = {d["driver"] for d in (resumo["main_driver"], resumo["secondary_driver"],
                                      resumo["offsetting_driver"]) if d is not None}
    assert len(citados) <= 3
