#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATION + DIAGNOSTICS ONLY - nao imputa dado, nao altera PPI/IPIA/
publication status/VERSAO_METODOLOGIA/reporting.

Sprint "IPIA-HRC - MISSING DATA AUDIT", Pergunta B: quais dados realmente
faltam no pipeline do IPIA-HRC, por que faltam e quais prejudicam
materialmente o calculo/historico/analise? Reusa exclusivamente funcoes de
producao ja existentes (nunca reimplementa PIA/IPP/import-side) - so
adiciona a camada de inventario/classificacao/cobertura que nao existe em
nenhum script de producao.

Faz chamadas de rede reais (Comex Stat, BCB/SGS, IBGE/SIDRA) e le o CSV
curado local (nunca escreve nele). Toda saida vai para
data/processed/validation/ipia_hrc_missing_data/.

Uso:
    python scripts/auditar_ipia_hrc_missing.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd

import indices_setoriais as m

OUT_DIR = "data/processed/validation/ipia_hrc_missing_data"
JANELA_INI = "2019-01-01"
JANELA_FIM = "2026-07-01"

# =============================================================================
# Taxonomia de ausencia (Sec.20 do sprint)
# =============================================================================

TECHNICAL_MISSING = "A_TECHNICAL_MISSING"
ECONOMIC_NO_OBSERVATION = "B_ECONOMIC_NO_OBSERVATION"
FREQUENCY_MISMATCH = "C_FREQUENCY_MISMATCH"
PUBLICATION_LAG = "D_PUBLICATION_LAG"
HISTORICAL_UNAVAILABLE = "E_HISTORICAL_UNAVAILABLE"
STRUCTURAL_PARAMETER = "F_STRUCTURAL_PARAMETER"
TAXONOMIA = (TECHNICAL_MISSING, ECONOMIC_NO_OBSERVATION, FREQUENCY_MISMATCH,
             PUBLICATION_LAG, HISTORICAL_UNAVAILABLE, STRUCTURAL_PARAMETER)


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


def coverage_pct(n_observado: int, n_esperado: int) -> float:
    """% de cobertura - nunca None/0 quando n_esperado==0 (indefinido, nao zero)."""
    if n_esperado <= 0:
        return float("nan")
    return n_observado / n_esperado


def linha_cobertura(component: str, first, last, expected_freq: str,
                     n_observed: int, n_expected: int | None, missing_type: str,
                     nota: str = "") -> dict:
    """n_expected=None quando "observacao esperada" nao faz sentido para o
    componente (constante estrutural, benchmark de validacao independente
    sem cadencia obrigatoria) - Sec.21 do sprint pede que isso seja
    explicado, nunca forcado a um numero arbitrario."""
    if n_expected is None:
        n_missing, cobertura = None, float("nan")
    else:
        n_missing = max(n_expected - n_observed, 0)
        cobertura = coverage_pct(n_observed, n_expected)
    return {"component": component, "first": first, "last": last,
            "expected_freq": expected_freq, "observed": n_observed,
            "missing": n_missing, "coverage_pct": cobertura,
            "missing_type": missing_type, "nota": nota}


# =============================================================================
# 1. Import side
# =============================================================================

def diagnostico_import_side() -> tuple[pd.DataFrame, dict]:
    """Roda a serie completa IPIA-HRC V2 PIA-based (producao,
    `calcular_ipia_hrc_v2_pia`) so para ler os status ja calculados - nunca
    recalcula regra de politica comercial aqui."""
    serie = m.calcular_ipia_hrc_v2_pia(ano_ini=2019, ano_fim=2026)
    contagem = serie["publication_status"].value_counts().to_dict()
    return serie, contagem


# =============================================================================
# 2. Domestic side (PIA + IPP)
# =============================================================================

