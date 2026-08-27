"""Unit tests for the IPIA-HRC V2 PDF report (Stage G6):
`preparar_dados_relatorio_ipia_hrc`/`gerar_relatorio_ipia_hrc`
(`reporting/report_builder.py`), the status/disclosure constants and
helper functions in `reporting/pages.py`, and the `--pdf-ipia` branch of
`main()`. Deterministic, no network: vintages are built via
`executar_pipeline_ipia_hrc` with injected `ppi_mensal_df`/
`pia_domestico_df` (same fixture pattern as
`test_ipia_hrc_cli_pipeline.py`), never a real Comex/IBGE/BCB call.

Covers (Stage G6 task section 21): loads latest vintage; no network
calls; no new vintage created; clear failure with no vintage (no legacy
fallback); current value sourced from PROVISIONAL (falls back to
OFFICIAL labeled historical); provisional wording; official/provisional
separation survives into the report data; EXPERIMENTAL/PUBLICATION_GRADE/
PROVISIONAL visually distinguishable (distinct colors); UNKNOWN never
plotted as observed (calendar reindex leaves real gaps); domestic
methodology disclosure is PIA-based, not the corporate benchmark;
corporate benchmark never labeled as the canonical domestic price;
report data comes from the vintage's own import_side/domestic_price
snapshots (identity, never recollected); vintage_id/methodology_version/
last_pia_year present in report data; low-liquidity disclosure present
with the exact approved text and no threshold/percentile/volume-cutoff
language; parity=100 values are never rebased; legacy auxiliary metrics
(country origin, Aço Brasil) are not touched by the V2 path; unrelated
CLI flags keep working; report reproducibility (same vintage -> same
report data on repeated generation).
"""
import os
import sys

import pandas as pd
import pytest

import indices_setoriais as m
from reporting import pages
from reporting.report_builder import gerar_relatorio_ipia_hrc, preparar_dados_relatorio_ipia_hrc
from steel_indicator.parameters.trade_policy import STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL

from test_ipia_hrc_cli_pipeline import _fixture_completo


def _vintage_real(tmp_path, vintage_id="20260101T000000Z"):
    """Publica uma vintage de verdade (pipeline real, dado injetado) e a
    recarrega via `carregar_vintage_ipia_hrc_v2` - garante que os testes
    usam exatamente o mesmo contrato de vintage que a producao usa, nunca
    um dict inventado a mao."""
    ppi, dom = _fixture_completo()
    base_dir = str(tmp_path / "vintages")
    m.executar_pipeline_ipia_hrc(base_dir=base_dir, output_dir=str(tmp_path / "processed"),
                                 ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id=vintage_id)
    return m.carregar_vintage_ipia_hrc_v2(vintage_id, base_dir=base_dir)


# --- 1/13. Relatorio usa exatamente os snapshots persistidos na vintage ----

