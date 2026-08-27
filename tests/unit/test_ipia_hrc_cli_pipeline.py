"""Unit tests for the IPIA-HRC canonical publication pipeline and CLI
wiring (Stage G5): `executar_pipeline_ipia_hrc()`,
`imprimir_resumo_publicacao_ipia_hrc()`, and the `--ipia`/`--ipia-latest`
branches of `main()`. Deterministic, no network: `ppi_mensal_df`/
`pia_domestico_df` are injected (same pattern as the rest of the module);
`--ipia`/`--ipia-latest` CLI tests monkeypatch `sys.argv` and, where the
real pipeline would hit the network, monkeypatch
`indices_setoriais.executar_pipeline_ipia_hrc` itself.

Covers: --ipia routes to the PIA-based pipeline, never the corporate
benchmark or the legacy calcular_ipia_mensal path; CLI and
scripts/gerar_ipia_hrc_v2_pia.py share the same orchestration function;
one execution creates exactly one vintage; official/provisional stay
separate; EXPERIMENTAL/PUBLICATION_GRADE/PROVISIONAL remain labeled;
UNKNOWN never published; current value always presented as provisional;
legacy corporate remains callable but never the public path; a failure
before vintage finalization publishes nothing; a failure during vintage
persistence never presents LATEST as a successful publication; LATEST
always corresponds to the finalized vintage; publication metadata
survives; unrelated CLI flags keep working; the script uses the same
shared orchestration.
"""
import importlib.util
import os
import sys

import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.parameters.trade_policy import STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN

STATUS_PROVISIONAL = m.STATUS_PROVISIONAL

_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "gerar_ipia_hrc_v2_pia.py")


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


def _fixture_completo():
    """Um mes EXPERIMENTAL, um PUBLICATION_GRADE, um PROVISIONAL - cobre
    os tres status publicaveis numa unica execucao de teste."""
    ppi = _ppi_df(
        _ppi_row("2019-06-01", ppi=3900.0, status=STATUS_EXPERIMENTAL),
        _ppi_row("2023-06-01", ppi=3900.0, status=STATUS_PUBLICATION_GRADE),
        _ppi_row("2024-06-01", ppi=3950.0, status=STATUS_PUBLICATION_GRADE),
    )
    dom = _pia_df(
        _pia_row("2019-06-01", preco=5000.0, pia_reference_year=2019, is_provisional=False),
        _pia_row("2023-06-01", preco=5100.0, pia_reference_year=2023, is_provisional=False),
        _pia_row("2024-06-01", preco=5150.0, pia_reference_year=2023, is_provisional=True),
    )
    return ppi, dom


def _importar_script():
    spec = importlib.util.spec_from_file_location("gerar_ipia_hrc_v2_pia_teste", _SCRIPT_PATH)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["gerar_ipia_hrc_v2_pia_teste"] = modulo
    spec.loader.exec_module(modulo)  # so define funcoes - o bloco __main__ nao roda ao importar
    return modulo


# --- 1/9. Pipeline: PIA-based, nunca corporate/legado; UNKNOWN nunca publicado

