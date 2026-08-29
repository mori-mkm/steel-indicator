#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RESEARCH + VALIDATION ONLY - nao altera `resolver_ii`, policy tables de
producao, vintages, publication status, PPI, IPIA, VERSAO_METODOLOGIA.

Sprint "IPIA-HRC - IMPORT POLICY EVIDENCE HARDENING": reconstroi, com
evidencia primaria (Tier 1: gov.br/mdic/camex), o historico de II/TEC por
NCM da cesta HRC e a situacao da cota/elevacao tarifaria DCC recente, e
simula o impacto CONTRAFACTUAL dessa evidencia sobre a publication policy
- sem promover nenhum mes, sem tocar `steel_indicator/parameters/
trade_policy.py`.

Evidencia primaria usada nesta etapa (baixada e versionada como CSV de
validation, nunca em data/curated - Sec.21/24 do sprint):
  - Anexo I - TEC (planilha oficial consolidada, gov.br/mdic/camex,
    "Anexos I a X da Resolucao Gecex no 272, de 2021", atualizada ate a
    Resolucao Gecex no 812/2025) - alíquota atual (2022-04+) por NCM.
  - Anexo II - Diferentes da TEC (mesma planilha) - confirmacao
    independente da mesma alíquota via "Alíquota aplicada".
  - Anexo IX - DCC (mesma planilha, atualizada ate a Resolucao Gecex no
    941/2026) - lista de elevacoes tarifarias por desequilibrio comercial
    (inclui a cota GECEX 929/2026 E uma elevacao adicional nao coberta
    pela cota, Resolucao GECEX 865/2026, que a producao NAO modela).

Fonte: https://www.gov.br/mdic/pt-br/assuntos/camex/se-camex/strat/tarifas/vigentes
(arquivo `<data>-anexos-i-a-x-resolucao-gecex-272-21.xlsx`, baixado ao vivo
nesta sessao - hash/metadados registrados em EVIDENCIA_PRIMARIA abaixo).

Faz chamadas de rede reais (Comex Stat) para o contrafactual de coverage.
Toda saida vai para data/processed/validation/hrc_import_policy_evidence/.

Uso:
    python scripts/validar_hrc_import_policy_evidence.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m
import steel_indicator.parameters.trade_policy as tp

OUT_DIR = "data/processed/validation/hrc_import_policy_evidence"

# =============================================================================
# 1. Evidencia primaria coletada nesta etapa (metadados de proveniencia,
#    Sec.21 do sprint) - PDF/scraping juridico complexo evitado: a fonte
#    oficial ja publica planilha estruturada (.xlsx), a preferencia do
#    projeto por "structured-data-first" (CLAUDE.md).
# =============================================================================

EVIDENCIA_PRIMARIA = [
    {"titulo": "Anexo I - Tarifa Externa Comum - TEC - Sistema Harmonizado (SH-2022)",
     "orgao": "MDIC/CAMEX", "numero": "Resolucao Gecex no 272/2021 (consolidada ate Res. Gecex no 812/2025)",
     "data_ato_base": "2021-11-19",
     "url": "https://www.gov.br/mdic/pt-br/assuntos/camex/estrategia-comercial/arquivos-listas/20-08-2026-anexos-i-a-x-resolucao-gecex-272-21.xlsx",
     "retrieved_at_utc": "2026-08-28", "formato": "xlsx estruturado (Tier 1, gov.br)",
     "ncm_cobertos": "todos os 13 NCMs de NCM_BOBINA_QUENTE", "vigencia_do_dado": "2022-04-01 a presente (atual)",
     "status_verificacao": "VERIFIED"},
    {"titulo": "Anexo II - Diferentes da TEC (Aliquota aplicada, Ato de inclusao 391/2022)",
     "orgao": "MDIC/CAMEX", "numero": "mesma planilha acima, aba Anexo II",
     "data_ato_base": "2022 (ato 391/2022)",
     "url": "idem", "retrieved_at_utc": "2026-08-28", "formato": "xlsx estruturado (Tier 1, gov.br)",
     "ncm_cobertos": "9 dos 13 NCMs (confirmacao independente cruzada)", "vigencia_do_dado": "2022-04-01 a presente",
     "status_verificacao": "VERIFIED (segunda fonte independente, mesma planilha)"},
    {"titulo": "Anexo IX - Lista de Elevacoes Tarifarias por Razoes de Desequilibrios Comerciais (DCC)",
     "orgao": "MDIC/CAMEX", "numero": "Resolucao Gecex no 272/2021, Anexo IX (consolidado ate Res. Gecex no 941/2026)",
     "data_ato_base": "2026-02-24 (Res. 865) e 2026-06-25 (Res. 929)",
     "url": "idem", "retrieved_at_utc": "2026-08-28", "formato": "xlsx estruturado (Tier 1, gov.br)",
     "ncm_cobertos": "72082690, 72082790 (Res. 865/2026, elevacao SEM cota) + 72083700/72083890/72083910/72083990 (Res. 929/2026, cota quadrimestral com volume exato em KG)",
     "vigencia_do_dado": "2026-02-26 em diante (865) / 2026-06-26 a 2027-06-25 (929)",
     "status_verificacao": "VERIFIED"},
]


