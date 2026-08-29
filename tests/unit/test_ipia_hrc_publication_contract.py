"""Publication contract tests for IPIA-HRC (Stage G4B, ADR 0013).

Formaliza, como um checkpoint nomeado e estavel, os invariantes que o
contrato de publicacao aprovado (ADR 0013) depende - a maioria ja
protegida por testes de stages anteriores (E11: test_ipia_hrc_v2_pia_
integrado.py; G2: test_ipia_hrc_v2_vintages.py) com nomes proprios; este
arquivo existe para que uma futura mudanca que viole o CONTRATO DE
PUBLICACAO (nao so a mecanica interna) falhe aqui, num lugar
explicitamente ligado ao ADR, independente de qualquer refactor dos
testes de unidade originais.

Deterministic, no network. Nao testa liquidity_status (Stage G4B decidiu
NAO implementar esse campo ainda - threshold sem decisao Level 3, ver
ADR 0013 e o relatorio desta stage) nem qualquer texto de disclosure
(wording aprovado como referencia, nao como codigo).
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


def _pia_row(data, preco=5000.0, pia_reference_year=2023, pia_anchor_price_rs_t=5000.0,
             is_provisional=False, is_proxy=True, provenance="ESTIMADO", validation="VERIFICADO", **kw):
    linha = {"reference_period": pd.Timestamp(data), "preco_domestico_rs_t": preco,
             "pia_reference_year": pia_reference_year, "pia_anchor_price_rs_t": pia_anchor_price_rs_t,
             "ipp_series_id": m.IPP_SIDERURGIA_SERIES_ID, "provenance_level": provenance, "is_proxy": is_proxy,
             "proxy_reason": m.PROXY_REASON_DESTINATION_MIX, "is_provisional": is_provisional,
             "validation_status": validation}
    linha.update(kw)
    return linha


def _pia_df(*linhas):
    return pd.DataFrame(list(linhas))


# --- 1/2. EXPERIMENTAL e PUBLICATION_GRADE permanecem publicados no OFFICIAL --

def test_contrato_experimental_permanece_no_arquivo_official():
    ppi = _ppi_df(_ppi_row("2019-06-01", ppi=3900.0, status=STATUS_EXPERIMENTAL))
    dom = _pia_df(_pia_row("2019-06-01", preco=5000.0, is_provisional=False))
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    oficial, _ = m.separar_ipia_hrc_v2_oficial_provisional(serie)
    assert list(oficial["publication_status"]) == [STATUS_EXPERIMENTAL]
    assert not np.isnan(oficial["ipia_hrc_v2"].iloc[0])


def test_contrato_publication_grade_permanece_no_arquivo_official():
    ppi = _ppi_df(_ppi_row("2023-06-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2023-06-01", preco=5000.0, is_provisional=False))
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    oficial, _ = m.separar_ipia_hrc_v2_oficial_provisional(serie)
    assert list(oficial["publication_status"]) == [STATUS_PUBLICATION_GRADE]


# --- 3. PROVISIONAL fica so na serie provisional -----------------------------

def test_contrato_provisional_fica_so_no_arquivo_provisional():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2024-06-01", preco=5100.0, is_provisional=True))
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    oficial, provisional = m.separar_ipia_hrc_v2_oficial_provisional(serie)
    assert oficial.empty
    assert list(provisional["publication_status"]) == [STATUS_PROVISIONAL]


# --- 4. UNKNOWN nunca entra em nenhum arquivo publicado ----------------------

def test_contrato_unknown_nunca_entra_em_official_nem_provisional():
    ppi = _ppi_df(_ppi_row("2024-06-01", ppi=np.nan, status=STATUS_UNKNOWN))
    dom = _pia_df(_pia_row("2024-06-01", preco=5100.0, is_provisional=True))
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    assert (serie["publication_status"] == STATUS_UNKNOWN).any()
    oficial, provisional = m.separar_ipia_hrc_v2_oficial_provisional(serie)
    assert not (oficial["publication_status"] == STATUS_UNKNOWN).any()
    assert not (provisional["publication_status"] == STATUS_UNKNOWN).any()
    assert oficial.empty and provisional.empty  # o unico mes do fixture e UNKNOWN


# --- 9. Corporate benchmark nunca entra no calculo PIA-based -----------------

def test_contrato_corporate_benchmark_nunca_entra_no_calculo_oficial(monkeypatch):
    def _explode(*a, **kw):
        raise AssertionError("IPIA-HRC Corporate Benchmark (calcular_serie_ipia_hrc_v2/"
                             "preco_domestico_hrc_mensal_v2) nao deveria ser chamado pelo "
                             "caminho oficial IPIA-HRC")
    monkeypatch.setattr(m, "preco_domestico_hrc_mensal_v2", _explode)
    monkeypatch.setattr(m, "calcular_serie_ipia_hrc_v2", _explode)
    ppi = _ppi_df(_ppi_row("2023-06-01", status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2023-06-01", is_provisional=False))
    m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)  # nao deve levantar


# --- 10. Metadado de naming/documentacao nao altera o calculo ----------------

def test_contrato_docstrings_de_naming_nao_alteram_o_resultado_numerico():
    # Stage G4B so adicionou notas de nomenclatura publica aos docstrings de
    # calcular_serie_ipia_hrc_v2/calcular_ipia_hrc_v2_pia - docstring nao e
    # executado, entao o resultado numerico tem que ser identico ao que a
    # formula sempre produziu. Prova indireta: reconciliar contra a formula
    # crua, nao contra um valor congelado de execucao anterior.
    ppi = _ppi_df(_ppi_row("2023-06-01", ppi=4000.0, status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2023-06-01", preco=4800.0, is_provisional=False))
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    assert serie["ipia_hrc_v2"].iloc[0] == pytest.approx(4800.0 / 4000.0 * 100.0)
    assert m.calcular_serie_ipia_hrc_v2.__doc__ is not None  # docstring existe e nao quebrou a definicao
    assert m.calcular_ipia_hrc_v2_pia.__doc__ is not None


# --- Baixa liquidez: decisao final (Stage G4C) = NO THRESHOLD / DISCLOSURE ONLY
# Nenhum liquidity_status/low_liquidity/threshold_t foi criado - ver
# docs/METODOLOGIA.md secao 11.1 e ADR 0013 item 2. Os testes abaixo provam
# COMPORTAMENTO (nao so ausencia de nome de coluna): total_kg continua
# publicado sem transformacao; publication_status/ipia_hrc_v2 sao
# matematicamente independentes de total_kg; nenhum vestigio do mecanismo
# legado VOLUME_MINIMO_T/suavizar_preco_importacao (peso de confiabilidade
# continuo, blend com media movel) alcanca o calculo V2; um mes isolado de
# volume baixissimo nunca e puxado na direcao dos vizinhos (prova direta de
# ausencia de smoothing/interpolacao).

def test_total_kg_permanece_publicado_sem_transformacao():
    ppi = _ppi_df(_ppi_row("2023-06-01", status=STATUS_PUBLICATION_GRADE, total_kg=1234.0))
    dom = _pia_df(_pia_row("2023-06-01", is_provisional=False))
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    assert "total_kg" in serie.columns
    assert serie["total_kg"].iloc[0] == pytest.approx(1234.0)  # valor observado, nao transformado


def test_publication_status_e_ipia_independem_de_total_kg():
    # dois meses IDENTICOS em tudo (coverage, uncertainty, preco, ppi,
    # status), so total_kg difere por 5 ordens de grandeza (1 mil kg vs
    # 100 milhoes de kg) - publication_status e ipia_hrc_v2 tem que ser
    # EXATAMENTE iguais nos dois casos. Se algum dia total_kg passar a
    # influenciar o calculo (smoothing, threshold, peso), este teste falha.
    ppi_baixo_volume = _ppi_df(_ppi_row("2023-06-01", ppi=4000.0, status=STATUS_PUBLICATION_GRADE,
                                        total_kg=1_000.0, known_policy_kg=1_000.0))
    ppi_alto_volume = _ppi_df(_ppi_row("2023-06-01", ppi=4000.0, status=STATUS_PUBLICATION_GRADE,
                                       total_kg=100_000_000.0, known_policy_kg=100_000_000.0))
    dom = _pia_df(_pia_row("2023-06-01", preco=4800.0, is_provisional=False))

    serie_baixo = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_baixo_volume, pia_domestico_df=dom)
    serie_alto = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi_alto_volume, pia_domestico_df=dom)

    assert serie_baixo["publication_status"].iloc[0] == serie_alto["publication_status"].iloc[0]
    assert serie_baixo["ipia_hrc_v2"].iloc[0] == pytest.approx(serie_alto["ipia_hrc_v2"].iloc[0])
    assert serie_baixo["ipia_hrc_v2"].iloc[0] == pytest.approx(4800.0 / 4000.0 * 100.0)  # formula crua, nos dois


def test_volume_abaixo_de_volume_minimo_t_legado_nao_e_suavizado():
    # total_kg << VOLUME_MINIMO_T (legado, mecanismo de suavizacao V1 -
    # src/indices_setoriais.py) - se esse mecanismo tivesse vazado para o
    # V2, o ipia_hrc_v2 desse mes sairia diferente da formula crua
    # (blend com media movel/peso de confiabilidade). Prova que nao vaza.
    assert 500.0 < m.VOLUME_MINIMO_T  # sanity check da premissa do teste
    ppi = _ppi_df(_ppi_row("2023-06-01", ppi=4000.0, status=STATUS_PUBLICATION_GRADE,
                           total_kg=500.0, known_policy_kg=500.0))
    dom = _pia_df(_pia_row("2023-06-01", preco=4800.0, is_provisional=False))
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    assert serie["ipia_hrc_v2"].iloc[0] == pytest.approx(4800.0 / 4000.0 * 100.0)
    assert serie["publication_status"].iloc[0] == STATUS_PUBLICATION_GRADE  # nunca UNKNOWN por volume


def test_mes_de_volume_baixissimo_nao_e_puxado_na_direcao_dos_vizinhos():
    # tres meses consecutivos: vizinhos com IPIA proximo de 100, mes do
    # meio com volume baixissimo e IPIA MUITO fora da faixa dos vizinhos
    # (33.33, longe de ~100) - se houvesse qualquer suavizacao/
    # interpolacao entre meses, o valor do meio seria puxado para perto
    # dos vizinhos. Prova que cada mes e calculado isoladamente.
    ppi = _ppi_df(
        _ppi_row("2023-05-01", ppi=4000.0, status=STATUS_PUBLICATION_GRADE, total_kg=5_000_000.0),
        _ppi_row("2023-06-01", ppi=9000.0, status=STATUS_PUBLICATION_GRADE, total_kg=500.0),  # baixo volume
        _ppi_row("2023-07-01", ppi=4000.0, status=STATUS_PUBLICATION_GRADE, total_kg=5_000_000.0),
    )
    dom = _pia_df(
        _pia_row("2023-05-01", preco=4000.0, is_provisional=False),
        _pia_row("2023-06-01", preco=3000.0, is_provisional=False),
        _pia_row("2023-07-01", preco=4000.0, is_provisional=False),
    )
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom).set_index("reference_period")
    assert serie.loc["2023-05-01", "ipia_hrc_v2"] == pytest.approx(100.0)
    assert serie.loc["2023-07-01", "ipia_hrc_v2"] == pytest.approx(100.0)
    assert serie.loc["2023-06-01", "ipia_hrc_v2"] == pytest.approx(3000.0 / 9000.0 * 100.0)  # ~33.33, cru


def test_contrato_nao_ha_campo_de_liquidez_no_core():
    # decisao final (Stage G4C): NO THRESHOLD / DISCLOSURE ONLY - nunca um
    # campo estruturado. Continua como tripwire: falha de proposito se
    # algum campo desses for adicionado sem revisitar conscientemente
    # esta decisao (e o disclosure textual em METODOLOGIA §11.1).
    ppi = _ppi_df(_ppi_row("2023-06-01", status=STATUS_PUBLICATION_GRADE))
    dom = _pia_df(_pia_row("2023-06-01", is_provisional=False))
    serie = m.calcular_ipia_hrc_v2_pia(ppi_mensal_df=ppi, pia_domestico_df=dom)
    for campo_proibido in ("liquidity_status", "low_liquidity", "threshold_t", "liquidity_flag"):
        assert campo_proibido not in serie.columns
