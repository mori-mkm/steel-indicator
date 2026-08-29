"""Motor de narrativa determinístico do IPIA-HRC (Reporting V3).

Traduz números já calculados (IPIA, decomposição Shapley,
publication_status) em frases curtas e auditáveis - NUNCA recalcula
metodologia, NUNCA envia dado a um LLM, NUNCA introduz causa externa
(decisão de banco central, notícia de mercado, geopolítica) que não
esteja matematicamente presente na decomposição recebida como entrada.
Todo vocabulário vem de um conjunto FECHADO de templates fixos + os
nomes legíveis de driver já definidos em `indices_setoriais` - nunca
texto livre injetado.

Funções puras: nenhuma chamada de rede/filesystem, nenhuma dependência
de matplotlib. Testável isoladamente (`tests/unit/test_reporting_narrative.py`).
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import indices_setoriais as motor  # noqa: E402

DRIVERS_PPI_COST = motor.DRIVERS_PPI_COST
NOMES_LEGIVEIS = motor.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC

# Polaridade: para a maioria dos drivers de custo, uma contribuição
# NEGATIVA ao IPIA significa que o valor subjacente do driver SUBIU
# (custo de importação mais caro reduz o IPIA - Sec.14/15 do sprint
# anterior de Driver Decomposition, já testado em
# tests/unit/test_ipia_hrc_driver_decomposition.py). Para
# `domestic_price`, a relação é DIRETA (contribuição positiva = preço
# doméstico subiu). `margin` (só no modo Offer) segue a mesma polaridade
# inversa dos drivers de custo.
_DRIVERS_POLARIDADE_DIRETA = {"domestic_price"}


def direcao_valor_driver(driver: str, contribuicao: float, tol: float = 1e-9) -> str:
    """'alta'/'queda'/'estável' - a direção do VALOR subjacente do driver
    (não da contribuição em si), inferida da polaridade conhecida da
    fórmula (nunca uma suposição causal externa)."""
    if abs(contribuicao) <= tol:
        return "estável"
    positiva_significa_alta = driver in _DRIVERS_POLARIDADE_DIRETA
    subiu = (contribuicao > 0) == positiva_significa_alta
    return "alta" if subiu else "queda"


def ranking_drivers(contribuicoes: Dict[str, float],
                    drivers: Optional[Sequence[str]] = None) -> List[Tuple[str, float]]:
    """Ordena por |contribuição| decrescente (Sec.32 - nunca por
    contribuição líquida percentual). `drivers` restringe as chaves
    consideradas (por padrão, todas as chaves de `contribuicoes` que
    também estão em `DRIVERS_PPI_COST`/`margin` - ignora metadata como
    `residual`/`decomposition_method`)."""
    chaves_validas = set(drivers) if drivers is not None else (set(DRIVERS_PPI_COST) | {"margin"})
    itens = [(k, v) for k, v in contribuicoes.items() if k in chaves_validas]
    return sorted(itens, key=lambda kv: abs(kv[1]), reverse=True)


def classificar_sinal_paridade(ipia_atual: float) -> dict:
    """IMPORT PARITY SIGNAL (Sec.10) - puramente descritivo, SEM
    threshold arbitrário: só duas categorias (acima/abaixo de 100) mais
    o caso exato (=100), com a distância em pontos sempre reportada
    explicitamente ao lado da categoria - nunca uma faixa "near parity"
    inventada."""
    distancia = ipia_atual - 100.0
    if distancia > 0:
        categoria = "Domestic Premium"
    elif distancia < 0:
        categoria = "Import-Cost Premium"
    else:
        categoria = "At Parity"
    return {"categoria": categoria, "distancia_pts": distancia, "distancia_abs_pts": abs(distancia)}


def montar_interpretacao_100(ipia_atual: float) -> str:
    """Interpretação oficial do threshold 100 sob PPI_COST (ADR
    0015/0016 - nunca o texto legado de preço ofertado/margem)."""
    if ipia_atual > 100.0:
        return ("O preço doméstico está acima do custo estimado de paridade de importação "
                "(PPI_COST) — o produtor doméstico opera com prêmio sobre o custo de importar.")
    if ipia_atual < 100.0:
        return ("O preço doméstico está abaixo do custo estimado de paridade de importação "
                "(PPI_COST) — o produtor doméstico opera com desconto sobre o custo de importar.")
    return "O preço doméstico está exatamente no custo estimado de paridade de importação (PPI_COST)."


def montar_headline(ipia_atual: float) -> str:
    return f"IPIA-HRC em {ipia_atual:.1f} pontos"


def montar_tendencia_vantagem(ipia_atual: float, ipia_anterior: float) -> str:
    """'ampliando'/'reduzindo'/'mantendo estável' a distância (vantagem
    ou desvantagem) em relação à paridade 100 - derivado só da
    magnitude |IPIA-100|, nunca de uma causa externa."""
    vantagem_atual = abs(ipia_atual - 100.0)
    vantagem_anterior = abs(ipia_anterior - 100.0)
    if vantagem_atual > vantagem_anterior:
        return "ampliando"
    if vantagem_atual < vantagem_anterior:
        return "reduzindo"
    return "mantendo estável"


def montar_interpretacao_executiva(ipia_atual: float, ipia_anterior: float) -> str:
    """Frase interpretativa curta (Sec.7): posição vs. paridade +
    tendência da distância - inteiramente derivada dos dois números,
    nunca hardcoded."""
    posicao = "acima" if ipia_atual > 100.0 else "abaixo" if ipia_atual < 100.0 else "na"
    tendencia = montar_tendencia_vantagem(ipia_atual, ipia_anterior)
    if ipia_atual == 100.0:
        return "O preço doméstico está exatamente na paridade de custo de importação estimada."
    return (f"O preço doméstico permanece {posicao} do custo estimado de paridade de importação, "
           f"{tendencia} a distância no mês.")


def montar_what_changed(delta_ipia: float, contribuicoes: Dict[str, float],
                        drivers: Optional[Sequence[str]] = None) -> dict:
    """'O que mudou' (Sec.9): principal driver, segundo driver (mesma
    direção do movimento) e compensador (maior contribuição de sinal
    OPOSTO) - no máximo 3 drivers citados na sentença (Sec.9/33), vindos
    exclusivamente do ranking por |contribuição| (Sec.32), nunca de uma
    causa externa. Linguagem auditável (Sec.33): "principal
    contribuição"/"segunda maior contribuição"/"parcialmente compensado
    por" - nunca "forte"/"pressão significativa" sem regra quantitativa."""
    ranking = ranking_drivers(contribuicoes, drivers=drivers)
    ranking = [(k, v) for k, v in ranking if abs(v) > 1e-9]
    if not ranking:
        return {"principal": None, "segundo": None, "compensador": None,
               "sentenca": "Nenhum driver individual teve contribuição material no período."}

    mesma_direcao = [d for d in ranking if delta_ipia == 0 or (d[1] > 0) == (delta_ipia > 0)]
    oposta_direcao = [d for d in ranking if delta_ipia != 0 and (d[1] > 0) != (delta_ipia > 0)]

    principal = mesma_direcao[0] if mesma_direcao else ranking[0]
    segundo = mesma_direcao[1] if len(mesma_direcao) > 1 else None
    compensador = oposta_direcao[0] if oposta_direcao else None

    def _nome(driver: str) -> str:
        return NOMES_LEGIVEIS.get(driver, driver)

    verbo_movimento = "alta" if delta_ipia > 0 else "queda" if delta_ipia < 0 else "estabilidade"
    lideres_nomes = [_nome(principal[0])] + ([_nome(segundo[0])] if segundo else [])
    if len(lideres_nomes) == 1:
        trecho_lideres = lideres_nomes[0]
    else:
        trecho_lideres = f"{lideres_nomes[0]} e {lideres_nomes[1]}"

    sentenca = f"A {verbo_movimento} mensal foi liderada por {trecho_lideres}"
    if compensador:
        sentenca += f", parcialmente compensada por {_nome(compensador[0])}"
    sentenca += "."

    return {
        "principal": {"driver": principal[0], "nome": _nome(principal[0]), "contribuicao": principal[1],
                     "direcao_valor": direcao_valor_driver(principal[0], principal[1])},
        "segundo": ({"driver": segundo[0], "nome": _nome(segundo[0]), "contribuicao": segundo[1],
                    "direcao_valor": direcao_valor_driver(segundo[0], segundo[1])} if segundo else None),
        "compensador": ({"driver": compensador[0], "nome": _nome(compensador[0]), "contribuicao": compensador[1],
                        "direcao_valor": direcao_valor_driver(compensador[0], compensador[1])}
                       if compensador else None),
        "sentenca": sentenca,
    }


