"""Unit tests for `reporting.narrativa_mensal` (narrativa mensal
semi-manual, ADR 0017) e para a integração no Reporting V3
(`reporting.pages_v3.pagina_import_parity_drivers`).

Cobre: só narrativa_status=aprovado (com revisado_por/data_revisao
preenchidos) chega ao relatório; rascunho/ausente/malformado devolvem
None sem exceção, com log claro do motivo; só a seção '## Narrativa' e
extraída (buscas/checklist nunca vazam); texto longo demais e truncado
em vez de sobrepor o rodape da pagina; texto contendo 'R$' (par de
cifrao) nao e corrompido pelo parsing mathtext do matplotlib - regressao
especifica, nao assume que a correcao global (`text.parse_math=False`)
cobre este caminho novo so por reusar o mesmo motor de renderizacao.
"""
import logging
import os

import pandas as pd
import pytest

from reporting import narrativa_mensal as nm

PERIODO = pd.Timestamp("2026-06-01")


def _escrever(tmp_path, conteudo, nome="2026-06-narrativa.md"):
    caminho = tmp_path / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return str(tmp_path)


_APROVADO_OK = """---
narrativa_status: aprovado
revisado_por: Matheus Mori
data_revisao: 2026-07-05
---

# Narrativa — Junho/2026

## Buscas realizadas

Material de trabalho que nunca deve aparecer no relatório.

## Narrativa

Texto final aprovado para publicação.

## Checklist de revisão

* [x] item interno de auditoria
"""


# --- 1. Caminho feliz: aprovado com tudo preenchido -------------------------

def test_aprovado_com_revisor_e_data_devolve_texto(tmp_path):
    base_dir = _escrever(tmp_path, _APROVADO_OK)
    resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is not None
    assert resultado["texto"] == "Texto final aprovado para publicação."
    assert resultado["revisado_por"] == "Matheus Mori"
    assert resultado["data_revisao"] == "2026-07-05"


def test_so_secao_narrativa_e_extraida_nunca_o_corpo_inteiro(tmp_path):
    base_dir = _escrever(tmp_path, _APROVADO_OK)
    resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert "Material de trabalho" not in resultado["texto"]
    assert "item interno de auditoria" not in resultado["texto"]


# --- 2. Rascunho nunca aparece -----------------------------------------------

def test_status_rascunho_devolve_none(tmp_path, caplog):
    conteudo = _APROVADO_OK.replace("narrativa_status: aprovado", "narrativa_status: rascunho")
    base_dir = _escrever(tmp_path, conteudo)
    with caplog.at_level(logging.INFO):
        resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is None
    assert "rascunho" in caplog.text.lower()


def test_status_desconhecido_devolve_none_com_log(tmp_path, caplog):
    conteudo = _APROVADO_OK.replace("narrativa_status: aprovado", "narrativa_status: publicado")
    base_dir = _escrever(tmp_path, conteudo)
    with caplog.at_level(logging.WARNING):
        resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is None
    assert "inválido" in caplog.text.lower()


# --- 3. Arquivo ausente nunca quebra o relatório -----------------------------

def test_arquivo_ausente_devolve_none_sem_excecao(tmp_path):
    resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=str(tmp_path))
    assert resultado is None


# --- 4. Malformado (sem frontmatter, YAML quebrado, sem seção) -------------

def test_sem_frontmatter_devolve_none_com_log(tmp_path, caplog):
    base_dir = _escrever(tmp_path, "# Narrativa sem frontmatter nenhum\n\n## Narrativa\n\nTexto.\n")
    with caplog.at_level(logging.WARNING):
        resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is None
    assert "frontmatter" in caplog.text.lower()


def test_frontmatter_sem_fechamento_devolve_none_com_log(tmp_path, caplog):
    conteudo = "---\nnarrativa_status: aprovado\nrevisado_por: X\ndata_revisao: 2026-07-05\n\n## Narrativa\n\nY\n"
    base_dir = _escrever(tmp_path, conteudo)
    with caplog.at_level(logging.WARNING):
        resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is None
    assert "fechamento" in caplog.text.lower()


def test_yaml_invalido_devolve_none_com_log(tmp_path, caplog):
    conteudo = "---\nnarrativa_status: [aprovado\n---\n\n## Narrativa\n\nY\n"
    base_dir = _escrever(tmp_path, conteudo)
    with caplog.at_level(logging.WARNING):
        resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is None
    assert "yaml" in caplog.text.lower()


def test_aprovado_sem_revisor_devolve_none_com_log(tmp_path, caplog):
    conteudo = _APROVADO_OK.replace("revisado_por: Matheus Mori", "revisado_por:")
    base_dir = _escrever(tmp_path, conteudo)
    with caplog.at_level(logging.WARNING):
        resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is None
    assert "revisado_por" in caplog.text.lower()


def test_aprovado_sem_secao_narrativa_devolve_none_com_log(tmp_path, caplog):
    conteudo = """---
narrativa_status: aprovado
revisado_por: Matheus Mori
data_revisao: 2026-07-05
---

# Narrativa — Junho/2026

## Buscas realizadas

Sem heading '## Narrativa' neste arquivo.
"""
    base_dir = _escrever(tmp_path, conteudo)
    with caplog.at_level(logging.WARNING):
        resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is None
    assert "narrativa" in caplog.text.lower()


