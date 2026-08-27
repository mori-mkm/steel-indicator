"""Contrato generico de proveniencia: taxonomia OBSERVADO/CALCULADO/ESTIMADO,
PROXY (eixo ortogonal), VintageInfo e validacao de cutoff/look-ahead.

Extraido de src/indices_setoriais.py (Spec 0003, batch 2) sem alteracao de
comportamento. Nao contem nenhuma logica especifica de IPIA/HRC - as funcoes
classificar_* que decidem OBSERVADO/CALCULADO/ESTIMADO/PROXY a partir de
colunas especificas do IPIA V1 (tipo_dado_domestico, metodo_domestico,
tipo_dado_penetracao) permanecem em src/indices_setoriais.py, pois encodam
premissas metodologicas ainda nao congeladas (ver docs/METODOLOGIA.md secao
12 e docs/specs/0003-modularize-engine.md secao 3). Este modulo so representa
o contrato: o que um numero E, nao como classifica-lo.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

NIVEL_OBSERVADO = "OBSERVADO"  # valor direto da fonte, sem calculo nosso
NIVEL_CALCULADO = "CALCULADO"  # formula aplicada sobre observados, sem estimativa
NIVEL_ESTIMADO  = "ESTIMADO"   # interpolado, encadeado ou suavizado
NIVEIS_DADO = (NIVEL_OBSERVADO, NIVEL_CALCULADO, NIVEL_ESTIMADO)

# metodo=METODO_FORMULA_ALTERNATIVA: mesma fonte/instituto do numero oficial,
# mesmo alvo conceitual, mas formula propria (nao a formula oficial) - nao e
# nivel ESTIMADO (nao ha interpolacao/encadeamento/suavizacao) nem PROXY (o
# escopo e o mesmo, so a formula difere).
METODO_FORMULA_ALTERNATIVA = "formula_alternativa"


@dataclass
class VintageInfo:
    """Proveniencia de UM numero especifico exibido no relatorio - dado
    estrutural, sem nenhuma formatacao de apresentacao (isso e
    responsabilidade de src/reporting/, nunca deste modulo)."""
    variavel: str
    reference_period: pd.Timestamp  # mes mais recente que este numero reflete
    fonte: str
    nivel: str                      # NIVEL_OBSERVADO | NIVEL_CALCULADO | NIVEL_ESTIMADO
    proxy: bool = False
    proxy_motivo: Optional[str] = None
    metodo: Optional[str] = None         # subtipo dentro do nivel (ex. "encadeado_ipp")
    metodo_motivo: Optional[str] = None  # texto so quando o metodo pede explicacao (ex. formula_alternativa)
    periodo_texto: Optional[str] = None  # rotulo para janelas (ex. origem por pais); None = mes unico


def vintage_table(infos: List[VintageInfo]) -> pd.DataFrame:
    """Serializa uma lista de VintageInfo na tabela de vintage padrao - uma
    linha por variavel, mesmas colunas/ordem para qualquer indice que
    monte sua propria lista de VintageInfo (IPIA, ICCS, ICS)."""
    return pd.DataFrame([{
        "variavel": v.variavel, "reference_period": v.reference_period, "fonte": v.fonte,
        "nivel": v.nivel, "proxy": v.proxy, "proxy_motivo": v.proxy_motivo,
        "metodo": v.metodo, "metodo_motivo": v.metodo_motivo, "periodo_texto": v.periodo_texto,
    } for v in infos])


def validar_report_cutoff(tabela_vintage: pd.DataFrame, report_cutoff: pd.Timestamp) -> List[str]:
    """Lista as variaveis cuja `reference_period` e POSTERIOR ao mes do
    `report_cutoff` - nunca deveria acontecer (seria usar dado que ainda
    nao existia na data de geracao da edicao, look-ahead). Lista vazia =
    tudo dentro do cutoff."""
    cutoff_mes = pd.Timestamp(report_cutoff.year, report_cutoff.month, 1)
    problema = tabela_vintage[tabela_vintage["reference_period"] > cutoff_mes]
    return problema["variavel"].tolist()