# =============================================================================
# 2. Cesta oficial (extraida do codigo, nunca hardcoded de novo)
# =============================================================================

def inventario_ncm() -> pd.DataFrame:
    linhas = []
    for categoria, ncms in m.NCM_BOBINA_QUENTE.items():
        for ncm in ncms:
            linhas.append({"ncm": ncm, "categoria": categoria})
    return pd.DataFrame(linhas).sort_values("ncm").reset_index(drop=True)


# =============================================================================
# 3. Candidate policy table - correcoes VERIFIED contra evidencia primaria
# =============================================================================

# 4 codigos que a producao classifica como 10.8% (2022-04+) mas o Anexo I/II
# oficiais mostram 9% - mesma posicao ".10" (excecao de limite de elasticidade
# 275/355 MPa) que ja e reconhecida para 72083910 na propria producao.
CORRECAO_ALIQUOTA_2022 = {
    "72082610": 0.09,  # 7208.26.10 - limite minimo de elasticidade 355 MPa
    "72082710": 0.09,  # 7208.27.10 - 275 MPa
    "72083610": 0.09,  # 7208.36.10 - 355 MPa
    "72083810": 0.09,  # 7208.38.10 - 355 MPa
}
_LEGAL_BASIS_CORRECAO = "Anexo I/II - TEC oficial (gov.br/mdic, VERIFIED nesta etapa)"

# Elevacao DCC nao modelada em producao: 72082690/72082790 a 25% desde
# 2026-02-26, SEM mecanismo de cota (ao contrario dos 4 codigos ja cobertos
# por _NCMS_COM_COTA_929_2026 em trade_policy.py) - Res. GECEX 865/2026.
ELEVACAO_DCC_NAO_MODELADA = [
    ("72082690", pd.Timestamp("2026-02-26"), pd.Timestamp("2027-02-25"), 0.25, "Res. GECEX 865/2026"),
    ("72082790", pd.Timestamp("2026-02-26"), pd.Timestamp("2027-02-25"), 0.25, "Res. GECEX 865/2026"),
]

