"""Unit tests for the generic provenance contract in
steel_indicator/domain/provenance.py. Deterministic, no network, no
dependency on indices_setoriais or any index-specific classification logic.
"""
import pandas as pd

from steel_indicator.domain.provenance import (
    NIVEL_OBSERVADO, NIVEL_CALCULADO, NIVEL_ESTIMADO, NIVEIS_DADO,
    METODO_FORMULA_ALTERNATIVA, VintageInfo, vintage_table, validar_report_cutoff,
)


def test_niveis_dado_sao_tres_e_mutuamente_exclusivos():
    assert NIVEIS_DADO == (NIVEL_OBSERVADO, NIVEL_CALCULADO, NIVEL_ESTIMADO)
    assert len(set(NIVEIS_DADO)) == 3


def test_metodo_formula_alternativa_e_string_estavel():
    assert METODO_FORMULA_ALTERNATIVA == "formula_alternativa"


def test_vintage_info_defaults():
    info = VintageInfo(
        variavel="x", reference_period=pd.Timestamp("2026-01-01"),
        fonte="fonte-teste", nivel=NIVEL_OBSERVADO,
    )
    assert info.proxy is False
    assert info.proxy_motivo is None
    assert info.metodo is None
    assert info.metodo_motivo is None
    assert info.periodo_texto is None


def test_vintage_table_colunas_e_ordem():
    infos = [
        VintageInfo(variavel="a", reference_period=pd.Timestamp("2026-01-01"),
                    fonte="fonte-a", nivel=NIVEL_OBSERVADO),
        VintageInfo(variavel="b", reference_period=pd.Timestamp("2026-02-01"),
                    fonte="fonte-b", nivel=NIVEL_ESTIMADO, proxy=True,
                    proxy_motivo="motivo-b", metodo="encadeado_x",
                    metodo_motivo="motivo-metodo-b", periodo_texto="2026-01 a 2026-02"),
    ]
    tabela = vintage_table(infos)
    assert list(tabela.columns) == [
        "variavel", "reference_period", "fonte", "nivel", "proxy",
        "proxy_motivo", "metodo", "metodo_motivo", "periodo_texto",
    ]
    assert tabela["variavel"].tolist() == ["a", "b"]
    linha_b = tabela.set_index("variavel").loc["b"]
    assert linha_b["reference_period"] == pd.Timestamp("2026-02-01")
    assert linha_b["nivel"] == NIVEL_ESTIMADO
    assert bool(linha_b["proxy"]) is True
    assert linha_b["proxy_motivo"] == "motivo-b"
    assert linha_b["metodo"] == "encadeado_x"
    assert linha_b["periodo_texto"] == "2026-01 a 2026-02"


def test_vintage_table_vazia_para_lista_vazia():
    tabela = vintage_table([])
    assert len(tabela) == 0


def test_validar_report_cutoff_sem_problema_quando_dentro_do_prazo():
    tabela = vintage_table([
        VintageInfo(variavel="a", reference_period=pd.Timestamp("2026-06-01"),
                    fonte="f", nivel=NIVEL_OBSERVADO),
    ])
    assert validar_report_cutoff(tabela, pd.Timestamp("2026-06-15")) == []


def test_validar_report_cutoff_detecta_look_ahead():
    tabela = vintage_table([
        VintageInfo(variavel="a", reference_period=pd.Timestamp("2026-07-01"),
                    fonte="f", nivel=NIVEL_OBSERVADO),
    ])
    problemas = validar_report_cutoff(tabela, pd.Timestamp("2026-06-15"))
    assert problemas == ["a"]
