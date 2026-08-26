#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script de INVESTIGACAO ao vivo (Spec 0003, Stage E3) sobre a vigencia
historica dos 13 codigos NCM atualmente usados para HRC (NCM_BOBINA_QUENTE).

NAO e codigo de producao. NAO faz parte da suite pytest. Faz chamadas de
rede reais - execucao explicitamente opt-in:

    python scripts/research_hrc_ncm_history.py

Reproduz as secoes 2 e 3 de docs/research/hrc_ncm_history.md (consultas ao
Comex Stat). A secao 4 desse documento (tabelas oficiais de correlacao de
NCM do MDIC/Camex) precisa ser obtida manualmente nas URLs citadas la -
nao incluida aqui para nao versionar copia de documento de terceiros.

Usa apenas o adapter de producao ja existente (steel_indicator.sources.comex)
e a cesta atual NCM_BOBINA_QUENTE como AMOSTRA de teste - nao altera nem
valida definitivamente essa constante.
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from collections import Counter

import pandas as pd
import requests

from steel_indicator.sources.comex import COMEX_URL, _post_json
import indices_setoriais as m

NCM_AMOSTRA = sorted(sum(m.NCM_BOBINA_QUENTE.values(), []))


def secao2_inventario_posicao_7208():
    print("=" * 78)
    print("SECAO 2 - inventario completo da posicao 7208 (/tables/ncm)")
    print("=" * 78)
    r = requests.get("https://api-comexstat.mdic.gov.br/tables/ncm",
                      params={"search": "7208"}, timeout=30,
                      headers={"User-Agent": "pesquisa-setorial/1.0"})
    r.raise_for_status()
    lista = r.json().get("data", {}).get("list", [])
    codigos = sorted(item["coNcm"] for item in lista)
    print(f"total de codigos sob 7208: {len(codigos)}")
    print("codigos:", codigos)
    fora_da_amostra = sorted(set(codigos) - set(NCM_AMOSTRA))
    print("codigos sob 7208 que NAO estao em NCM_BOBINA_QUENTE (nao decidir nada sobre eles aqui):",
          fora_da_amostra)
    print()


def secao3_presenca_por_ano():
    print("=" * 78)
    print("SECAO 3 - presenca de comercio por (NCM, ano), 1997-2024 - evidencia de APOIO")
    print("=" * 78)
    janelas = [(1997, 2001), (2002, 2006), (2007, 2011), (2012, 2016), (2017, 2021), (2022, 2024)]
    linhas = []
    for ini, fim in janelas:
        payload = {
            "flow": "import", "monthDetail": True,
            "period": {"from": f"{ini}-01", "to": f"{fim}-12"},
            "filters": [{"filter": "ncm", "values": NCM_AMOSTRA}],
            "details": ["ncm", "country"],
            "metrics": ["metricFOB", "metricKG"],
        }
        dados = _post_json(COMEX_URL, payload)
        lista = dados.get("data", {}).get("list", [])
        print(f"janela {ini}-{fim}: {len(lista)} registros")
        linhas.extend(lista)

    df = pd.DataFrame(linhas)
    df["year"] = df["year"].astype(int)
    tabela = df.groupby(["coNcm", "year"]).size().unstack(fill_value=0)
    tabela = tabela.reindex(columns=range(1997, 2025), fill_value=0).reindex(NCM_AMOSTRA)

    print("\nresumo por NCM: primeiro/ultimo ano com >=1 registro, anos intermediarios sem registro:")
    for ncm in NCM_AMOSTRA:
        linha = tabela.loc[ncm]
        anos_com = linha[linha > 0].index.tolist()
        anos_sem = linha[linha == 0].index.tolist()
        primeiro = min(anos_com) if anos_com else None
        ultimo = max(anos_com) if anos_com else None
        gaps = [a for a in anos_sem if primeiro and ultimo and primeiro < a < ultimo]
        print(f"  {ncm}: primeiro={primeiro} ultimo={ultimo} anos_sem_registro_intermediarios={gaps}")
    print()


if __name__ == "__main__":
    secao2_inventario_posicao_7208()
    secao3_presenca_por_ano()
    print("Secao 4 (tabelas oficiais de correlacao NCM 2012<->2017 e 2017<->2022) "
          "precisa ser obtida manualmente - ver docs/research/hrc_ncm_history.md secao 1.")
