#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VALIDATION ONLY - nao altera Denton, preco domestico oficial, vintages,
formula do IPIA, VERSAO_METODOLOGIA nem reporting.

Valida empiricamente se o IPP 242-Siderurgia (`ibge_sidra_ipp_siderurgia`)
carrega sinal util sobre a dinamica de preco do HRC, medido contra a
PIA-Produto HRC (`ibge_sidra_pia_hrc_anual`) - a pergunta que sustenta o
uso do IPP como indicador de alta frequencia dentro do Proportional
Denton (`denton_proporcional`, ADR 0010).

Reusa as funcoes de producao para buscar/calcular tudo (nunca reimplementa
Denton, nunca refaz a chamada da PIA/IPP com parametros proprios) - so
adiciona a camada de comparacao/estatistica que nao existe em nenhum
script de producao.

Faz chamadas de rede reais (IBGE/SIDRA) e le o CSV curado local
(data/curated/preco_domestico_aco.csv) - nunca escreve nele. Toda saida
vai para data/processed/validation/ipp242_pia_hrc/ (validation artifact,
nunca confundido com data/curated nem com uma vintage).

Uso:
    python scripts/validar_ipp242_pia_hrc.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

import indices_setoriais as m

OUT_DIR = "data/processed/validation/ipp242_pia_hrc"


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


# =============================================================================
# 1. Series reais (confirmadas direto no codigo/dado, nao so na documentacao)
# =============================================================================

def buscar_series():
    pia = m.ibge_sidra_pia_hrc_anual()
    ipp = m.ibge_sidra_ipp_siderurgia()
    return pia, ipp


def tabela_series(pia: pd.DataFrame, ipp: pd.Series) -> pd.DataFrame:
    anos_ipp_completos = sorted({ano for ano, g in ipp.groupby(ipp.index.year) if len(g) == 12})
    linhas = [
        {"serie": "PIA-HRC (preco implicito)", "fonte": "IBGE/SIDRA", "codigo": "tabela 7752, categoria 54849 (Prodlist 2422.2020)",
         "frequencia": "Anual", "unidade": "R$/t (nominal, receita/volume)",
         "cobertura": f"{pia.index.min()}-{pia.index.max()} ({len(pia)} anos)",
         "papel": "Ancora de nivel (benchmark anual do Denton)"},
        {"serie": "IPP 242-Siderurgia", "fonte": "IBGE/SIDRA", "codigo": "tabela 6723, classificacao 844[47259]",
         "frequencia": "Mensal", "unidade": "numero-indice (dez/2018=100, nominal)",
         "cobertura": f"{ipp.index.min():%Y-%m} a {ipp.index.max():%Y-%m}, {len(anos_ipp_completos)} ano(s) com 12 meses completos ({anos_ipp_completos[0]}-{anos_ipp_completos[-1]})",
         "papel": "Indicador de movimento intra-ano (Proportional Denton)"},
    ]
    return pd.DataFrame(linhas)


# =============================================================================
# 2. Series anuais comparaveis (variacao, nao nivel)
# =============================================================================

def ipp_anual_media(ipp: pd.Series) -> pd.Series:
    """A - media aritmetica do indice dentro do ano civil, so para anos com
    os 12 meses presentes (nunca extrapola um ano parcial)."""
    completos = {ano for ano, g in ipp.groupby(ipp.index.year) if len(g) == 12}
    media = ipp.groupby(ipp.index.year).mean()
    return media.loc[sorted(completos)]


def ipp_anual_dez_dez(ipp: pd.Series) -> pd.Series:
    """C - robustness: valor do proprio mes de dezembro de cada ano (nao
    precisa do ano completo, so do mes de dezembro existir)."""
    dez = ipp[ipp.index.month == 12]
    return dez.groupby(dez.index.year).first()


def crescimento_anual(nivel: pd.Series) -> pd.Series:
    """g(t) = nivel(t)/nivel(t-1) - 1, so para anos consecutivos presentes."""
    s = nivel.sort_index()
    g = {}
    for ano in s.index:
        if (ano - 1) in s.index:
            g[ano] = s.loc[ano] / s.loc[ano - 1] - 1.0
    return pd.Series(g).sort_index()


