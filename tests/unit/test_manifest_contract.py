"""Unit tests for CollectionVintage / validar_collection_vintage in
steel_indicator/storage/manifest.py. Deterministic, no network, no
dependency on indices_setoriais, collectors or any index-specific logic.
"""
import pandas as pd
import pytest

from steel_indicator.data.contracts import VALIDACAO_VERIFICADO, VALIDACAO_DOCUMENTADO, VALIDACAO_A_CONFIRMAR
from steel_indicator.storage.manifest import CollectionVintage, validar_collection_vintage


def _vintage_valido(**overrides) -> CollectionVintage:
    campos = dict(
        source_id="comex_stat",
        dataset_id="ncm_bobina_quente",
        collected_at=pd.Timestamp("2026-08-01"),
        reference_start=pd.Timestamp("2020-01-01"),
        reference_end=pd.Timestamp("2026-07-01"),
        n_obs=100,
        validation_status=VALIDACAO_VERIFICADO,
    )
    campos.update(overrides)
    return CollectionVintage(**campos)


# --- casos validos -----------------------------------------------------------

def test_collection_vintage_valido_com_verificado():
    validar_collection_vintage(_vintage_valido(validation_status=VALIDACAO_VERIFICADO))


def test_collection_vintage_valido_com_documentado():
    validar_collection_vintage(_vintage_valido(validation_status=VALIDACAO_DOCUMENTADO))


def test_collection_vintage_valido_com_a_confirmar():
    validar_collection_vintage(_vintage_valido(validation_status=VALIDACAO_A_CONFIRMAR))


def test_n_obs_zero_e_valido():
    validar_collection_vintage(_vintage_valido(n_obs=0))


# --- validation_status --------------------------------------------------------

def test_validation_status_invalido_levanta_value_error():
    with pytest.raises(ValueError, match="validation_status"):
        validar_collection_vintage(_vintage_valido(validation_status="INVALIDO"))


# --- reference_start / reference_end -----------------------------------------

def test_reference_start_posterior_a_reference_end_levanta_value_error():
    with pytest.raises(ValueError, match="reference_start"):
        validar_collection_vintage(_vintage_valido(
            reference_start=pd.Timestamp("2026-08-01"), reference_end=pd.Timestamp("2026-01-01")))


def test_reference_start_invalido_ou_nat_levanta_value_error():
    with pytest.raises(ValueError, match="reference_start"):
        validar_collection_vintage(_vintage_valido(reference_start=pd.NaT))


def test_reference_start_nao_timestamp_levanta_value_error():
    with pytest.raises(ValueError, match="reference_start"):
        validar_collection_vintage(_vintage_valido(reference_start="2026-01-01"))


def test_reference_end_invalido_ou_nat_levanta_value_error():
    with pytest.raises(ValueError, match="reference_end"):
        validar_collection_vintage(_vintage_valido(reference_end=pd.NaT))


def test_reference_end_nao_timestamp_levanta_value_error():
    with pytest.raises(ValueError, match="reference_end"):
        validar_collection_vintage(_vintage_valido(reference_end="2026-07-01"))


# --- n_obs ---------------------------------------------------------------------

def test_n_obs_negativo_levanta_value_error():
    with pytest.raises(ValueError, match="n_obs"):
        validar_collection_vintage(_vintage_valido(n_obs=-1))


# --- source_id / dataset_id -----------------------------------------------------

def test_source_id_vazio_levanta_value_error():
    with pytest.raises(ValueError, match="source_id"):
        validar_collection_vintage(_vintage_valido(source_id=""))


def test_dataset_id_vazio_levanta_value_error():
    with pytest.raises(ValueError, match="dataset_id"):
        validar_collection_vintage(_vintage_valido(dataset_id=""))


# --- collected_at ----------------------------------------------------------------

def test_collected_at_invalido_levanta_value_error():
    with pytest.raises(ValueError, match="collected_at"):
        validar_collection_vintage(_vintage_valido(collected_at="2026-08-01"))


def test_collected_at_nat_levanta_value_error():
    with pytest.raises(ValueError, match="collected_at"):
        validar_collection_vintage(_vintage_valido(collected_at=pd.NaT))
