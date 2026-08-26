"""Contrato de collection vintage: o que sabemos sobre UMA coleta de UMA
fonte, em memoria, logo apos a coleta - antes de qualquer persistencia
existir. Nenhuma funcao aqui grava em disco, calcula hash ou gera ID; nao
ha rede nem I/O.

Extraido como infraestrutura preparatoria (Spec 0003, Stage C3 / batch 4).
Representa somente o conceito C descrito na proposta ("qual versao da fonte
foi observada naquela coleta") - deliberadamente distinto de:

  - reference_period / provenance de um NUMERO PUBLICADO
    (OBSERVADO/CALCULADO/ESTIMADO, PROXY) - isso e `VintageInfo` em
    steel_indicator/domain/provenance.py (Batch 2) e permanece la;
  - publication vintage (qual conjunto de collection vintages + versao de
    codigo/metodologia produziu um indice publicado) - conceito D,
    explicitamente FORA de escopo deste batch, ainda sem nenhuma
    representacao em codigo.

CollectionVintage NAO contem methodology_version, code_version, publication
timestamp/ID nem nivel/proxy - esses pertencem a outras camadas (ver acima).

Tambem fora de escopo deste batch (nao formalizado ainda): vintage_id,
sha256, timezone, "collected_at posterior a reference_end", frequencia,
taxonomia canonica de source_id/dataset_id.
"""
from __future__ import annotations
from dataclasses import dataclass

import pandas as pd

from steel_indicator.data.contracts import VALIDACOES_STATUS


@dataclass
class CollectionVintage:
    """Descreve UMA coleta de UMA fonte/dataset - nao persistida, nao
    tem ID proprio ainda (ver modulo acima)."""
    source_id: str
    dataset_id: str
    collected_at: pd.Timestamp
    reference_start: pd.Timestamp
    reference_end: pd.Timestamp
    n_obs: int
    validation_status: str


def _timestamp_valido(valor: object) -> bool:
    return isinstance(valor, pd.Timestamp) and not pd.isna(valor)


def validar_collection_vintage(vintage: CollectionVintage) -> None:
    """Levanta ValueError se `vintage` violar qualquer uma das condicoes
    estruturais minimas: validation_status reconhecido, timestamps validos
    (pd.Timestamp, nao NaT), reference_start <= reference_end, n_obs >= 0,
    source_id/dataset_id nao vazios. n_obs == 0 e valido (uma coleta pode
    legitimamente nao ter retornado registros - isso e um fato a reportar,
    nao um erro a esconder)."""
    if vintage.validation_status not in VALIDACOES_STATUS:
        raise ValueError(
            f"validation_status invalido: {vintage.validation_status!r} "
            f"(esperado um de {VALIDACOES_STATUS})")
    if not vintage.source_id:
        raise ValueError("source_id nao pode ser vazio")
    if not vintage.dataset_id:
        raise ValueError("dataset_id nao pode ser vazio")
    if not _timestamp_valido(vintage.collected_at):
        raise ValueError(f"collected_at invalido: {vintage.collected_at!r} (esperado pd.Timestamp, nao NaT)")
    if not _timestamp_valido(vintage.reference_start):
        raise ValueError(f"reference_start invalido: {vintage.reference_start!r} (esperado pd.Timestamp, nao NaT)")
    if not _timestamp_valido(vintage.reference_end):
        raise ValueError(f"reference_end invalido: {vintage.reference_end!r} (esperado pd.Timestamp, nao NaT)")
    if vintage.reference_start > vintage.reference_end:
        raise ValueError(
            f"reference_start ({vintage.reference_start}) posterior a "
            f"reference_end ({vintage.reference_end})")
    if vintage.n_obs < 0:
        raise ValueError(f"n_obs nao pode ser negativo: {vintage.n_obs}")