def ipp_crescimento_media_de_yoy_mensal(ipp: pd.Series) -> pd.Series:
    """B - robustness: media, dentro do ano, das variacoes YoY mes a mes do
    proprio IPP (12 razoes mes(t)/mes(t-12) por ano, quando disponiveis) -
    alternativa a "crescimento da media anual" que pondera igualmente cada
    mes em vez de deixar a media anual absorver a forma intra-ano."""
    yoy_mensal = ipp / ipp.shift(12) - 1.0
    yoy_mensal = yoy_mensal.dropna()
    completos = {ano for ano, g in yoy_mensal.groupby(yoy_mensal.index.year) if len(g) == 12}
    return yoy_mensal.groupby(yoy_mensal.index.year).mean().loc[sorted(completos)]


# =============================================================================
# 3. Correlacao, direcao, beta, leave-one-out
# =============================================================================

def alinhar(g_pia: pd.Series, g_ipp: pd.Series) -> pd.DataFrame:
    anos = sorted(set(g_pia.index) & set(g_ipp.index))
    return pd.DataFrame({"g_pia": g_pia.loc[anos], "g_ipp": g_ipp.loc[anos]}, index=anos)


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return float("nan")
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    return pearson(rx, ry)


def direcao_tabela(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["mesmo_sinal"] = np.sign(out["g_pia"]) == np.sign(out["g_ipp"])
    out["diff_pp"] = (out["g_pia"] - out["g_ipp"]) * 100.0
    return out


def beta_simples(df: pd.DataFrame) -> float:
    """beta = cov(g_pia, g_ipp)/var(g_ipp) - regressao simples g_pia ~ g_ipp,
    diagnostico (nunca usado para recalibrar nada)."""
    if len(df) < 2 or df["g_ipp"].var() == 0:
        return float("nan")
    return float(np.cov(df["g_pia"], df["g_ipp"])[0, 1] / df["g_ipp"].var())


def leave_one_out(df: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for ano_removido in df.index:
        resto = df.drop(index=ano_removido)
        linhas.append({
            "ano_removido": ano_removido, "n": len(resto),
            "pearson": pearson(resto["g_pia"].to_numpy(), resto["g_ipp"].to_numpy()),
            "spearman": spearman(resto["g_pia"].to_numpy(), resto["g_ipp"].to_numpy()),
            "directional_accuracy": resto["mesmo_sinal"].mean() if "mesmo_sinal" in resto else
                (np.sign(resto["g_pia"]) == np.sign(resto["g_ipp"])).mean(),
        })
    return pd.DataFrame(linhas).set_index("ano_removido")


# =============================================================================
# 4. Corporate anchor - reproducao + ressalva de contaminacao por IPP
#    compartilhado + checagem trimestral independente (pre-IPP)
# =============================================================================

def comparacao_mensal_corporate_vs_pia(pia: pd.DataFrame, ipp: pd.Series) -> pd.DataFrame:
    """Reproduz a comparacao ja existente (Stage G3,
    docs/validation/ipia_hrc_v2_final_validation.md secao 4) - AMBAS as
    series usam ibge_sidra_ipp_siderurgia() para encadear mes a mes, entao
    NAO e um teste independente do IPP (ver ressalva no relatorio)."""
    corporate = m.preco_domestico_hrc_mensal_v2(ipp_mensal=ipp)
    pia_mensal = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)
    if corporate.empty or pia_mensal.empty:
        return pd.DataFrame()
    c = corporate.set_index("reference_period")["preco_domestico_rs_t"]
    p = pia_mensal.set_index("reference_period")["preco_domestico_rs_t"]
    idx = c.index.intersection(p.index)
    out = pd.DataFrame({"corporate_rs_t": c.loc[idx], "pia_rs_t": p.loc[idx]})
    out["delta_pct"] = (out["pia_rs_t"] - out["corporate_rs_t"]) / out["corporate_rs_t"] * 100.0
    return out.sort_index()


def checagem_trimestral_independente(pia: pd.DataFrame, ipp: pd.Series) -> pd.DataFrame:
    """Checagem MAIS independente que a mensal acima: usa a ancora
    trimestral BRUTA (soma receita/soma volume, ANTES de qualquer
    encadeamento por IPP) contra a media trimestral da serie PIA+IPP -
    a ancora trimestral em si nunca usou IPP-242, entao seu movimento
    trimestre a trimestre e uma evidencia genuinamente independente.

    Inclui tambem uma baseline "flat" (sem indicador algum: repete o
    ultimo nivel BENCHMARKED, is_provisional=False, por todo o periodo
    provisional) - value-added direto do IPP na extensao provisional:
    o quanto a direcao acertada pelo IPP supera a de simplesmente nao
    usar nenhum indicador."""
    bruto = m.carregar_preco_domestico_trimestral_v2()
    ancora = m.ancora_domestica_ponderada_v2(bruto)
    if ancora.empty:
        return pd.DataFrame()
    pia_mensal = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)
    if pia_mensal.empty:
        return pd.DataFrame()
    s = pia_mensal.set_index("reference_period")["preco_domestico_rs_t"]
    s_trimestral = s.groupby(s.index.to_period("Q")).mean()

    bench = pia_mensal[~pia_mensal["is_provisional"]].set_index("reference_period")["preco_domestico_rs_t"]
    flat_nivel = float(bench.iloc[-1]) if not bench.empty else float("nan")

    ancora = ancora.set_index("trimestre").sort_index()
    ancora.index = pd.PeriodIndex(ancora.index, freq="Q")
    idx = ancora.index.intersection(s_trimestral.index)
    if len(idx) == 0:
        return pd.DataFrame()
    out = pd.DataFrame({
        "corporate_bruto_rs_t": ancora.loc[idx, "preco_rs_t"],
        "pia_ipp_trimestral_rs_t": s_trimestral.loc[idx],
        "flat_sem_indicador_rs_t": flat_nivel,
    }).sort_index()
    out["g_corporate"] = out["corporate_bruto_rs_t"].pct_change()
    out["g_pia_ipp"] = out["pia_ipp_trimestral_rs_t"].pct_change()
    out["g_flat"] = out["flat_sem_indicador_rs_t"].pct_change()  # sempre 0.0 por construcao
    return out


