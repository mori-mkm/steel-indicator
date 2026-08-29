"""Decomposicao exata de Shapley para funcoes nao-lineares com multiplos
drivers - motor generico, sem nenhuma premissa de indice especifico
(serve IPIA, e futuramente ICCS/ICS, conforme docs/architecture.md
"a mesma infraestrutura deve servir IPIA, ICCS e ICS").

Nenhuma funcao aqui faz rede ou I/O de arquivo; tudo opera sobre valores
escalares/dicts explicitamente recebidos.

## Por que Shapley

Para uma funcao f(driver_1, ..., driver_n) nao-linear (produtos/razoes
entre drivers), decompor Delta_f = f(t) - f(t-1) numa soma de
contribuicoes por driver exige uma regra de atribuicao das interacoes
cruzadas (ex.: FX multiplica FOB/frete/seguro - a variacao conjunta de
FX e FOB nao pertence inteiramente a nenhum dos dois isoladamente).
Alternativas mais simples tem problemas conhecidos:

- **Sequential replacement** (trocar um driver de cada vez, na ordem
  A,B,C,...): o resultado depende da ordem escolhida - cada ordem atribui
  a interacao cruzada inteira ao driver que "chega primeiro".
- **Log-decomposition** (Delta log f = soma de Delta log de cada fator):
  exata e aditiva SE f for um produto puro de drivers positivos, mas
  IPIA_t = P_dom / PPI_COST(...) tem soma dentro do denominador (CIF+II+
  AFRMM+AD+D_porto+D_interno) - nao e um produto puro, entao log-decomp
  do PPI internamente ja teria o mesmo problema de atribuicao de
  interacao que motivou esta escolha.
- **Shapley value** (media das contribuicoes marginais de um driver
  sobre TODAS as ordens possiveis de introducao): e a UNICA regra que
  satisfaz simultaneamente efficiency (soma das contribuicoes = Delta_f
  exato, sem residuo por construcao), symmetry (dois drivers com o mesmo
  efeito marginal em toda ordem recebem a mesma contribuicao) e linearity
  - resultado matematico classico (Shapley 1953), ja usado em decomposicao
  de indices/desigualdade em economia (Shorrocks 2013, "Decomposition
  procedures for distributional analysis: a unified framework based on
  the Shapley value").

## Custo computacional

Calcular Shapley por FORCA BRUTA (media sobre todas as n! ordens de
introducao) e caro: para n=10 drivers, 10! = 3.628.800 ordens. Mas o
valor de Shapley tem uma formula fechada equivalente, que soma sobre os
2^n SUBCONJUNTOS de drivers (nao sobre as ordens) - matematicamente
identica (mesmo resultado exato), so reorganizada:

    phi_i = sum_{S subseteq N\\{i}} w(|S|) * [f(S uniao {i}) - f(S)]
    w(s) = s! * (n-s-1)! / n!

onde f(S) significa: avaliar f com os drivers em S no valor de
TRATAMENTO (periodo t) e os demais no valor de BASELINE (periodo t-1).
Para n=10, isso e 2^10=1024 avaliacoes de f (nao 3.628.800) - a mesma
resposta exata, ~3.500x mais barato. Para n=11 (com margem, modo Offer),
2^11=2048 avaliacoes. Ambos triviais computacionalmente (f e uma formula
fechada de poucas operacoes aritmeticas) - nenhuma aproximacao Monte
Carlo e necessaria nesta escala; o guard-rail em `MAX_DRIVERS_EXATO`
existe para nunca aplicar esta formula (2^n) a uma escala onde deixaria
de ser trivial.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

MAX_DRIVERS_EXATO = 20  # 2^20 ~ 1e6 avaliacoes - ainda administravel; acima
# disso, a formula de subconjuntos deixa de ser trivial e uma decisao
# metodologica separada (agrupamento hierarquico ou Monte Carlo com seed
# fixa) seria necessaria - fora do escopo de qualquer indice atual deste
# projeto (IPIA-HRC usa 10 drivers no core, 11 no modo Offer).


@dataclass
class ResultadoShapley:
    """Resultado de uma decomposicao Shapley exata: contribuicao por
    driver (em unidade de `f`, nao percentual), residuo (deve ser ~0 por
    construcao - efficiency property) e o delta total observado."""
    contribuicoes: Dict[str, float]
    residual: float
    delta_total: float
    valor_baseline: float
    valor_treatment: float
    drivers: List[str] = field(default_factory=list)

    def abs_contribution_share(self) -> Dict[str, float]:
        """|contribuicao_i| / soma(|contribuicoes|) - identifica drivers
        dominantes sem se confundir com cancelamentos (dois drivers de
        sinais opostos e mesma magnitude somam ~0 no delta liquido, mas
        cada um continua tendo peso real na decomposicao)."""
        soma_abs = sum(abs(v) for v in self.contribuicoes.values())
        if soma_abs == 0:
            return {k: 0.0 for k in self.contribuicoes}
        return {k: abs(v) / soma_abs for k, v in self.contribuicoes.items()}

    def top_positive_driver(self) -> Optional[str]:
        positivos = {k: v for k, v in self.contribuicoes.items() if v > 0}
        return max(positivos, key=positivos.get) if positivos else None

    def top_negative_driver(self) -> Optional[str]:
        negativos = {k: v for k, v in self.contribuicoes.items() if v < 0}
        return min(negativos, key=negativos.get) if negativos else None

    def dominant_driver(self) -> Optional[str]:
        """Driver de maior |contribuicao| absoluta - o que mais move o
        resultado, independente de sinal."""
        if not self.contribuicoes:
            return None
        return max(self.contribuicoes, key=lambda k: abs(self.contribuicoes[k]))


def _peso_shapley(s: int, n: int) -> float:
    """w(s) = s!(n-s-1)!/n! - peso de um subconjunto de tamanho s na
    media ponderada das contribuicoes marginais (formula fechada
    equivalente a media sobre todas as n! ordens)."""
    return math.factorial(s) * math.factorial(n - s - 1) / math.factorial(n)


def shapley_contributions(f: Callable[..., float], baseline: Dict[str, float],
                          treatment: Dict[str, float],
                          drivers: Optional[Sequence[str]] = None) -> ResultadoShapley:
    """Decompoe `f(treatment) - f(baseline)` em contribuicoes exatas por
    driver, via a formula fechada de subconjuntos (2^n avaliacoes de
    `f`, n = numero de drivers) - resultado matematicamente identico a
    tomar a media das contribuicoes marginais sobre todas as n! ordens
    possiveis de introducao dos drivers (ver docstring do modulo).

    `f` deve aceitar todos os `drivers` como keyword arguments e devolver
    um escalar (`float`). `baseline`/`treatment` sao dicts nome_driver ->
    valor, um por periodo (ex.: t-1 e t). `drivers` (opcional) fixa a
    ordem/subconjunto de chaves a decompor - por padrao, todas as chaves
    de `baseline` (que deve ter as mesmas chaves de `treatment`).

    Propriedade garantida por construcao (Shapley efficiency):
    `sum(contribuicoes) == f(treatment) - f(baseline)` exatamente (a
    menos de ruido de ponto flutuante, reportado em `.residual`) - nunca
    depende da ordem de `drivers`.

    Nunca usa aproximacao Monte Carlo - `MAX_DRIVERS_EXATO` e um guard-rail
    contra uso indevido em escala onde 2^n deixaria de ser trivial.
    """
    drivers = list(drivers) if drivers is not None else list(baseline.keys())
    faltando_baseline = set(drivers) - set(baseline.keys())
    faltando_treatment = set(drivers) - set(treatment.keys())
    if faltando_baseline or faltando_treatment:
        raise ValueError(f"drivers sem valor em baseline/treatment: "
                         f"{faltando_baseline | faltando_treatment}")
    n = len(drivers)
    if n == 0:
        raise ValueError("nenhum driver informado")
    if n > MAX_DRIVERS_EXATO:
        raise ValueError(f"{n} drivers excede MAX_DRIVERS_EXATO={MAX_DRIVERS_EXATO} - "
                         f"2^{n} avaliacoes deixaria de ser trivial; decisao "
                         f"metodologica separada (agrupamento hierarquico ou "
                         f"Monte Carlo com seed fixa) seria necessaria antes de "
                         f"prosseguir, fora do escopo desta funcao.")

    # cache de f(subconjunto) por bitmask - cada bit ligado = driver naquele
    # indice usa o valor de TRATAMENTO; bit desligado = valor de BASELINE.
    valores: Dict[int, float] = {}
    for mask in range(1 << n):
        kwargs = {}
        for idx, nome in enumerate(drivers):
            usar_treatment = bool(mask & (1 << idx))
            kwargs[nome] = treatment[nome] if usar_treatment else baseline[nome]
        valores[mask] = float(f(**kwargs))

    full_mask = (1 << n) - 1
    valor_baseline = valores[0]
    valor_treatment = valores[full_mask]

    contribuicoes = {nome: 0.0 for nome in drivers}
    for idx, nome in enumerate(drivers):
        bit = 1 << idx
        for mask in range(1 << n):
            if mask & bit:
                continue  # so subconjuntos QUE NAO CONTEM o driver i
            s = bin(mask).count("1")
            peso = _peso_shapley(s, n)
            contribuicoes[nome] += peso * (valores[mask | bit] - valores[mask])

    delta_total = valor_treatment - valor_baseline
    residual = delta_total - sum(contribuicoes.values())

    return ResultadoShapley(contribuicoes=contribuicoes, residual=residual,
                            delta_total=delta_total, valor_baseline=valor_baseline,
                            valor_treatment=valor_treatment, drivers=drivers)


def shapley_contributions_forca_bruta(f: Callable[..., float], baseline: Dict[str, float],
                                       treatment: Dict[str, float],
                                       drivers: Optional[Sequence[str]] = None) -> ResultadoShapley:
    """Mesma decomposicao de `shapley_contributions`, mas por MEDIA SOBRE
    TODAS AS N! ORDENS de introducao dos drivers (definicao original de
    Shapley, nao a formula fechada de subconjuntos) - custa n! avaliacoes
    de `f` por driver introduzido em cada ordem, entao O(n * n!) no total.

    Existe SOMENTE para validacao cruzada em teste (provar que a formula
    de subconjuntos, muito mais barata, produz o mesmo resultado exato) -
    nunca deve ser chamada em producao com n>~7 (7!=5040 ja e o limite
    pratico razoavel para um teste; `shapley_contributions` e a unica
    funcao que o motor de decomposicao do IPIA-HRC usa)."""
    from itertools import permutations
    drivers = list(drivers) if drivers is not None else list(baseline.keys())
    n = len(drivers)
    if n > 8:
        raise ValueError(f"{n}! e caro demais mesmo para um teste de validacao cruzada "
                         f"(guard-rail conservador, n<=8)")

    contribuicoes = {nome: 0.0 for nome in drivers}
    n_ordens = 0
    for ordem in permutations(drivers):
        n_ordens += 1
        atual = dict(baseline)
        valor_atual = float(f(**atual))
        for nome in ordem:
            atual[nome] = treatment[nome]
            novo_valor = float(f(**atual))
            contribuicoes[nome] += novo_valor - valor_atual
            valor_atual = novo_valor
    contribuicoes = {k: v / n_ordens for k, v in contribuicoes.items()}

    valor_baseline = float(f(**baseline))
    valor_treatment = float(f(**treatment))
    delta_total = valor_treatment - valor_baseline
    residual = delta_total - sum(contribuicoes.values())
    return ResultadoShapley(contribuicoes=contribuicoes, residual=residual,
                            delta_total=delta_total, valor_baseline=valor_baseline,
                            valor_treatment=valor_treatment, drivers=drivers)