def diagnostico_domestic_side():
    pia = m.ibge_sidra_pia_hrc_anual()
    ipp = m.ibge_sidra_ipp_siderurgia()
    full_idx = pd.date_range(ipp.index.min(), ipp.index.max(), freq="MS")
    ipp_faltando = full_idx.difference(ipp.index)
    return pia, ipp, ipp_faltando


def diagnostico_corporate_anchor(caminho_csv: str = m.CAMINHO_PRECO_DOMESTICO_CSV):
    cur = pd.read_csv(caminho_csv)
    trimestres = sorted(cur["trimestre"].unique())
    return cur, trimestres


# =============================================================================
# 3. Matriz de cobertura (Sec.21)
# =============================================================================

def montar_matriz_cobertura(serie_import: pd.DataFrame, pia: pd.DataFrame,
                             ipp: pd.Series, ipp_faltando, trimestres_curado) -> pd.DataFrame:
    janela_meses = len(pd.date_range(JANELA_INI, JANELA_FIM, freq="MS"))
    contagem_import = serie_import["publication_status"].value_counts()
    n_import_calculavel = int(contagem_import.get("PUBLICATION_GRADE", 0)
                               + contagem_import.get("EXPERIMENTAL", 0)
                               + contagem_import.get("PROVISIONAL", 0))

    ref = pd.to_datetime(serie_import["reference_period"])
    linhas = [
        linha_cobertura("FOB/KG/frete/seguro (Comex Stat, bottom-up NCMxpaisxmes)",
                         f"{ref.min():%Y-%m}", f"{ref.max():%Y-%m}",
                         "mensal", len(serie_import), janela_meses, "-",
                         "cobertura de LINHAS retornadas pela fonte; ver import_status abaixo para calculabilidade real"),
        linha_cobertura("FX (BCB/SGS, media mensal)", "2019-01", "2026-07", "mensal (derivado de diario)",
                         janela_meses, janela_meses, "-", "calcular_fx_mensal levanta ValueError fail-fast se algum mes faltar - nunca chegou a faltar em producao"),
        linha_cobertura("II/AFRMM/antidumping (import_status calculavel)", "2019-02", "2023-12 (OFFICIAL) / 2026-06+ (PROVISIONAL)",
                         "mensal", n_import_calculavel, janela_meses, "-",
                         f"UNKNOWN={int(contagem_import.get('UNKNOWN', 0))} meses (policy_coverage<60% ou <100% na janela publication-grade) - ver auditoria dedicada"),
        linha_cobertura("PIA-HRC (IBGE/SIDRA 7752)", str(pia.index.min()), str(pia.index.max()),
                         "anual", len(pia), pia.index.max() - pia.index.min() + 1, PUBLICATION_LAG,
                         f"ultimo ano observado={pia.index.max()}; anos {pia.index.max()+1}+ sao D_PUBLICATION_LAG, nunca imputados"),
        linha_cobertura("IPP 242-Siderurgia (IBGE/SIDRA 6723)", str(ipp.index.min())[:7], str(ipp.index.max())[:7],
                         "mensal", len(ipp), len(ipp) + len(ipp_faltando), "-" if len(ipp_faltando) == 0 else TECHNICAL_MISSING,
                         "zero meses faltando na janela observada" if len(ipp_faltando) == 0 else f"{len(ipp_faltando)} meses faltando"),
        linha_cobertura("Corporate anchor (Usiminas+CSN curado)", trimestres_curado[0], trimestres_curado[-1],
                         "trimestral", len(trimestres_curado), None, "-",
                         "benchmark de validacao independente, NUNCA usado para calibrar a serie oficial (ADR 0010) - cobertura curta e esperada, nao um defeito"),
        linha_cobertura("D_porto / D_interno / margem (ParamsIPIA)", "n/a", "n/a", "n/a (constante)",
                         0, None, STRUCTURAL_PARAMETER,
                         "nao sao series observadas - parametros hold-flat unicos (METODOLOGIA Sec.9.8/9.9), 'expected observation' nao se aplica"),
        linha_cobertura("Benchmark externo (UN Comtrade, sprint anterior)", "2019-01", "2024-12",
                         "mensal", 72, janela_meses, PUBLICATION_LAG,
                         "so validation reference (nunca produto oficial) - defasagem de publicacao da fonte chinesa, nao um gap do projeto"),
    ]
    return pd.DataFrame(linhas)


