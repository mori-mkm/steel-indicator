"""Unit tests for calcular_ipia_hrc_v2_pia()/separar_ipia_hrc_v2_oficial_provisional()
- integracao do import side V2 (agregar_ipia_hrc_multi_ncm_mensal, Stage E7)
com o Domestic Price V2 caminho PIA (preco_domestico_hrc_pia_v2, Stage
E10/ADR 0010), acrescentando o quarto status PROVISIONAL e a separacao
oficial/provisional (Stage E11, ADR 0011). Deterministic, no network:
`ppi_mensal_df`/`pia_domestico_df` sao injetados prontos (mesmo padrao ja
usado pelo resto do modulo e por test_ipia_hrc_v2_integrado.py).

Cobre a secao 8 da decisao Level 3 aprovada (14 itens): PROVISIONAL existe
como status real; as quatro combinacoes de status conjunto; PROXY
ortogonal; separacao oficial/provisional estrita; ancora corporativa nunca
usada neste caminho; formula do IPIA preservada; congelamento no fluxo
normal (mudanca de IPP sem nova PIA nao move meses ja congelados); avanco
mensal do provisional.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN

STATUS_PROVISIONAL = m.STATUS_PROVISIONAL


def _ppi_row(data, ppi=3900.0, status=STATUS_PUBLICATION_GRADE, **kw):
    linha = {"reference_period": pd.Timestamp(data), "ppi_rs_t": ppi,
             "ppi_offer_rs_t": ppi * 1.03,  # PPI_COST*(1+margem default) - so fixture, nunca lido pelo IPIA
             "publication_status": status,
             "total_kg": 1e7, "known_policy_kg": 1e7, "unknown_policy_kg": 0.0, "policy_coverage": 1.0,
             "ppi_lower": ppi, "ppi_upper": ppi, "ppi_uncertainty_range_pct": 0.0}
    linha.update(kw)
    return linha


def _ppi_df(*linhas):
    return pd.DataFrame(list(linhas))


def _pia_row(data, preco=5000.0, pia_reference_year=2020, pia_anchor_price_rs_t=5000.0,
             is_provisional=False, is_proxy=True, provenance="ESTIMADO", validation="VERIFICADO", **kw):
    linha = {"reference_period": pd.Timestamp(data), "preco_domestico_rs_t": preco,
             "pia_reference_year": pia_reference_year, "pia_anchor_price_rs_t": pia_anchor_price_rs_t,
             "ipp_series_id": m.IPP_SIDERURGIA_SERIES_ID, "provenance_level": provenance, "is_proxy": is_proxy,
             "proxy_reason": m.PROXY_REASON_DESTINATION_MIX, "is_provisional": is_provisional,
             "validation_status": validation}
    linha.update(kw)
    return linha


_PIA_COLS = ["reference_period", "preco_domestico_rs_t", "pia_reference_year", "pia_anchor_price_rs_t",
             "ipp_series_id", "provenance_level", "is_proxy", "proxy_reason", "is_provisional",
             "validation_status"]


def _pia_df(*linhas):
    if not linhas:
        vazio = pd.DataFrame(columns=_PIA_COLS)
        vazio["reference_period"] = pd.to_datetime(vazio["reference_period"])
        for col in ("preco_domestico_rs_t", "pia_anchor_price_rs_t"):
            vazio[col] = vazio[col].astype(float)
        return vazio
    return pd.DataFrame(list(linhas))


# --- 1. PROVISIONAL existe como status real ---------------------------------

def test_provisional_e_um_status_real_e_distinto():
    assert STATUS_PROVISIONAL == "PROVISIONAL"
    assert STATUS_PROVISIONAL not in (STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN)


# --- 2/3. domestico benchmarked + import experimental/publication_grade -----

def test_domestico_benchmarked_import_experimental_da_experimental():
    ppi = _ppi_df(_ppi_row("2019-06-01", ppi=3973.9, status=STATUS_EXPERIMENTAL))
    dom = _pia_df(_pia_row("2019-06-01", preco=5000.0, is_provisional=False))
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_EXPERIMENTAL
    assert out["ipia_hrc_v2"] == pytest.approx(5000.0 / 3973.9 * 100.0)


def test_domestico_benchmarked_import_publication_grade_da_publication_grade():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=3917.9964, status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2024-06-01", preco=5236.0, is_provisional=False))
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_PUBLICATION_GRADE
    assert out["ipia_hrc_v2"] == pytest.approx(5236.0 / 3917.9964 * 100.0)


# --- 4/5. domestico provisional + import publication_grade/experimental ----

def test_domestico_provisional_import_publication_grade_da_provisional():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2024-06-01", preco=5100.0, is_provisional=True))
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_PROVISIONAL
    assert out["ipia_hrc_v2"] == pytest.approx(5100.0 / 3900.0 * 100.0)


def test_domestico_provisional_import_experimental_da_provisional_se_calculavel():
    ppi = _ppi_df(_ppi_row("2019-06-01", ppi=3900.0, status=STATUS_EXPERIMENTAL))
    dom = _pia_df(_pia_row("2019-06-01", preco=5100.0, is_provisional=True))
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_PROVISIONAL
    assert not np.isnan(out["ipia_hrc_v2"])


# --- 6. Qualquer lado UNKNOWN -> UNKNOWN ------------------------------------

def test_import_unknown_da_unknown_mesmo_com_domestico_provisional():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=np.nan, status=STATUS_UNKNOWN))
    dom = _pia_df(_pia_row("2024-06-01", preco=5100.0, is_provisional=True))
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["ipia_hrc_v2"])


def test_domestico_ausente_da_unknown():
    ppi = _ppi_df(_ppi_row("2024-06-01", status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df()  # nenhum mes de domestico
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["ipia_hrc_v2"])
    assert np.isnan(out["preco_domestico_rs_t"])


# --- 7. PROXY ortogonal a publication_status --------------------------------

def test_domestic_is_proxy_e_ortogonal_a_publication_status():
    ppi = _ppi_df(_ppi_row("2024-06-01", status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2024-06-01", is_provisional=False, is_proxy=True))
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).iloc[0]
    assert bool(out["domestic_is_proxy"]) is True
    assert out["publication_status"] == STATUS_PUBLICATION_GRADE  # PROXY nao rebaixa sozinho

    ppi_prov = _ppi_df(_ppi_row("2024-07-01", status=STATUS_PUBLICATION_GRADE))
    dom_prov = _pia_df(_pia_row("2024-07-01", is_provisional=True, is_proxy=True))
    out_prov = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_prov, pia_domestico_df=dom_prov).iloc[0]
    assert bool(out_prov["domestic_is_proxy"]) is True
    assert out_prov["publication_status"] == STATUS_PROVISIONAL  # PROXY nao vira sinonimo de PROVISIONAL


# --- 8/9. Separacao oficial/provisional -------------------------------------

def test_arquivo_oficial_nunca_contem_provisional_e_provisional_so_contem_provisional():
    ppi = _ppi_df(
        _ppi_row("2020-01-01", status=STATUS_PUBLICATION_GRADE),
        _ppi_row("2024-06-01", status=STATUS_PUBLICATION_GRADE),
        _ppi_row("2024-07-01", status=STATUS_UNKNOWN, ppi=np.nan),
    )
    dom = _pia_df(
        _pia_row("2020-01-01", preco=5000.0, is_provisional=False),
        _pia_row("2024-06-01", preco=5100.0, is_provisional=True),
        _pia_row("2024-07-01", preco=5200.0, is_provisional=True),
    )
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    oficial, provisional = m.separar_ipia_hrc_v2_oficial_provisional(serie)

    assert not (oficial["publication_status"] == STATUS_PROVISIONAL).any()
    assert not (oficial["publication_status"] == STATUS_UNKNOWN).any()
    assert set(oficial["publication_status"]) <= {STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL}
    assert set(provisional["publication_status"]) == {STATUS_PROVISIONAL}
    assert "is_provisional" in provisional.columns and "last_pia_year" in provisional.columns
    assert len(oficial) == 1  # so 2020-01 (2024-07 e UNKNOWN, nunca entra no oficial)
    assert len(provisional) == 1  # so 2024-06 (2024-07 e UNKNOWN, import ausente de status calculavel)


# --- 10. Ancora corporativa nunca usada neste caminho ------------------------

def test_ancora_corporativa_nunca_e_chamada(monkeypatch):
    chamada = {"ocorreu": False}

    def _explode(*a, **kw):
        chamada["ocorreu"] = True
        raise AssertionError("preco_domestico_hrc_mensal_v2 (ancora corporativa) nao deveria ser chamada")

    monkeypatch.setattr(m, "preco_domestico_hrc_mensal_v2", _explode)
    ppi = _ppi_df(_ppi_row("2024-06-01", status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2024-06-01", is_provisional=False))
    m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    assert chamada["ocorreu"] is False


def test_pia_domestico_df_default_usa_preco_domestico_hrc_pia_v2(monkeypatch):
    chamado = {}

    def _fake_pia_v2():
        chamado["ok"] = True
        return _pia_df(_pia_row("2024-06-01", is_provisional=False))

    monkeypatch.setattr(m, "preco_domestico_hrc_pia_v2", _fake_pia_v2)
    ppi = _ppi_df(_ppi_row("2024-06-01", status=STATUS_PUBLICATION_GRADE))
    m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi)
    assert chamado.get("ok") is True


# --- 11. Formula do IPIA preservada -----------------------------------------

def test_formula_ipia_preservada():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=4000.0, status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2024-06-01", preco=4800.0, is_provisional=False))
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).iloc[0]
    assert out["ipia_hrc_v2"] == pytest.approx(4800.0 / 4000.0 * 100.0)


# --- 13. Congelamento no fluxo normal ----------------------------------------

def test_mudanca_de_ipp_sem_nova_pia_nao_altera_meses_ja_congelados():
    ppi_v1 = _ppi_df(_ppi_row("2020-01-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    dom_v1 = _pia_df(_pia_row("2020-01-01", preco=5000.0, is_provisional=False))
    serie_v1 = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_v1, pia_domestico_df=dom_v1)
    oficial_v1, _ = m.separar_ipia_hrc_v2_oficial_provisional(serie_v1)
    ipia_v1 = oficial_v1.set_index("reference_period").loc["2020-01-01", "ipia_hrc_v2"]

    # simula IPP revisado (sem nova PIA): mesmo mes, PPI e preco domestico
    # DIFERENTES do que geraram a serie oficial congelada.
    ppi_v2 = _ppi_df(_ppi_row("2020-01-01", ppi=9999.0, status=STATUS_PUBLICATION_GRADE))
    dom_v2 = _pia_df(_pia_row("2020-01-01", preco=1234.0, is_provisional=False))
    serie_v2_sem_congelar = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_v2, pia_domestico_df=dom_v2)
    ipia_v2_sem_congelar = serie_v2_sem_congelar.set_index("reference_period").loc["2020-01-01", "ipia_hrc_v2"]
    assert ipia_v2_sem_congelar != pytest.approx(ipia_v1)  # sanity: a mudanca upstream de fato move o numero sozinha

    serie_v2_congelada = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_v2, pia_domestico_df=dom_v2,
                                                     congelado_df=oficial_v1)
    linha_congelada = serie_v2_congelada.set_index("reference_period").loc["2020-01-01"]
    assert linha_congelada["ipia_hrc_v2"] == pytest.approx(ipia_v1)
    assert linha_congelada["preco_domestico_rs_t"] == pytest.approx(5000.0)
    assert linha_congelada["ppi_rs_t"] == pytest.approx(3900.0)
    assert linha_congelada["publication_status"] == STATUS_PUBLICATION_GRADE


def test_mes_congelado_nunca_desaparece_se_recalculo_fresco_deixa_de_cobri_lo():
    # cenario de revisao encontrado no code review: um mes ja congelado
    # (OFICIAL) some do recalculo fresco (ex.: import side recomputado com
    # uma janela mais estreita que nao cobre mais 2020-01) - o mes NUNCA
    # pode simplesmente sumir do resultado, so por omissao. Reinserido a
    # partir do proprio congelado_df.
    ppi_v1 = _ppi_df(_ppi_row("2020-01-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    dom_v1 = _pia_df(_pia_row("2020-01-01", preco=5000.0, is_provisional=False))
    serie_v1 = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_v1, pia_domestico_df=dom_v1)
    oficial_v1, _ = m.separar_ipia_hrc_v2_oficial_provisional(serie_v1)

    # recalculo fresco que NAO cobre mais 2020-01 (so um mes totalmente
    # diferente) - simula janela de import side mais estreita/fonte fora
    # do ar naquele mes especifico.
    ppi_v2 = _ppi_df(_ppi_row("2024-06-01", ppi=4000.0, status=STATUS_PUBLICATION_GRADE))
    dom_v2 = _pia_df(_pia_row("2024-06-01", preco=4800.0, is_provisional=True))
    serie_v2 = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_v2, pia_domestico_df=dom_v2,
                                          congelado_df=oficial_v1)

    assert pd.Timestamp("2020-01-01") in set(serie_v2["reference_period"])
    linha_congelada = serie_v2.set_index("reference_period").loc["2020-01-01"]
    assert linha_congelada["publication_status"] == STATUS_PUBLICATION_GRADE
    assert linha_congelada["ipia_hrc_v2"] == pytest.approx(
        oficial_v1.set_index("reference_period").loc["2020-01-01", "ipia_hrc_v2"])
    assert bool(linha_congelada["is_provisional"]) is False

    oficial_v2, provisional_v2 = m.separar_ipia_hrc_v2_oficial_provisional(serie_v2)
    assert pd.Timestamp("2020-01-01") in set(oficial_v2["reference_period"])
    assert pd.Timestamp("2020-01-01") not in set(provisional_v2["reference_period"])


# --- 14. Provisional continua podendo avancar mensalmente -------------------

def test_provisional_avanca_quando_um_novo_mes_e_adicionado():
    ppi_1mes = _ppi_df(_ppi_row("2024-06-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    dom_1mes = _pia_df(_pia_row("2024-06-01", preco=5000.0, is_provisional=True))
    serie_1mes = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_1mes, pia_domestico_df=dom_1mes)
    _, prov_1mes = m.separar_ipia_hrc_v2_oficial_provisional(serie_1mes)
    assert list(prov_1mes["reference_period"]) == [pd.Timestamp("2024-06-01")]

    ppi_2mes = _ppi_df(_ppi_row("2024-06-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE),
                       _ppi_row("2024-07-01", ppi=3950.0, status=STATUS_PUBLICATION_GRADE))
    dom_2mes = _pia_df(_pia_row("2024-06-01", preco=5000.0, is_provisional=True),
                       _pia_row("2024-07-01", preco=5050.0, is_provisional=True))
    serie_2mes = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_2mes, pia_domestico_df=dom_2mes,
                                             congelado_df=m.separar_ipia_hrc_v2_oficial_provisional(serie_1mes)[0])
    _, prov_2mes = m.separar_ipia_hrc_v2_oficial_provisional(serie_2mes)
    assert list(prov_2mes["reference_period"]) == [pd.Timestamp("2024-06-01"), pd.Timestamp("2024-07-01")]
    # o mes que ja existia (junho) continua igual - so avancou, nao reabriu.
    assert prov_2mes.set_index("reference_period").loc["2024-06-01", "ipia_hrc_v2"] == pytest.approx(
        prov_1mes.set_index("reference_period").loc["2024-06-01", "ipia_hrc_v2"])


# --- last_pia_year dinamico ---------------------------------------------------

def test_last_pia_year_e_dinamico_a_partir_do_domestico():
    ppi = _ppi_df(_ppi_row("2020-01-01", status=STATUS_PUBLICATION_GRADE),
                  _ppi_row("2024-06-01", status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2020-01-01", pia_reference_year=2020, is_provisional=False),
                 _pia_row("2024-06-01", pia_reference_year=2020, is_provisional=True))
    out = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    assert (out["last_pia_year"] == 2020).all()