def test_dados_do_relatorio_vem_dos_snapshots_da_propria_vintage(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados = preparar_dados_relatorio_ipia_hrc(vintage)
    pd.testing.assert_frame_equal(dados["import_side"], vintage["import_side"])
    pd.testing.assert_frame_equal(dados["domestic_price"], vintage["domestic_price"])


# --- 2. Sem chamada de rede -------------------------------------------------

def test_gerar_relatorio_nao_faz_nenhuma_chamada_de_rede(tmp_path, monkeypatch):
    import requests
    def _explode(*a, **kw):
        raise AssertionError("gerar_relatorio_ipia_hrc nao deveria fazer nenhuma chamada de rede")
    monkeypatch.setattr(requests, "get", _explode)
    monkeypatch.setattr(requests, "post", _explode)

    vintage = _vintage_real(tmp_path)
    caminho = str(tmp_path / "relatorio.pdf")
    resultado = gerar_relatorio_ipia_hrc(caminho, vintage)
    assert resultado["n_paginas"] == 4
    assert os.path.exists(caminho)


# --- 3. Nenhuma vintage nova e criada ---------------------------------------

def test_gerar_relatorio_nao_cria_vintage_nova(tmp_path, monkeypatch):
    vintage = _vintage_real(tmp_path)
    chamadas = {"n": 0}
    original = m.vintage_store.criar_vintage

    def _contando(*a, **kw):
        chamadas["n"] += 1
        return original(*a, **kw)

    monkeypatch.setattr(m.vintage_store, "criar_vintage", _contando)
    gerar_relatorio_ipia_hrc(str(tmp_path / "relatorio.pdf"), vintage)
    assert chamadas["n"] == 0


# --- 4. Sem vintage -> ValueError explicito, nunca fallback para o legado --

def test_gerar_relatorio_sem_vintage_falha_explicito():
    with pytest.raises(ValueError, match="ja carregada"):
        gerar_relatorio_ipia_hrc("qualquer.pdf", None)
    with pytest.raises(ValueError, match="ja carregada"):
        gerar_relatorio_ipia_hrc("qualquer.pdf", {})


def test_cli_pdf_ipia_sem_vintage_falha_com_saida_nao_zero_sem_fallback(monkeypatch, capsys):
    monkeypatch.setattr(m, "ultima_vintage_ipia_hrc_v2", lambda base_dir=None: None)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--pdf-ipia"])
    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code != 0
    saida = capsys.readouterr().out
    assert "Nenhuma vintage" in saida
    assert "--ipia" in saida
    assert "relatorio_ipia" not in saida.lower()  # nao menciona o caminho legado


# --- 5/6. Valor corrente: PROVISIONAL sempre que existir; nunca "corrente" p/ OFFICIAL --

def test_valor_corrente_usa_ultimo_provisional_com_rotulo_provisorio(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados = preparar_dados_relatorio_ipia_hrc(vintage)
    rotulo, periodo, valor, e_provisorio = pages._valor_corrente_ipia_hrc(dados)
    assert e_provisorio is True
    assert "Provisório" in rotulo
    assert valor == dados["ultimo_provisional"]["ipia_hrc_v2"]


def test_valor_corrente_sem_provisional_cai_para_oficial_rotulado_historico():
    dados = {
        "ultimo_provisional": None,
        "ultimo_oficial": pd.Series({"reference_period": pd.Timestamp("2023-06-01"), "ipia_hrc_v2": 111.0}),
    }
    rotulo, periodo, valor, e_provisorio = pages._valor_corrente_ipia_hrc(dados)
    assert e_provisorio is False
    assert "corrente" not in rotulo.lower()
    assert "provis" not in rotulo.lower()
    assert "histórico" in rotulo.lower() or "historico" in rotulo.lower()


# --- 7. Separacao oficial/provisional sobrevive na camada de relatorio -----

def test_oficial_e_provisional_permanecem_separados_nos_dados_do_relatorio(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados = preparar_dados_relatorio_ipia_hrc(vintage)
    assert not dados["oficial"].empty and not dados["provisional"].empty
    assert set(dados["oficial"]["publication_status"]) == {STATUS_EXPERIMENTAL, STATUS_PUBLICATION_GRADE}
    assert set(dados["provisional"]["publication_status"]) == {m.STATUS_PROVISIONAL}
    assert len(dados["combinada"]) == len(dados["oficial"]) + len(dados["provisional"])


# --- 8/9. EXPERIMENTAL e PUBLICATION_GRADE tem cores distintas -------------

def test_publication_grade_e_experimental_tem_cores_visualmente_distintas():
    cor_pg = pages._CORES_STATUS_HRC[pages.STATUS_PUBLICATION_GRADE_HRC]
    cor_exp = pages._CORES_STATUS_HRC[pages.STATUS_EXPERIMENTAL_HRC]
    assert cor_pg != cor_exp
    assert cor_pg != pages._COR_PROVISIONAL_HRC
    assert cor_exp != pages._COR_PROVISIONAL_HRC


# --- 10. UNKNOWN nunca plotado como observado (gap real no calendario) -----

def test_reindexar_calendario_deixa_gap_real_para_mes_ausente():
    referencia = pd.Series(pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01"]))
    serie = pd.Series([100.0, 102.0], index=pd.to_datetime(["2023-01-01", "2023-03-01"]))
    reindexada = pages._reindexar_calendario(serie, referencia)
    assert len(reindexada) == 3
    assert pd.isna(reindexada.loc[pd.Timestamp("2023-02-01")])  # mes ausente vira NaN, nunca interpolado
    assert reindexada.loc[pd.Timestamp("2023-01-01")] == 100.0
    assert reindexada.loc[pd.Timestamp("2023-03-01")] == 102.0


# --- 11/12. Preco domestico e PIA-based; benchmark corporativo so validacao -

def test_disclosure_domestico_e_pia_based_nao_corporativo():
    assert "PIA-Produto" in pages._DISCLOSURE_PROXY_DOMESTICO
    assert "IPP 242" in pages._DISCLOSURE_PROXY_DOMESTICO
    assert "Usiminas" not in pages._DISCLOSURE_PROXY_DOMESTICO
    assert "CSN" not in pages._DISCLOSURE_PROXY_DOMESTICO


def test_pagina_4_fonte_do_modulo_nunca_rotula_corporativo_como_oficial():
    import inspect
    fonte = inspect.getsource(pages.pagina_mercado_metodologia_ipia_hrc)
    assert "Preço doméstico oficial" not in fonte
    assert "validação" in fonte.lower()


# --- 14/15/16. Metadados de vintage aparecem nos dados do relatorio --------

def test_metadados_de_vintage_presentes_nos_dados_do_relatorio(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados = preparar_dados_relatorio_ipia_hrc(vintage)
    assert dados["vintage_id"] == vintage["manifest"]["vintage_id"] == "20260101T000000Z"
    assert dados["methodology_version"] == vintage["manifest"]["methodology_version"]
    assert dados["created_at_utc"] == vintage["manifest"]["created_at_utc"]
    assert "last_pia_year" in dados  # pode ser None se o manifest nao tiver o campo, mas a chave existe


# --- 17. Disclosure de baixa liquidez: texto exato aprovado, sem threshold -

def test_disclosure_baixa_liquidez_texto_exato_sem_threshold():
    texto_aprovado = ("Meses com menor volume importado podem apresentar maior sensibilidade à "
                      "composição das operações observadas. O IPIA-HRC preserva os valores "
                      "observados e não aplica suavização ou exclusão automática baseada em volume.")
    assert pages._DISCLOSURE_BAIXA_LIQUIDEZ == texto_aprovado
    for termo_proibido in ("threshold", "percentil", "corte de volume", "liquidity_status"):
        assert termo_proibido not in pages._DISCLOSURE_BAIXA_LIQUIDEZ.lower()


# --- 18. Parity = 100 nunca normalizado/rebaseado ---------------------------

def test_parity_100_nunca_e_rebaseado_nos_dados_do_relatorio(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados = preparar_dados_relatorio_ipia_hrc(vintage)
    esperado = pd.concat([vintage["official"], vintage["provisional"]], ignore_index=True) \
        .sort_values("reference_period").reset_index(drop=True)["ipia_hrc_v2"]
    pd.testing.assert_series_equal(dados["combinada"]["ipia_hrc_v2"].reset_index(drop=True),
                                    esperado.reset_index(drop=True), check_names=False)


# --- 19. Remocao de metricas legadas auxiliares nao quebra caminhos alheios -

def test_pdf_ipia_nao_chama_indicadores_de_origem_legados(tmp_path, monkeypatch):
    def _explode(*a, **kw):
        raise AssertionError("relatorio V2 nao deveria chamar indicadores de origem/pais legados")
    monkeypatch.setattr(m, "origem_importacao_bobina_por_pais", _explode)
    vintage = _vintage_real(tmp_path)
    gerar_relatorio_ipia_hrc(str(tmp_path / "relatorio.pdf"), vintage)  # nao deve levantar


def test_flag_ipia_latest_nao_relacionada_a_pdf_continua_funcionando(monkeypatch, capsys, tmp_path):
    vintage_id = "20260101T000000Z"
    vintage = _vintage_real(tmp_path, vintage_id)
    monkeypatch.setattr(m, "ultima_vintage_ipia_hrc_v2", lambda base_dir=None: vintage_id)
    monkeypatch.setattr(m, "carregar_vintage_ipia_hrc_v2", lambda vid, base_dir=None: vintage)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--ipia-latest"])
    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code == 0


# --- CLI --pdf-ipia: usa a vintage mais recente, sem rede, sem vintage nova -

def test_cli_pdf_ipia_usa_vintage_mais_recente_e_imprime_vintage_e_caminho(monkeypatch, capsys, tmp_path):
    vintage_id = "20260101T000000Z"
    vintage = _vintage_real(tmp_path, vintage_id)

    chamadas_pipeline = {"n": 0}

    def _pipeline_nao_deveria_ser_chamado(*a, **kw):
        chamadas_pipeline["n"] += 1
        raise AssertionError("--pdf-ipia nunca deveria criar/recalcular uma vintage nova")

    monkeypatch.setattr(m, "ultima_vintage_ipia_hrc_v2", lambda base_dir=None: vintage_id)
    monkeypatch.setattr(m, "carregar_vintage_ipia_hrc_v2", lambda vid, base_dir=None: vintage)
    monkeypatch.setattr(m, "executar_pipeline_ipia_hrc", _pipeline_nao_deveria_ser_chamado)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--pdf-ipia"])

    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code == 0
    assert chamadas_pipeline["n"] == 0
    saida = capsys.readouterr().out
    assert vintage_id in saida
    assert os.path.join("data", "processed", "ipia_relatorio.pdf") in saida.replace("/", os.sep) \
        or "ipia_relatorio.pdf" in saida
    assert os.path.exists(os.path.join("data", "processed", "ipia_relatorio.pdf"))


def test_cli_pdf_ipia_ano_ini_fim_diferente_do_default_gera_aviso(monkeypatch, capsys, tmp_path):
    vintage_id = "20260101T000000Z"
    vintage = _vintage_real(tmp_path, vintage_id)
    monkeypatch.setattr(m, "ultima_vintage_ipia_hrc_v2", lambda base_dir=None: vintage_id)
    monkeypatch.setattr(m, "carregar_vintage_ipia_hrc_v2", lambda vid, base_dir=None: vintage)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv",
                        ["indices_setoriais.py", "--pdf-ipia", "--ano-ini", "1999", "--ano-fim", "2001"])
    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code == 0
    saida = capsys.readouterr().out
    assert "ignorados" in saida.lower()


# --- 20. --ipia continua funcionando sem alteracao de comportamento --------

def test_flag_ipia_continua_funcionando_sem_alteracao(monkeypatch, capsys, tmp_path):
    ppi, dom = _fixture_completo()
    original = m.executar_pipeline_ipia_hrc

    def _para_tmp(*a, **kw):
        return original(base_dir=str(tmp_path / "vintages"), output_dir=str(tmp_path / "processed"),
                        ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id="20260101T000000Z")

    monkeypatch.setattr(m, "executar_pipeline_ipia_hrc", _para_tmp)
    monkeypatch.setattr(sys, "argv", ["indices_setoriais.py", "--ipia"])
    with pytest.raises(SystemExit) as exc_info:
        m.main()
    assert exc_info.value.code == 0
    saida = capsys.readouterr().out
    assert "IPIA-HRC Provisorio" in saida


# --- Reprodutibilidade: mesma vintage -> mesmo conteudo semantico ----------

def test_relatorio_e_reproduzivel_para_a_mesma_vintage(tmp_path):
    vintage = _vintage_real(tmp_path)
    dados_1 = preparar_dados_relatorio_ipia_hrc(vintage)
    dados_2 = preparar_dados_relatorio_ipia_hrc(vintage)
    pd.testing.assert_frame_equal(dados_1["combinada"], dados_2["combinada"])
    assert dados_1["vintage_id"] == dados_2["vintage_id"]
    assert dados_1["contagem_status"] == dados_2["contagem_status"]

    caminho_1 = str(tmp_path / "r1.pdf")
    caminho_2 = str(tmp_path / "r2.pdf")
    gerar_relatorio_ipia_hrc(caminho_1, vintage)
    gerar_relatorio_ipia_hrc(caminho_2, vintage)
    assert os.path.getsize(caminho_1) > 0
    assert os.path.getsize(caminho_2) > 0