# =============================================================================
# 4. Matriz mensal (month x component) - Sec.22
# =============================================================================

def montar_matriz_mensal(serie_import: pd.DataFrame, pia: pd.DataFrame, ipp: pd.Series) -> pd.DataFrame:
    idx = pd.date_range(JANELA_INI, JANELA_FIM, freq="MS")
    df = pd.DataFrame(index=idx)
    df.index.name = "reference_period"

    imp = serie_import.set_index(pd.to_datetime(serie_import["reference_period"]))["publication_status"]
    mapa_import = {"PUBLICATION_GRADE": "OBSERVED", "EXPERIMENTAL": "ESTIMATED",
                   "PROVISIONAL": "ESTIMATED", "UNKNOWN": "MISSING"}
    df["import_side"] = imp.reindex(idx).map(mapa_import).fillna("MISSING")

    ultimo_ano_pia = pia.index.max()
    def status_domestico(dt):
        if dt.year <= ultimo_ano_pia and dt >= pd.Timestamp("2019-02-01"):
            return "CALCULATED"  # ancora PIA + Denton, benchmarked
        if dt.year > ultimo_ano_pia:
            return "PROVISIONAL"  # extensao pos-ultima-PIA
        return "MISSING"  # 2019-01: antes do primeiro mes benchmarked
    df["domestic_pia"] = [status_domestico(dt) for dt in idx]

    df["ipp_242"] = ["OBSERVED" if dt in ipp.index else "MISSING" for dt in idx]
    df["structural_params"] = "NOT_APPLICABLE"  # constantes, nao series - nunca "missing"

    return df


# =============================================================================
# 5. Model-imputation candidates (Sec.28) - so classificacao, YES/NO/MAYBE
# =============================================================================

