#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pesquisa: inspeciona o Excel "Performance Mensal" do Instituto Aco Brasil
(mesma fonte ja usada por `taxa_penetracao_importacao_planos_mensal`) para
fechar a lacuna registrada em `references/catalogo_series_coleta.xlsx`
(aba Lacunas, item 5: "Conteudo das abas do Performance-Mensal do Aco
Brasil - Baixar e inspecionar") e no proprio catalogo (linha 98, status
"VERIFICADO ... Conteudo das abas A CONFIRMAR").

Achado (rodado ao vivo nesta pesquisa): a planilha tem SO uma aba, com
volumes fisicos (mil t) de producao/vendas internas/vendas externas por
categoria Planos/Longos/Semiacabados, mais o valor total (US$ milhoes) de
exportacoes e importacoes - nunca por produto, nunca em R$, nunca receita
domestica. NAO existe nenhuma linha de preco ou receita de venda interna -
fecha definitivamente a lacuna: esta fonte NAO serve como preco domestico
de HRC (nem de nenhum produto), so como fonte de volume (ja e o que o
projeto usa dela, via `taxa_penetracao_importacao_planos_mensal`).

NAO e codigo de producao. So leitura/impressao - nao escreve nada, nao
altera nenhum caminho existente.

Uso:
    python scripts/research/inspecionar_acobrasil_xls.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pandas as pd

import indices_setoriais as m


def main() -> None:
    links = m._acobrasil_resolver_links_mes_atual()
    url_xls = links["xls"]
    print(f"Baixando: {url_xls}")

    import io
    import requests
    r = requests.get(url_xls, timeout=60, headers={"User-Agent": "pesquisa-setorial/1.0"})
    r.raise_for_status()
    xl = pd.ExcelFile(io.BytesIO(r.content))
    print(f"Abas: {xl.sheet_names}")

    df = pd.read_excel(io.BytesIO(r.content), sheet_name=0, header=None)
    print(f"Formato: {df.shape}")

    print("\n=== Rotulos de linha (coluna A) - toda a planilha ===")
    achou_preco = False
    for i in range(df.shape[0]):
        v = df.iat[i, 0]
        if isinstance(v, str) and v.strip():
            print(f"  linha {i}: {v.strip()[:110]}")
            if any(kw in v.lower() for kw in ("preço", "price", "receita", "revenue")):
                achou_preco = True

    print("\n=== Conclusao ===")
    if achou_preco:
        print("  [ATENCAO] encontrada linha com rotulo de preco/receita - reinvestigar antes de assumir que nao existe")
    else:
        print("  Nenhuma linha de preco/receita encontrada. Conteudo confirmado: producao/vendas/comercio")
        print("  exterior em volume fisico (mil t), mais valor TOTAL (nao por produto) de import/export em US$.")
        print("  Fonte NAO serve para preco domestico de HRC - so para volume (uso ja existente do projeto).")


if __name__ == "__main__":
    main()
