"""Unit tests for the IPIA-HRC Reporting V3 (`reporting.report_builder`
V3 functions + `reporting.pages_v3`). Deterministic, no network: vintages
built via `executar_pipeline_ipia_hrc` with injected data (mesmo padrao
de test_ipia_hrc_pdf_reporting.py).

Cobre: contrato de vintage (nunca busca rede, nunca cria vintage nova,
falha explicito sem vintage); decomposicao opcional (degrada
graciosamente quando ausente/nao corresponde a vintage); PROVISIONAL
aparece corretamente; UNKNOWN/vintage vazia nunca gera narrativa
numerica; VERSAO_METODOLOGIA nao muda; PDF gerado com 4 paginas.
"""
import os
import sys

import pandas as pd
import pytest

import indices_setoriais as m
from reporting.report_builder import (
    gerar_relatorio_ipia_hrc_v3, preparar_dados_relatorio_ipia_hrc_v3,
)

from test_ipia_hrc_cli_pipeline import _fixture_completo


def _vintage_real(tmp_path, vintage_id="20260101T000000Z"):
    ppi, dom = _fixture_completo()
    base_dir = str(tmp_path / "vintages")
    m.executar_pipeline_ipia_hrc(base_dir=base_dir, output_dir=str(tmp_path / "processed"),
                                 ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id=vintage_id)
    return m.carregar_vintage_ipia_hrc_v2(vintage_id, base_dir=base_dir)


def _decomposicao_para_vintage(vintage, vintage_id):
    """Constroi um decomposicao_df sintetico e MATCHING (mesmo vintage_id
    e reference_period do ultimo mes calculavel da vintage de teste) -
    nunca uma chamada real ao script de geracao (que exige rede)."""
    combinada = pd.concat([vintage["official"], vintage["provisional"]], ignore_index=True) \
        .sort_values("reference_period").reset_index(drop=True)
    calculavel = combinada[combinada["ipia_hrc_v2"].notna()]
    if len(calculavel) < 2:
        return None
    periodo_t = calculavel.iloc[-1]["reference_period"]
    periodo_t_1 = calculavel.iloc[-2]["reference_period"]
    linha = {d: 0.0 for d in m.DRIVERS_PPI_COST}
    linha.update({"domestic_price": 2.0, "fob": -3.0, "fx": -1.5})
    linha.update({
        "reference_period": periodo_t, "previous_reference_period": periodo_t_1,
        "vintage_id": vintage_id, "methodology_version": vintage["manifest"]["methodology_version"],
        "delta_ipia": sum(linha.values()), "residual": 0.0,
        "dominant_driver": "fob", "top_positive_driver": "domestic_price", "top_negative_driver": "fob",
        "decomposition_method": "shapley_exact_subset_2^n", "modo": "cost",
    })
    return pd.DataFrame([linha])


# --- 1. Contrato de vintage (Sec.49) -----------------------------------------

def test_v3_sem_vintage_falha_explicito():
    with pytest.raises(ValueError, match="ja carregada"):
        gerar_relatorio_ipia_hrc_v3("qualquer.pdf", None)
    with pytest.raises(ValueError, match="ja carregada"):
        gerar_relatorio_ipia_hrc_v3("qualquer.pdf", {})


def test_v3_nao_faz_nenhuma_chamada_de_rede(tmp_path, monkeypatch):
    import requests
    def _explode(*a, **kw):
        raise AssertionError("gerar_relatorio_ipia_hrc_v3 nao deveria fazer chamada de rede")
    monkeypatch.setattr(requests, "get", _explode)
    monkeypatch.setattr(requests, "post", _explode)
    vintage = _vintage_real(tmp_path)
    resultado = gerar_relatorio_ipia_hrc_v3(str(tmp_path / "r.pdf"), vintage,
                                            decomposicao_df=None, componentes_mensais_df=None)
    assert resultado["n_paginas"] == 4
    assert os.path.exists(str(tmp_path / "r.pdf"))


def test_v3_nao_cria_vintage_nova(tmp_path, monkeypatch):
    vintage = _vintage_real(tmp_path)
    chamadas = {"n": 0}
    original = m.vintage_store.criar_vintage

    def _contando(*a, **kw):
        chamadas["n"] += 1
        return original(*a, **kw)

    monkeypatch.setattr(m.vintage_store, "criar_vintage", _contando)
    gerar_relatorio_ipia_hrc_v3(str(tmp_path / "r.pdf"), vintage, decomposicao_df=None, componentes_mensais_df=None)
    assert chamadas["n"] == 0


# --- 2. Decomposicao opcional - degradacao graciosa (Sec.36/49) ------------

