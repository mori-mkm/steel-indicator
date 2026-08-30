"""Unit tests for the diagnostico de composicao atipica na importacao (ADR
0018) - wiring em `reporting.report_builder` e render na pagina 2 do
Reporting V3 (`reporting.pages_v3.pagina_import_parity_drivers`).

Cobre: `carregar_diagnostico_importacao_se_disponivel` degrada
graciosamente (arquivo ausente -> None); `preparar_dados_relatorio_ipia_hrc_v3`
so preenche `diagnostico_importacao_atual` quando o artefato injetado tem
uma linha casando (reference_period, vintage_id) - nunca fabrica; PDF
completo gera sem erro com e sem o diagnostico (regressao: layout
identico quando ausente, ja validado por render manual nesta tarefa;
aqui so a garantia de nao-excecao/paginas corretas).
"""
import pandas as pd
import pytest

import indices_setoriais as m
from reporting.report_builder import (
    carregar_diagnostico_importacao_se_disponivel, gerar_relatorio_ipia_hrc_v3,
    preparar_dados_relatorio_ipia_hrc_v3,
)

from test_reporting_v3 import _vintage_real, _decomposicao_para_vintage

VINTAGE_ID = "20260101T000000Z"


def _diagnostico_df(vintage, vintage_id, status="atipico"):
    combinada = pd.concat([vintage["official"], vintage["provisional"]], ignore_index=True) \
        .sort_values("reference_period").reset_index(drop=True)
    periodo_atual = combinada[combinada["ipia_hrc_v2"].notna()].iloc[-1]["reference_period"]
    return pd.DataFrame([{
        "reference_period": periodo_atual, "vintage_id": vintage_id, "methodology_version": "1.5",
        "status": status, "razao_volume": 0.23, "volume_atual_t": 16281.0, "mediana_trailing_t": 44843.0,
        "n_meses_trailing": 11, "limiar": m.LIMIAR_RAZAO_VOLUME_ATIPICO,
        "top_pais": "China", "top_pais_pct": 46.1, "top_pais_mes_anterior": "Egito",
        "top_pais_pct_mes_anterior": 48.3, "motivos": "volume abaixo do limiar",
    }])


# --- carregar_diagnostico_importacao_se_disponivel --------------------------

def test_carregar_diagnostico_arquivo_ausente_devolve_none(tmp_path):
    caminho = str(tmp_path / "nao_existe.csv")
    assert carregar_diagnostico_importacao_se_disponivel(caminho) is None


def test_carregar_diagnostico_le_csv_existente(tmp_path):
    caminho = str(tmp_path / "diagnostico.csv")
    pd.DataFrame([{"reference_period": "2026-06-01", "vintage_id": VINTAGE_ID, "status": "atipico"}]) \
        .to_csv(caminho, index=False)
    df = carregar_diagnostico_importacao_se_disponivel(caminho)
    assert df is not None
    assert df.iloc[0]["status"] == "atipico"
    assert pd.api.types.is_datetime64_any_dtype(df["reference_period"])


# --- preparar_dados_relatorio_ipia_hrc_v3 wiring ----------------------------

def test_diagnostico_ausente_por_padrao(tmp_path):
    vintage = _vintage_real(tmp_path, vintage_id=VINTAGE_ID)
    decomposicao_df = _decomposicao_para_vintage(vintage, VINTAGE_ID)
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=decomposicao_df)
    assert dados["diagnostico_importacao_atual"] is None


def test_diagnostico_atipico_injetado_aparece_em_dados(tmp_path):
    vintage = _vintage_real(tmp_path, vintage_id=VINTAGE_ID)
    decomposicao_df = _decomposicao_para_vintage(vintage, VINTAGE_ID)
    diagnostico_df = _diagnostico_df(vintage, VINTAGE_ID, status="atipico")
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=decomposicao_df,
                                                 diagnostico_importacao_df=diagnostico_df)
    assert dados["diagnostico_importacao_atual"] is not None
    assert dados["diagnostico_importacao_atual"]["status"] == "atipico"


def test_diagnostico_status_normal_injetado_nao_e_atipico(tmp_path):
    vintage = _vintage_real(tmp_path, vintage_id=VINTAGE_ID)
    decomposicao_df = _decomposicao_para_vintage(vintage, VINTAGE_ID)
    diagnostico_df = _diagnostico_df(vintage, VINTAGE_ID, status="normal")
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=decomposicao_df,
                                                 diagnostico_importacao_df=diagnostico_df)
    assert dados["diagnostico_importacao_atual"]["status"] == "normal"


def test_diagnostico_de_outro_vintage_id_nao_casa(tmp_path):
    vintage = _vintage_real(tmp_path, vintage_id=VINTAGE_ID)
    decomposicao_df = _decomposicao_para_vintage(vintage, VINTAGE_ID)
    diagnostico_df = _diagnostico_df(vintage, "outro-vintage-qualquer", status="atipico")
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=decomposicao_df,
                                                 diagnostico_importacao_df=diagnostico_df)
    assert dados["diagnostico_importacao_atual"] is None


# --- PDF completo (regressao + smoke com diagnostico) -----------------------

def test_pdf_gera_sem_erro_com_diagnostico_atipico(tmp_path):
    vintage = _vintage_real(tmp_path, vintage_id=VINTAGE_ID)
    decomposicao_df = _decomposicao_para_vintage(vintage, VINTAGE_ID)
    diagnostico_df = _diagnostico_df(vintage, VINTAGE_ID, status="atipico")
    caminho_pdf = str(tmp_path / "relatorio.pdf")
    resultado = gerar_relatorio_ipia_hrc_v3(caminho_pdf, vintage, decomposicao_df=decomposicao_df,
                                            diagnostico_importacao_df=diagnostico_df)
    assert resultado["n_paginas"] == 4


def test_pdf_gera_sem_erro_sem_diagnostico_regressao(tmp_path):
    vintage = _vintage_real(tmp_path, vintage_id=VINTAGE_ID)
    decomposicao_df = _decomposicao_para_vintage(vintage, VINTAGE_ID)
    caminho_pdf = str(tmp_path / "relatorio.pdf")
    resultado = gerar_relatorio_ipia_hrc_v3(caminho_pdf, vintage, decomposicao_df=decomposicao_df)
    assert resultado["n_paginas"] == 4
