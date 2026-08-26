"""Unit tests for the generic data contract validators in
steel_indicator/data/contracts.py. Deterministic, no network, no dependency
on indices_setoriais or any index-specific logic.
"""
import pandas as pd
import pytest

from steel_indicator.data.contracts import validar_colunas_obrigatorias, validar_indice_temporal


# --- validar_colunas_obrigatorias -------------------------------------------

def test_validar_colunas_obrigatorias_passa_quando_todas_existem():
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    validar_colunas_obrigatorias(df, ["a", "b"])  # nao deve levantar


def test_validar_colunas_obrigatorias_falha_quando_falta_uma_coluna():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="b"):
        validar_colunas_obrigatorias(df, ["a", "b"])


def test_validar_colunas_obrigatorias_mostra_multiplas_colunas_ausentes():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError) as exc_info:
        validar_colunas_obrigatorias(df, ["a", "b", "c"])
    assert "b" in str(exc_info.value)
    assert "c" in str(exc_info.value)


def test_validar_colunas_obrigatorias_inclui_contexto_na_mensagem():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="carregar_preco_domestico"):
        validar_colunas_obrigatorias(df, ["b"], contexto="carregar_preco_domestico")


def test_validar_colunas_obrigatorias_nao_modifica_o_dataframe():
    df = pd.DataFrame({"a": [1], "b": [2]})
    df_antes = df.copy()
    try:
        validar_colunas_obrigatorias(df, ["a", "z"])
    except ValueError:
        pass
    pd.testing.assert_frame_equal(df, df_antes)


# --- validar_indice_temporal -------------------------------------------------

def _idx_valido():
    return pd.date_range("2026-01-01", periods=3, freq="MS")


def test_validar_indice_temporal_passa_para_datetimeindex_ordenado_e_unico():
    df = pd.DataFrame({"v": [1, 2, 3]}, index=_idx_valido())
    validar_indice_temporal(df)  # nao deve levantar


def test_validar_indice_temporal_funciona_com_series():
    s = pd.Series([1, 2, 3], index=_idx_valido())
    validar_indice_temporal(s)  # nao deve levantar


def test_validar_indice_temporal_funciona_com_dataframe():
    df = pd.DataFrame({"v": [1, 2, 3]}, index=_idx_valido())
    validar_indice_temporal(df)  # nao deve levantar


def test_validar_indice_temporal_falha_para_indice_nao_datetime():
    df = pd.DataFrame({"v": [1, 2, 3]}, index=[0, 1, 2])
    with pytest.raises(ValueError, match="DatetimeIndex"):
        validar_indice_temporal(df)


def test_validar_indice_temporal_falha_para_indice_fora_de_ordem():
    idx = pd.DatetimeIndex(["2026-03-01", "2026-01-01", "2026-02-01"])
    df = pd.DataFrame({"v": [1, 2, 3]}, index=idx)
    with pytest.raises(ValueError, match="ordenado"):
        validar_indice_temporal(df)


def test_validar_indice_temporal_falha_para_timestamps_duplicados():
    idx = pd.DatetimeIndex(["2026-01-01", "2026-02-01", "2026-02-01"])
    df = pd.DataFrame({"v": [1, 2, 3]}, index=idx)
    with pytest.raises(ValueError, match="duplicados"):
        validar_indice_temporal(df)
