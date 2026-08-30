"""Carregamento de narrativa mensal semi-manual (texto humano revisado,
NUNCA gerado ou publicado automaticamente).

Distinto de `reporting.narrative` (motor determinístico de vocabulário
FECHADO, derivado só de números já calculados) - este módulo lê texto
livre escrito por um humano fora do Claude Code (busca guiada pelos
drivers do Shapley, achados jornalísticos citáveis) e só o expõe ao
relatório quando `narrativa_status: aprovado` está explicitamente
marcado no arquivo, com revisor e data preenchidos. Rascunho, arquivo
ausente ou frontmatter malformado devolvem `None` silenciosamente - o
relatório sempre gera normalmente, sem essa seção, nunca travando nem
publicando rascunho como se fosse texto final.

Função de carregamento faz I/O de arquivo (não é literalmente pura) mas
é determinística/injetável, sem rede - mesmo padrão de
`reporting.report_builder.carregar_decomposicao_se_disponivel`.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

CAMINHO_BASE_PADRAO = "docs/research"
STATUS_RASCUNHO = "rascunho"
STATUS_APROVADO = "aprovado"
_STATUS_VALIDOS = {STATUS_RASCUNHO, STATUS_APROVADO}
_MARCADOR_FRONTMATTER = "---"
_HEADING_NARRATIVA = "## Narrativa"


def _dividir_frontmatter(conteudo: str):
    """Separa o bloco YAML entre os dois `---` do corpo markdown que vem
    depois. Devolve (meta: dict, corpo: str, erro: None) ou
    (None, "", "motivo") - nunca lança exceção, o motivo é sempre uma
    frase curta para log."""
    linhas = conteudo.splitlines()
    if not linhas or linhas[0].strip() != _MARCADOR_FRONTMATTER:
        return None, "", "arquivo não começa com frontmatter '---'"
    try:
        fim = linhas.index(_MARCADOR_FRONTMATTER, 1)
    except ValueError:
        return None, "", "frontmatter sem '---' de fechamento"
    bloco = "\n".join(linhas[1:fim])
    corpo = "\n".join(linhas[fim + 1:])
    try:
        meta = yaml.safe_load(bloco)
    except yaml.YAMLError as e:
        return None, "", f"YAML inválido no frontmatter: {e}"
    if not isinstance(meta, dict):
        return None, "", "frontmatter não é um mapeamento YAML (chave: valor)"
    return meta, corpo, None


def _extrair_secao_narrativa(corpo: str) -> Optional[str]:
    """Extrai só o conteúdo sob o heading `## Narrativa` (até o próximo
    `## `, ou fim do arquivo) - nunca o corpo inteiro. Seções de trabalho
    (Buscas realizadas, Checklist de revisão) nunca vazam para o
    relatório publicado, mesmo com o arquivo aprovado."""
    linhas = corpo.splitlines()
    try:
        inicio = next(i for i, l in enumerate(linhas) if l.strip() == _HEADING_NARRATIVA)
    except StopIteration:
        return None
    fim = next((i for i in range(inicio + 1, len(linhas)) if linhas[i].startswith("## ")), len(linhas))
    texto = "\n".join(linhas[inicio + 1:fim]).strip()
    return texto or None


def carregar_narrativa_aprovada(periodo, base_dir: str = CAMINHO_BASE_PADRAO) -> Optional[dict]:
    """Lê `{base_dir}/{periodo:%Y-%m}-narrativa.md` e devolve
    `{"texto", "revisado_por", "data_revisao", "caminho"}` SOMENTE se
    `narrativa_status: aprovado` E `revisado_por`/`data_revisao`
    preenchidos E a seção `## Narrativa` existe com conteúdo. Qualquer
    outro caso (ausente, rascunho, YAML quebrado, aprovado mas sem
    revisor/data, sem seção `## Narrativa`) devolve `None` e loga o
    motivo - nunca lança exceção, nunca deixa o relatório travar."""
    caminho = os.path.join(base_dir, f"{periodo:%Y-%m}-narrativa.md")
    if not os.path.exists(caminho):
        logger.info("Narrativa mensal não encontrada em %s - relatório segue sem essa seção.", caminho)
        return None

    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read()

    meta, corpo, erro = _dividir_frontmatter(conteudo)
    if erro:
        logger.warning("Narrativa mensal em %s malformada (%s) - ignorada.", caminho, erro)
        return None

    status = meta.get("narrativa_status")
    if status not in _STATUS_VALIDOS:
        logger.warning("Narrativa mensal em %s com narrativa_status=%r inválido - ignorada.", caminho, status)
        return None
    if status != STATUS_APROVADO:
        logger.info("Narrativa mensal em %s com status=%r (não aprovado) - não incluída no relatório.",
                    caminho, status)
        return None

    revisado_por = meta.get("revisado_por")
    data_revisao = meta.get("data_revisao")
    if not revisado_por or not data_revisao:
        logger.warning("Narrativa mensal em %s marcada aprovado mas sem revisado_por/data_revisao "
                       "preenchidos - ignorada (aprovação exige atribuição explícita).", caminho)
        return None

    texto = _extrair_secao_narrativa(corpo)
    if texto is None:
        logger.warning("Narrativa mensal em %s aprovada mas sem seção '## Narrativa' com conteúdo - ignorada.",
                       caminho)
        return None

    texto_exibido = _truncar_para_orcamento_da_pagina(texto, caminho)

    return {"texto": texto_exibido, "revisado_por": str(revisado_por), "data_revisao": str(data_revisao),
            "caminho": caminho}


# =============================================================================
# Scaffold do rascunho (ADR 0018) - roda ANTES da busca humana. Funcao PURA
# (nenhum I/O) que so monta o texto markdown a partir de dado ja calculado
# (ranking de drivers Shapley + diagnostico de composicao atipica, ambos ja
# persistidos por scripts/gerar_ipia_hrc_driver_decomposition.py). O I/O
# (escrever o arquivo) fica em scripts/gerar_rascunho_narrativa_mensal.py -
# nunca aqui, mesma separacao de `.claude/rules/python.md`.
# =============================================================================

_EXPLICACAO_ESTRUTURAL_TEMPLATE = (
    "Diagnóstico estrutural (ADR 0018) — NÃO é necessário buscar notícia de mercado para "
    "este driver neste mês. {motivo} Busque apenas se quiser corroborar com um evento real "
    "conhecido (ex.: uma queda de preço internacional genuína pode coexistir com o efeito "
    "estrutural acima, sem que um explique o outro)."
)


def gerar_rascunho_narrativa_markdown(periodo, ranking: list, diagnostico: Optional[dict] = None,
                                      top_n: int = 5) -> str:
    """Monta o markdown inicial de `docs/research/AAAA-MM-narrativa.md` -
    SEMPRE `narrativa_status: rascunho` (nunca aprovado - ADR 0017 continua
    valendo integralmente, isto só reduz busca inútil, nunca decide
    publicação). `ranking`: lista de `(driver_key, nome_legivel,
    contribuicao)` já ordenada por |contribuição| (mesma saída de
    `narrative.ranking_drivers`, com nomes já traduzidos). `diagnostico`
    (opcional): dict de `indices_setoriais.detectar_composicao_atipica_importacao`
    para o mês - drivers em `indices_setoriais.DRIVERS_VULNERAVEIS_COMPOSICAO`
    recebem a explicação estrutural pré-preenchida na subseção "Buscas
    realizadas" quando `diagnostico["status"] == "atipico"`; os demais
    mantêm o placeholder de busca de sempre (nenhuma mudança de
    comportamento para o caso comum)."""
    import indices_setoriais as motor  # import local: evita import no topo do modulo (mesmo padrao de narrative.py)

    # nome do mes por mapeamento fixo, nunca `%B` (depende de locale do sistema -
    # mesmo cuidado ja documentado em `indices_setoriais._mes_ano_pt_br`).
    nome_mes_ano = f"{motor.ACOBRASIL_MESES_PT[periodo.month - 1]}/{periodo.year}"
    mes_atipico = diagnostico is not None and diagnostico.get("status") == motor.STATUS_COMPOSICAO_ATIPICO
    linhas_drivers = [f"{i}. {nome} — {contrib:+.2f} pts" for i, (_, nome, contrib) in enumerate(ranking[:top_n], 1)]

    secoes_busca = []
    for driver_key, nome, _ in ranking[:top_n]:
        if mes_atipico and driver_key in motor.DRIVERS_VULNERAVEIS_COMPOSICAO:
            motivo = " ".join(diagnostico.get("motivos", [])) or "Volume do mês abaixo do padrão histórico."
            secoes_busca.append(f"### Driver: {nome} — diagnóstico estrutural\n\n"
                                f"{_EXPLICACAO_ESTRUTURAL_TEMPLATE.format(motivo=motivo)}\n")
        else:
            secoes_busca.append(f"### Driver: {nome} — achado pendente\n\n"
                                f"Query: \"\"\n\n"
                                f"* Fonte: (preencher)\n")

    return (
        f"---\n"
        f"narrativa_status: rascunho\n"
        f"revisado_por: null\n"
        f"data_revisao: null\n"
        f"---\n\n"
        f"# Narrativa — {nome_mes_ano}\n\n"
        f"## Drivers do mês (Shapley, já calculado)\n\n"
        + "\n".join(linhas_drivers) + "\n\n"
        f"## Buscas realizadas\n\n"
        + "\n".join(secoes_busca) + "\n"
        f"## Narrativa\n\n"
        f"(preencher após revisão dos achados acima)\n\n"
        f"## Checklist de revisão\n\n"
        f"* [ ] Todo claim tem fonte com data e trecho, ou está marcado como diagnóstico estrutural\n"
        f"* [ ] Nenhuma causalidade inventada além do que os achados sustentam\n\n"
        f"## Aprovação\n\n"
        f"Aprovado por: (pendente)\n"
        f"Data: (pendente)\n"
    )


# Orçamento medido empiricamente (docs/validation - preview manual desta
# tarefa) para a seção "Narrativa do mês" da página 2 do Reporting V3
# (fonte 7.6pt, largura útil da página): ~650 caracteres cabem em ~4
# linhas sem colidir com o rodapé. Texto humano é entrada de tamanho livre
# (fronteira de confiança, nunca controlada pelo layout) - trunca em vez
# de deixar o parágrafo vazar por cima do rodapé.
MAX_CARACTERES_TEXTO = 650


_SUFIXO_TRUNCAMENTO = "… (texto truncado — íntegra no arquivo fonte)"


def _truncar_para_orcamento_da_pagina(texto: str, caminho: str) -> str:
    """Trunca em largura FIXA (nunca embute `caminho` no texto exibido -
    esse tamanho varia com o ambiente, ex. tmp_path de teste vs.
    `docs/research/...` em produção, e poderia por si só estourar o
    orçamento da página); o caminho completo já vai pro log."""
    if len(texto) <= MAX_CARACTERES_TEXTO:
        return texto
    corte = texto.rfind(" ", 0, MAX_CARACTERES_TEXTO)
    if corte <= 0:
        corte = MAX_CARACTERES_TEXTO
    logger.warning("Narrativa mensal em %s tem %d caracteres (> %d) - truncada para caber na página; "
                   "texto completo permanece no arquivo fonte.", caminho, len(texto), MAX_CARACTERES_TEXTO)
    return texto[:corte].rstrip(" ,;") + _SUFIXO_TRUNCAMENTO
