"""Testes puros e deterministicos (sem rede) para
scripts/validar_ipia_hrc_cost_parameters.py - sprint "IPIA-HRC - MARGIN/
PORT/INLAND COST PARAMETER CALIBRATION". VALIDATION ONLY: nao testa
nenhuma decisao metodologica (Level 3, do usuario) - so garante que
cenarios/isolamento/elasticidade estao matematicamente corretos e que
`ParamsIPIA()` default nunca e mutado por este script.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pandas as pd
import pytest

import validar_ipia_hrc_cost_parameters as v
import indices_setoriais as m


# =============================================================================
# CenarioParametros / to_params - nunca muta o default de producao
# =============================================================================

def test_cenario_to_params_produz_parametros_corretos():
    c = v.CenarioParametros("teste", despesas_porto_rs_t=999.0, frete_interno_rs_t=888.0,
                             margem_importador=0.5)
    p = c.to_params()
    assert p.despesas_porto_rs_t == 999.0
    assert p.frete_interno_rs_t == 888.0
    assert p.margem_importador == 0.5


def test_default_params_ipia_nunca_e_mutado_apos_criar_cenarios():
    original_porto = m.ParamsIPIA().despesas_porto_rs_t
    original_interno = m.ParamsIPIA().frete_interno_rs_t
    original_margem = m.ParamsIPIA().margem_importador
    for c in v.montar_cenarios() + v.montar_cenarios_isolados():
        c.to_params()  # cria uma instancia nova, nunca toca o default
    novo = m.ParamsIPIA()
    assert novo.despesas_porto_rs_t == original_porto == 210.0
    assert novo.frete_interno_rs_t == original_interno == 140.0
    assert novo.margem_importador == original_margem == 0.03


def test_cenario_current_bate_com_default_de_producao():
    cenarios = {c.nome: c for c in v.montar_cenarios()}
    current = cenarios["Current"]
    default = m.ParamsIPIA()
    assert current.despesas_porto_rs_t == default.despesas_porto_rs_t
    assert current.frete_interno_rs_t == default.frete_interno_rs_t
    assert current.margem_importador == default.margem_importador


def test_montar_cenarios_tem_low_current_evidence_base_high():
    nomes = {c.nome for c in v.montar_cenarios()}
    assert nomes == {"Low", "Current", "Evidence Base", "High"}


def test_montar_cenarios_isolados_altera_so_um_parametro_por_vez():
    default = m.ParamsIPIA()
    for c in v.montar_cenarios_isolados():
        mudou = [c.despesas_porto_rs_t != default.despesas_porto_rs_t,
                  c.frete_interno_rs_t != default.frete_interno_rs_t,
                  c.margem_importador != default.margem_importador]
        assert sum(mudou) == 1, f"{c.nome} deveria alterar exatamente 1 parametro"


# =============================================================================
# comparar_cenarios - delta% e deteccao de mudanca de status
# =============================================================================

def test_comparar_cenarios_calcula_delta_pct_corretamente():
    idx = pd.to_datetime(["2023-01-01", "2023-02-01"])
    base = pd.DataFrame({"ppi_rs_t": [1000.0, 2000.0], "publication_status": ["PUBLICATION_GRADE"] * 2},
                         index=idx)
    alterado = pd.DataFrame({"ppi_rs_t": [1100.0, 1900.0], "publication_status": ["PUBLICATION_GRADE"] * 2},
                             index=idx)
    comp = v.comparar_cenarios(base, alterado, "teste")
    assert comp["ppi_delta_pct"].iloc[0] == pytest.approx(10.0)
    assert comp["ppi_delta_pct"].iloc[1] == pytest.approx(-5.0)
    assert comp["cenario"].iloc[0] == "teste"


def test_comparar_cenarios_detecta_mudanca_de_status():
    idx = pd.to_datetime(["2023-01-01"])
    base = pd.DataFrame({"ppi_rs_t": [1000.0], "publication_status": ["UNKNOWN"]}, index=idx)
    alterado = pd.DataFrame({"ppi_rs_t": [1000.0], "publication_status": ["EXPERIMENTAL"]}, index=idx)
    comp = v.comparar_cenarios(base, alterado, "teste")
    assert comp["status_current"].iloc[0] != comp["status_cenario"].iloc[0]


def test_comparar_cenarios_usa_apenas_meses_em_comum():
    base = pd.DataFrame({"ppi_rs_t": [1000.0], "publication_status": ["PUBLICATION_GRADE"]},
                         index=pd.to_datetime(["2023-01-01"]))
    alterado = pd.DataFrame({"ppi_rs_t": [1000.0], "publication_status": ["PUBLICATION_GRADE"]},
                             index=pd.to_datetime(["2023-02-01"]))  # mes diferente
    comp = v.comparar_cenarios(base, alterado, "teste")
    assert len(comp) == 0  # nenhuma intersecao


# =============================================================================
# pearson helper (sem scipy, mesma convencao do resto do projeto)
# =============================================================================

def test_pearson_casos_conhecidos():
    import numpy as np
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([2.0, 4.0, 6.0, 8.0])
    assert v.pearson(x, y) == pytest.approx(1.0)
    y_const = np.array([5.0, 5.0, 5.0, 5.0])
    assert np.isnan(v.pearson(x, y_const))


# =============================================================================
# auditar_parametros_atuais - reflete o codigo de producao, nunca hardcode
# =============================================================================

def test_auditar_parametros_atuais_reflete_default_de_producao():
    audit = v.auditar_parametros_atuais()
    default = m.ParamsIPIA()
    linha_porto = audit[audit["parameter"] == "D_porto"].iloc[0]
    linha_interno = audit[audit["parameter"] == "D_interno"].iloc[0]
    linha_margem = audit[audit["parameter"] == "margem"].iloc[0]
    assert linha_porto["current"] == default.despesas_porto_rs_t
    assert linha_interno["current"] == default.frete_interno_rs_t
    assert linha_margem["current"] == default.margem_importador
    assert (audit["provenance"] == "ESTIMADO").all()
    assert (audit["time_varying"] == "No").all()