# =============================================================================
# 5. Denton vs baselines analiticos (linear, step) - NUNCA publicados
# =============================================================================

def baseline_linear(alvos: pd.Series, meses_idx: pd.DatetimeIndex) -> pd.Series:
    """Interpolacao linear entre os niveis anuais, ancorados no MEIO do ano
    (1o de julho) - convencao padrao para interpolar uma media anual (evita
    deslocar de fase o ano inteiro para janeiro, que a media anual NAO
    representa)."""
    pontos_x = pd.to_datetime([f"{ano}-07-01" for ano in alvos.index]).asi8
    pontos_y = alvos.to_numpy()
    x = meses_idx.asi8
    y = np.interp(x, pontos_x, pontos_y)
    return pd.Series(y, index=meses_idx, name="linear")


def baseline_step(alvos: pd.Series, meses_idx: pd.DatetimeIndex) -> pd.Series:
    """Carry-forward/degrau anual: todo mes do ano y recebe o nivel anual
    de y (sem nenhuma variacao intra-ano)."""
    mapa = alvos.to_dict()
    return pd.Series([mapa[a.year] for a in meses_idx], index=meses_idx, name="step")


def metricas_suavidade(serie: pd.Series) -> dict:
    var_mensal_pct = serie.pct_change().dropna()
    return {
        "std_var_mensal_pct": float(var_mensal_pct.std() * 100),
        "mad_var_mensal_pct": float(var_mensal_pct.abs().mean() * 100),
        "n_meses": len(serie),
    }


# =============================================================================
# main
# =============================================================================

