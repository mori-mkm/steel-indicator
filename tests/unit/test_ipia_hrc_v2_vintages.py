"""Unit tests for the IPIA-HRC V2 vintage layer (Stage G2, ADR 0012):
`calcular_revised`, `preparar_series_para_vintage`, `salvar_vintage_ipia_hrc_v2`,
`carregar_vintage_ipia_hrc_v2`, `listar_vintages_ipia_hrc_v2`,
`ultima_vintage_ipia_hrc_v2`. Deterministic, no network - `ppi_mensal_df`/
`pia_domestico_df` sao injetados prontos (mesmo padrao de
test_ipia_hrc_v2_pia_integrado.py), sempre persistindo em tmp_path (nunca
em data/processed real).

Cobre a secao "TESTES" da decisao Level 3 aprovada: manifest com campos
minimos; official/provisional/import_side/domestic_price persistidos;
data_vintage/source_vintage_id/methodology_version em toda linha
publicada; previous_vintage_id correto; official anterior carregado como
congelado_df no fluxo normal; revised correto (novo/inalterado/mudou,
ignorando so-o-identificador-de-execucao); promocao provisional->official
sem alterar a vintage anterior; reproducao do calculo a partir dos inputs
processados persistidos.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN

STATUS_PROVISIONAL = m.STATUS_PROVISIONAL


def _ppi_row(data, ppi=3900.0, status=STATUS_PUBLICATION_GRADE, **kw):
    linha = {"reference_period": pd.Timestamp(data), "ppi_rs_t": ppi, "publication_status": status,
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


def _salvar(ppi_df, pia_df, vintage_id, base_dir, vintage_anterior=None, sources_fetch_at_utc=None):
    serie = m.calcular_ipia_hrc_v2_pia(
        ppi_mensal_df=ppi_df, pia_domestico_df=pia_df,
        congelado_df=vintage_anterior["official"] if vintage_anterior is not None else None)
    manifest = m.salvar_vintage_ipia_hrc_v2(
        serie, import_side_df=ppi_df, domestic_price_df=pia_df, vintage_anterior=vintage_anterior,
        base_dir=base_dir, vintage_id=vintage_id, sources_fetch_at_utc=sources_fetch_at_utc)
    return serie, manifest


# --- calcular_revised (puro, sem I/O) ---------------------------------------

def test_revised_false_para_linha_nova():
    atual = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                          "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PROVISIONAL}])
    resultado = m.calcular_revised(atual, serie_anterior=None)
    assert list(resultado) == [False]


def test_revised_false_quando_valor_nao_mudou():
    linha = {"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
             "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PROVISIONAL}
    atual = pd.DataFrame([dict(linha)])
    anterior = pd.DataFrame([dict(linha)])
    resultado = m.calcular_revised(atual, anterior)
    assert list(resultado) == [False]


def test_revised_true_quando_valor_economico_mudou():
    anterior = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                             "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PROVISIONAL}])
    atual = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5200.0,
                          "ppi_rs_t": 4000.0, "ipia_hrc_v2": 130.0, "publication_status": STATUS_PROVISIONAL}])
    resultado = m.calcular_revised(atual, anterior)
    assert list(resultado) == [True]


def test_revised_true_quando_apenas_status_mudou():
    anterior = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                             "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PROVISIONAL}])
    atual = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                          "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PUBLICATION_GRADE}])
    resultado = m.calcular_revised(atual, anterior)
    assert list(resultado) == [True]


def test_mudanca_apenas_de_vintage_id_nao_gera_revised_true():
    # data_vintage/source_vintage_id nao entram na comparacao - so as 4
    # colunas economicas. Mesmo com identificadores de execucao diferentes
    # (que calcular_revised nem recebe), o resultado e False.
    anterior = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                             "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PROVISIONAL,
                             "data_vintage": "20260101T000000Z", "source_vintage_id": "20260101T000000Z"}])
    atual = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                          "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PROVISIONAL,
                          "data_vintage": "20260201T000000Z", "source_vintage_id": "20260201T000000Z"}])
    resultado = m.calcular_revised(atual, anterior)
    assert list(resultado) == [False]


def test_revised_tolera_ruido_de_ponto_flutuante():
    anterior = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                             "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.00000001, "publication_status": STATUS_PROVISIONAL}])
    atual = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                          "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PROVISIONAL}])
    resultado = m.calcular_revised(atual, anterior)
    assert list(resultado) == [False]


def test_revised_fronteira_exata_da_tolerancia():
    # tol_abs=1e-6, tol_rel=1e-9 (default). Para ipia~125, o termo relativo
    # (1e-9*125=1.25e-7) e dominado pelo absoluto - o limiar efetivo e
    # ~1e-6. Diferenca EXATAMENTE no limiar (1e-6) ainda conta como "igual"
    # (math.isclose usa <=); uma diferenca ligeiramente MAIOR ja conta
    # como revisao - prova que a tolerancia tem uma fronteira real, nao e
    # so "qualquer coisa pequena passa".
    anterior = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                             "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0, "publication_status": STATUS_PROVISIONAL}])
    no_limiar = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                              "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0 + 1e-6, "publication_status": STATUS_PROVISIONAL}])
    acima_do_limiar = pd.DataFrame([{"reference_period": pd.Timestamp("2024-06-01"), "preco_domestico_rs_t": 5000.0,
                                    "ppi_rs_t": 4000.0, "ipia_hrc_v2": 125.0 + 5e-6, "publication_status": STATUS_PROVISIONAL}])
    assert list(m.calcular_revised(no_limiar, anterior)) == [False]
    assert list(m.calcular_revised(acima_do_limiar, anterior)) == [True]


# --- salvar/carregar_vintage_ipia_hrc_v2 - primeira vintage ------------------

def test_primeira_vintage_completa(tmp_path):
    ppi = _ppi_df(_ppi_row("2023-12-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    pia = _pia_df(_pia_row("2023-12-01", preco=5000.0, is_provisional=False))
    serie, manifest = _salvar(ppi, pia, "20260101T000000Z", str(tmp_path))

    assert manifest["previous_vintage_id"] is None
    assert manifest["methodology_version"] == m.VERSAO_METODOLOGIA
    assert manifest["coverage"]["official_first_period"] == "2023-12-01"
    assert manifest["files"] == {"official": "official.csv", "provisional": "provisional.csv",
                                 "import_side": "import_side.csv", "domestic_price": "domestic_price.csv"}
    assert set(manifest["hashes"]) == set(manifest["files"])

    carregado = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=str(tmp_path))
    assert carregado["official"]["data_vintage"].iloc[0] == "20260101T000000Z"
    assert carregado["official"]["source_vintage_id"].iloc[0] == "20260101T000000Z"
    assert carregado["official"]["methodology_version"].iloc[0] == m.VERSAO_METODOLOGIA
    assert bool(carregado["official"]["revised"].iloc[0]) is False  # primeira vintage, nunca revisado
    assert len(carregado["import_side"]) == len(ppi)
    assert len(carregado["domestic_price"]) == len(pia)


def test_manifest_contem_campos_minimos(tmp_path):
    ppi = _ppi_df(_ppi_row("2023-12-01", status=STATUS_PUBLICATION_GRADE))
    pia = _pia_df(_pia_row("2023-12-01", is_provisional=False))
    _, manifest = _salvar(ppi, pia, "20260101T000000Z", str(tmp_path))
    for campo in ("vintage_id", "created_at_utc", "previous_vintage_id", "methodology_version",
                  "series", "coverage", "counts", "sources", "files", "hashes"):
        assert campo in manifest, f"campo minimo ausente do manifest: {campo}"
    for campo in ("official_first_period", "official_last_period",
                  "provisional_first_period", "provisional_last_period"):
        assert campo in manifest["coverage"]
    for campo in ("experimental", "publication_grade", "provisional", "unknown_complete_series"):
        assert campo in manifest["counts"]
    for campo in ("pia_last_observed_year", "pia_fetch_at_utc", "ipp_fetch_at_utc",
                  "comex_fetch_at_utc", "bcb_fetch_at_utc"):
        assert campo in manifest["sources"]


def test_sources_fetch_at_utc_e_repassado_ao_manifest(tmp_path):
    ppi = _ppi_df(_ppi_row("2023-12-01", status=STATUS_PUBLICATION_GRADE))
    pia = _pia_df(_pia_row("2023-12-01", is_provisional=False))
    fetch = {"pia_fetch_at_utc": "2026-08-27T10:00:00+00:00", "comex_fetch_at_utc": "2026-08-27T09:00:00+00:00"}
    _, manifest = _salvar(ppi, pia, "20260101T000000Z", str(tmp_path), sources_fetch_at_utc=fetch)
    assert manifest["sources"]["pia_fetch_at_utc"] == fetch["pia_fetch_at_utc"]
    assert manifest["sources"]["comex_fetch_at_utc"] == fetch["comex_fetch_at_utc"]
    assert manifest["sources"]["ipp_fetch_at_utc"] is None  # nao fornecido -> None, nunca inventado


# --- listar/ultima_vintage_ipia_hrc_v2 ---------------------------------------

def test_listar_e_ultima_vintage_ipia_hrc_v2(tmp_path):
    assert m.listar_vintages_ipia_hrc_v2(base_dir=str(tmp_path)) == []
    assert m.ultima_vintage_ipia_hrc_v2(base_dir=str(tmp_path)) is None

    ppi = _ppi_df(_ppi_row("2023-12-01", status=STATUS_PUBLICATION_GRADE))
    pia = _pia_df(_pia_row("2023-12-01", is_provisional=False))
    _salvar(ppi, pia, "20260101T000000Z", str(tmp_path))
    _salvar(ppi, pia, "20260201T000000Z", str(tmp_path))

    assert m.listar_vintages_ipia_hrc_v2(base_dir=str(tmp_path)) == ["20260101T000000Z", "20260201T000000Z"]
    assert m.ultima_vintage_ipia_hrc_v2(base_dir=str(tmp_path)) == "20260201T000000Z"


# --- fluxo normal: official anterior alimenta congelado_df -------------------

def test_official_anterior_e_carregado_como_congelado_no_fluxo_normal(tmp_path):
    ppi_v1 = _ppi_df(_ppi_row("2023-12-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    pia_v1 = _pia_df(_pia_row("2023-12-01", preco=5000.0, is_provisional=False))
    _, manifest_v1 = _salvar(ppi_v1, pia_v1, "20260101T000000Z", str(tmp_path))
    ipia_v1 = manifest_v1  # so pra clareza; valor real conferido abaixo via carregar

    ultima = m.ultima_vintage_ipia_hrc_v2(base_dir=str(tmp_path))
    assert ultima == "20260101T000000Z"
    vintage_anterior = m.carregar_vintage_ipia_hrc_v2(ultima, base_dir=str(tmp_path))

    # simula uma mudanca upstream (sem nova PIA) para o MESMO mes -
    # o fluxo normal (script) usa vintage_anterior["official"] como
    # congelado_df ao recalcular.
    ppi_v2 = _ppi_df(_ppi_row("2023-12-01", ppi=9999.0, status=STATUS_PUBLICATION_GRADE))
    pia_v2 = _pia_df(_pia_row("2023-12-01", preco=1234.0, is_provisional=False))
    serie_v2, manifest_v2 = _salvar(ppi_v2, pia_v2, "20260201T000000Z", str(tmp_path),
                                    vintage_anterior=vintage_anterior)

    linha = serie_v2.set_index("reference_period").loc["2023-12-01"]
    assert linha["ppi_rs_t"] == pytest.approx(3900.0)  # continua o valor CONGELADO, nao 9999.0
    assert linha["preco_domestico_rs_t"] == pytest.approx(5000.0)  # continua o valor CONGELADO, nao 1234.0
    assert manifest_v2["previous_vintage_id"] == "20260101T000000Z"

    carregado_v2 = m.carregar_vintage_ipia_hrc_v2("20260201T000000Z", base_dir=str(tmp_path))
    linha_v2 = carregado_v2["official"].set_index("reference_period").loc["2023-12-01"]
    assert bool(linha_v2["revised"]) is False  # congelado -> nao mudou -> nunca revisado


def test_provisional_pode_ganhar_novo_mes_entre_vintages(tmp_path):
    ppi_v1 = _ppi_df(_ppi_row("2024-01-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    pia_v1 = _pia_df(_pia_row("2024-01-01", preco=5000.0, pia_reference_year=2023, is_provisional=True))
    _, manifest_v1 = _salvar(ppi_v1, pia_v1, "20260101T000000Z", str(tmp_path))
    vintage_anterior = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=str(tmp_path))
    assert list(vintage_anterior["provisional"]["reference_period"]) == [pd.Timestamp("2024-01-01")]

    ppi_v2 = _ppi_df(_ppi_row("2024-01-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE),
                     _ppi_row("2024-02-01", ppi=3950.0, status=STATUS_PUBLICATION_GRADE))
    pia_v2 = _pia_df(_pia_row("2024-01-01", preco=5000.0, pia_reference_year=2023, is_provisional=True),
                     _pia_row("2024-02-01", preco=5050.0, pia_reference_year=2023, is_provisional=True))
    serie_v2, _ = _salvar(ppi_v2, pia_v2, "20260201T000000Z", str(tmp_path), vintage_anterior=vintage_anterior)

    carregado_v2 = m.carregar_vintage_ipia_hrc_v2("20260201T000000Z", base_dir=str(tmp_path))
    assert list(carregado_v2["provisional"]["reference_period"]) == [
        pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01")]
    linhas = carregado_v2["provisional"].set_index("reference_period")
    assert bool(linhas.loc["2024-01-01", "revised"]) is False  # ja existia, nao mudou
    assert bool(linhas.loc["2024-02-01", "revised"]) is False  # mes NOVO -> revised=False, nao True


def test_provisional_pode_mudar_de_valor_sem_alterar_a_vintage_anterior(tmp_path):
    # Vintage A: 2024-06 PROVISIONAL = X. Vintage B: MESMO mes, ainda
    # PROVISIONAL, mas valor Y != X (nenhuma promocao, so revisao normal
    # do provisional - nunca congelado). A vintage A precisa continuar
    # byte a byte identica.
    ppi_a = _ppi_df(_ppi_row("2024-06-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    pia_a = _pia_df(_pia_row("2024-06-01", preco=5000.0, pia_reference_year=2023, is_provisional=True))
    serie_a, _ = _salvar(ppi_a, pia_a, "20260101T000000Z", str(tmp_path))
    _, provisional_a = m.separar_ipia_hrc_v2_oficial_provisional(serie_a)
    valor_x = provisional_a.set_index("reference_period").loc["2024-06-01", "ipia_hrc_v2"]

    conteudo_provisional_a_antes = (tmp_path / "ipia_hrc_v2" / "20260101T000000Z" / "provisional.csv").read_bytes()
    conteudo_official_a_antes = (tmp_path / "ipia_hrc_v2" / "20260101T000000Z" / "official.csv").read_bytes()
    vintage_a = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=str(tmp_path))

    # mesmo mes, ainda provisional (pia_reference_year continua 2023 - nenhuma
    # nova PIA), so o VALOR mudou (ex.: IPP revisado).
    ppi_b = _ppi_df(_ppi_row("2024-06-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE))
    pia_b = _pia_df(_pia_row("2024-06-01", preco=5555.0, pia_reference_year=2023, is_provisional=True))
    serie_b, _ = _salvar(ppi_b, pia_b, "20260201T000000Z", str(tmp_path), vintage_anterior=vintage_a)
    _, provisional_b = m.separar_ipia_hrc_v2_oficial_provisional(serie_b)
    valor_y = provisional_b.set_index("reference_period").loc["2024-06-01", "ipia_hrc_v2"]

    assert valor_y != pytest.approx(valor_x)  # o valor realmente mudou (Y != X)

    carregado_b = m.carregar_vintage_ipia_hrc_v2("20260201T000000Z", base_dir=str(tmp_path))
    assert bool(carregado_b["provisional"].set_index("reference_period").loc["2024-06-01", "revised"]) is True
    assert carregado_b["provisional"].set_index("reference_period").loc["2024-06-01", "publication_status"] \
        == STATUS_PROVISIONAL  # continua provisional, nunca promovido nesta simulacao

    # vintage A NAO mudou - nem um byte.
    assert (tmp_path / "ipia_hrc_v2" / "20260101T000000Z" / "provisional.csv").read_bytes() \
        == conteudo_provisional_a_antes
    assert (tmp_path / "ipia_hrc_v2" / "20260101T000000Z" / "official.csv").read_bytes() \
        == conteudo_official_a_antes
    vintage_a_recarregada = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=str(tmp_path))
    assert vintage_a_recarregada["provisional"].set_index("reference_period").loc[
        "2024-06-01", "ipia_hrc_v2"] == pytest.approx(valor_x)


# --- promocao provisional -> official ----------------------------------------

def test_promocao_provisional_para_official_apos_nova_pia(tmp_path):
    # Vintage A: 2023-12 OFFICIAL, 2024-01..2024-03 PROVISIONAL.
    ppi_a = _ppi_df(
        _ppi_row("2023-12-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE),
        _ppi_row("2024-01-01", ppi=3950.0, status=STATUS_PUBLICATION_GRADE),
        _ppi_row("2024-02-01", ppi=3960.0, status=STATUS_EXPERIMENTAL),
        _ppi_row("2024-03-01", ppi=3970.0, status=STATUS_PUBLICATION_GRADE),
    )
    pia_a = _pia_df(
        _pia_row("2023-12-01", preco=5000.0, pia_reference_year=2023, is_provisional=False),
        _pia_row("2024-01-01", preco=5100.0, pia_reference_year=2023, is_provisional=True),
        _pia_row("2024-02-01", preco=5150.0, pia_reference_year=2023, is_provisional=True),
        _pia_row("2024-03-01", preco=5200.0, pia_reference_year=2023, is_provisional=True),
    )
    serie_a, manifest_a = _salvar(ppi_a, pia_a, "20260101T000000Z", str(tmp_path))
    oficial_a, provisional_a = m.separar_ipia_hrc_v2_oficial_provisional(serie_a)
    assert list(oficial_a["reference_period"]) == [pd.Timestamp("2023-12-01")]
    assert list(provisional_a["reference_period"]) == [
        pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01"), pd.Timestamp("2024-03-01")]

    vintage_a = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=str(tmp_path))
    conteudo_provisional_a_antes = (tmp_path / "ipia_hrc_v2" / "20260101T000000Z" / "provisional.csv").read_bytes()
    conteudo_official_a_antes = (tmp_path / "ipia_hrc_v2" / "20260101T000000Z" / "official.csv").read_bytes()

    # Nova PIA disponivel: 2024 inteiro passa a ser BENCHMARKED
    # (is_provisional=False, pia_reference_year=2024) - import side igual,
    # so o lado domestico mudou de provisional para benchmarked.
    ppi_b = ppi_a  # mesmo import side (2023-12..2024-03)
    pia_b = _pia_df(
        _pia_row("2023-12-01", preco=5000.0, pia_reference_year=2023, is_provisional=False),
        _pia_row("2024-01-01", preco=5300.0, pia_reference_year=2024, is_provisional=False),
        _pia_row("2024-02-01", preco=5350.0, pia_reference_year=2024, is_provisional=False),
        _pia_row("2024-03-01", preco=5400.0, pia_reference_year=2024, is_provisional=False),
    )
    serie_b, manifest_b = _salvar(ppi_b, pia_b, "20260201T000000Z", str(tmp_path), vintage_anterior=vintage_a)

    linha_dez = serie_b.set_index("reference_period").loc["2023-12-01"]
    assert linha_dez["preco_domestico_rs_t"] == pytest.approx(5000.0)  # continua EXATAMENTE igual ao congelado

    oficial_b, provisional_b = m.separar_ipia_hrc_v2_oficial_provisional(serie_b)
    assert set(oficial_b["reference_period"]) == {
        pd.Timestamp("2023-12-01"), pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-02-01"), pd.Timestamp("2024-03-01")}
    assert provisional_b.empty  # os 3 meses foram promovidos, nenhum continua provisional

    status_b = oficial_b.set_index("reference_period")["publication_status"]
    assert status_b.loc["2024-01-01"] == STATUS_PUBLICATION_GRADE  # import PUBLICATION_GRADE
    assert status_b.loc["2024-02-01"] == STATUS_EXPERIMENTAL       # import EXPERIMENTAL
    assert status_b.loc["2024-03-01"] == STATUS_PUBLICATION_GRADE

    carregado_b = m.carregar_vintage_ipia_hrc_v2("20260201T000000Z", base_dir=str(tmp_path))
    revised_b = carregado_b["official"].set_index("reference_period")["revised"]
    assert bool(revised_b.loc["2023-12-01"]) is False  # congelado, nunca revisado
    assert bool(revised_b.loc["2024-01-01"]) is True    # existia como provisional com outro status/valor -> revisado
    assert bool(revised_b.loc["2024-02-01"]) is True
    assert bool(revised_b.loc["2024-03-01"]) is True

    # a vintage A NAO MUDOU - nenhum byte diferente nos arquivos dela.
    assert (tmp_path / "ipia_hrc_v2" / "20260101T000000Z" / "provisional.csv").read_bytes() \
        == conteudo_provisional_a_antes
    assert (tmp_path / "ipia_hrc_v2" / "20260101T000000Z" / "official.csv").read_bytes() \
        == conteudo_official_a_antes
    vintage_a_recarregada = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=str(tmp_path))
    assert list(vintage_a_recarregada["provisional"]["reference_period"]) == [
        pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01"), pd.Timestamp("2024-03-01")]
    assert (vintage_a_recarregada["provisional"]["publication_status"] == STATUS_PROVISIONAL).all()


# --- reproducibility: recalcular a partir dos inputs persistidos ------------

def test_reproducao_a_partir_dos_inputs_processados_persistidos(tmp_path):
    ppi = _ppi_df(
        _ppi_row("2019-02-01", ppi=3107.39, status=STATUS_EXPERIMENTAL),
        _ppi_row("2023-12-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE),
        _ppi_row("2024-06-01", ppi=3950.0, status=STATUS_PUBLICATION_GRADE),
    )
    pia = _pia_df(
        _pia_row("2019-02-01", preco=2416.6, pia_reference_year=2019, is_provisional=False),
        _pia_row("2023-12-01", preco=5000.0, pia_reference_year=2023, is_provisional=False),
        _pia_row("2024-06-01", preco=5300.0, pia_reference_year=2023, is_provisional=True),
    )
    serie_original, manifest = _salvar(ppi, pia, "20260101T000000Z", str(tmp_path))
    oficial_original, provisional_original = m.separar_ipia_hrc_v2_oficial_provisional(serie_original)

    carregado = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=str(tmp_path))
    # reproduz o calculo usando SOMENTE os inputs processados persistidos -
    # nenhuma chamada de rede, nenhum fixture original reutilizado.
    serie_reproduzida = m.calcular_ipia_hrc_v2_pia(
        ppi_mensal_df=carregado["import_side"], pia_domestico_df=carregado["domestic_price"])
    oficial_reproduzida, provisional_reproduzida = m.separar_ipia_hrc_v2_oficial_provisional(serie_reproduzida)

    colunas_economicas = ["reference_period", "preco_domestico_rs_t", "ppi_rs_t", "ipia_hrc_v2",
                          "publication_status"]
    pd.testing.assert_frame_equal(
        oficial_original[colunas_economicas].reset_index(drop=True),
        oficial_reproduzida[colunas_economicas].reset_index(drop=True), check_exact=False, rtol=1e-9)
    pd.testing.assert_frame_equal(
        provisional_original[colunas_economicas].reset_index(drop=True),
        provisional_reproduzida[colunas_economicas].reset_index(drop=True), check_exact=False, rtol=1e-9)

    # tambem bate contra o que foi de fato PERSISTIDO em official.csv/provisional.csv
    # (nao so contra o objeto em memoria do proprio teste).
    pd.testing.assert_frame_equal(
        carregado["official"][colunas_economicas].reset_index(drop=True),
        oficial_reproduzida[colunas_economicas].reset_index(drop=True), check_exact=False, rtol=1e-9)
    pd.testing.assert_frame_equal(
        carregado["provisional"][colunas_economicas].reset_index(drop=True),
        provisional_reproduzida[colunas_economicas].reset_index(drop=True), check_exact=False, rtol=1e-9)
