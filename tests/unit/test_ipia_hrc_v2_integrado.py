"""Unit tests for calcular_serie_ipia_hrc_v2() - integracao do import side V2
(agregar_ipia_hrc_multi_ncm_mensal, Stage E7) com o Domestic Price V2
(preco_domestico_hrc_mensal_v2, Stage E8) por reference_period (Stage E9).
Deterministic, no network: `ppi_mensal_df`/`preco_domestico_df` sao
injetados prontos (mesmo padrao ja usado pelo resto do modulo).

Prova: IPIA = preco_domestico_v2/ppi_v2*100 somente quando os dois lados
sao validos; merge e SO por reference_period; UNKNOWN em qualquer lado
propaga para UNKNOWN; EXPERIMENTAL/PUBLICATION_GRADE propagam quando o
outro lado esta presente; domestic_is_proxy e uma flag separada de
publication_status; nenhum fallback legado; sem look-ahead; output
ordenado e sem reference_period duplicado.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN


def _ppi_row(data, ppi=3900.0, status=STATUS_PUBLICATION_GRADE, **kw):
    linha = {"reference_period": pd.Timestamp(data), "ppi_rs_t": ppi,
             "ppi_offer_rs_t": ppi * 1.03,  # PPI_COST*(1+margem default) - so fixture, nunca lido pelo IPIA
             "publication_status": status,
             "total_kg": 1e7, "known_policy_kg": 1e7, "unknown_policy_kg": 0.0, "policy_coverage": 1.0,
             "ppi_lower": ppi, "ppi_upper": ppi, "ppi_uncertainty_range_pct": 0.0}
    linha.update(kw)
    return linha


def _dom_row(data, preco=5000.0, is_proxy=True, provenance="CALCULADO", validation="DOCUMENTADO", **kw):
    linha = {"reference_period": pd.Timestamp(data), "preco_domestico_rs_t": preco,
             "anchor_reference_period": "2024Q2", "anchor_price_rs_t": preco, "companies_used": "CSNA3,USIM5",
             "ipp_series_id": m.IPP_SIDERURGIA_SERIES_ID, "provenance_level": provenance, "is_proxy": is_proxy,
             "validation_status": validation, "receita_total": 1e9, "volume_total": 2e5,
             "quantidade_empresas": 2}
    linha.update(kw)
    return linha


def _ppi_df(*linhas):
    return pd.DataFrame(list(linhas))


_DOM_COLS = ["reference_period", "preco_domestico_rs_t", "anchor_reference_period", "anchor_price_rs_t",
             "companies_used", "ipp_series_id", "provenance_level", "is_proxy", "validation_status",
             "receita_total", "volume_total", "quantidade_empresas"]


_DOM_COLS_NUMERICAS = ["preco_domestico_rs_t", "anchor_price_rs_t", "receita_total", "volume_total",
                       "quantidade_empresas"]


def _dom_df(*linhas):
    if not linhas:
        # DataFrame vazio, mas com os MESMOS dtypes que o dado real teria
        # (float para colunas numericas, datetime64 para reference_period) -
        # um DataFrame vazio construido so com `columns=` cai em dtype
        # `object` em tudo, o que faz o merge/atribuicao adiante falhar por
        # incompatibilidade de tipo - um problema so desta fixture de
        # teste, nao do dado real (Domestic Price V2 nunca produz colunas
        # numericas em dtype object).
        vazio = pd.DataFrame(columns=_DOM_COLS)
        vazio["reference_period"] = pd.to_datetime(vazio["reference_period"])
        for col in _DOM_COLS_NUMERICAS:
            vazio[col] = vazio[col].astype(float)
        return vazio
    return pd.DataFrame(list(linhas))


# --- 1. Formula: ipia == preco_domestico / ppi * 100 ------------------------

def test_formula_ipia_hrc_v2():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=3917.9964))
    dom = _dom_df(_dom_row("2024-06-01", preco=5000.0))
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom).iloc[0]
    assert out["ipia_hrc_v2"] == pytest.approx(5000.0 / 3917.9964 * 100.0)


# --- 2. Merge somente por reference_period (meses nao coincidentes) --------

def test_merge_somente_por_reference_period():
    ppi = _ppi_df(_ppi_row("2024-06-01"), _ppi_row("2024-07-01"))
    dom = _dom_df(_dom_row("2024-07-01"))  # so julho tem domestico
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom).set_index("reference_period")
    assert out.loc["2024-06-01", "publication_status"] == STATUS_UNKNOWN  # sem domestico nesse mes
    assert out.loc["2024-07-01", "publication_status"] == STATUS_PUBLICATION_GRADE
    assert not np.isnan(out.loc["2024-07-01", "ipia_hrc_v2"])


# --- 3. Import side UNKNOWN -> IPIA UNKNOWN/NaN -----------------------------

def test_import_unknown_propaga_para_ipia_unknown():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=np.nan, status=STATUS_UNKNOWN))
    dom = _dom_df(_dom_row("2024-06-01"))
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["ipia_hrc_v2"])


# --- 4. Domestico ausente -> IPIA UNKNOWN/NaN -------------------------------

def test_domestico_ausente_propaga_para_ipia_unknown():
    ppi = _ppi_df(_ppi_row("2024-06-01"))
    dom = _dom_df()  # nenhum mes de domestico
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["ipia_hrc_v2"])
    assert np.isnan(out["preco_domestico_rs_t"])


# --- 5. Import EXPERIMENTAL + domestico presente -> IPIA EXPERIMENTAL ------

def test_import_experimental_e_domestico_presente_da_experimental():
    ppi = _ppi_df(_ppi_row("2019-06-01", ppi=3973.9, status=STATUS_EXPERIMENTAL))
    dom = _dom_df(_dom_row("2019-06-01", preco=5000.0))
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_EXPERIMENTAL
    assert not np.isnan(out["ipia_hrc_v2"])


# --- 6. Import PUBLICATION_GRADE + domestico presente -> IPIA calculado ----

def test_publication_grade_valido_calcula_indice():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=3917.9964, status=STATUS_PUBLICATION_GRADE))
    dom = _dom_df(_dom_row("2024-06-01", preco=5236.0))
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_PUBLICATION_GRADE
    assert out["ipia_hrc_v2"] == pytest.approx(5236.0 / 3917.9964 * 100.0)


# --- 7. domestic_is_proxy separado de publication_status --------------------

def test_domestic_is_proxy_nao_e_sinonimo_de_unknown_nem_experimental():
    ppi = _ppi_df(_ppi_row("2024-06-01", status=STATUS_PUBLICATION_GRADE))
    dom = _dom_df(_dom_row("2024-06-01", is_proxy=True))
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom).iloc[0]
    assert bool(out["domestic_is_proxy"]) is True
    assert out["publication_status"] == STATUS_PUBLICATION_GRADE  # PROXY nao rebaixa o status sozinho


# --- 8. Nenhum fallback legado ------------------------------------------------

def test_nenhum_fallback_legado_quando_domestico_v2_ausente():
    # mesmo com o CSV curado legado real disponivel, um mes ausente do
    # Domestic Price V2 injetado NUNCA e preenchido pelo legado - fica
    # UNKNOWN, nao "recuperado" de outra fonte.
    ppi = _ppi_df(_ppi_row("2024-06-01"))
    dom = _dom_df()  # V2 nao tem nada - nao deve haver fallback pro legado aqui
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom).iloc[0]
    assert out["publication_status"] == STATUS_UNKNOWN
    assert np.isnan(out["preco_domestico_rs_t"])


# --- 9. Ausencia de look-ahead: mes seguinte nao contamina o mes atual -----

def test_sem_look_ahead_entre_meses():
    ppi_so_junho = _ppi_df(_ppi_row("2024-06-01", ppi=3900.0))
    ppi_junho_julho = _ppi_df(_ppi_row("2024-06-01", ppi=3900.0), _ppi_row("2024-07-01", ppi=9999.0))
    dom_so_junho = _dom_df(_dom_row("2024-06-01", preco=5000.0))
    dom_junho_julho = _dom_df(_dom_row("2024-06-01", preco=5000.0), _dom_row("2024-07-01", preco=8888.0))

    so_junho = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi_so_junho, preco_domestico_df=dom_so_junho)
    com_julho = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi_junho_julho, preco_domestico_df=dom_junho_julho)

    junho_so = so_junho.set_index("reference_period").loc["2024-06-01"]
    junho_com = com_julho.set_index("reference_period").loc["2024-06-01"]
    assert junho_so["ipia_hrc_v2"] == pytest.approx(junho_com["ipia_hrc_v2"])
    assert junho_so["publication_status"] == junho_com["publication_status"]


# --- 10. Output mensal ordenado e sem reference_period duplicado -----------

def test_output_ordenado_e_sem_duplicata_de_mes():
    ppi = _ppi_df(_ppi_row("2024-07-01"), _ppi_row("2024-06-01"))  # fora de ordem de proposito
    dom = _dom_df(_dom_row("2024-07-01"), _dom_row("2024-06-01"))
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom)
    assert list(out["reference_period"]) == sorted(out["reference_period"])
    assert out["reference_period"].is_unique


def test_ppi_mensal_df_com_reference_period_duplicado_levanta_erro():
    # `validate="one_to_one"` do merge deve pegar isso - nunca silenciar
    # uma duplicata de mes no lado de importacao.
    ppi = _ppi_df(_ppi_row("2024-06-01"), _ppi_row("2024-06-01"))
    dom = _dom_df(_dom_row("2024-06-01"))
    with pytest.raises(Exception):  # pandas.errors.MergeError
        m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom)


# --- 11. CSV exportado preserva os valores calculados -----------------------

def test_csv_exportado_preserva_valores(tmp_path):
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=3917.9964))
    dom = _dom_df(_dom_row("2024-06-01", preco=5236.0))
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom)
    caminho = tmp_path / "ipia_hrc_v2_monthly.csv"
    out.to_csv(caminho, index=False)
    lido = pd.read_csv(caminho, parse_dates=["reference_period"])
    assert lido.loc[0, "ipia_hrc_v2"] == pytest.approx(out.iloc[0]["ipia_hrc_v2"])
    assert lido.loc[0, "publication_status"] == out.iloc[0]["publication_status"]


# --- 12. Gap (mes sem import nem domestico) nao e inventado -----------------

def test_gap_entre_meses_nao_e_preenchido():
    # import side pula de junho pra agosto (julho sem nenhum registro
    # Comex, gap real) - o merge nao deve inventar uma linha de julho.
    ppi = _ppi_df(_ppi_row("2024-06-01"), _ppi_row("2024-08-01"))
    dom = _dom_df(_dom_row("2024-06-01"), _dom_row("2024-08-01"))
    out = m.calcular_serie_ipia_hrc_v2(ppi_mensal_df=ppi, preco_domestico_df=dom)
    assert list(out["reference_period"]) == [pd.Timestamp("2024-06-01"), pd.Timestamp("2024-08-01")]
    assert pd.Timestamp("2024-07-01") not in set(out["reference_period"])