def test_sem_decomposicao_disponivel_degrada_sem_crashar(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=None, componentes_mensais_df=None)
    assert dados["decomposicao_disponivel"] is False
    assert dados["resumo_executivo"] is None
    # gerar_relatorio_ipia_hrc_v3 nao deve levantar mesmo sem decomposicao
    resultado = gerar_relatorio_ipia_hrc_v3(str(tmp_path / "r.pdf"), vintage,
                                            decomposicao_df=None, componentes_mensais_df=None)
    assert resultado["n_paginas"] == 4


def test_decomposicao_de_vintage_diferente_e_ignorada_nunca_misturada(tmp_path):
    vintage = _vintage_real(tmp_path, vintage_id="20260101T000000Z")
    decomp_errada = pd.DataFrame([{
        "reference_period": pd.Timestamp("2024-06-01"), "previous_reference_period": pd.Timestamp("2024-05-01"),
        "vintage_id": "OUTRA_VINTAGE_DIFERENTE", "methodology_version": "1.5",
        **{d: 0.0 for d in m.DRIVERS_PPI_COST}, "delta_ipia": 0.0, "residual": 0.0,
        "dominant_driver": "fob", "modo": "cost",
    }])
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=decomp_errada,
                                                 componentes_mensais_df=None)
    assert dados["decomposicao_disponivel"] is False  # vintage_id nao bate -> nunca usa por engano


def test_decomposicao_disponivel_quando_vintage_e_periodo_batem(tmp_path):
    vintage_id = "20260101T000000Z"
    vintage = _vintage_real(tmp_path, vintage_id=vintage_id)
    decomp = _decomposicao_para_vintage(vintage, vintage_id)
    if decomp is None:
        pytest.skip("fixture nao tem 2+ meses calculaveis para montar uma transicao")
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=decomp, componentes_mensais_df=None)
    assert dados["decomposicao_disponivel"] is True
    assert dados["resumo_executivo"] is not None
    assert dados["resumo_executivo"]["main_driver"]["driver"] in m.DRIVERS_PPI_COST


# --- 3. PROVISIONAL aparece corretamente ------------------------------------

def test_provisional_aparece_corretamente_nos_dados_v3(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=None, componentes_mensais_df=None)
    if dados["is_provisional_atual"]:
        assert "Provisório" in dados["rotulo_atual"]
        assert dados["status_atual"] == m.STATUS_PROVISIONAL


# --- 4. UNKNOWN/vintage vazia nunca gera narrativa numerica -----------------

def test_vintage_vazia_ipia_atual_none_nao_numerico():
    vintage_vazio = {
        "manifest": {"vintage_id": "X", "methodology_version": "1.5", "created_at_utc": "2026-01-01T00:00:00Z"},
        "official": pd.DataFrame(columns=["reference_period", "ipia_hrc_v2", "publication_status",
                                          "ppi_rs_t", "preco_domestico_rs_t"]),
        "provisional": pd.DataFrame(columns=["reference_period", "ipia_hrc_v2", "publication_status",
                                             "ppi_rs_t", "preco_domestico_rs_t"]),
        "import_side": pd.DataFrame(), "domestic_price": pd.DataFrame(),
    }
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage_vazio, decomposicao_df=None, componentes_mensais_df=None)
    assert dados["ipia_atual"] is None
    assert dados["resumo_executivo"] is None


def test_vintage_vazia_pdf_gerado_sem_crashar_paginas_avisam_sem_dado(tmp_path):
    vintage_vazio = {
        "manifest": {"vintage_id": "X", "methodology_version": "1.5", "created_at_utc": "2026-01-01T00:00:00Z"},
        "official": pd.DataFrame(columns=["reference_period", "ipia_hrc_v2", "publication_status",
                                          "ppi_rs_t", "preco_domestico_rs_t"]),
        "provisional": pd.DataFrame(columns=["reference_period", "ipia_hrc_v2", "publication_status",
                                             "ppi_rs_t", "preco_domestico_rs_t"]),
        "import_side": pd.DataFrame(), "domestic_price": pd.DataFrame(),
    }
    resultado = gerar_relatorio_ipia_hrc_v3(str(tmp_path / "vazio.pdf"), vintage_vazio,
                                            decomposicao_df=None, componentes_mensais_df=None)
    assert resultado["n_paginas"] == 4
    assert os.path.exists(str(tmp_path / "vazio.pdf"))


# --- 4b. Mes mais recente UNKNOWN mas anterior/ano-anterior calculavel -----
# (achado do code review desta stage: crash real reproduzido com um
# vintage sintetico onde o ultimo mes de `provisional` tem ipia_hrc_v2
# NaN mas o mes anterior tem valor - `preparar_dados_relatorio_ipia_hrc_v3`
# levantava TypeError em vez de degradar graciosamente).

