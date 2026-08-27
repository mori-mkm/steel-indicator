"""Validacao generica de contrato de dados: colunas obrigatorias, indice
temporal minimo e taxonomia de status de validacao de fonte. Nenhuma funcao
aqui envolve rede, arquivo ou dataclass de transporte - series/tabelas
continuam sendo pandas DataFrame/Series.

Extraido como infraestrutura preparatoria (Spec 0003, Stage C2 / batch 3),
generalizando um idioma ja existente no projeto (`EspecIndice.validar()` em
steel_indicator/domain/index_engine.py e o check inline em
`carregar_preco_domestico_trimestral()` de src/indices_setoriais.py): checar
uma condicao estrutural e levantar ValueError com mensagem explicita, nunca
falhar em silencio.

Deliberadamente NAO validado aqui (nao formalizado ainda, ver docs/specs/
0003-modularize-engine.md Stage C2/C3):
  - frequencia mensal;
  - nome obrigatorio do indice (ex. "data");
  - timezone;
  - periodicidade especifica;
  - ausencia de lacunas no intervalo;
  - o conceito de `reference_period` como campo novo.

Este modulo ainda nao e chamado por nenhum produtor/consumidor existente -
e infraestrutura testada, pronta para ser adotada incrementalmente.

VALIDACAO_* / VALIDACOES_STATUS: taxonomia de status de validade/qualidade de
FONTE (ver docs/METODOLOGIA.md secao 5.2 e docs/data-sources.md) - distinta
da taxonomia OBSERVADO/CALCULADO/ESTIMADO/PROXY de numero publicado
(domain/provenance.py, Batch 2). Fica aqui, nao em storage/manifest.py,
porque e um contrato compartilhado: sera usado por CollectionVintage (Stage
C3) e, futuramente, por source adapters e validacao (Stage E) - nao e
propriedade exclusiva de nenhum consumidor especifico.
"""
from __future__ import annotations
from typing import Iterable

import pandas as pd

VALIDACAO_VERIFICADO = "VERIFICADO"
VALIDACAO_DOCUMENTADO = "DOCUMENTADO"
VALIDACAO_A_CONFIRMAR = "A_CONFIRMAR"

VALIDACOES_STATUS = (
    VALIDACAO_VERIFICADO,
    VALIDACAO_DOCUMENTADO,
    VALIDACAO_A_CONFIRMAR,
)


def validar_colunas_obrigatorias(df: pd.DataFrame, obrigatorias: Iterable[str],
                                 contexto: str = "") -> None:
    """Levanta ValueError se `df` nao tiver todas as colunas de `obrigatorias`.

    Nao altera `df` (so le `df.columns`). `contexto`, quando informado,
    aparece na mensagem de erro para facilitar o diagnostico de qual
    chamada falhou.
    """
    faltando = sorted(set(obrigatorias) - set(df.columns))
    if faltando:
        prefixo = f"{contexto}: " if contexto else ""
        raise ValueError(f"{prefixo}colunas obrigatorias ausentes: {faltando}")


def validar_indice_temporal(obj: pd.DataFrame | pd.Series) -> None:
    """Levanta ValueError se o indice de `obj` nao for um DatetimeIndex
    ordenado de forma crescente e sem timestamps duplicados - a suposicao
    que operacoes como reindex/intersection/loc ja dependem implicitamente
    em todo o pipeline de series mensais.
    """
    idx = obj.index
    if not isinstance(idx, pd.DatetimeIndex):
        raise ValueError(f"indice precisa ser DatetimeIndex, recebido {type(idx).__name__}")
    if not idx.is_monotonic_increasing:
        raise ValueError("indice temporal precisa estar ordenado de forma crescente")
    if idx.has_duplicates:
        duplicados = sorted(set(idx[idx.duplicated()]))
        raise ValueError(f"indice temporal tem timestamps duplicados: {duplicados}")