def test_pipeline_calcula_via_pia_based_nunca_corporate_ou_legado(monkeypatch, tmp_path):
    def _explode(*a, **kw):
        raise AssertionError("caminho legado/corporate nao deveria ser chamado pelo pipeline IPIA-HRC")
    monkeypatch.setattr(m, "calcular_ipia_mensal", _explode)
    monkeypatch.setattr(m, "calcular_serie_ipia_hrc_v2", _explode)
    monkeypatch.setattr(m, "preco_domestico_hrc_mensal_v2", _explode)

    ppi, dom = _fixture_completo()
    resultado = m.executar_pipeline_ipia_hrc(
        base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")
    assert resultado["manifest"]["vintage_id"] == "20260101T000000Z"


def test_unknown_nunca_aparece_em_oficial_nem_provisional(tmp_path):
    ppi = _ppi_df(_ppi_row("2020-01-01", ppi=float("nan"), status=STATUS_UNKNOWN))
    dom = _pia_df(_pia_row("2020-01-01", preco=5000.0, is_provisional=False))
    resultado = m.executar_pipeline_ipia_hrc(
        base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")
    assert not (resultado["oficial"]["publication_status"] == STATUS_UNKNOWN).any()
    assert not (resultado["provisional"]["publication_status"] == STATUS_UNKNOWN).any()
    assert resultado["oficial"].empty and resultado["provisional"].empty  # unico mes do fixture e UNKNOWN


# --- 2/16. Orquestracao canonica compartilhada entre CLI e script --------

def test_script_usa_a_mesma_orquestracao_canonica(monkeypatch, capsys, tmp_path):
    # o script deve chamar exatamente a MESMA `executar_pipeline_ipia_hrc`
    # que a CLI usa - a prova real e contar chamadas envolvendo a funcao
    # verdadeira (sem rede, dado injetado), nao uma fake com estrutura
    # de retorno inventada a mao (que divergiria silenciosamente do
    # contrato real - data_vintage/source_vintage_id/revised etc, so
    # preenchidos por `salvar_vintage_ipia_hrc_v2` de verdade).
    modulo_script = _importar_script()
    chamadas = {"n": 0}
    original = m.executar_pipeline_ipia_hrc

    def _pipeline_contado(*a, **kw):
        chamadas["n"] += 1
        ppi, dom = _fixture_completo()
        return original(base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
                        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")

    monkeypatch.setattr(m, "executar_pipeline_ipia_hrc", _pipeline_contado)
    monkeypatch.setattr(m, "ultima_vintage_ipia_hrc_v2", lambda base_dir=None: None)
    monkeypatch.setattr(modulo_script, "gerar_grafico_validacao", lambda *a, **kw: None)  # sem matplotlib no teste
    monkeypatch.setattr(m, "calcular_serie_ipia_hrc_v2",
                        lambda **kw: pd.DataFrame(columns=["reference_period", "ipia_hrc_v2"]))

    modulo_script.main()
    assert chamadas["n"] == 1
    saida = capsys.readouterr().out
    assert "VINTAGE" in saida


# --- 3. Uma execucao cria no maximo uma vintage -----------------------------

def test_uma_execucao_cria_apenas_uma_vintage(monkeypatch, tmp_path):
    chamadas = {"n": 0}
    original = m.vintage_store.criar_vintage

    def _contando(*a, **kw):
        chamadas["n"] += 1
        return original(*a, **kw)

    monkeypatch.setattr(m.vintage_store, "criar_vintage", _contando)
    ppi, dom = _fixture_completo()
    m.executar_pipeline_ipia_hrc(
        base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")
    assert chamadas["n"] == 1


# --- 4/5/6/7. Official/provisional separados; status permanecem rotulados --

def test_official_provisional_separados_e_status_rotulados(tmp_path):
    ppi, dom = _fixture_completo()
    resultado = m.executar_pipeline_ipia_hrc(
        base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")
    oficial, provisional = resultado["oficial"], resultado["provisional"]
    assert set(oficial["publication_status"]) == {STATUS_EXPERIMENTAL, STATUS_PUBLICATION_GRADE}
    assert set(provisional["publication_status"]) == {STATUS_PROVISIONAL}
    assert not (oficial["publication_status"] == STATUS_PROVISIONAL).any()
    assert not (provisional["publication_status"].isin([STATUS_EXPERIMENTAL, STATUS_PUBLICATION_GRADE])).any()


# --- 8. Valor corrente sempre apresentado como provisional ------------------

def test_resumo_apresenta_valor_corrente_como_provisorio(tmp_path, capsys):
    ppi, dom = _fixture_completo()
    resultado = m.executar_pipeline_ipia_hrc(
        base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")
    m.imprimir_resumo_publicacao_ipia_hrc(resultado["manifest"], resultado["oficial"], resultado["provisional"])
    saida = capsys.readouterr().out
    assert "IPIA-HRC Provisorio" in saida
    assert "nao e definitivo" in saida
    assert "126.74" not in saida  # sanity: nao vazou nenhum valor hardcoded de outra execucao


# --- 10. Legado/corporate continua chamavel, mas nao e o caminho publico ---

def test_legado_corporate_continua_chamavel_diretamente_mas_nao_e_usado_por_ipia(monkeypatch, tmp_path):
    # chamavel diretamente:
    assert callable(m.calcular_serie_ipia_hrc_v2)
    assert callable(m.calcular_ipia_mensal)
    # mas o pipeline (o caminho publico de --ipia) nunca os chama:
    monkeypatch.setattr(m, "calcular_serie_ipia_hrc_v2",
                        lambda **kw: (_ for _ in ()).throw(AssertionError("nao deveria ser chamado")))
    monkeypatch.setattr(m, "calcular_ipia_mensal",
                        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("nao deveria ser chamado")))
    ppi, dom = _fixture_completo()
    m.executar_pipeline_ipia_hrc(
        base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")  # nao deve levantar


# --- 11. Falha antes da finalizacao da vintage nao publica nada -------------

def test_falha_antes_da_vintage_nao_publica_nada(monkeypatch, tmp_path):
    def _falha(*a, **kw):
        raise RuntimeError("falha simulada na persistencia da vintage")
    monkeypatch.setattr(m, "salvar_vintage_ipia_hrc_v2", _falha)

    ppi, dom = _fixture_completo()
    base_dir = str(tmp_path / "vintages")
    output_dir = str(tmp_path / "processed")
    with pytest.raises(RuntimeError, match="falha simulada"):
        m.executar_pipeline_ipia_hrc(base_dir=base_dir, output_dir=output_dir,
                                     ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")

    assert m.listar_vintages_ipia_hrc_v2(base_dir=base_dir) == []
    assert not os.path.exists(f"{output_dir}/ipia_hrc_v2_official.csv")
    assert not os.path.exists(f"{output_dir}/ipia_hrc_v2_provisional.csv")


# --- 12. Falha na persistencia nao aparenta sucesso via CLI -----------------

def test_cli_ipia_falha_com_saida_nao_zero_e_nao_finge_sucesso(monkeypatch, capsys):
    def _falha(*a, **kw):
        raise RuntimeError("falha simulada de rede")
    monkeypatch.setattr(m, "executar_pipeline_ipia_hrc", _falha)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--ipia"])

    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code != 0
    saida = capsys.readouterr().out
    assert "Falha ao publicar" in saida
    assert "nenhuma vintage nova foi criada" in saida.lower() or "nenhuma vintage" in saida.lower()


# --- 13. LATEST corresponde exatamente a vintage finalizada -----------------

def test_latest_corresponde_a_vintage_finalizada(tmp_path):
    ppi, dom = _fixture_completo()
    base_dir = str(tmp_path / "vintages")
    output_dir = str(tmp_path / "processed")
    resultado = m.executar_pipeline_ipia_hrc(base_dir=base_dir, output_dir=output_dir,
                                             ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")

    vintage_persistida = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=base_dir)
    # mesmas colunas de texto que carregar_vintage_ipia_hrc_v2 ja forca de
    # volta a string (senao "1.2" round-tripa como float via pd.read_csv,
    # ver _COLS_VINTAGE_TEXTO) - sem isso a comparacao falha por um motivo
    # que nao tem nada a ver com o invariante que este teste prova.
    dtype_texto = {c: str for c in m._COLS_VINTAGE_TEXTO}
    latest_oficial = pd.read_csv(resultado["csv_oficial"], parse_dates=["reference_period"], dtype=dtype_texto)
    latest_provisional = pd.read_csv(resultado["csv_provisional"], parse_dates=["reference_period"], dtype=dtype_texto)

    pd.testing.assert_frame_equal(
        latest_oficial.reset_index(drop=True),
        vintage_persistida["official"].reset_index(drop=True), check_dtype=False)
    pd.testing.assert_frame_equal(
        latest_provisional.reset_index(drop=True),
        vintage_persistida["provisional"].reset_index(drop=True), check_dtype=False)


# --- 14. Metadados de publicacao sobrevivem --------------------------------

def test_metadados_de_publicacao_sobrevivem(tmp_path):
    ppi, dom = _fixture_completo()
    resultado = m.executar_pipeline_ipia_hrc(
        base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")
    for coluna in ("reference_period", "publication_status", "data_vintage", "source_vintage_id",
                  "methodology_version", "revised", "preco_domestico_rs_t", "ppi_rs_t", "ipia_hrc_v2"):
        assert coluna in resultado["oficial"].columns, f"coluna ausente em oficial: {coluna}"
    assert (resultado["oficial"]["data_vintage"] == "20260101T000000Z").all()
    assert (resultado["oficial"]["methodology_version"] == m.VERSAO_METODOLOGIA).all()


# --- 15. Flags de CLI nao relacionados ao IPIA continuam funcionando -------

def test_flag_spec_nao_relacionado_ao_ipia_continua_funcionando(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--spec"])
    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code == 0
    saida = capsys.readouterr().out
    assert "ICCS" in saida


# --- --ipia-latest: caminho de leitura, sem rede, sem criar vintage nova ---

def test_ipia_latest_sem_vintage_falha_com_mensagem_clara(monkeypatch, capsys):
    monkeypatch.setattr(m, "ultima_vintage_ipia_hrc_v2", lambda base_dir=None: None)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--ipia-latest"])
    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code != 0
    saida = capsys.readouterr().out
    assert "Nenhuma vintage" in saida


def test_ipia_latest_com_vintage_imprime_resumo_sem_criar_vintage_nova(monkeypatch, capsys, tmp_path):
    ppi, dom = _fixture_completo()
    m.executar_pipeline_ipia_hrc(
        base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")
    vintage_carregada = m.carregar_vintage_ipia_hrc_v2("20260101T000000Z", base_dir=str(tmp_path / "vintages"))

    chamadas_criar = {"n": 0}
    original_criar = m.vintage_store.criar_vintage

    def _contando(*a, **kw):
        chamadas_criar["n"] += 1
        return original_criar(*a, **kw)

    monkeypatch.setattr(m.vintage_store, "criar_vintage", _contando)
    monkeypatch.setattr(m, "ultima_vintage_ipia_hrc_v2", lambda base_dir=None: "20260101T000000Z")
    monkeypatch.setattr(m, "carregar_vintage_ipia_hrc_v2", lambda vid, base_dir=None: vintage_carregada)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--ipia-latest"])

    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code == 0
    assert chamadas_criar["n"] == 0  # caminho de leitura nunca cria vintage
    saida = capsys.readouterr().out
    assert "IPIA-HRC Provisorio" in saida
    assert "nao e definitivo" in saida


# --- --ano-ini/--ano-fim: aviso so quando diferente do default -------------

def _redireciona_pipeline_para_tmp(monkeypatch, tmp_path):
    """Garante que uma chamada real a --ipia dentro do teste nunca escreve
    em data/processed/ real - redireciona para tmp_path com dado injetado."""
    original = m.executar_pipeline_ipia_hrc
    ppi, dom = _fixture_completo()

    def _redirecionada(*a, **kw):
        return original(base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
                        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")

    monkeypatch.setattr(m, "executar_pipeline_ipia_hrc", _redirecionada)


def test_ano_ini_fim_diferente_do_default_gera_aviso_mas_nao_impede_publicacao(monkeypatch, capsys, tmp_path):
    _redireciona_pipeline_para_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--ipia", "--ano-ini", "1999", "--ano-fim", "2001"])
    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code == 0
    saida = capsys.readouterr().out
    assert "ignorados" in saida.lower()
    assert "IPIA-HRC Provisorio" in saida  # a publicacao aconteceu normalmente


def test_ano_ini_fim_default_nao_gera_aviso(monkeypatch, capsys, tmp_path):
    _redireciona_pipeline_para_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--ipia"])
    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code == 0
    saida = capsys.readouterr().out
    assert "ignorados" not in saida.lower()
