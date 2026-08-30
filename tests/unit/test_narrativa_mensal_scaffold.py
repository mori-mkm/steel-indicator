"""Unit tests for `reporting.narrativa_mensal.gerar_rascunho_narrativa_markdown`
(ADR 0018/0017) - funcao PURA, sem I/O.

Cobre: frontmatter sempre `narrativa_status: rascunho` (nunca aprovado -
esta funcao nunca decide publicacao); driver vulneravel (fob/freight/
insurance) num mes atipico recebe explicacao estrutural pre-preenchida em
vez do placeholder de busca; driver nao-vulneravel ou mes normal mantem o
placeholder de sempre (regressao); parseavel pelo mesmo loader
(`carregar_narrativa_aprovada` via frontmatter) sem erro.
"""
import pandas as pd
import pytest

from reporting import narrativa_mensal as nm

PERIODO = pd.Timestamp("2026-06-01")

_RANKING = [
    ("fob", "Preço FOB", -3.75),
    ("fx", "Câmbio", -3.38),
    ("domestic_price", "Preço doméstico", 1.55),
    ("ii", "Imposto de Importação", -1.18),
    ("freight", "Frete internacional", -0.43),
]

_DIAGNOSTICO_ATIPICO = {
    "status": "atipico",
    "motivos": ["Volume importado do mês (16.281 t) é 23% da mediana dos 11 meses anteriores (~44.843 t)."],
}
_DIAGNOSTICO_NORMAL = {"status": "normal", "motivos": []}


def test_frontmatter_sempre_rascunho():
    md = nm.gerar_rascunho_narrativa_markdown(PERIODO, _RANKING, diagnostico=_DIAGNOSTICO_ATIPICO)
    assert "narrativa_status: rascunho" in md
    assert "narrativa_status: aprovado" not in md


def test_sem_diagnostico_mantem_placeholder_para_todos():
    md = nm.gerar_rascunho_narrativa_markdown(PERIODO, _RANKING, diagnostico=None)
    assert "— diagnóstico estrutural" not in md
    assert md.count('Query: ""') == len(_RANKING)


def test_mes_normal_mantem_placeholder_mesmo_com_fob_no_ranking():
    md = nm.gerar_rascunho_narrativa_markdown(PERIODO, _RANKING, diagnostico=_DIAGNOSTICO_NORMAL)
    assert "— diagnóstico estrutural" not in md


def test_mes_atipico_pre_preenche_apenas_drivers_vulneraveis():
    md = nm.gerar_rascunho_narrativa_markdown(PERIODO, _RANKING, diagnostico=_DIAGNOSTICO_ATIPICO)
    # fob e freight (vulneraveis, no ranking) recebem explicacao estrutural
    assert "Driver: Preço FOB — diagnóstico estrutural" in md
    assert "Driver: Frete internacional — diagnóstico estrutural" in md
    assert "16.281" in md or "23%" in md  # numero real do diagnostico aparece, nao generico
    # domestic_price/fx/ii (nao vulneraveis) mantem o placeholder de busca de sempre
    assert "Driver: Câmbio — achado pendente" in md
    assert "Driver: Preço doméstico — achado pendente" in md
    assert "Driver: Imposto de Importação — achado pendente" in md


def test_nunca_aprova_mesmo_com_diagnostico_atipico():
    md = nm.gerar_rascunho_narrativa_markdown(PERIODO, _RANKING, diagnostico=_DIAGNOSTICO_ATIPICO)
    assert "Aprovado por: (pendente)" in md


def test_markdown_gerado_e_parseavel_pelo_loader_sem_erro(tmp_path):
    """O rascunho gerado precisa ser um frontmatter valido (mesmo parser
    de carregar_narrativa_aprovada) - continua None porque e rascunho,
    mas nao pode ser tratado como malformado."""
    md = nm.gerar_rascunho_narrativa_markdown(PERIODO, _RANKING, diagnostico=_DIAGNOSTICO_ATIPICO)
    caminho = tmp_path / "2026-06-narrativa.md"
    caminho.write_text(md, encoding="utf-8")
    resultado = nm.carregar_narrativa_aprovada(PERIODO, base_dir=str(tmp_path))
    assert resultado is None  # rascunho, nunca aprovado automaticamente