def test_ultimo_mes_unknown_com_mes_anterior_calculavel_nao_crasha(tmp_path):
    vintage = _vintage_real(tmp_path)
    combinada_original = pd.concat([vintage["official"], vintage["provisional"]], ignore_index=True) \
        .sort_values("reference_period").reset_index(drop=True)
    if len(combinada_original) < 2:
        pytest.skip("fixture precisa de pelo menos 2 meses calculaveis")

    # simula o ultimo mes da vintage como UNKNOWN (ipia_hrc_v2 NaN) -
    # cenario realista de atraso de dado no mes mais recente, mesmo com
    # o mes anterior ja calculavel.
    provisional_mod = vintage["provisional"].copy()
    if not provisional_mod.empty:
        ultima_linha = provisional_mod.index[-1]
        provisional_mod.loc[ultima_linha, "ipia_hrc_v2"] = float("nan")
        provisional_mod.loc[ultima_linha, "ppi_rs_t"] = float("nan")
    vintage_mod = dict(vintage, provisional=provisional_mod)

    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage_mod, decomposicao_df=None, componentes_mensais_df=None)
    assert dados["ipia_atual"] is None
    assert dados["delta_mom_ipia"] is None
    assert dados["delta_yoy_ipia"] is None
    assert dados["decomposicao_disponivel"] is False

    resultado = gerar_relatorio_ipia_hrc_v3(str(tmp_path / "r_unknown.pdf"), vintage_mod,
                                            decomposicao_df=None, componentes_mensais_df=None)
    assert resultado["n_paginas"] == 4


# --- 4c. Linha atual presente mas PPI/preco domestico NaN -------------------

def test_linha_atual_presente_mas_ppi_nan_normaliza_para_none(tmp_path):
    vintage = _vintage_real(tmp_path)
    oficial_mod = vintage["official"].copy()
    if oficial_mod.empty:
        pytest.skip("fixture sem meses oficiais")
    provisional_vazio = vintage["provisional"].iloc[0:0]  # forca fallback para ultimo_oficial
    ultima_linha = oficial_mod.index[-1]
    oficial_mod.loc[ultima_linha, "ppi_rs_t"] = float("nan")
    oficial_mod.loc[ultima_linha, "preco_domestico_rs_t"] = float("nan")
    vintage_mod = dict(vintage, official=oficial_mod, provisional=provisional_vazio)

    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage_mod, decomposicao_df=None, componentes_mensais_df=None)
    assert dados["ppi_atual"] is None
    assert dados["preco_domestico_atual"] is None


# --- 5. Metodologia nao muda (Sec.50) ----------------------------------------

def test_versao_metodologia_permanece_1_5():
    assert m.VERSAO_METODOLOGIA == "1.5"


def test_v3_nao_altera_versao_metodologia_da_vintage(tmp_path):
    vintage = _vintage_real(tmp_path)
    versao_antes = vintage["manifest"]["methodology_version"]
    gerar_relatorio_ipia_hrc_v3(str(tmp_path / "r.pdf"), vintage, decomposicao_df=None, componentes_mensais_df=None)
    assert vintage["manifest"]["methodology_version"] == versao_antes == m.VERSAO_METODOLOGIA


# --- 6. Reprodutibilidade ------------------------------------------------------

def test_v3_reproduzivel_para_a_mesma_vintage(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados_1 = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=None, componentes_mensais_df=None)
    dados_2 = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=None, componentes_mensais_df=None)
    assert dados_1["ipia_atual"] == dados_2["ipia_atual"]
    assert dados_1["vintage_id"] == dados_2["vintage_id"]


# --- 7. Posicao historica (Sec.19) -------------------------------------------

def test_posicao_historica_percentil_dentro_de_0_100(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=None, componentes_mensais_df=None)
    pos = dados["posicao_historica"]
    if pos is not None:
        assert 0.0 <= pos["percentil"] <= 100.0
        assert pos["min"] <= pos["mediana"] <= pos["max"]


# --- 8. Fonte portatil (Sec.39) ----------------------------------------------

def test_fontes_resolvidas_sao_strings_nao_listas():
    from reporting import theme as t
    assert isinstance(t.FONTE_SANS, str)
    assert isinstance(t.FONTE_SERIF, str)


def test_resolver_fonte_instalada_sempre_cai_no_bundled_matplotlib():
    from reporting.theme import _resolver_fonte_instalada
    resolvida = _resolver_fonte_instalada(["FonteInexistente123", "OutraTambemFalsa456", "DejaVu Sans"])
    assert resolvida == "DejaVu Sans"