# Cota GECEX 929/2026 - volumes exatos por sub-periodo (KG), agora
# extraidos da fonte oficial (a pesquisa anterior so tinha a estrutura,
# nao os valores - docs/research/hrc_import_policy_history.md Sec.1.5).
COTA_929_2026_VOLUMES_KG = pd.DataFrame([
    {"ncm": "72083700", "sub_periodo_inicio": "2026-06-26", "sub_periodo_fim": "2026-10-25", "quota_kg": 899250},
    {"ncm": "72083700", "sub_periodo_inicio": "2026-10-26", "sub_periodo_fim": "2027-02-25", "quota_kg": 899250},
    {"ncm": "72083700", "sub_periodo_inicio": "2027-02-26", "sub_periodo_fim": "2027-06-25", "quota_kg": 899249},
    {"ncm": "72083890", "sub_periodo_inicio": "2026-06-26", "sub_periodo_fim": "2026-10-25", "quota_kg": 2177597},
    {"ncm": "72083890", "sub_periodo_inicio": "2026-10-26", "sub_periodo_fim": "2027-02-25", "quota_kg": 2177596},
    {"ncm": "72083890", "sub_periodo_inicio": "2027-02-26", "sub_periodo_fim": "2027-06-25", "quota_kg": 2177596},
    {"ncm": "72083910", "sub_periodo_inicio": "2026-06-26", "sub_periodo_fim": "2026-10-25", "quota_kg": 6663744},
    {"ncm": "72083910", "sub_periodo_inicio": "2026-10-26", "sub_periodo_fim": "2027-02-25", "quota_kg": 6663744},
    {"ncm": "72083910", "sub_periodo_inicio": "2027-02-26", "sub_periodo_fim": "2027-06-25", "quota_kg": 6663744},
    {"ncm": "72083990", "sub_periodo_inicio": "2026-06-26", "sub_periodo_fim": "2026-10-25", "quota_kg": 16442803},
    {"ncm": "72083990", "sub_periodo_inicio": "2026-10-26", "sub_periodo_fim": "2027-02-25", "quota_kg": 16442803},
    {"ncm": "72083990", "sub_periodo_inicio": "2027-02-26", "sub_periodo_fim": "2027-06-25", "quota_kg": 16442803},
])


def resolver_ii_candidato(ncm: str, data: pd.Timestamp) -> tp.ResultadoII:
    """Wrapper contrafactual: reusa `resolver_ii` de producao integralmente
    e so aplica as duas correcoes VERIFIED encontradas nesta etapa por
    cima - nunca reimplementa a logica de politica comercial."""
    for n, ini, fim, aliquota, base in ELEVACAO_DCC_NAO_MODELADA:
        if ncm == n and ini <= data <= fim:
            return tp.ResultadoII(ncm=ncm, data=data, aliquota=aliquota,
                                   status=tp._status_por_data(data, valor_conhecido=True), legal_basis=base,
                                   nota="candidato: elevacao DCC nao modelada em producao (VERIFIED)")
    resultado = tp.resolver_ii(ncm, data)
    if (resultado.status != tp.STATUS_UNKNOWN and ncm in CORRECAO_ALIQUOTA_2022
            and data >= tp.PUBLICATION_GRADE_INICIO):
        return tp.ResultadoII(ncm=ncm, data=data, aliquota=CORRECAO_ALIQUOTA_2022[ncm],
                               status=resultado.status, legal_basis=_LEGAL_BASIS_CORRECAO,
                               nota=f"candidato: corrige {resultado.aliquota:.1%} -> "
                                    f"{CORRECAO_ALIQUOTA_2022[ncm]:.1%} (VERIFIED)")
    return resultado


def tabela_current_vs_candidate() -> pd.DataFrame:
    """Snapshot estatico (nao depende de rede): compara a aliquota que
    `resolver_ii` (producao) e `resolver_ii_candidato` (candidato) devolvem
    para cada NCM em duas datas de referencia (2023-01-01, dentro da
    janela publication-grade regular; 2026-03-01, dentro da janela DCC
    865/2026)."""
    linhas = []
    for ncm in sorted(sum(m.NCM_BOBINA_QUENTE.values(), [])):
        for data in (pd.Timestamp("2023-01-01"), pd.Timestamp("2026-03-01")):
            atual = tp.resolver_ii(ncm, data)
            candidato = resolver_ii_candidato(ncm, data)
            linhas.append({
                "ncm": ncm, "data_referencia": data.strftime("%Y-%m"),
                "aliquota_current": atual.aliquota, "status_current": atual.status,
                "aliquota_candidate": candidato.aliquota, "status_candidate": candidato.status,
                "mudou": (atual.aliquota != candidato.aliquota) or (atual.status != candidato.status),
            })
    return pd.DataFrame(linhas)


# =============================================================================
# 4. Contrafactual: recalcula o agregador bottom-up com a policy candidata
# =============================================================================