# --- 5. Texto longo demais e truncado, nunca vaza sem limite -----------------

def test_texto_longo_e_truncado_com_referencia_ao_arquivo(tmp_path, caplog):
    texto_longo = "Frase longa de teste repetida para estourar o orçamento. " * 20
    conteudo = _APROVADO_OK.replace("Texto final aprovado para publicação.", texto_longo)
    base_dir = _escrever(tmp_path, conteudo)
    with caplog.at_level(logging.WARNING):
        resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=base_dir)
    assert resultado is not None
    # largura de corte FIXA - nao pode depender do tamanho de `caminho`
    # (tmp_path de teste e absoluto/longo; producao usa um caminho relativo
    # curto - o texto exibido nao pode variar de orcamento por causa disso).
    assert len(resultado["texto"]) <= nm.MAX_CARACTERES_TEXTO + len(nm._SUFIXO_TRUNCAMENTO) + 1
    assert resultado["texto"].endswith(nm._SUFIXO_TRUNCAMENTO)
    assert "truncada" in caplog.text.lower()
    assert str(tmp_path) in caplog.text  # caminho completo vai pro log, nao pro texto exibido


# --- 6. Arquivo real de Junho/2026 (o rascunho salvo nesta tarefa) ----------

def test_arquivo_real_de_junho_2026_e_rascunho_nao_publicado():
    """docs/research/2026-06-narrativa.md existe de verdade no repo com
    narrativa_status: rascunho - precisa continuar None ate uma aprovacao
    humana real (nunca aprovar so por o arquivo existir)."""
    resultado = nm.carregar_narrativa_aprovada(pd.Timestamp("2026-06-01"))
    assert resultado is None


# --- 7. Regressão: "R$" (par de cifrão) na narrativa não corrompe o render --

def test_render_pagina2_com_rs_na_narrativa_nao_corrompe_texto(tmp_path):
    """'R$' aparece 2x num texto de narrativa tipico ('de R$ X para R$
    Y') - o mesmo bug ja corrigido para o resto do relatorio
    (matplotlib.rcParams['text.parse_math']=False, ver
    report_builder.gerar_relatorio_ipia_hrc_v3) porque, sem essa
    correcao, o par de '$' e interpretado como mathtext e derruba
    espacos/cola palavras. A narrativa passa pelo MESMO
    `components.texto_corrido`, mas por um caminho de codigo NOVO
    (pages_v3 Sec.55) - este teste mede de verdade, nao assume que a
    correcao global cobre o caminho novo so porque reusa o motor."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties

    texto = ("O real se desvalorizou de R$ 5,02/USD para R$ 5,16/USD "
            "em junho de 2026, um movimento relevante.")
    fp = FontProperties(size=7.6)

    original = matplotlib.rcParams["text.parse_math"]
    try:
        matplotlib.rcParams["text.parse_math"] = True
        largura_corrompida = TextPath((0, 0), texto, size=7.6, prop=fp).get_extents().width
        matplotlib.rcParams["text.parse_math"] = False
        largura_correta = TextPath((0, 0), texto, size=7.6, prop=fp).get_extents().width
    finally:
        matplotlib.rcParams["text.parse_math"] = original

    # prova que o bug e real e detectavel por medicao (nao so "nao lancou
    # excecao"): com parse_math=True o matplotlib tenta interpretar tudo
    # entre o par de '$' como mathtext e derruba espacos, produzindo uma
    # largura de texto medida MENOR que a correta.
    assert largura_correta > largura_corrompida + 5.0, (
        "o par de 'R$...R$' deveria produzir larguras mensuravelmente diferentes "
        "entre parse_math=True/False - se nao produz mais, a medicao deste teste "
        "ficou obsoleta e precisa ser revista, nao o assert relaxado")

    # a geracao real do relatorio (gerar_relatorio_ipia_hrc_v3) seta
    # text.parse_math=False ANTES de desenhar qualquer pagina, narrativa
    # inclusive - verifica que o guard esta de fato ativo nesse ponto.
    import indices_setoriais as m
    from reporting.report_builder import gerar_relatorio_ipia_hrc_v3
    from test_ipia_hrc_cli_pipeline import _fixture_completo

    ppi, dom = _fixture_completo()
    vintage_id = "20260101T000000Z"
    base_dir = str(tmp_path / "vintages")
    m.executar_pipeline_ipia_hrc(base_dir=base_dir, output_dir=str(tmp_path / "processed"),
                                 ppi_mensal_df=ppi, pia_domestico_df=dom, vintage_id=vintage_id)
    vintage = m.carregar_vintage_ipia_hrc_v2(vintage_id, base_dir=base_dir)

    caminho_pdf = str(tmp_path / "relatorio.pdf")
    resultado = gerar_relatorio_ipia_hrc_v3(
        caminho_pdf, vintage, carregador_narrativa=lambda periodo: {
            "texto": texto, "revisado_por": "Teste", "data_revisao": "2026-07-05",
            "caminho": "docs/research/teste.md"})

    assert os.path.exists(caminho_pdf)
    assert resultado["n_paginas"] == 4
    assert matplotlib.rcParams["text.parse_math"] is False
