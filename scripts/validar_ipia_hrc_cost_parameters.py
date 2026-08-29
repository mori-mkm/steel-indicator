#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RESEARCH + VALIDATION ONLY - nao altera `ParamsIPIA`, PPI oficial,
IPIA, vintages, VERSAO_METODOLOGIA nem reporting.

Sprint "IPIA-HRC - MARGIN / PORT / INLAND COST PARAMETER CALIBRATION":
audita os tres parametros ESTIMADO/hold-flat do PPI (`despesas_porto_rs_t`,
`frete_interno_rs_t`, `margem_importador`) contra evidencia publica
reproduzivel, constroi cenarios LOW/BASE/HIGH e roda o impacto
CONTRAFACTUAL no PPI/IPIA reusando `agregar_ipia_hrc_multi_ncm_mensal`
(producao, parametro `p` ja aceita um `ParamsIPIA` diferente do default -
nenhuma funcao de calculo e reimplementada).

Faz chamadas de rede reais (Comex Stat, BCB/SGS). Toda saida vai para
data/processed/validation/ipia_hrc_cost_parameters/.

Uso:
    python scripts/validar_ipia_hrc_cost_parameters.py
"""
from __future__ import annotations
import dataclasses
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m

OUT_DIR = "data/processed/validation/ipia_hrc_cost_parameters"
JANELA_INI, JANELA_FIM = "2019-01-01", "2026-07-01"

DEFAULT = m.ParamsIPIA()


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


def pearson(x, y) -> float:
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


# =============================================================================
# 1. Current parameter audit (do proprio codigo, nunca hardcoded de novo)
# =============================================================================

def auditar_parametros_atuais() -> pd.DataFrame:
    return pd.DataFrame([
        {"parameter": "D_porto", "current": DEFAULT.despesas_porto_rs_t, "unit": "R$/t",
         "provenance": "ESTIMADO", "time_varying": "No"},
        {"parameter": "D_interno", "current": DEFAULT.frete_interno_rs_t, "unit": "R$/t",
         "provenance": "ESTIMADO", "time_varying": "No"},
        {"parameter": "margem", "current": DEFAULT.margem_importador, "unit": "%",
         "provenance": "ESTIMADO", "time_varying": "No"},
    ])


# =============================================================================
# 2. Portos/UFs relevantes - direto do Comex Stat (nunca assumido)
# =============================================================================

def portos_relevantes(ano_ini: int = 2022, ano_fim: int = 2026) -> pd.DataFrame:
    """Usa o mesmo endpoint /general do Comex Stat, com `details` incluindo
    `state`/`urf` (confirmado ao vivo nesta etapa que a fonte expoe essas
    dimensoes) - nunca assume Santos por conveniencia."""
    import requests
    ncms = sorted(sum(m.NCM_BOBINA_QUENTE.values(), []))
    payload = {
        "flow": "import", "monthDetail": True,
        "period": {"from": f"{ano_ini}-01", "to": f"{ano_fim}-12"},
        "filters": [{"filter": "ncm", "values": ncms}],
        "details": ["ncm", "state", "urf"],
        "metrics": ["metricFOB", "metricKG"],
    }
    r = requests.post("https://api-comexstat.mdic.gov.br/general", json=payload, timeout=90,
                       headers={"User-Agent": "pesquisa-setorial/1.0", "Content-Type": "application/json"})
    r.raise_for_status()
    linhas = r.json()["data"]["list"]
    df = pd.DataFrame(linhas)
    df["metricKG"] = pd.to_numeric(df["metricKG"], errors="coerce")
    por_uf = df.groupby("state")["metricKG"].sum().sort_values(ascending=False)
    total = por_uf.sum()
    return pd.DataFrame({"uf": por_uf.index, "kg": por_uf.values, "share": por_uf.values / total})


# =============================================================================
# 3. Cenarios de parametro (evidencia curada nesta etapa - ver validation doc)
# =============================================================================

@dataclasses.dataclass
class CenarioParametros:
    nome: str
    despesas_porto_rs_t: float
    frete_interno_rs_t: float
    margem_importador: float

    def to_params(self) -> m.ParamsIPIA:
        return m.ParamsIPIA(despesas_porto_rs_t=self.despesas_porto_rs_t,
                             frete_interno_rs_t=self.frete_interno_rs_t,
                             margem_importador=self.margem_importador)


# D_porto: terminal relevante (Porto Itapoá/SC, 2o maior UF de entrada) nao
# publica R$/t para carga de projeto/granel siderurgico (breakbulk) - so
# "Sob Consulta" - confirmado ao vivo nesta etapa. Faixa abaixo e uma
# ORDEM DE GRANDEZA a partir de armazenagem ad valorem tipica (~0,4%-0,7%
# do CIF por periodo) e movimentacao de container observadas na mesma
# tabela, NUNCA um valor de breakbulk medido diretamente - ver Sec.
# "D_porto evidence" do validation document para a ressalva completa.
D_PORTO_LOW, D_PORTO_BASE, D_PORTO_HIGH = 120.0, 210.0, 320.0

# D_interno: ANTT Resolucao 6084/2026, Tabela A (carga geral) - CCD (R$/km)
# + CC (fixo por operacao). 5 eixos (~27t utgeis, carreta) e a
# configuracao mais plausivel para bobina a quente. Rotas curadas
# (distancias rodoviarias aproximadas, nao medidas por API de mapas
# nesta etapa): short haul = Sao Francisco do Sul/SC -> Joinville/SC
# (~50km, consumo industrial local); base route = Sao Francisco do
# Sul/SC -> Sao Paulo/SP (~450km, polo indutrial-automotivo de
# referencia); long haul = Itaguai/RJ -> Belo Horizonte/MG (~550km) ou
# equivalente de longa distancia.
D_INTERNO_LOW, D_INTERNO_BASE, D_INTERNO_HIGH = 60.0, 140.0, 260.0

# Margem: nenhum benchmark publico de markup de trading de aco plano foi
# localizado nesta etapa (Sec. "Margin evidence" do validation document) -
# a faixa abaixo NAO e evidencia direta, e uma faixa de sensibilidade
# analitica em torno do valor atual, para a matriz de cenarios funcionar
# sem fabricar um "industry standard".
MARGEM_LOW, MARGEM_BASE, MARGEM_HIGH = 0.0, 0.03, 0.06


def montar_cenarios() -> list[CenarioParametros]:
    return [
        CenarioParametros("Low", D_PORTO_LOW, D_INTERNO_LOW, MARGEM_LOW),
        CenarioParametros("Current", DEFAULT.despesas_porto_rs_t, DEFAULT.frete_interno_rs_t,
                           DEFAULT.margem_importador),
        CenarioParametros("Evidence Base", D_PORTO_BASE, D_INTERNO_BASE, MARGEM_BASE),
        CenarioParametros("High", D_PORTO_HIGH, D_INTERNO_HIGH, MARGEM_HIGH),
    ]


def montar_cenarios_isolados() -> list[CenarioParametros]:
    """One-at-a-time: cada parametro sozinho no extremo HIGH, os outros dois
    no Current - isola qual parametro domina o impacto (Sec.22 do sprint)."""
    c = DEFAULT
    return [
        CenarioParametros("D_porto only (HIGH)", D_PORTO_HIGH, c.frete_interno_rs_t, c.margem_importador),
        CenarioParametros("D_interno only (HIGH)", c.despesas_porto_rs_t, D_INTERNO_HIGH, c.margem_importador),
        CenarioParametros("Margem only (HIGH)", c.despesas_porto_rs_t, c.frete_interno_rs_t, MARGEM_HIGH),
    ]


# =============================================================================
# 4. Contrafactual - reusa agregar_ipia_hrc_multi_ncm_mensal(p=...) direto
# =============================================================================

def rodar_cenario(df_bruto: pd.DataFrame, cenario: CenarioParametros,
                   domestico_dummy: pd.DataFrame) -> pd.DataFrame:
    """`agregar_ipia_hrc_multi_ncm_mensal` sem `domestico_df` cai no
    caminho domestico LEGADO (ancora corporativa curada, so
    2025Q2-2026Q2) e trunca o resultado pela intersecao - usa-se um
    domestico dummy de cobertura total (mesmo artificio ja usado nos
    sprints de liquidez/missing-data/policy evidence) so para nao
    truncar; nenhuma coluna de preco domestico real e usada nesta etapa
    (o foco e o PPI, nao o IPIA composto - Sec.20/21 usam um preco
    domestico hipotetico separado, ver main())."""
    p = cenario.to_params()
    out = m.agregar_ipia_hrc_multi_ncm_mensal(ano_ini=2019, ano_fim=2026, df_bruto=df_bruto, p=p,
                                                domestico_df=domestico_dummy)
    out = out.set_index("reference_period")
    out["cenario"] = cenario.nome
    return out


def comparar_cenarios(base: pd.DataFrame, alterado: pd.DataFrame, nome: str) -> pd.DataFrame:
    idx = base.index.intersection(alterado.index)
    comp = pd.DataFrame({
        "ppi_current": base.loc[idx, "ppi_rs_t"],
        "ppi_cenario": alterado.loc[idx, "ppi_rs_t"],
        "status_current": base.loc[idx, "publication_status"],
        "status_cenario": alterado.loc[idx, "publication_status"],
    })
    comp["ppi_delta_pct"] = (comp["ppi_cenario"] / comp["ppi_current"] - 1) * 100
    comp["cenario"] = nome
    return comp


# =============================================================================
# 5. Real/nominal erosion (IPCA)
# =============================================================================

def erosao_real_ipca(desde: str = "2019-01-01") -> dict:
    """R$210/R$140 sao nominais desde a pesquisa original - quanto valem em
    termos reais hoje, deflacionados pelo IPCA acumulado (BCB/SGS 433,
    var. % mensal)? Consulta com janela de data explicita (nunca
    /ultimos/N)."""
    ipca_mensal = m.sgs(433, inicio=pd.Timestamp(desde).strftime("%d/%m/%Y"))
    fator_acumulado = (1 + ipca_mensal / 100).prod()
    return {
        "periodo": f"{desde[:7]} a {ipca_mensal.index.max():%Y-%m}",
        "ipca_acumulado_pct": (fator_acumulado - 1) * 100,
        "D_porto_valor_real_hoje": DEFAULT.despesas_porto_rs_t / fator_acumulado,
        "D_interno_valor_real_hoje": DEFAULT.frete_interno_rs_t / fator_acumulado,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    secao("1. CURRENT PARAMETER AUDIT")
    audit = auditar_parametros_atuais()
    print(audit.to_string(index=False))
    audit.to_csv(f"{OUT_DIR}/current_parameters.csv", index=False)

    secao("2. PORTOS/UFs RELEVANTES (Comex Stat, 2022-2026)")
    portos = portos_relevantes()
    print(portos.head(10).to_string(index=False))
    portos.to_csv(f"{OUT_DIR}/portos_relevantes.csv", index=False)

    secao("3. EROSAO REAL (IPCA) DOS PARAMETROS NOMINAIS")
    erosao = erosao_real_ipca()
    for k, v in erosao.items():
        print(f"  {k}: {v}")

    secao("4. BUSCANDO DADO BRUTO (Comex Stat, janela de publicacao)")
    df_bruto = m._comex_bobina_bruto(2019, 2026)
    print(f"  {len(df_bruto)} linhas brutas")
    full_idx = pd.date_range(JANELA_INI, JANELA_FIM, freq="MS")
    domestico_dummy = pd.DataFrame({"preco_rs_t": 1.0}, index=full_idx)

    secao("5. RODANDO CENARIOS (matriz principal: Low/Current/Evidence Base/High)")
    cenarios = montar_cenarios()
    resultados = {c.nome: rodar_cenario(df_bruto, c, domestico_dummy) for c in cenarios}
    base = resultados["Current"]

    resumo_matriz = []
    for c in cenarios:
        r = resultados[c.nome]
        comp = comparar_cenarios(base, r, c.nome)
        validos = comp.dropna(subset=["ppi_current", "ppi_cenario"])
        resumo_matriz.append({
            "scenario": c.nome, "D_porto": c.despesas_porto_rs_t, "D_interno": c.frete_interno_rs_t,
            "margem": c.margem_importador,
            "mean_ppi": r["ppi_rs_t"].mean(), "median_ppi": r["ppi_rs_t"].median(),
            "mean_delta_pct": validos["ppi_delta_pct"].mean(),
            "max_abs_delta_pct": validos["ppi_delta_pct"].abs().max(),
            "status_changed_months": int((validos["status_current"] != validos["status_cenario"]).sum()),
        })
    matriz = pd.DataFrame(resumo_matriz)
    print(matriz.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
    matriz.to_csv(f"{OUT_DIR}/scenario_matrix.csv", index=False)

    secao("6. IMPACTO NO IPIA (requer preco domestico - usa dummy constante so p/ status/threshold, nao para nivel real)")
    # Nota: sem o dominio do preco domestico real aqui (fora de escopo
    # desta calibracao de custo), o "IPIA" desta secao usa um preco
    # domestico CONSTANTE hipotetico so para testar threshold-crossing
    # mecanico do PPI isoladamente - nunca deve ser lido como IPIA real.
    preco_domestico_hipotetico = 4800.0
    for c in cenarios:
        r = resultados[c.nome].dropna(subset=["ppi_rs_t"])
        ipia_hipotetico = preco_domestico_hipotetico / r["ppi_rs_t"] * 100
        cruzamentos = ((ipia_hipotetico > 100) != (preco_domestico_hipotetico / base.loc[r.index, "ppi_rs_t"] * 100 > 100)).sum()
        print(f"  {c.nome:16s}  IPIA_hipotetico medio={ipia_hipotetico.mean():7.2f}  "
              f"threshold_crossings_vs_current={int(cruzamentos)}")

    secao("7. ISOLAMENTO ONE-AT-A-TIME")
    isolados = montar_cenarios_isolados()
    linhas_isolado = []
    for c in isolados:
        r = rodar_cenario(df_bruto, c, domestico_dummy)
        comp = comparar_cenarios(base, r, c.nome)
        validos = comp.dropna(subset=["ppi_current", "ppi_cenario"])
        linhas_isolado.append({"cenario": c.nome, "mean_delta_pct": validos["ppi_delta_pct"].mean(),
                                "max_abs_delta_pct": validos["ppi_delta_pct"].abs().max()})
    isolado_df = pd.DataFrame(linhas_isolado)
    print(isolado_df.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
    isolado_df.to_csv(f"{OUT_DIR}/isolamento_one_at_a_time.csv", index=False)

    secao("8. ELASTICIDADE APROXIMADA (%DeltaPPI / %Deltaparametro)")
    for nome, atual, alto in [("D_porto", DEFAULT.despesas_porto_rs_t, D_PORTO_HIGH),
                               ("D_interno", DEFAULT.frete_interno_rs_t, D_INTERNO_HIGH)]:
        pct_delta_param = (alto / atual - 1) * 100
        delta_ppi = isolado_df.loc[isolado_df["cenario"].str.startswith(nome), "mean_delta_pct"].iloc[0]
        elasticidade = delta_ppi / pct_delta_param
        print(f"  {nome}: %Deltaparametro={pct_delta_param:.1f}%  %DeltaPPI medio={delta_ppi:.4f}%  "
              f"elasticidade~={elasticidade:.4f}")
    # margem e um markup percentual, nao um R$/t - elasticidade expressa
    # em pontos percentuais de margem, nao %, conforme Sec.23 do sprint
    delta_margem_pp = (MARGEM_HIGH - DEFAULT.margem_importador) * 100
    delta_ppi_margem = isolado_df.loc[isolado_df["cenario"].str.startswith("Margem"), "mean_delta_pct"].iloc[0]
    print(f"  Margem: Deltamargem={delta_margem_pp:.2f}pp  %DeltaPPI medio={delta_ppi_margem:.4f}%  "
          f"sensibilidade~={delta_ppi_margem / delta_margem_pp:.4f}%%PPI por pp de margem")

    secao("FIM - artefatos salvos em " + OUT_DIR)


if __name__ == "__main__":
    main()