_TEMPLATES_CONFIANCA = {
    motor_status: texto for motor_status, texto in [
        ("PUBLICATION_GRADE", "Cobertura integral de política comercial validada para o período — "
                              "classificação de maior confiança da série."),
        ("EXPERIMENTAL", "Cobertura de política comercial com limitações conhecidas e quantificadas "
                         "para o período — ver metodologia para o intervalo de incerteza."),
        ("PROVISIONAL", "O preço doméstico após a última PIA anual é estimado pelo movimento do IPP e "
                        "será revisto quando um novo benchmark anual estiver disponível."),
    ]
}


def montar_confidence_sentence(publication_status: str) -> str:
    """Traduz o status técnico (Sec.21) em uma frase em linguagem clara -
    vocabulário fechado (`_TEMPLATES_CONFIANCA`), nunca texto livre."""
    return _TEMPLATES_CONFIANCA.get(
        publication_status,
        f"Status de publicação: {publication_status} — ver metodologia para o significado completo.")


def agrupar_para_waterfall(contribuicoes: Dict[str, float], limiar: float = 0.05,
                           drivers: Optional[Sequence[str]] = None,
                           rotulo_outros: str = "Outros") -> List[Tuple[str, float]]:
    """Agrupa, para exibição visual (Sec.14), drivers com |contribuição|
    abaixo de `limiar` num único item `rotulo_outros` - a soma dos itens
    devolvidos é SEMPRE exatamente igual à soma de `contribuicoes`
    (nenhum dado é descartado, só reagrupado para reduzir ruído visual).
    Preserva a ordem de entrada dos drivers materiais; o grupo "Outros"
    (se houver algum driver abaixo do limiar) vai por último. Nomes
    traduzidos via `NOMES_LEGIVEIS` - drivers desconhecidos mantêm o
    nome técnico."""
    itens = [(k, v) for k, v in contribuicoes.items()
            if drivers is None or k in drivers]
    materiais = [(NOMES_LEGIVEIS.get(k, k), v) for k, v in itens if abs(v) >= limiar]
    ruido = [v for _, v in itens if abs(v) < limiar]
    if ruido:
        materiais.append((rotulo_outros, sum(ruido)))
    return materiais


