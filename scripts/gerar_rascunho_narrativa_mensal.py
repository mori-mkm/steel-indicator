#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ADR 0018/0017 - gera o RASCUNHO inicial de
docs/research/AAAA-MM-narrativa.md para o ultimo mes calculavel da ultima
vintage publicada, a partir dos artefatos ja persistidos por
scripts/gerar_ipia_hrc_driver_decomposition.py (decomposicao_mensal.csv +
diagnostico_importacao_mensal.csv - NUNCA recalcula nada, so le).

Roda ANTES da busca humana por noticia: para drivers marcados como
composicao atipica (ADR 0018), pre-preenche a explicacao estrutural em vez
do placeholder de busca - poupa o revisor de caçar causa de mercado para
algo que pode ser artefato estatistico. NUNCA aprova nada (frontmatter
sempre narrativa_status: rascunho) e NUNCA sobrescreve um arquivo ja
existente (pode ja ter revisao humana em andamento ou aprovada).

Uso:
    python scripts/gerar_rascunho_narrativa_mensal.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import indices_setoriais as m
from reporting import narrative as narr
from reporting import narrativa_mensal
from reporting.report_builder import (
    carregar_decomposicao_se_disponivel, carregar_diagnostico_importacao_se_disponivel,
)


def main() -> None:
    vintage_id = m.ultima_vintage_ipia_hrc_v2()
    if vintage_id is None:
        print("Nenhuma vintage publicada ainda - rode --ipia primeiro.")
        sys.exit(1)
    vintage = m.carregar_vintage_ipia_hrc_v2(vintage_id)

    decomposicao_df = carregar_decomposicao_se_disponivel()
    if decomposicao_df is None or decomposicao_df.empty:
        print("Nenhum artefato de decomposicao encontrado - rode "
              "scripts/gerar_ipia_hrc_driver_decomposition.py primeiro.")
        sys.exit(1)
    linhas_do_vintage = decomposicao_df[decomposicao_df["vintage_id"] == vintage_id]
    if linhas_do_vintage.empty:
        print(f"Nenhuma transicao decomposta para a vintage atual ({vintage_id}) - "
              "rode scripts/gerar_ipia_hrc_driver_decomposition.py de novo.")
        sys.exit(1)
    ultima = linhas_do_vintage.sort_values("reference_period").iloc[-1]
    periodo = ultima["reference_period"]

    diagnostico_df = carregar_diagnostico_importacao_se_disponivel()
    diagnostico = None
    if diagnostico_df is not None:
        filtro = (diagnostico_df["reference_period"] == periodo) & (diagnostico_df["vintage_id"] == vintage_id)
        linha_diag = diagnostico_df[filtro]
        if not linha_diag.empty:
            diagnostico = linha_diag.iloc[0].to_dict()
            diagnostico["motivos"] = str(diagnostico.get("motivos") or "").split(" | ")

    ranking_bruto = narr.ranking_drivers({d: float(ultima[d]) for d in m.DRIVERS_PPI_COST})
    ranking = [(d, m.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC.get(d, d), v) for d, v in ranking_bruto]

    markdown = narrativa_mensal.gerar_rascunho_narrativa_markdown(periodo, ranking, diagnostico=diagnostico)

    caminho = os.path.join(narrativa_mensal.CAMINHO_BASE_PADRAO, f"{periodo:%Y-%m}-narrativa.md")
    if os.path.exists(caminho):
        print(f"Ja existe {caminho} - nao sobrescrevo (pode ter revisao humana em andamento ou "
              "aprovada). Apague/mova o arquivo manualmente se quiser gerar um rascunho novo.")
        sys.exit(1)

    os.makedirs(narrativa_mensal.CAMINHO_BASE_PADRAO, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(markdown)
    status_diag = diagnostico["status"] if diagnostico else "indisponível"
    print(f"Rascunho escrito em {caminho} (mês {periodo:%Y-%m}, diagnóstico de composição: {status_diag}).")
    print("narrativa_status: rascunho - segue pendente de revisão/aprovação humana explícita (ADR 0017).")


if __name__ == "__main__":
    main()