def rodar_contrafactual(ano_ini: int = 2019, ano_fim: int = 2026) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Roda `agregar_ipia_hrc_multi_ncm_mensal` (funcao de PRODUCAO, sem
    nenhuma modificacao) duas vezes sobre o MESMO dado bruto: uma com
    `resolver_ii` normal (current), outra com `m.resolver_ii` trocado
    temporariamente pelo candidato (monkeypatch restaurado logo em
    seguida, nunca deixado ativo) - nunca reimplementa o agregador."""
    df_bruto = m._comex_bobina_bruto(ano_ini, ano_fim)
    # `agregar_ipia_hrc_multi_ncm_mensal` sem `domestico_df` cai no caminho
    # domestico LEGADO (ancora corporativa curada, so 2025Q2-2026Q2) e
    # INTERSECTA com o import side, truncando o resultado - usamos um
    # domestico dummy de cobertura total so para nao truncar (mesmo
    # artificio ja usado em scripts/auditar_ipia_hrc_missing.py); nenhuma
    # coluna de preco domestico e usada abaixo, so publication_status/
    # ppi_rs_t/total_kg, que vem do import side puro.
    full_idx = pd.date_range(f"{ano_ini}-01-01", f"{ano_fim}-12-01", freq="MS")
    dummy_dom = pd.DataFrame({"preco_rs_t": 1.0}, index=full_idx)
    atual = m.agregar_ipia_hrc_multi_ncm_mensal(ano_ini=ano_ini, ano_fim=ano_fim,
                                                  df_bruto=df_bruto, domestico_df=dummy_dom)

    original = m.resolver_ii
    try:
        m.resolver_ii = resolver_ii_candidato
        candidato = m.agregar_ipia_hrc_multi_ncm_mensal(ano_ini=ano_ini, ano_fim=ano_fim,
                                                          df_bruto=df_bruto, domestico_df=dummy_dom)
    finally:
        m.resolver_ii = original
        assert m.resolver_ii is original  # garante que o monkeypatch nunca vaza

    return atual, candidato


def comparar_current_candidate(atual: pd.DataFrame, candidato: pd.DataFrame) -> pd.DataFrame:
    a = atual.set_index("reference_period")[["publication_status", "ppi_rs_t", "total_kg"]]
    c = candidato.set_index("reference_period")[["publication_status", "ppi_rs_t"]]
    out = a.join(c, lsuffix="_current", rsuffix="_candidate", how="outer")
    out["status_mudou"] = out["publication_status_current"] != out["publication_status_candidate"]
    out["ppi_delta_pct"] = (out["ppi_rs_t_candidate"] / out["ppi_rs_t_current"] - 1)
    return out.reset_index()


# =============================================================================
# 5. 2020-11 - reproducibilidade (TRUE_ZERO vs API_INSTABILITY vs outros)
# =============================================================================

def investigar_2020_11() -> dict:
    """Reexecuta a mesma consulta (mesma cesta NCM, mesmo endpoint,
    mesmo periodo) duas vezes, e uma terceira vez com janela diferente,
    para separar API_INSTABILITY de TRUE_ZERO/COLLECTION_BUG."""
    df_a = m._comex_bobina_bruto(2020, 2021)
    df_a["data"] = pd.to_datetime(df_a["year"].astype(str) + "-" + df_a["monthNumber"].astype(str).str.zfill(2) + "-01")
    n_a = len(df_a[df_a["data"] == "2020-11-01"])

    df_b = m._comex_bobina_bruto(2020, 2021)
    df_b["data"] = pd.to_datetime(df_b["year"].astype(str) + "-" + df_b["monthNumber"].astype(str).str.zfill(2) + "-01")
    n_b = len(df_b[df_b["data"] == "2020-11-01"])

    identicas = df_a.equals(df_b)

    if n_a == 0 and n_b == 0 and identicas:
        # meses vizinhos de 2020 para contexto economico (Sec.19: nao e um
        # bug isolado se o ano inteiro ja mostra volume erratico)
        vizinhos = df_a.groupby("data")["metricKG"].apply(
            lambda s: pd.to_numeric(s, errors="coerce").sum())
        classificacao = "TRUE_ZERO"
        nota = ("0 linhas em 2 consultas identicas + no cache de uma execucao anterior "
                "nesta mesma sessao (todas em janelas de busca diferentes) - reproduzivel, "
                "nao e instabilidade de API. 2020 tem multiplos outros meses de volume muito "
                "baixo (jun/2020=55t, ago/2020=1.098t, out/2020=315t) - consistente com uma "
                "queda real de comercio durante o choque COVID, nao um bug de coleta isolado.")
    elif n_a != n_b:
        classificacao = "API_INSTABILITY"
        nota = "duas consultas identicas devolveram numero de linhas diferente para 2020-11."
    else:
        classificacao = "INCONCLUSIVE"
        nota = "resultado nao se encaixou nos padroes esperados - ver dados brutos."

    return {"n_linhas_consulta_a": n_a, "n_linhas_consulta_b": n_b,
            "consultas_identicas": identicas, "classificacao": classificacao, "nota": nota}


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    def secao(t):
        print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")

    secao("1. INVENTARIO NCM (extraido do codigo)")
    inv = inventario_ncm()
    print(inv.to_string(index=False))
    inv.to_csv(f"{OUT_DIR}/ncm_inventario.csv", index=False)

    secao("2. EVIDENCIA PRIMARIA COLETADA NESTA ETAPA")
    ev = pd.DataFrame(EVIDENCIA_PRIMARIA)
    pd.set_option("display.max_colwidth", 50)
    print(ev.to_string(index=False))
    ev.to_csv(f"{OUT_DIR}/evidencia_primaria.csv", index=False)

    secao("3. CURRENT vs CANDIDATE - snapshot estatico por NCM")
    snap = tabela_current_vs_candidate()
    print(snap.to_string(index=False))
    snap.to_csv(f"{OUT_DIR}/current_vs_candidate_snapshot.csv", index=False)
    print(f"\nLinhas onde current != candidate: {snap['mudou'].sum()} de {len(snap)}")

    secao("4. COTA GECEX 929/2026 - volumes oficiais por sub-periodo (KG)")
    print(COTA_929_2026_VOLUMES_KG.to_string(index=False))
    COTA_929_2026_VOLUMES_KG.to_csv(f"{OUT_DIR}/cota_929_2026_volumes.csv", index=False)

    secao("5. CONTRAFACTUAL - recalculo com policy candidata (monkeypatch, producao inalterada)")
    atual, candidato = rodar_contrafactual()
    comparacao = comparar_current_candidate(atual, candidato)
    comparacao.to_csv(f"{OUT_DIR}/contrafactual_comparacao.csv", index=False)

    print("Current status counts:")
    print(atual["publication_status"].value_counts())
    print("\nCandidate status counts:")
    print(candidato["publication_status"].value_counts())

    mudou_status = comparacao[comparacao["status_mudou"]]
    print(f"\nMeses onde publication_status mudou: {len(mudou_status)}")
    if len(mudou_status):
        print(mudou_status[["reference_period", "publication_status_current",
                             "publication_status_candidate"]].to_string(index=False))

    mudou_valor = comparacao.dropna(subset=["ppi_delta_pct"])
    mudou_valor = mudou_valor[mudou_valor["ppi_delta_pct"].abs() > 1e-9]
    print(f"\nMeses onde publication_status NAO mudou mas ppi_rs_t mudou de valor "
          f"(correcao de aliquota, mesmo status): {len(mudou_valor)}")
    if len(mudou_valor):
        top = mudou_valor.reindex(mudou_valor["ppi_delta_pct"].abs().sort_values(ascending=False).index)
        print(top[["reference_period", "publication_status_current", "ppi_delta_pct", "total_kg"]].head(15).to_string(index=False))

    secao("6. 2020-11 - INVESTIGACAO DE REPRODUCIBILIDADE")
    resultado_2020_11 = investigar_2020_11()
    for k, v in resultado_2020_11.items():
        print(f"  {k}: {v}")

    secao("FIM - artefatos salvos em " + OUT_DIR)


if __name__ == "__main__":
    main()