def gerar_resumo_executivo_ipia(ipia_atual: float, ipia_anterior: float,
                                decomposicao: dict, publication_status: str) -> dict:
    """Função determinística principal (Sec.31). Entradas: IPIA atual/
    anterior, o dict de decomposição de `indices_setoriais.decompor_variacao_ipia_hrc`
    (contribuições por driver + `delta_ipia`/`residual`/`dominant_driver`/
    `top_positive_driver`/`top_negative_driver`) e o `publication_status`
    do período atual.

    Saída estruturada (nunca só uma string): `headline`, `interpretation`,
    `signal` (Sec.10), `what_changed` (Sec.9 - principal/segundo/
    compensador/sentença), `main_driver`/`secondary_driver`/
    `offsetting_driver` (atalhos para `what_changed`, Sec.31),
    `confidence_sentence`, `delta_ipia_mom`.
    """
    what_changed = montar_what_changed(decomposicao["delta_ipia"], decomposicao)
    return {
        "headline": montar_headline(ipia_atual),
        "interpretation": montar_interpretacao_executiva(ipia_atual, ipia_anterior),
        "parity_interpretation": montar_interpretacao_100(ipia_atual),
        "signal": classificar_sinal_paridade(ipia_atual),
        "what_changed": what_changed,
        "main_driver": what_changed["principal"],
        "secondary_driver": what_changed["segundo"],
        "offsetting_driver": what_changed["compensador"],
        "confidence_sentence": montar_confidence_sentence(publication_status),
        "delta_ipia_mom": decomposicao["delta_ipia"],
    }
