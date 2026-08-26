#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script de INVESTIGACAO ao vivo do Comex Stat (Spec 0003, Stage E2).

NAO e codigo de producao. NAO faz parte da suite pytest (nunca importado
por tests/). Faz chamadas de rede reais - execucao explicitamente opt-in:

    python scripts/research_comex_live.py

Usa o adapter de producao ja existente (steel_indicator.sources.comex) e a
cesta atual NCM_BOBINA_QUENTE apenas como AMOSTRA para testar a API - isto
NAO valida a cesta historica de NCM (investigacao separada, ainda pendente).

Objetivo: reproduzir a evidencia registrada em
docs/research/comex_live_validation.md. Ver esse documento para a leitura
consolidada dos resultados; este script existe soh para permitir
re-execucao/atualizacao dessa evidencia.

Nao altera NCM_BOBINA_QUENTE, formulas, parametros ou metodologia.
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import json
from collections import Counter

import pandas as pd

from steel_indicator.sources.comex import COMEX_URL, _post_json
import indices_setoriais as m

METRICAS = ["metricFOB", "metricKG", "metricFreight", "metricInsurance"]
NCM_AMOSTRA = sorted(sum(m.NCM_BOBINA_QUENTE.values(), []))  # amostra de teste, NAO validacao de vigencia


def _consulta(ano_ini: int, ano_fim: int, ncm=None, metrics=None) -> dict:
    payload = {
        "flow": "import",
        "monthDetail": True,
        "period": {"from": f"{ano_ini}-01", "to": f"{ano_fim}-12"},
        "filters": [{"filter": "ncm", "values": ncm or NCM_AMOSTRA}],
        "details": ["ncm", "country"],
        "metrics": metrics or METRICAS,
    }
    dados = _post_json(COMEX_URL, payload)
    return payload, dados


def fase1_schema():
    print("=" * 78)
    print("FASE 1 - schema real (1 NCM, 2024)")
    print("=" * 78)
    payload, dados = _consulta(2024, 2024, ncm=[NCM_AMOSTRA[6]])  # 72083610
    print("endpoint:", COMEX_URL)
    print("payload:", json.dumps(payload, ensure_ascii=False))
    print("chaves top-level:", list(dados.keys()))
    lista = dados.get("data", {}).get("list", [])
    print(f"n registros: {len(lista)}")
    if lista:
        print("colunas:", sorted(lista[0].keys()))
        print("registro exemplo:", json.dumps(lista[0], ensure_ascii=False))
    print()


def fase1b_metric_cif():
    print("=" * 78)
    print("FASE 1b - metricCIF e aceito?")
    print("=" * 78)
    _, dados = _consulta(2024, 2024, ncm=[NCM_AMOSTRA[6]], metrics=METRICAS + ["metricCIF"])
    lista = dados.get("data", {}).get("list", [])
    if lista:
        r = lista[0]
        print("colunas:", sorted(r.keys()))
        soma = float(r["metricFOB"]) + float(r["metricFreight"]) + float(r["metricInsurance"])
        print(f"metricCIF={r.get('metricCIF')}  FOB+Freight+Insurance={soma}")
    print()


def fase5_ncm_amostra():
    print("=" * 78)
    print("FASE 5 - cesta atual (amostra), cobertura em 2024")
    print("=" * 78)
    _, dados = _consulta(2024, 2024)
    lista = dados.get("data", {}).get("list", [])
    contagem = Counter(r["coNcm"] for r in lista)
    for ncm in NCM_AMOSTRA:
        print(f"  {ncm}: {contagem.get(ncm, 0)} registros" + ("  <- SEM DADO EM 2024" if ncm not in contagem else ""))
    print()


def fase2_3_profundidade():
    print("=" * 78)
    print("FASE 2/3 - profundidade historica e preenchimento (janelas 1998-2024)")
    print("=" * 78)
    janelas = [(2020, 2024), (2015, 2019), (2010, 2014), (2005, 2009), (1998, 2004)]
    linhas = []
    for ano_ini, ano_fim in janelas:
        _, dados = _consulta(ano_ini, ano_fim)
        lista = dados.get("data", {}).get("list", [])
        print(f"janela {ano_ini}-{ano_fim}: {len(lista)} registros")
        linhas.extend(lista)

    df = pd.DataFrame(linhas)
    df["data"] = pd.to_datetime(df["year"].astype(str) + "-" + df["monthNumber"].astype(str).str.zfill(2) + "-01")
    for col in METRICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"\ntotal combinado: {len(df)}  intervalo: {df['data'].min()} a {df['data'].max()}")
    for col in METRICAS:
        preench = df[col].notna()
        pos = preench & (df[col] > 0)
        print(f"{col}: preenchido={preench.mean()*100:.1f}%  >0={pos.mean()*100:.1f}%  "
              f"1o_periodo={df.loc[preench,'data'].min()}  ultimo={df.loc[preench,'data'].max()}")
    print()


def fase3_fronteira(anos=(1995, 1996, 1997)):
    print("=" * 78)
    print(f"FASE 3 - fronteira historica ({anos})")
    print("=" * 78)
    for ano in anos:
        _, dados = _consulta(ano, ano)
        lista = dados.get("data", {}).get("list", [])
        print(f"ano {ano}: n_registros={len(lista)}")
        if lista:
            df = pd.DataFrame(lista)
            for col in METRICAS:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            for col in METRICAS:
                print(f"  {col}: preenchido={df[col].notna().sum()}/{len(df)}  >0={int((df[col] > 0).sum())}")
    print()


if __name__ == "__main__":
    fase1_schema()
    fase1b_metric_cif()
    fase5_ncm_amostra()
    fase2_3_profundidade()
    fase3_fronteira()