def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    secao("1. Series reais confirmadas")
    pia, ipp = buscar_series()
    tab = tabela_series(pia, ipp)
    print(tab.to_string(index=False))
    tab.to_csv(f"{OUT_DIR}/series_confirmadas.csv", index=False)
    print(f"\n  PIA-HRC (R$/t) por ano:\n{pia['preco_rs_t'].round(1).to_string()}")

    secao("2. Series anuais comparaveis (variacao, nao nivel)")
    ipp_a = ipp_anual_media(ipp)
    ipp_c = ipp_anual_dez_dez(ipp)
    ipp_b = ipp_crescimento_media_de_yoy_mensal(ipp)
    print(f"  IPP anual (A - media do indice): {ipp_a.round(2).to_dict()}")
    print(f"  IPP anual (C - dez/dez): {ipp_c.round(2).to_dict()}")

    g_pia = crescimento_anual(pia["preco_rs_t"])
    g_ipp_a = crescimento_anual(ipp_a)
    g_ipp_c = crescimento_anual(ipp_c)
    g_ipp_b = ipp_b  # ja e uma taxa de crescimento, nao um nivel

    secao("3. PRINCIPAL: g_PIA vs g_IPP (metodo A - crescimento da media anual)")
    principal = direcao_tabela(alinhar(g_pia, g_ipp_a))
    print(principal.round(4).to_string())
    print(f"\n  N = {len(principal)}")
    print(f"  Pearson  = {pearson(principal['g_pia'].to_numpy(), principal['g_ipp'].to_numpy()):.4f}")
    print(f"  Spearman = {spearman(principal['g_pia'].to_numpy(), principal['g_ipp'].to_numpy()):.4f}")
    print(f"  directional accuracy = {principal['mesmo_sinal'].sum()}/{len(principal)} "
          f"({100*principal['mesmo_sinal'].mean():.1f}%)")
    print(f"  MAE (diff pp) = {principal['diff_pp'].abs().mean():.2f} pp   "
          f"max |diff| = {principal['diff_pp'].abs().max():.2f} pp")
    beta = beta_simples(principal)
    print(f"  beta (g_pia ~ g_ipp, diagnostico) = {beta:.3f}")
    principal.to_csv(f"{OUT_DIR}/anual_principal_metodo_A.csv")

    secao("3b. Robustness - metodo C (dezembro contra dezembro)")
    rob_c = direcao_tabela(alinhar(g_pia, g_ipp_c))
    print(rob_c.round(4).to_string())
    print(f"  N = {len(rob_c)}  Pearson = {pearson(rob_c['g_pia'].to_numpy(), rob_c['g_ipp'].to_numpy()):.4f}  "
          f"directional accuracy = {rob_c['mesmo_sinal'].sum()}/{len(rob_c)}")
    rob_c.to_csv(f"{OUT_DIR}/anual_robustness_metodo_C_dez_dez.csv")

    secao("3c. Robustness - metodo B (media das variacoes YoY mensais do IPP)")
    rob_b = direcao_tabela(alinhar(g_pia, g_ipp_b))
    print(rob_b.round(4).to_string())
    print(f"  N = {len(rob_b)}  Pearson = {pearson(rob_b['g_pia'].to_numpy(), rob_b['g_ipp'].to_numpy()):.4f}  "
          f"directional accuracy = {rob_b['mesmo_sinal'].sum()}/{len(rob_b)}")
    rob_b.to_csv(f"{OUT_DIR}/anual_robustness_metodo_B_media_yoy.csv")

    secao("4. Leave-one-out / jackknife (metodo principal A)")
    loo = leave_one_out(principal)
    print(loo.round(4).to_string())
    loo.to_csv(f"{OUT_DIR}/leave_one_out_metodo_A.csv")

    secao("5. Corporate anchor - comparacao mensal existente (AVISO: mesmo IPP-242 dos dois lados)")
    comp_mensal = comparacao_mensal_corporate_vs_pia(pia, ipp)
    if comp_mensal.empty:
        print("  Sem sobreposicao mensal entre corporate e PIA+IPP no dado atual.")
    else:
        print(f"  N meses = {len(comp_mensal)}  janela = {comp_mensal.index.min():%Y-%m} a {comp_mensal.index.max():%Y-%m}")
        print(f"  delta_pct: media={comp_mensal['delta_pct'].mean():.2f}%  mediana={comp_mensal['delta_pct'].median():.2f}%  "
              f"std={comp_mensal['delta_pct'].std():.2f}pp  min={comp_mensal['delta_pct'].min():.2f}%  max={comp_mensal['delta_pct'].max():.2f}%")
        corr_niveis = pearson(comp_mensal["corporate_rs_t"].to_numpy(), comp_mensal["pia_rs_t"].to_numpy())
        print(f"  correlacao de niveis = {corr_niveis:.4f}")
        x = np.arange(len(comp_mensal))
        if len(comp_mensal) > 1:
            tend = np.polyfit(x, comp_mensal["delta_pct"].to_numpy(), 1)[0]
            print(f"  tendencia do gap = {tend:+.4f} pp/mes")
        comp_mensal.to_csv(f"{OUT_DIR}/corporate_vs_pia_mensal.csv")
        print("  [AVISO METODOLOGICO] corporate (preco_domestico_hrc_mensal_v2) e a serie PIA "
              "usam o MESMO IPP-242 para encadear mes a mes - esta comparacao NAO isola o sinal "
              "do IPP de forma independente (ver secao 5b para uma checagem mais limpa).")

    secao("5b. Checagem MAIS independente - ancora trimestral BRUTA (pre-IPP) vs PIA+IPP trimestral")
    trib = checagem_trimestral_independente(pia, ipp)
    if trib.empty:
        print("  Sem trimestres qualificados sobrepostos com a janela PIA+IPP no dado atual.")
    else:
        print(trib.round(4).to_string())
        validos = trib.dropna(subset=["g_corporate", "g_pia_ipp"])
        if len(validos) >= 2:
            mesmo_sinal = (np.sign(validos["g_corporate"]) == np.sign(validos["g_pia_ipp"]))
            mesmo_sinal_flat = (np.sign(validos["g_corporate"]) == np.sign(validos["g_flat"]))
            print(f"\n  N trimestres com QoQ comparavel = {len(validos)}")
            print(f"  mesmo sinal QoQ (PIA+IPP242): {int(mesmo_sinal.sum())}/{len(validos)}")
            print(f"  mesmo sinal QoQ (flat, SEM indicador): {int(mesmo_sinal_flat.sum())}/{len(validos)} "
                  "(g_flat=0 sempre -> nunca acerta direcao de um movimento real, por construcao)")
            print(f"  correlacao QoQ (PIA+IPP242) = {pearson(validos['g_corporate'].to_numpy(), validos['g_pia_ipp'].to_numpy()):.4f}")
            print("  >> VALUE ADDED do IPP-242 na extensao provisional: "
                  f"{int(mesmo_sinal.sum())}/{len(validos)} vs. {int(mesmo_sinal_flat.sum())}/{len(validos)} sem indicador")
        else:
            print(f"\n  N insuficiente para direcao QoQ (N={len(validos)})")
        trib.to_csv(f"{OUT_DIR}/corporate_bruto_vs_pia_ipp_trimestral.csv")

    secao("6. Denton (atual) vs baselines analiticos (linear, step) - so diagnostico, nunca publicado")
    anos_bench = sorted(set(pia.index) & {a for a, g in ipp.groupby(ipp.index.year) if len(g) == 12})
    if len(anos_bench) >= 2:
        primeiro, ultimo = min(anos_bench), max(anos_bench)
        idx_mensal = pd.date_range(f"{primeiro}-01-01", f"{ultimo}-12-01", freq="MS")
        alvos = pia.loc[primeiro:ultimo, "preco_rs_t"]
        indicador = ipp.loc[f"{primeiro}-01-01": f"{ultimo}-12-31"]

        denton_atual = m.denton_proporcional(indicador, alvos)
        linear = baseline_linear(alvos, idx_mensal)
        step = baseline_step(alvos, idx_mensal)

        for nome, serie in [("Denton+IPP242 (atual)", denton_atual), ("Linear", linear), ("Step", step)]:
            met = metricas_suavidade(serie)
            print(f"  {nome:24s} std(var% mensal)={met['std_var_mensal_pct']:.3f}  "
                  f"MAD(var% mensal)={met['mad_var_mensal_pct']:.3f}  n_meses={met['n_meses']}")

        comparativo = pd.DataFrame({"denton_ipp242": denton_atual, "linear": linear, "step": step})
        comparativo.to_csv(f"{OUT_DIR}/denton_vs_baselines_mensal.csv")
        print(f"\n  escrito: {OUT_DIR}/denton_vs_baselines_mensal.csv "
              f"({len(comparativo)} meses, {primeiro}-{ultimo})")
    else:
        print("  Anos insuficientes com PIA+IPP completo para montar a janela benchmarked.")

    secao("FIM")
    print(f"  Todos os artefatos em {OUT_DIR}/ - nenhum arquivo oficial, curado ou de vintage foi escrito.")


if __name__ == "__main__":
    main()
