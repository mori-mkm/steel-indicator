#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pesquisa (Level 3 - decisao de fonte do preco domestico do IPIA-HRC V2):
investiga se o IBGE/SIDRA tem alguma serie de preco/valor mais especifica de
produto do que "242 Siderurgia" (unica classificacao usada hoje por
`ibge_sidra_ipp_siderurgia`, um agregado de TODA a siderurgia).

Achado (rodado ao vivo nesta pesquisa): a tabela SIDRA 7752 ("Producao e
vendas dos produtos e/ou servicos industriais", PIA-Produto, classificacao
1264 = Prodlist 2016/2019/2022) tem a categoria 54849 = "2422.2020 Bobinas
a quente de acos ao carbono, nao revestidos" - HRC especifico de verdade,
unidade "Toneladas" (confirmado no proprio metadado da categoria). As
variaveis 864 (Receita liquida de vendas, Mil Reais) e 1982 (Quantidade
vendida, Toneladas) permitem a MESMA tecnica receita/volume ja usada pelo
projeto (`ancora_domestica_ponderada_v2`), mas aplicada a um universo
nacional agregado (todos os produtores, nao so Usiminas+CSN) e
HOMOGENEO POR PRODUTO (um unico codigo Prodlist, nao "Siderurgia inteira").

Limitacoes ja conhecidas (nao escondidas aqui):
  - frequencia ANUAL, cobertura 2014-2023 (defasagem de ~2 anos - a tabela
    nao cobre 2024/2025/2026, entao nao serve para o mes corrente);
  - agregado NACIONAL (nao decompoe por empresa) - Usiminas/CSN continuam
    sendo a unica fonte de nivel trimestral/empresa;
  - "quantidade vendida" e levantamento amostral (PIA, pesquisa anual do
    IBGE), nao transacao individual.

Os niveis resultantes (R$/t: ~2.840 em 2020, ~5.645 em 2021 - pico do
supercycle -, ~5.393 em 2022, ~4.844 em 2023) sao economicamente plausiveis
e consistentes com o ciclo de preco do aço já conhecido (2021 = pico
pos-pandemia) - evidencia adicional de que a serie e real, nao ruido.

NAO e codigo de producao. So leitura/impressao - nao escreve nada, nao
conecta a nenhum calculo do IPIA.

Uso:
    python scripts/research/ibge_pia_produto_hrc.py
"""
from __future__ import annotations
import requests

METADADOS_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/7752/metadados"
DADOS_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/7752/periodos/all/variaveis/864|1982"
CATEGORIA_HRC = 54849  # "2422.2020 Bobinas a quente de acos ao carbono, nao revestidos"


def confirmar_categoria_hrc() -> dict:
    r = requests.get(METADADOS_URL, timeout=60, headers={"User-Agent": "pesquisa-setorial/1.0"})
    r.raise_for_status()
    data = r.json()
    print(f"Periodicidade: {data['periodicidade']}")
    classificacao = next(c for c in data["classificacoes"] if c["id"] == 1264)
    categoria = next(c for c in classificacao["categorias"] if c["id"] == CATEGORIA_HRC)
    print(f"Categoria {CATEGORIA_HRC}: {categoria['nome']} (unidade: {categoria['unidade']})")
    return categoria


def buscar_serie_hrc() -> None:
    r = requests.get(DADOS_URL, params={"localidades": "N1[all]", "classificacao": f"1264[{CATEGORIA_HRC}]"},
                      timeout=60, headers={"User-Agent": "pesquisa-setorial/1.0"})
    r.raise_for_status()
    variaveis = r.json()

    series = {}
    for var in variaveis:
        serie = var["resultados"][0]["series"][0]["serie"]
        series[str(var["id"])] = {int(ano): float(v) for ano, v in serie.items()}

    receita = series["864"]  # Mil Reais
    quantidade = series["1982"]  # Toneladas
    print("\n=== Preco unitario implicito (receita liquida / quantidade vendida), R$/t ===")
    print(f"{'ano':>6} {'receita (mil R$)':>18} {'quantidade (t)':>16} {'R$/t':>10}")
    for ano in sorted(receita):
        preco = receita[ano] * 1000 / quantidade[ano]
        print(f"{ano:>6} {receita[ano]:>18,.0f} {quantidade[ano]:>16,.0f} {preco:>10,.2f}")


def main() -> None:
    print("=== Confirmando categoria HRC na classificacao Prodlist (tabela SIDRA 7752) ===")
    confirmar_categoria_hrc()
    print("\n=== Buscando serie anual de receita/quantidade (nacional, HRC especifico) ===")
    buscar_serie_hrc()


if __name__ == "__main__":
    main()
