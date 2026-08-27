"""Comex Stat source adapter: construcao de request, execucao HTTP e
parsing/validacao estrutural minima do endpoint `/general`.

Extraido de src/indices_setoriais.py (Spec 0003, Stage E1) sem alteracao de
comportamento - characterization coverage em
tests/characterization/test_comex_current.py.

Deliberadamente NAO contem (permanece em src/indices_setoriais.py, ver
docs/specs/0003-modularize-engine.md Stage E1 e secao 3 - premissas
metodologicas legacy nao viram contrato final do adapter generico):
  - NCM final de HRC (`NCM_BOBINA_QUENTE`) ou de vergalhao;
  - regras historicas de vigencia de NCM;
  - `_comex_bobina_bruto` (wrapper que ja escolhe a cesta HRC);
  - calculo de preco unitario, custo de importacao, II/AFRMM/antidumping,
    cambio, margem, preco domestico, IPIA ou qualquer provenance
    especifica do IPIA.

O endpoint exige POST (uma chamada GET com filtro na querystring recebe
403 do WAF da API) - ver docs/data-sources.md.
"""
from __future__ import annotations
from typing import List

import pandas as pd
import time

COMEX_URL = "https://api-comexstat.mdic.gov.br/general"


def _post_json(url: str, payload: dict, tentativas: int = 3):
    """POST com JSON no corpo. O endpoint /general do Comex Stat exige POST -
    uma chamada GET com o filtro na querystring (como uma versao anterior
    deste script fazia) recebe 403 do WAF da API, nao por falta de acesso."""
    import requests
    for i in range(tentativas):
        try:
            r = requests.post(url, json=payload, timeout=60,
                              headers={"User-Agent": "pesquisa-setorial/1.0",
                                       "Content-Type": "application/json"})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == tentativas - 1:
                raise
            time.sleep(2 ** i)


def comex_importacao_ncm(ncm: List[str], ano_ini: int, ano_fim: int) -> pd.DataFrame:
    """Importacao por NCM no Comex Stat, com valor FOB, frete, seguro e peso.

    O valor unitario daqui (FOB / peso) e o preco que o importador brasileiro
    efetivamente pagou - para efeito de paridade, e uma referencia melhor que a
    cotacao FOB de origem, e nao depende de licenca de agencia de precos.
    """
    payload = {
        "flow": "import",
        "monthDetail": True,
        "period": {"from": f"{ano_ini}-01", "to": f"{ano_fim}-12"},
        "filters": [{"filter": "ncm", "values": ncm}],
        "details": ["ncm", "country"],
        "metrics": ["metricFOB", "metricKG", "metricFreight", "metricInsurance"],
    }
    dados = _post_json(COMEX_URL, payload)
    if "data" not in dados:
        # a resposta veio, mas nao no formato esperado - imprime as chaves
        # de topo para facilitar o diagnostico em vez de falhar silencioso
        raise ValueError(f"resposta sem campo 'data'; chaves recebidas: {list(dados.keys())}")
    lista = dados.get("data", {}).get("list", [])
    return pd.DataFrame(lista)