def candidatos_imputacao() -> pd.DataFrame:
    linhas = [
        {"componente": "Comex Stat FOB/KG (mes com policy_coverage<60%, EXPERIMENTAL)",
         "tipo": TECHNICAL_MISSING, "model_imputation_suitable": "NO",
         "justificativa": "o dado de comercio EXISTE (o mes tem volume observado); o que falta e a POLITICA (II individual do NCM), nao o preco/volume - imputacao nao resolve uma lacuna regulatoria; a acao correta e pesquisa documental adicional (ADR 0009), nao modelagem estatistica"},
        {"componente": "Mes/NCM/pais sem nenhum registro (kg=0 implicito)",
         "tipo": ECONOMIC_NO_OBSERVATION, "model_imputation_suitable": "NO",
         "justificativa": "ausencia de evento economico nao e uma lacuna de dado - nao houve importacao daquela combinacao; imputar inventaria um fluxo comercial que nao ocorreu"},
        {"componente": "PIA anual -> preco mensal", "tipo": FREQUENCY_MISMATCH,
         "model_imputation_suitable": "MAYBE (ja resolvido por Denton)",
         "justificativa": "temporal disaggregation ja e o metodo em producao (Proportional Denton, ADR 0010) - nao e um gap em aberto, e a solucao ja aprovada para este tipo de ausencia"},
        {"componente": "PIA do ano corrente (2024+, ainda nao publicada)",
         "tipo": PUBLICATION_LAG, "model_imputation_suitable": "MAYBE",
         "justificativa": "ja existe uma extensao model-assisted (encadeamento pelo IPP a partir do ultimo ano PIA, is_provisional=True, ESTIMADO) - um modelo probabilistico mais sofisticado (state-space/Kalman) poderia dar uma banda de incerteza explicita em vez de um ponto unico, candidato razoavel a pesquisa futura, nao substitui o mecanismo atual"},
        {"componente": "II individual dos 9 NCMs nao comprovados, 2012-01 a 2022-03",
         "tipo": HISTORICAL_UNAVAILABLE, "model_imputation_suitable": "MAYBE",
         "justificativa": "e um parametro REGULATORIO (uma decisao de politica publica), nao uma serie estocastica - um modelo estatistico nao pode 'prever' que aliquota a CAMEX decidiu; o candidato realista e pesquisa documental adicional (Diario Oficial/Camex), nao ARMA/Kalman"},
        {"componente": "D_porto / D_interno / margem (constantes hold-flat)",
         "tipo": STRUCTURAL_PARAMETER, "model_imputation_suitable": "NO",
         "justificativa": "nao sao series com historico a reconstruir - sao parametros de calibracao unica (contato com despachantes aduaneiros, ja recomendado na pesquisa original, METODOLOGIA Sec.9.9); um motor ARMA/GARCH nao se aplica a uma constante"},
        {"componente": "Corporate anchor (Usiminas+CSN) fora de 2025Q2-2026Q2",
         "tipo": HISTORICAL_UNAVAILABLE, "model_imputation_suitable": "NO",
         "justificativa": "e so um benchmark de validacao independente, nunca a serie oficial - estender via modelo daria a falsa impressao de uma segunda fonte observada quando na verdade seria so o proprio IPP reaplicado"},
    ]
    return pd.DataFrame(linhas)


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    secao("1. IMPORT SIDE (producao: calcular_ipia_hrc_v2_pia)")
    serie_import, contagem_import = diagnostico_import_side()
    print(f"{len(serie_import)} meses, {serie_import['reference_period'].min()} a {serie_import['reference_period'].max()}")
    print(pd.Series(contagem_import))
    serie_import.to_csv(f"{OUT_DIR}/serie_import_side_completa.csv", index=False)
    unk = serie_import[serie_import["publication_status"] == "UNKNOWN"]
    print("\nMeses UNKNOWN:")
    print(unk[["reference_period", "total_kg", "known_policy_kg", "policy_coverage"]].to_string(index=False))

    secao("2. DOMESTIC SIDE (PIA + IPP)")
    pia, ipp, ipp_faltando = diagnostico_domestic_side()
    print(f"PIA: {pia.index.min()}-{pia.index.max()} ({len(pia)} anos)")
    print(f"IPP: {ipp.index.min():%Y-%m} a {ipp.index.max():%Y-%m} ({len(ipp)} meses), faltando={len(ipp_faltando)}")

    secao("3. CORPORATE ANCHOR (curado)")
    cur, trimestres = diagnostico_corporate_anchor()
    print(f"{len(cur)} linhas, trimestres: {trimestres}")

    secao("4. MATRIZ DE COBERTURA POR COMPONENTE")
    matriz = montar_matriz_cobertura(serie_import, pia, ipp, ipp_faltando, trimestres)
    print(matriz.to_string(index=False))
    matriz.to_csv(f"{OUT_DIR}/matriz_cobertura.csv", index=False)

    secao("5. MATRIZ MENSAL (month x component)")
    mensal = montar_matriz_mensal(serie_import, pia, ipp)
    print(mensal.tail(10).to_string())
    mensal.to_csv(f"{OUT_DIR}/matriz_mensal.csv")
    print("\nDistribuicao de status por componente:")
    for col in ("import_side", "domestic_pia", "ipp_242"):
        print(f"  {col}: {mensal[col].value_counts().to_dict()}")

    secao("6. MODEL-IMPUTATION CANDIDATES")
    cand = candidatos_imputacao()
    print(cand[["componente", "tipo", "model_imputation_suitable"]].to_string(index=False))
    cand.to_csv(f"{OUT_DIR}/candidatos_imputacao.csv", index=False)

    secao("FIM - artefatos salvos em " + OUT_DIR)


if __name__ == "__main__":
    main()
