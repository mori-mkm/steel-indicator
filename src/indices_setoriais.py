#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 INDICES SETORIAIS - motor de calculo de referencia
 Casa de research macro e setorial (Brasil)
=============================================================================

 Implementa:
   ICCS  - Indice de Condicoes de Credito Setorial   (mensal, 100% dado publico)
   IPIA  - Indice de Paridade de Importacao do Aco    (mensal + nowcast semanal)
   ICS   - Indice de Condicoes Setoriais              (sintetico; camada de
           survey opcional, pode ser plugada depois)

 Filosofia de desenho
 --------------------
 1. A JANELA DE REFERENCIA DA PADRONIZACAO E FIXA. Media e desvio-padrao sao
    calculados numa janela historica congelada (default: 2013-2019). Se voce
    recalcular media/desvio com a amostra cheia a cada mes, o passado do seu
    indice muda todo mes e a serie perde comparabilidade. Esse e o erro mais
    comum e o mais caro em construcao de indice.
 2. PESOS SAO TEORICOS E FIXOS, nao estimados. PCA serve para VALIDAR os pesos,
    nunca para defini-los - pesos estimados mudam a cada revisao.
 3. DADO FALTANTE redistribui peso proporcionalmente dentro do pilar e a
    cobertura do mes e publicada junto com o indice.
 4. TUDO E VERSIONADO. Cada publicacao gera um "vintage" arquivado.

 Uso
 ---
   python indices_setoriais.py --selftest        # valida a matematica, sem rede
   python indices_setoriais.py --check-sources   # testa as APIs publicas
   python indices_setoriais.py --iccs            # calcula o ICCS
   python indices_setoriais.py --ipia            # calcula o IPIA
   python indices_setoriais.py --pdf-ipia        # gera relatorio PDF de 1 pagina do IPIA

 Dependencias: pandas, numpy, requests, matplotlib  (statsmodels opcional, p/ ajuste sazonal)
=============================================================================
"""
from __future__ import annotations
import argparse, json, re, sys, time, datetime as dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

import numpy as np
import pandas as pd

# =============================================================================
# 0. CONFIGURACAO
# =============================================================================

JANELA_REF = ("2013-01-01", "2019-12-31")   # janela de padronizacao CONGELADA
WINSOR_Z   = 3.0                            # corte de outlier, em desvios
ESCALA_A   = 50.0                           # ancora: 50 = media da janela de ref.
ESCALA_B   = 10.0                           # 1 desvio-padrao = 10 pontos
COBERTURA_MINIMA = 0.60                     # abaixo disso, nao publique o setor

# --- Series SGS do Banco Central -------------------------------------------
# VERIFICADAS AO VIVO nesta sessao (valores de jun/2026 conferidos):
#   21082 -> 4,68  | inadimplencia total do SFN        (bate com o divulgado)
#   21086 -> 4,00  | inadimplencia PJ total            (bate com o divulgado)
# NAO CONFIRMADAS NOMINALMENTE (valores plausiveis, rotulo a confirmar):
#   21084 -> 5,57  | provavel: inadimplencia recursos livres - total
#   21083 -> 3,19  | provavel: inadimplencia recursos direcionados - total
# Confirme o rotulo de cada codigo em https://www3.bcb.gov.br/sgspub/ antes de
# publicar. O metodo --check-sources imprime os ultimos valores de cada uma.
SGS = {
    "inad_total":        21082,   # VERIFICADA
    "inad_pj_total":     21086,   # VERIFICADA
    "inad_livres_total": 21084,   # a confirmar
    "inad_direc_total":  21083,   # a confirmar
    "cambio_venda":      1,       # a confirmar: PTAX. Cheque a ordem de grandeza
    "selic_meta":        432,     # a confirmar
    "ipca_mes":          433,     # a confirmar
}

SGS_URL   = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados?formato=json"
SGS_ULT   = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/{n}?formato=json"
COMEX_URL = "https://api-comexstat.mdic.gov.br/general"
SCR_BASE  = "https://www.bcb.gov.br/pda/desig/planilha_{aaaamm}.zip"  # confira no portal

# --- NCM de 8 digitos: bobina laminada a quente, nao ligada, largura >=600mm
# Fonte: Circular SECEX 39/2025 (abertura da investigacao antidumping de
# laminados a quente da China), filtrando SO as posicoes "em rolos". Ficaram
# de fora do escopo original da circular: 7208.40/53/54/90 (chapa, nao
# enrolado), 7211.xx (largura <600mm) e 7225/7226 (aco ligado) - produtos
# diferentes, mesma investigacao. Confirme no Siscomex antes do primeiro calculo.
NCM_BOBINA_QUENTE = {
    "com_relevo":       ["72081000"],
    "decapada":         ["72082500", "72082610", "72082690", "72082710", "72082790"],
    "nao_decapada":     ["72083610", "72083690", "72083700",
                          "72083810", "72083890", "72083910", "72083990"],
}

# --- Mapa setor -> CNAE (secao/divisao) ------------------------------------
SETORES = {
    "siderurgia_metalurgia": {"cnae": ["24"],        "ncm_ref": ["7208", "7213", "7219"]},
    "petroleo_gas":          {"cnae": ["06", "19"],  "ncm_ref": []},
    "mineracao":             {"cnae": ["07"],        "ncm_ref": ["2601"]},
    "tecnologia":            {"cnae": ["62", "63"],  "ncm_ref": []},
    "agro_alimentos":        {"cnae": ["01", "10"],  "ncm_ref": ["1201", "1005"]},
    "papel_celulose":        {"cnae": ["17"],        "ncm_ref": ["4703"]},
    "quimica":               {"cnae": ["20"],        "ncm_ref": []},
    "construcao":            {"cnae": ["41", "42", "43"], "ncm_ref": []},
}

# =============================================================================
# 1. MOTOR GENERICO DE INDICE
# =============================================================================

@dataclass
class Variavel:
    """Uma variavel componente do indice."""
    nome: str
    pilar: str
    peso: float                      # peso DENTRO do pilar (soma 1 por pilar)
    orientacao: int = 1              # +1 = maior e melhor; -1 = maior e pior
    transform: Optional[str] = None  # None | "var12m" | "var12m_real" | "log"
    fonte: str = ""

@dataclass
class Pilar:
    nome: str
    peso: float                      # peso do pilar no indice (somam 1)
    descricao: str = ""

@dataclass
class EspecIndice:
    codigo: str
    nome: str
    pilares: List[Pilar]
    variaveis: List[Variavel]
    janela_ref: tuple = JANELA_REF

    def validar(self) -> None:
        soma_p = sum(p.peso for p in self.pilares)
        if abs(soma_p - 1.0) > 1e-9:
            raise ValueError(f"pesos dos pilares somam {soma_p}, deveriam somar 1")
        nomes_pilar = {p.nome for p in self.pilares}
        for pl in nomes_pilar:
            s = sum(v.peso for v in self.variaveis if v.pilar == pl)
            if abs(s - 1.0) > 1e-9:
                raise ValueError(f"pesos das variaveis do pilar '{pl}' somam {s}")
        for v in self.variaveis:
            if v.pilar not in nomes_pilar:
                raise ValueError(f"variavel '{v.nome}' aponta para pilar inexistente")


def aplicar_transform(s: pd.Series, transform: Optional[str],
                      deflator: Optional[pd.Series] = None) -> pd.Series:
    if transform is None:
        return s
    if transform == "log":
        return np.log(s.where(s > 0))
    if transform == "var12m":
        return s.pct_change(12) * 100
    if transform == "var12m_real":
        if deflator is None:
            raise ValueError("var12m_real exige deflator")
        real = s / deflator
        return real.pct_change(12) * 100
    raise ValueError(f"transform desconhecida: {transform}")


def zscore_janela_fixa(s: pd.Series, janela: tuple,
                       winsor: float = WINSOR_Z) -> pd.Series:
    """Padroniza usando media e desvio de uma janela historica CONGELADA.

    E isto que impede o passado do indice de mudar a cada nova observacao.
    """
    ini, fim = janela
    ref = s.loc[(s.index >= ini) & (s.index <= fim)].dropna()
    if len(ref) < 12:
        raise ValueError(f"janela de referencia tem so {len(ref)} obs (min. 12)")
    mu, sd = ref.mean(), ref.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    z = (s - mu) / sd
    return z.clip(-winsor, winsor)


def agregar(z: pd.DataFrame, espec: EspecIndice) -> pd.DataFrame:
    """Agrega z-scores em pilares e no indice, redistribuindo peso do que falta.

    Retorna colunas: um score por pilar, 'indice' (0-100) e 'cobertura'.
    """
    espec.validar()
    por_pilar, cob_pilar = {}, {}
    for p in espec.pilares:
        vs = [v for v in espec.variaveis if v.pilar == p.nome]
        cols = [v.nome for v in vs if v.nome in z.columns]
        if not cols:
            por_pilar[p.nome] = pd.Series(np.nan, index=z.index)
            cob_pilar[p.nome] = pd.Series(0.0, index=z.index)
            continue
        sub = z[cols]
        w = pd.Series({v.nome: v.peso * v.orientacao for v in vs if v.nome in cols})
        wabs = pd.Series({v.nome: v.peso for v in vs if v.nome in cols})
        disp = sub.notna()
        # peso efetivo renormalizado linha a linha pelos dados disponiveis
        wsum = disp.mul(wabs, axis=1).sum(axis=1)
        num = sub.fillna(0).mul(w, axis=1).sum(axis=1)
        por_pilar[p.nome] = np.where(wsum > 0, num / wsum.replace(0, np.nan), np.nan)
        por_pilar[p.nome] = pd.Series(por_pilar[p.nome], index=z.index)
        cob_pilar[p.nome] = wsum / wabs.sum()

    dfp = pd.DataFrame(por_pilar)
    dfc = pd.DataFrame(cob_pilar)
    wp = pd.Series({p.nome: p.peso for p in espec.pilares})

    disp_p = dfp.notna()
    wsum_p = disp_p.mul(wp, axis=1).sum(axis=1)
    z_comp = dfp.fillna(0).mul(wp, axis=1).sum(axis=1) / wsum_p.replace(0, np.nan)

    out = dfp.copy()
    out["z_composto"] = z_comp
    out["indice"] = (ESCALA_A + ESCALA_B * z_comp).clip(0, 100)
    out["cobertura"] = dfc.mul(wp, axis=1).sum(axis=1)
    out.loc[out["cobertura"] < COBERTURA_MINIMA, "indice"] = np.nan
    return out


def validar_com_pca(z: pd.DataFrame) -> dict:
    """Checagem de sanidade: o 1o componente principal deveria explicar boa
    parte da variancia e ter loadings do mesmo sinal das orientacoes teoricas.
    Se nao explicar, seus pilares estao medindo coisas diferentes demais."""
    x = z.dropna()
    if len(x) < 24 or x.shape[1] < 2:
        return {"ok": False, "motivo": "amostra insuficiente"}
    xc = (x - x.mean()) / x.std(ddof=1)
    cov = np.cov(xc.values, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    ordem = np.argsort(vals)[::-1]
    vals, vecs = vals[ordem], vecs[:, ordem]
    var_exp = float(vals[0] / vals.sum())
    load = pd.Series(vecs[:, 0], index=x.columns)
    if load.mean() < 0:
        load = -load
    return {"ok": True, "var_explicada_pc1": round(var_exp, 3),
            "loadings_pc1": load.round(3).to_dict(),
            "veredito": ("consistente" if var_exp >= 0.45 else
                         "PC1 fraco - revise a composicao dos pilares")}


def diagnostico_antecedencia(indice: pd.Series, alvo: pd.Series,
                             horizontes=(3, 6, 9, 12)) -> pd.DataFrame:
    """O teste que realmente importa: o indice antecipa o que promete antecipar?

    Correlaciona o indice em t com a VARIACAO do alvo em t+h. Se a correlacao
    nao for materialmente maior que a contemporanea, o indice e redundante.
    """
    linhas = []
    for h in horizontes:
        fut = alvo.diff(h).shift(-h)
        pares = pd.concat([indice, fut], axis=1).dropna()
        if len(pares) < 24:
            linhas.append({"horizonte_meses": h, "n": len(pares), "correlacao": np.nan})
            continue
        linhas.append({"horizonte_meses": h, "n": len(pares),
                       "correlacao": round(float(pares.corr().iloc[0, 1]), 3)})
    cont = pd.concat([indice, alvo.diff()], axis=1).dropna()
    base = round(float(cont.corr().iloc[0, 1]), 3) if len(cont) >= 24 else np.nan
    df = pd.DataFrame(linhas)
    df.attrs["correlacao_contemporanea"] = base
    return df

# =============================================================================
# 2. ESPECIFICACAO DO ICCS
# =============================================================================

ICCS = EspecIndice(
    codigo="ICCS",
    nome="Indice de Condicoes de Credito Setorial",
    pilares=[
        Pilar("qualidade",  0.30, "Qualidade da carteira de credito do setor"),
        Pilar("acesso",     0.25, "Volume e acesso ao credito"),
        Pilar("custo",      0.15, "Custo do credito"),
        Pilar("capacidade", 0.20, "Capacidade de pagamento do setor"),
        Pilar("externo",    0.10, "Pressao competitiva externa"),
    ],
    variaveis=[
        # --- pilar 1: qualidade (fonte: BCB SCR.data, por CNAE) -------------
        Variavel("inadimplencia_setor",      "qualidade", 0.45, -1, None,
                 fonte="BCB SCR.data / CNAE"),
        Variavel("ativo_problematico_ratio", "qualidade", 0.35, -1, None,
                 fonte="BCB SCR.data / CNAE"),
        Variavel("inad_var12m",              "qualidade", 0.20, -1, "var12m",
                 fonte="BCB SCR.data / CNAE"),
        # --- pilar 2: acesso -------------------------------------------------
        Variavel("saldo_credito_real_var12m","acesso",    0.50, +1, "var12m_real",
                 fonte="BCB SCR.data + IPCA"),
        Variavel("concessoes_real_var12m",   "acesso",    0.30, +1, "var12m_real",
                 fonte="BCB SCR.data + IPCA"),
        Variavel("credito_sobre_va_setor",   "acesso",    0.20, +1, None,
                 fonte="BCB SCR.data + IBGE Contas Nacionais"),
        # --- pilar 3: custo ---------------------------------------------------
        Variavel("icc_pj",                   "custo",     0.50, -1, None,
                 fonte="BCB ICC"),
        Variavel("spread_pj",                "custo",     0.30, -1, None,
                 fonte="BCB"),
        Variavel("juro_real_exante",         "custo",     0.20, -1, None,
                 fonte="BCB SGS + Focus"),
        # --- pilar 4: capacidade de pagamento ---------------------------------
        Variavel("producao_fisica_setor",    "capacidade",0.40, +1, "var12m",
                 fonte="IBGE PIM-PF / setorial (IABr, ANP, CONAB)"),
        Variavel("margem_proxy_ipp",         "capacidade",0.35, +1, "var12m",
                 fonte="IBGE IPP por CNAE"),
        Variavel("cobertura_juros_listadas", "capacidade",0.25, +1, None,
                 fonte="CVM ITR/DFP (dados abertos)"),
        # --- pilar 5: pressao externa ------------------------------------------
        Variavel("penetracao_importados",    "externo",   0.60, -1, None,
                 fonte="Comex Stat + producao domestica"),
        Variavel("termos_de_troca_setor",    "externo",   0.40, +1, "var12m",
                 fonte="Comex Stat (valor unitario exp/imp)"),
    ],
)

# =============================================================================
# 3. IPIA - PARIDADE DE IMPORTACAO DO ACO
# =============================================================================

@dataclass
class ParamsIPIA:
    """Parametros de internacao. O unico bloco subjetivo do indice -
    publique estes numeros junto com o indice e revise uma vez por ano."""
    aliquota_ii: float = 0.108          # Imposto de Importacao da NCM (TEC)
    afrmm: float = 0.08                 # 8% sobre o frete maritimo
    despesas_porto_rs_t: float = 210.0  # capatazia, armazenagem, despacho
    frete_interno_rs_t: float = 140.0   # porto -> cliente
    margem_importador: float = 0.03     # margem do trading
    antidumping_usd_t: float = 0.0      # direito especifico, US$/t - VARIA POR
        # EMPRESA EXPORTADORA E POR ORIGEM (China, Russia...) nas resolucoes
        # Gecex. Default 0 CONFIRMADO COMO PENDENTE em 23/08/2026 (pesquisado,
        # nao apenas assumido): cold-rolled (Resolucao Gecex 854) e revestido
        # (856) foram decididos em 12/02/2026, mas laminado a quente da China
        # NAO aparece em nenhuma resolucao Gecex ate a de numero 947
        # (04/08/2026, ultima verificada nesta checagem). Duas datas de
        # expectativa ja passaram sem decisao (fev-mar/2026 segundo imprensa,
        # jul/2026 segundo a propria Usiminas no release do 1T26). Isso NAO e
        # um fato permanente - reverifique periodicamente em
        # gov.br/mdic/.../defesa-comercial antes de cada publicacao, nao so
        # na primeira vez. Ao confirmar uma decisao, trate como parametro
        # versionado igual aos demais - nao como uma constante do codigo.


def custo_importacao_rs_t(preco_fob_usd_t: pd.Series,
                          frete_usd_t: pd.Series,
                          seguro_usd_t: pd.Series,
                          cambio: pd.Series,
                          p: ParamsIPIA) -> pd.DataFrame:
    """Custo de aquisicao do produto importado, posto no cliente, em R$/t.

    Entradas em US$/t vem do Comex Stat: valor FOB, frete e seguro sao
    publicados por NCM desde 2020, o que elimina a necessidade de estimar
    frete e de licenciar cotacao de agencia de precos.
    """
    cif_usd = preco_fob_usd_t + frete_usd_t + seguro_usd_t
    cif_brl = cif_usd * cambio
    ii      = cif_brl * p.aliquota_ii
    afrmm   = (frete_usd_t * cambio) * p.afrmm
    ad_brl  = p.antidumping_usd_t * cambio          # direito especifico, US$/t -> R$/t
    base    = cif_brl + ii + afrmm + ad_brl + p.despesas_porto_rs_t + p.frete_interno_rs_t
    total   = base * (1 + p.margem_importador)
    return pd.DataFrame({
        "cif_usd_t": cif_usd, "cif_brl_t": cif_brl, "ii_brl_t": ii,
        "afrmm_brl_t": afrmm, "antidumping_brl_t": ad_brl, "ppi_brl_t": total,
    })


def ipia(preco_domestico_rs_t: pd.Series, ppi_rs_t: pd.Series) -> pd.Series:
    """>100 = domestico acima da paridade (importar compensa).
       <100 = domestico abaixo da paridade (produtor local protegido)."""
    return (preco_domestico_rs_t / ppi_rs_t) * 100.0

# =============================================================================
# 3b. ANCORA DE PRECO DOMESTICO
# =============================================================================
# Diferente do lado da importacao (Comex Stat/BCB sao APIs), o preco domestico
# de bobina a quente vem de release trimestral de resultados de Usiminas/CSN -
# nao existe API publica para isso. A ingestao e semi-manual, mas o CSV
# resultante e pequeno e essencial para o indice rodar, entao fica VERSIONADO
# no Git (data/curated/, ao contrario de data/raw/ e data/processed/, que sao
# gitignored). Ver docs/adr/0003 para o raciocinio completo.
#
# Nos releases de 1T26 (Usiminas) e 2T26 (CSN) lidos de verdade nesta sessao,
# NENHUMA das duas empresas separa volume/receita de laminados a quente dos
# demais produtos planos no release trimestral nem na apresentacao de
# resultados - so o agregado do segmento "Siderurgia" inteiro. Por isso todo
# dado carregado por default hoje tem tipo="proxy_segmento_aco". Se um dia
# uma fonte especifica de bobina a quente for confirmada, ela entra com
# tipo="especifico_laminado_quente" na mesma tabela - o motor ja sabe
# distinguir (ver `preco_domestico_ponderado`), nao e preciso remodelar nada.

CAMINHO_PRECO_DOMESTICO_CSV = "data/curated/preco_domestico_aco.csv"
TIPOS_DADO_DOMESTICO = {"especifico_laminado_quente", "proxy_segmento_aco", "misto"}


def carregar_preco_domestico_trimestral(caminho_csv: str = CAMINHO_PRECO_DOMESTICO_CSV) -> pd.DataFrame:
    """Le o CSV curado (versionado) de preco domestico por trimestre e empresa.

    Calcula preco_rs_t = receita_liquida_segmento_rs / volume_vendas_t quando
    a coluna preco_rs_t nao vier preenchida direto da fonte (caso da CSN, que
    ja publica "Preco Medio" explicito no release, ao contrario da Usiminas).
    """
    df = pd.read_csv(caminho_csv)
    obrigatorias = {"trimestre", "empresa", "volume_vendas_t", "tipo", "fonte"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ValueError(f"CSV de preco domestico sem colunas obrigatorias: {faltando}")
    tipos_invalidos = set(df["tipo"]) - TIPOS_DADO_DOMESTICO
    if tipos_invalidos:
        raise ValueError(f"tipo de dado desconhecido no CSV: {tipos_invalidos}")
    if "preco_rs_t" not in df.columns:
        df["preco_rs_t"] = np.nan
    precisa_calcular = df["preco_rs_t"].isna()
    df.loc[precisa_calcular, "preco_rs_t"] = (
        df.loc[precisa_calcular, "receita_liquida_segmento_rs"]
        / df.loc[precisa_calcular, "volume_vendas_t"]
    )
    return df


def preco_domestico_ponderado(df: pd.DataFrame) -> pd.DataFrame:
    """Preco domestico por trimestre, media entre empresas ponderada por volume.

    tipo do trimestre agregado: mantem o tipo se todas as empresas do
    trimestre concordam; vira "misto" se ha tipos diferentes no mesmo
    trimestre - nunca finge que o blend inteiro e especifico se so uma
    parte e.
    """
    linhas = []
    for trimestre, g in df.groupby("trimestre", sort=True):
        preco = float(np.average(g["preco_rs_t"], weights=g["volume_vendas_t"]))
        tipo = g["tipo"].iloc[0] if g["tipo"].nunique() == 1 else "misto"
        linhas.append({
            "trimestre": trimestre,
            "preco_rs_t": preco,
            "volume_vendas_t": float(g["volume_vendas_t"].sum()),
            "tipo": tipo,
            "empresas": ",".join(sorted(g["empresa"].unique())),
        })
    return pd.DataFrame(linhas)


def encadear_preco_domestico_mensal(trimestral: pd.DataFrame, ipp_mensal: pd.Series) -> pd.DataFrame:
    """Expande o nivel trimestral (preco_rs_t) para uma serie mensal.

    Dentro do proprio trimestre confirmado, o nivel e usado direto
    (metodo="nivel_trimestral" - e o dado real daquele trimestre, nao ha o
    que encadear). Depois do trimestre mais recente confirmado, ate o
    proximo release sair, o nivel e projetado mes a mes pela variacao do IPP
    do IBGE (CNAE 24 - metalurgia):

        preco(mes M) = nivel_trimestral_confirmado *
                       (IPP[M] / IPP[ultimo mes do trimestre confirmado])

    Isso evita usar o trimestre SEGUINTE (ainda nao divulgado) para
    preencher meses passados - o problema de look-ahead que a interpolacao
    linear teria. Ver docs/adr/0002.

    Fallback: se o IPP do mes M ainda nao foi divulgado, repete o ultimo
    nivel calculado (metodo="hold_flat_fallback") em vez de extrapolar.
    """
    tri = trimestral.copy()
    tri["periodo"] = tri["trimestre"].apply(lambda t: pd.Period(t, freq="Q"))
    tri = tri.sort_values("periodo").reset_index(drop=True)
    ipp = pd.to_numeric(ipp_mensal, errors="coerce").sort_index()

    fim = tri["periodo"].max().end_time.normalize()
    if len(ipp):
        fim = max(fim, ipp.index.max())
    idx_mensal = pd.date_range(tri["periodo"].min().start_time.normalize(), fim, freq="MS")

    linhas = []
    ultimo_calculado = None
    for mes in idx_mensal:
        periodo_mes = pd.Period(mes, freq="Q")
        confirmados = tri[tri["periodo"] <= periodo_mes]
        if confirmados.empty:
            continue
        base = confirmados.iloc[-1]
        if base["periodo"] == periodo_mes:
            preco, metodo = float(base["preco_rs_t"]), "nivel_trimestral"
        else:
            mes_base = pd.Timestamp(base["periodo"].end_time.year, base["periodo"].end_time.month, 1)
            ipp_base = ipp.get(mes_base)
            ipp_m = ipp.get(mes)
            if ipp_base is not None and ipp_m is not None and pd.notna(ipp_base) and pd.notna(ipp_m):
                preco = float(base["preco_rs_t"]) * (float(ipp_m) / float(ipp_base))
                metodo = "encadeado_ipp"
            else:
                preco, metodo = ultimo_calculado, "hold_flat_fallback"
        ultimo_calculado = preco
        linhas.append({"data": mes, "preco_rs_t": preco, "metodo": metodo,
                       "trimestre_base": str(base["trimestre"]), "tipo_dado": base["tipo"]})
    return pd.DataFrame(linhas).set_index("data")

# =============================================================================
# 4. COLETORES (rede)
# =============================================================================

def _get_json(url: str, params: dict | None = None, tentativas: int = 3):
    import requests
    for i in range(tentativas):
        try:
            r = requests.get(url, params=params, timeout=60,
                             headers={"User-Agent": "pesquisa-setorial/1.0"})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == tentativas - 1:
                raise
            time.sleep(2 ** i)


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


def sgs(codigo: int, inicio: str = "01/01/2010") -> pd.Series:
    """Serie do Sistema Gerenciador de Series Temporais do Banco Central."""
    dados = _get_json(SGS_URL.format(cod=codigo), {"dataInicial": inicio})
    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df.set_index("data")["valor"].rename(f"sgs_{codigo}")


IBGE_SIDRA_IPP_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/6903/periodos/{periodos}/variaveis/10008"
# Tabela SIDRA 6903, variavel 10008 (numero-indice, dez/2018=100), classificacao
# 842, categoria 46641 = "24 METALURGIA". CONFIRMADA AO VIVO nesta sessao via
# servicodados.ibge.gov.br/api/v3/agregados/6903/metadados - a tabela 5796,
# que aparece em buscas antigas por "IPP CNAE", esta ENCERRADA desde jan/2019;
# nao usar.
IBGE_IPP_CLASSIFICACAO_METALURGIA = "842[46641]"


def ibge_sidra_ipp_metalurgia(periodos: str = "all") -> pd.Series:
    """IPP (Indice de Precos ao Produtor) mensal do IBGE/SIDRA, CNAE 24 -
    Metalurgia, numero-indice (dez/2018=100). Usado para encadear o preco
    domestico trimestral em serie mensal - ver `encadear_preco_domestico_mensal`.
    """
    url = IBGE_SIDRA_IPP_URL.format(periodos=periodos)
    dados = _get_json(url, {"localidades": "N1[all]", "classificacao": IBGE_IPP_CLASSIFICACAO_METALURGIA})
    serie = dados[0]["resultados"][0]["series"][0]["serie"]
    s = pd.to_numeric(pd.Series(serie), errors="coerce")
    s.index = pd.to_datetime(s.index, format="%Y%m")
    return s.rename("ipp_metalurgia").sort_index()


# --- Taxa de Penetracao das Importacoes (Instituto Aco Brasil) -------------
# Publicada mensalmente em acobrasil.org.br/site/estatistica-mensal/, em
# dois formatos - nenhum deles e uma API estavel:
#   - PDF "Estatistica Mensal": tabela "9.1 Taxa de Penetracao ... Mensal"
#     com o numero OFICIAL (Importacao/Consumo Aparente, excluindo
#     importacoes diretas pelas usinas), mas cada edicao so mostra o mes
#     corrente + o mesmo mes do ano anterior - sem serie historica.
#   - Excel "Performance Mensal": serie historica completa desde 2013, mas
#     so com os componentes brutos (Importacoes, Consumo Aparente) - SEM a
#     taxa pronta. Calculando Importacao/Consumo Aparente a partir dele NAO
#     reproduz o numero oficial do PDF (testado em jul/2026, Planos: Excel
#     da 16,66%, PDF oficial da 17,9% - diferenca real de ~1,2 p.p., porque
#     o Excel aparentemente nao aplica a mesma exclusao de importacoes das
#     usinas). Ver docs/adr/0007 para a investigacao completa, incluindo a
#     reverificacao manual da tabela 9.1 (consistente com uma tabela
#     independente do mesmo PDF e com o resumo executivo) e a divergencia
#     com um numero citado pela imprensa/BTG Pactual (formula propria nao
#     publica, nao e evidencia de erro do nosso lado).
#
# Granularidade real: so Planos vs. Longos (agregado) - nunca bobina a
# quente isolada. tipo_dado_penetracao marca a fonte: "oficial_mensal"
# (PDF) vs. "aproximado_consumo_aparente" (Excel, fallback historico).
#
# A pagina so expoe o arquivo do mes mais recente (sem arquivo de meses
# passados), e a URL nao e previsivel por mes (testado: adivinhar a pasta
# de upload falha para alguns meses) - por isso sempre resolve os links
# ao vivo da pagina, nunca constroi a URL na mao.
ACOBRASIL_ESTATISTICA_MENSAL_URL = "https://www.acobrasil.org.br/site/estatistica-mensal/"
ACOBRASIL_MESES_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                      "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
ACOBRASIL_MESES_PT_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _acobrasil_resolver_links_mes_atual() -> dict:
    """Resolve os links do PDF e do .xls do mes mais recente a partir da
    pagina ao vivo de estatistica mensal - nunca constroi a URL adivinhando
    a pasta de upload (testado: falha para alguns meses)."""
    import requests
    r = requests.get(ACOBRASIL_ESTATISTICA_MENSAL_URL, timeout=60,
                     headers={"User-Agent": "pesquisa-setorial/1.0"})
    r.raise_for_status()
    pdfs = re.findall(r'https://www\.acobrasil\.org\.br/site/wp-content/uploads/[^"\'<> ]+?\.pdf', r.text, re.I)
    xls = re.findall(r'https://www\.acobrasil\.org\.br/site/wp-content/uploads/[^"\'<> ]+?\.xlsx?', r.text, re.I)
    if not pdfs or not xls:
        raise ValueError(f"nao encontrei os links de PDF/xls na pagina de estatistica mensal "
                         f"({len(pdfs)} pdf(s), {len(xls)} xls(s)) - layout da pagina pode ter mudado")
    return {"pdf": pdfs[0], "xls": xls[0]}


def _parse_tabela_penetracao_pdf(texto_pagina: str) -> dict:
    """Funcao pura: recebe o texto ja extraido de UMA pagina do PDF e
    extrai a tabela '9.1 ... Mensal' - nunca a '9.2 ... Acumulado no Ano',
    que tem os mesmos rotulos de produto mas numeros diferentes (isolada
    fatiando o texto entre '9.1.' e '9.2.', antes de qualquer regex).
    """
    if "9.1." not in texto_pagina or "Mensal" not in texto_pagina:
        raise ValueError("secao '9.1 ... Mensal' nao encontrada no texto da pagina")
    inicio = texto_pagina.index("9.1.")
    fim = texto_pagina.find("9.2.")
    trecho = texto_pagina[inicio: fim if fim != -1 else len(texto_pagina)]

    mes_match = re.search(r"(" + "|".join(ACOBRASIL_MESES_PT) + r")\s*/", trecho)
    if not mes_match:
        raise ValueError("mes de referencia nao encontrado na secao 9.1")
    mes_nome = mes_match.group(1)

    # Os dois anos (ano anterior, ano atual) aparecem logo apos o cabecalho
    # de mes ("Julho / July Julho / July\n2025 2026\n...") - busca numa
    # janela a partir dai, NUNCA do inicio do trecho: "Produto" (rotulo da
    # coluna, mais abaixo) e substring de "Produtos" (que aparece no titulo
    # da secao, "... Produtos de Aço"), entao usar texto.find("Produto")
    # como ancora cortaria o cabecalho antes mesmo de chegar nos anos.
    janela_anos = trecho[mes_match.end(): mes_match.end() + 100]
    anos = re.findall(r"\b(20\d{2})\b", janela_anos)
    if len(anos) < 2:
        raise ValueError(f"esperava 2 anos no cabecalho da secao 9.1, encontrei {anos}")
    ano_anterior, ano_atual = int(anos[0]), int(anos[1])

    def _num_br(s: str) -> float:
        return float(s.replace(".", "").replace(",", "."))

    def _linha(rotulo_regex: str) -> dict:
        m = re.search(rotulo_regex + r"\s+([\d.]+)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)\s+([\d.]+)\s+([\d,]+)", trecho)
        if not m:
            raise ValueError(f"linha '{rotulo_regex}' nao encontrada na secao 9.1")
        g = [_num_br(x) for x in m.groups()]
        return {"consumo_aparente_t": g[3], "importacao_t": g[4], "taxa_penetracao_pct": g[5]}

    return {
        "mes_nome": mes_nome, "ano": ano_atual, "ano_anterior": ano_anterior,
        "planos": _linha(r"Planos\s*/\s*Flats"),
        "longos": _linha(r"Longos\s*/\s*Longs"),
    }


def acobrasil_taxa_penetracao_pdf_mes_atual(url_pdf: str | None = None) -> pd.DataFrame:
    """Baixa o PDF 'Estatistica Mensal' mais recente (via link resolvido ao
    vivo, a menos que url_pdf seja passado) e devolve a taxa de penetracao
    OFICIAL (tabela 9.1) do mes coberto - uma linha por categoria
    (planos/longos), tipo_dado_penetracao='oficial_mensal'.
    """
    import io, requests, pdfplumber
    if url_pdf is None:
        url_pdf = _acobrasil_resolver_links_mes_atual()["pdf"]
    r = requests.get(url_pdf, timeout=60, headers={"User-Agent": "pesquisa-setorial/1.0"})
    r.raise_for_status()
    texto = None
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        for pagina in pdf.pages:
            t = pagina.extract_text() or ""
            if "9.1." in t and "Mensal" in t:
                texto = t
                break
    if texto is None:
        raise ValueError("secao '9.1 ... Mensal' (Taxa de Penetracao) nao encontrada no PDF")
    dados = _parse_tabela_penetracao_pdf(texto)
    data = pd.Timestamp(year=dados["ano"], month=ACOBRASIL_MESES_PT.index(dados["mes_nome"]) + 1, day=1)
    linhas = [
        {"data": data, "categoria": cat, "tipo_dado_penetracao": "oficial_mensal",
         "fonte_penetracao": url_pdf, **dados[cat]}
        for cat in ("planos", "longos")
    ]
    return pd.DataFrame(linhas).set_index("data")


def _calcular_penetracao_de_performance_mensal(df_bruto: pd.DataFrame, categoria: str) -> pd.DataFrame:
    """Funcao pura: recebe o DataFrame bruto (header=None, como
    pd.read_excel devolve) do Excel 'Performance Mensal' e calcula
    Importacao/Consumo Aparente por mes para 'planos' ou 'longos'.
    Localiza as linhas por TEXTO (nunca por indice fixo de linha), para
    nao quebrar se o Instituto Aco Brasil inserir/remover uma linha do
    template. Retorna colunas: consumo_aparente_t, importacao_t,
    taxa_penetracao_pct (indice = mes).
    """
    if categoria not in ("planos", "longos"):
        raise ValueError(f"categoria invalida: {categoria!r} (use 'planos' ou 'longos')")
    rotulo = "Planos" if categoria == "planos" else "Longos"
    col0 = df_bruto.iloc[:, 0].astype(str)

    def _linha_apos_secao(nome_secao: str) -> int:
        idx_secao = col0[col0.str.contains(nome_secao, case=False, na=False)].index
        if len(idx_secao) == 0:
            raise ValueError(f"secao '{nome_secao}' nao encontrada na planilha")
        inicio = idx_secao[0]
        janela = col0.loc[inicio: inicio + 6]
        idx_produto = janela[janela.str.contains(rotulo, case=False, na=False)].index
        if len(idx_produto) == 0:
            raise ValueError(f"linha '{rotulo}' nao encontrada apos a secao '{nome_secao}'")
        return idx_produto[0]

    linha_importacao = _linha_apos_secao("Importa")
    linha_consumo = _linha_apos_secao("Consumo Aparente")

    linha_ano = next((i for i in range(min(10, df_bruto.shape[0]))
                      if (pd.to_numeric(df_bruto.iloc[i], errors="coerce") >= 2000).sum() >= 1), None)
    if linha_ano is None:
        raise ValueError("linha de anos nao encontrada na planilha (esperava valores >= 2000)")
    anos = df_bruto.iloc[linha_ano].ffill()
    meses = df_bruto.iloc[linha_ano + 1].astype(str).str.split("\n").str[0].str.strip()

    importacao = pd.to_numeric(df_bruto.iloc[linha_importacao], errors="coerce")
    consumo = pd.to_numeric(df_bruto.iloc[linha_consumo], errors="coerce")

    linhas = []
    for col in df_bruto.columns:
        mes, ano = meses.get(col), anos.get(col)
        if mes not in ACOBRASIL_MESES_PT_ABREV or pd.isna(ano):
            continue
        imp, cons = importacao.get(col), consumo.get(col)
        if pd.isna(imp) or pd.isna(cons) or cons == 0:
            continue
        data = pd.Timestamp(year=int(ano), month=ACOBRASIL_MESES_PT_ABREV.index(mes) + 1, day=1)
        # valores da planilha estao em MIL toneladas - converte para toneladas,
        # mesma unidade da tabela 9.1 do PDF (evita mistura de unidade na hora de combinar as duas fontes)
        linhas.append({"data": data, "consumo_aparente_t": cons * 1000, "importacao_t": imp * 1000,
                       "taxa_penetracao_pct": imp / cons * 100.0})
    return pd.DataFrame(linhas).drop_duplicates(subset="data", keep="last").set_index("data").sort_index()


def acobrasil_taxa_penetracao_xls_historico(ano_ini: int = 2013, ano_fim: int | None = None,
                                            url_xls: str | None = None) -> pd.DataFrame:
    """Baixa o Excel 'Performance Mensal' mais recente (via link resolvido
    ao vivo, a menos que url_xls seja passado) e devolve a serie historica
    APROXIMADA (nao reproduz o numero oficial do PDF - ver nota acima)
    de taxa de penetracao, planos e longos, desde ano_ini.
    tipo_dado_penetracao='aproximado_consumo_aparente'.
    """
    import io, requests
    if url_xls is None:
        url_xls = _acobrasil_resolver_links_mes_atual()["xls"]
    r = requests.get(url_xls, timeout=60, headers={"User-Agent": "pesquisa-setorial/1.0"})
    r.raise_for_status()
    df_bruto = pd.read_excel(io.BytesIO(r.content), sheet_name=0, header=None)

    partes = []
    for categoria in ("planos", "longos"):
        calc = _calcular_penetracao_de_performance_mensal(df_bruto, categoria)
        calc["categoria"] = categoria
        partes.append(calc)
    out = pd.concat(partes)
    out = out[(out.index.year >= ano_ini) & (out.index.year <= (ano_fim or out.index.year.max()))]
    out["tipo_dado_penetracao"] = "aproximado_consumo_aparente"
    out["fonte_penetracao"] = url_xls
    return out.sort_index()


def taxa_penetracao_importacao_planos_mensal(ano_ini: int = 2013, ano_fim: int | None = None,
                                              df_historico: pd.DataFrame | None = None,
                                              df_oficial: pd.DataFrame | None = None) -> pd.DataFrame:
    """Serie mensal da taxa de penetracao de importacao para PRODUTOS
    PLANOS (nao especifico de bobina a quente - e a granularidade real
    disponivel do Aco Brasil, ver docs/adr/0007). Combina as duas fontes:
    o PDF oficial para o(s) mes(es) que ele cobre, o Excel aproximado
    para preencher o resto do historico - o oficial NUNCA e sobrescrito
    pelo aproximado, mesmo que o Excel tambem cubra aquele mes.

    df_historico/df_oficial aceitam DataFrame ja pronto (mesmo formato de
    `acobrasil_taxa_penetracao_xls_historico`/`acobrasil_taxa_penetracao_pdf_mes_atual`)
    para uso em teste sem rede - se None, busca ao vivo.
    """
    if df_historico is None:
        df_historico = acobrasil_taxa_penetracao_xls_historico(ano_ini, ano_fim)
    if df_oficial is None:
        df_oficial = acobrasil_taxa_penetracao_pdf_mes_atual()

    cols = ["taxa_penetracao_pct", "tipo_dado_penetracao"]
    hist_planos = df_historico.loc[df_historico["categoria"] == "planos", cols]
    oficial_planos = df_oficial.loc[df_oficial["categoria"] == "planos", cols]
    hist_sem_sobreposicao = hist_planos[~hist_planos.index.isin(oficial_planos.index)]
    return pd.concat([hist_sem_sobreposicao, oficial_planos]).sort_index()


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

VOLUME_MINIMO_T = 5000.0  # abaixo disso, peso de confiabilidade cai linearmente ate 0
# Por que volume e nao numero de registros: um mes com poucos parceiros
# comerciais mas volume grande (ex. set/2021, pico do supercycle: 27 mil t
# em so 6 registros, porque o mercado global estava concentrado na escassez)
# e um sinal de preco REAL, nao ruido. Um mes com volume pequeno (ex. jun/2020,
# 55 t em 3 registros) e ruido de fato. Confundir os dois penalizaria
# exatamente os meses de maior conteudo informativo do indice.


def suavizar_preco_importacao(df: pd.DataFrame) -> pd.DataFrame:
    """Suavizacao SELETIVA do preco de importacao (`preco_usd_t`).

    So meses com peso_confiabilidade < 1.0 (volume abaixo de
    VOLUME_MINIMO_T) recebem, na coluna `preco_usd_t_publicado`, a media
    movel CENTRADA de 3 meses (rolling window=3, center=True,
    min_periods=1) - reduz o ruido de meses de volume fino sem descartar
    a observacao. Meses com peso_confiabilidade == 1.0 NUNCA sao
    suavizados, mesmo com poucos registros (ex.: pico de supercycle com
    volume alto mas poucos parceiros comerciais) - o publicado fica
    identico ao bruto. `preco_usd_t` (bruto) nunca e sobrescrito, fica
    sempre disponivel para auditoria. Adiciona a coluna booleana
    `suavizado` (True quando publicado difere do bruto).

    Requer as colunas `preco_usd_t` e `peso_confiabilidade` ja calculadas
    (ver `serie_mensal_preco_bobina`).
    """
    out = df.copy()
    media_movel = out["preco_usd_t"].rolling(window=3, center=True, min_periods=1).mean()
    out["preco_usd_t_publicado"] = out["preco_usd_t"].where(
        out["peso_confiabilidade"] >= 1.0, media_movel)
    out["suavizado"] = (out["preco_usd_t_publicado"] - out["preco_usd_t"]).abs() > 1e-9
    return out


def serie_mensal_preco_bobina(ano_ini: int = 2020, ano_fim: int = 2026) -> pd.DataFrame:
    """Serie mensal de preco unitario de importacao (USD/t) para os 13 NCMs de
    bobina a quente, ponderado por volume (soma FOB / soma KG de todos os NCMs
    e paises no mes - nao e media simples entre NCMs, e um preco medio real
    do que o Brasil comprou naquele mes).

    Aplica tres tratamentos, todos versionados e explicitos via colunas:
      - interpolado: mes sem registro no Comex Stat, preenchido por
        interpolacao linear entre os meses vizinhos. Provisorio - o ideal e
        investigar por que o mes ficou sem dado antes de publicar de verdade.
      - peso_confiabilidade: 1.0 para meses com volume >= VOLUME_MINIMO_T,
        caindo linearmente ate 0 abaixo disso. NAO usa numero de registros
        como criterio - ver nota acima.
      - preco_usd_t_publicado / suavizado: suavizacao seletiva via
        `suavizar_preco_importacao` - so meses de peso_confiabilidade < 1.0
        sao suavizados (media movel de 3 meses); meses de peso pleno ficam
        identicos ao bruto.

    Tambem agrega frete_usd_t e seguro_usd_t (mesmo criterio do preco_usd_t:
    soma do mes / soma de KG do mes) - sao os insumos que `custo_importacao_rs_t`
    precisa alem do FOB para montar o CIF. Nao sao suavizados - a suavizacao
    seletiva se aplica so ao preco (ver docs/METODOLOGIA.md secao 5).
    """
    ncms = sorted(sum(NCM_BOBINA_QUENTE.values(), []))
    df = comex_importacao_ncm(ncms, ano_ini, ano_fim)
    if df.empty:
        return df
    for col in ("metricFOB", "metricKG", "metricFreight", "metricInsurance"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["data"] = pd.to_datetime(df["year"].astype(str) + "-"
                                 + df["monthNumber"].astype(str).str.zfill(2) + "-01")
    mensal = (df.groupby("data")
                .agg(fob_usd=("metricFOB", "sum"), kg=("metricKG", "sum"),
                     frete_usd=("metricFreight", "sum"), seguro_usd=("metricInsurance", "sum"),
                     n_registros=("metricFOB", "size"))
                .reset_index())
    mensal["preco_usd_t"]  = 1000 * mensal["fob_usd"] / mensal["kg"]
    mensal["frete_usd_t"]  = 1000 * mensal["frete_usd"] / mensal["kg"]
    mensal["seguro_usd_t"] = 1000 * mensal["seguro_usd"] / mensal["kg"]
    mensal["toneladas"] = mensal["kg"] / 1000
    mensal = mensal.set_index("data")[
        ["toneladas", "preco_usd_t", "frete_usd_t", "seguro_usd_t", "n_registros"]]

    # revela e preenche buracos de mes (nenhum registro no Comex Stat naquele mes)
    completa = mensal.asfreq("MS")
    completa["interpolado"] = completa["preco_usd_t"].isna()
    for col in ("preco_usd_t", "frete_usd_t", "seguro_usd_t", "toneladas"):
        completa[col] = completa[col].interpolate(method="linear")
    completa["n_registros"] = completa["n_registros"].fillna(0).astype(int)

    completa["peso_confiabilidade"] = (completa["toneladas"] / VOLUME_MINIMO_T).clip(upper=1.0)
    completa.loc[completa["interpolado"], "peso_confiabilidade"] = 0.0  # mes interpolado nao e dado real

    completa = suavizar_preco_importacao(completa)

    return completa.reset_index()




def calcular_ipia_mensal(ano_ini: int = 2020, ano_fim: int = 2026) -> pd.DataFrame:
    """Calcula o IPIA mensal completo: custo de importacao real (Comex Stat +
    cambio BCB) contra a ancora de preco domestico (CSV curado + IPP).

    Mesmo calculo usado pelo branch `--ipia` da CLI e pelo relatorio PDF
    (`gerar_pdf_ipia`) - centralizado aqui para as duas saidas nunca
    divergirem. Retorna as colunas: ipia, preco_domestico_rs_t, ppi_rs_t,
    tipo_dado_domestico, metodo_domestico, peso_confiabilidade_importacao.
    """
    bobina = serie_mensal_preco_bobina(ano_ini, ano_fim)
    if bobina.empty:
        return bobina
    bobina = bobina.set_index("data")
    # cambio_venda (codigo 1, PTAX) e serie diaria - a API do BCB rejeita
    # (406) janela de consulta acima de 10 anos para series diarias, entao
    # o inicio e amarrado a ano_ini em vez do default de sgs() (2010),
    # que sozinho ja estoura o limite a partir de 2020.
    cambio = sgs(SGS["cambio_venda"], inicio=f"01/01/{ano_ini}").reindex(bobina.index, method="ffill")
    # preco_usd_t_publicado (nao o preco_usd_t bruto) alimenta o custo de
    # importacao: e a serie com suavizacao seletiva ja aplicada (identica ao
    # bruto em meses de peso pleno, media movel de 3 meses em meses de peso
    # reduzido) - ver `suavizar_preco_importacao` e docs/adr/0005. O bruto
    # continua disponivel na coluna preco_usd_t para auditoria, so nao e o
    # que entra no calculo do IPIA publicado.
    custo = custo_importacao_rs_t(bobina["preco_usd_t_publicado"], bobina["frete_usd_t"],
                                  bobina["seguro_usd_t"], cambio, ParamsIPIA())
    trimestral = carregar_preco_domestico_trimestral()
    blend = preco_domestico_ponderado(trimestral)
    ipp = ibge_sidra_ipp_metalurgia()
    domestico = encadear_preco_domestico_mensal(blend, ipp)
    # Taxa de penetracao de importacao (Aco Brasil, Planos - ver docs/adr/0007):
    # mes sem dado (nem oficial nem aproximado ainda disponivel) fica NaN
    # explicito via reindex sem ffill - nunca fabricado.
    penetracao = taxa_penetracao_importacao_planos_mensal()
    idx = bobina.index.intersection(domestico.index)
    return pd.DataFrame({
        "ipia": ipia(domestico.loc[idx, "preco_rs_t"], custo.loc[idx, "ppi_brl_t"]),
        "preco_domestico_rs_t": domestico.loc[idx, "preco_rs_t"],
        "ppi_rs_t": custo.loc[idx, "ppi_brl_t"],
        "tipo_dado_domestico": domestico.loc[idx, "tipo_dado"],
        "metodo_domestico": domestico.loc[idx, "metodo"],
        "peso_confiabilidade_importacao": bobina.loc[idx, "peso_confiabilidade"],
        "penetracao_importacao_planos_pct": penetracao["taxa_penetracao_pct"].reindex(idx),
        "tipo_dado_penetracao": penetracao["tipo_dado_penetracao"].reindex(idx),
    })

# =============================================================================
# 5. RELATORIO / VISUALIZACAO (PDF)
# =============================================================================

def gerar_pdf_ipia(df: pd.DataFrame, caminho_pdf: str, params: ParamsIPIA,
                   data_geracao: Optional[dt.datetime] = None) -> None:
    """Pagina unica em PDF com a serie do IPIA ja calculada.

    So visualiza - nao recalcula nem busca dado novo, tudo vem do
    DataFrame recebido (ver `calcular_ipia_mensal`). "Penetracao de
    importacao" (Planos, Aco Brasil - ver docs/adr/0007) mostra o numero
    real quando o mes mais recente do DataFrame tiver dado; se o mes nao
    tiver (nem oficial nem aproximado ainda disponivel), mostra "nao
    disponivel" - nunca um numero inventado para preencher a lacuna.
    """
    import textwrap
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    if df.empty:
        raise ValueError("DataFrame do IPIA vazio - nada para plotar")
    data_geracao = data_geracao or dt.datetime.now()
    ultimo = df.iloc[-1]
    spread_rs = ultimo["preco_domestico_rs_t"] - ultimo["ppi_rs_t"]

    fig = plt.figure(figsize=(8.27, 11.69))  # A4 retrato
    fig.suptitle("IPIA — Índice de Paridade de Importação do Aço",
                 fontsize=16, fontweight="bold", y=0.97)
    fig.text(0.5, 0.945, f"Gerado em {data_geracao:%d/%m/%Y %H:%M}",
             ha="center", fontsize=9, color="dimgray")

    # --- grafico da serie historica -----------------------------------------
    ax = fig.add_axes((0.10, 0.68, 0.85, 0.22))
    ax.plot(df.index, df["ipia"], marker="o", color="#1f4e79")
    ax.axhline(100, linestyle="--", color="gray", linewidth=1)
    ax.set_ylabel("IPIA (100 = paridade)")
    ax.set_title("Série histórica", fontsize=11, loc="left")
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
    ax.tick_params(axis="x", labelsize=8)

    # --- painel com os numeros mais recentes ---------------------------------
    penet = ultimo.get("penetracao_importacao_planos_pct")
    tipo_penet = ultimo.get("tipo_dado_penetracao")
    if pd.notna(penet):
        rotulo_penet = "oficial" if tipo_penet == "oficial_mensal" else "aproximado"
        linha_penetracao = f"Penetração de importação (Planos, {rotulo_penet}): {penet:.1f}%"
    else:
        linha_penetracao = "Penetração de importação: não disponível para este mês"
    linhas_painel = [
        f"IPIA atual ({df.index[-1]:%b/%Y}): {ultimo['ipia']:.1f}",
        f"Preço doméstico: R$ {ultimo['preco_domestico_rs_t']:,.0f}/t",
        f"Custo de importação (paridade): R$ {ultimo['ppi_rs_t']:,.0f}/t",
        f"Spread doméstico vs. paridade: R$ {spread_rs:,.0f}/t ({ultimo['ipia'] - 100:+.1f} pts)",
        linha_penetracao,
    ]
    ax_p = fig.add_axes((0.10, 0.50, 0.85, 0.12)); ax_p.axis("off")
    ax_p.text(0, 1, "\n".join(linhas_painel), fontsize=10, va="top", family="monospace")

    # --- ressalva de metodologia ---------------------------------------------
    ressalva = textwrap.fill(
        "RESSALVAS: preço doméstico é proxy do segmento \"Siderurgia\" "
        "(Usiminas+CSN), não específico de bobina a quente (ver "
        "docs/adr/0003). Antidumping ainda não confirmado "
        f"(antidumping_usd_t={params.antidumping_usd_t:.1f}, default zerado ate confirmacao).",
        width=90)
    ax_r = fig.add_axes((0.10, 0.36, 0.85, 0.11)); ax_r.axis("off")
    ax_r.text(0.02, 0.5, ressalva, fontsize=8.5, va="center",
              bbox=dict(boxstyle="round", facecolor="#fff3cd", edgecolor="#856404"))

    # --- rodape: fontes e metodologia -----------------------------------------
    rodape = textwrap.fill(
        "Fontes: Comex Stat (importação), BCB/SGS (câmbio), releases "
        "trimestrais Usiminas/CSN (preço doméstico), IBGE/SIDRA IPP "
        "metalurgia (encadeamento mensal), Instituto Aço Brasil "
        "(penetração de importação, Planos). Metodologia: IPIA = preço "
        "doméstico / custo de importação posto no cliente (CIF + II + "
        "AFRMM + antidumping + despesas de porto + frete interno + "
        "margem) × 100.", width=100)
    fig.text(0.10, 0.26, rodape, fontsize=7, va="bottom", color="#444444")

    import os
    diretorio = os.path.dirname(caminho_pdf)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)
    fig.savefig(caminho_pdf, format="pdf")
    plt.close(fig)


def _serie_sintetica(n=180, seed=0, tendencia=0.0, nivel=10.0, ruido=1.0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2012-01-01", periods=n, freq="MS")
    saz = 0.8 * np.sin(2 * np.pi * np.arange(n) / 12)
    return pd.Series(nivel + tendencia * np.arange(n) + saz +
                     rng.normal(0, ruido, n), index=idx)


def selftest() -> int:
    print("=" * 74)
    print(" AUTOTESTE - validacao da matematica do motor de indices")
    print("=" * 74)
    falhas = []

    def check(nome, cond, detalhe=""):
        print(f"  [{'OK ' if cond else 'FALHA'}] {nome}" + (f"  {detalhe}" if detalhe else ""))
        if not cond:
            falhas.append(nome)

    # --- 1. z-score de janela fixa nao reescreve o passado -------------------
    s = _serie_sintetica(seed=1)
    z1 = zscore_janela_fixa(s, JANELA_REF)
    s2 = pd.concat([s, _serie_sintetica(n=12, seed=99, nivel=40.0).set_axis(
        pd.date_range(s.index[-1] + pd.offsets.MonthBegin(), periods=12, freq="MS"))])
    z2 = zscore_janela_fixa(s2, JANELA_REF)
    dif = float((z2.loc[z1.index] - z1).abs().max())
    check("janela fixa: acrescentar 12 meses extremos nao altera o passado",
          dif < 1e-10, f"desvio maximo = {dif:.2e}")

    # contraprova: com janela = amostra cheia, o passado MUDA a cada mes novo
    def z_amostra_cheia(x):
        return (x - x.mean()) / x.std(ddof=1)
    d_exp = float((z_amostra_cheia(s2).loc[z1.index] - z_amostra_cheia(s)).abs().max())
    check("contraprova: padronizar pela amostra cheia reescreve o passado",
          d_exp > 1e-3, f"desvio maximo = {d_exp:.3f} (por isso a janela e congelada)")

    # --- 2. winsorizacao ----------------------------------------------------
    z = zscore_janela_fixa(_serie_sintetica(seed=2), JANELA_REF)
    check("winsorizacao respeita o limite de +/-3 desvios",
          float(z.abs().max()) <= WINSOR_Z + 1e-9, f"max |z| = {float(z.abs().max()):.3f}")

    # --- 3. media da janela de referencia cai em 50 --------------------------
    espec_min = EspecIndice("T", "teste",
                            [Pilar("p", 1.0)],
                            [Variavel("v", "p", 1.0, +1)])
    zz = pd.DataFrame({"v": zscore_janela_fixa(_serie_sintetica(seed=3), JANELA_REF)})
    out = agregar(zz, espec_min)
    ini, fim = JANELA_REF
    m = out.loc[(out.index >= ini) & (out.index <= fim), "indice"].mean()
    check("indice medio na janela de referencia = 50", abs(m - 50) < 0.6, f"media = {m:.2f}")

    # --- 4. orientacao inverte o sinal --------------------------------------
    e_pos = EspecIndice("A", "a", [Pilar("p", 1.0)], [Variavel("v", "p", 1.0, +1)])
    e_neg = EspecIndice("B", "b", [Pilar("p", 1.0)], [Variavel("v", "p", 1.0, -1)])
    a = agregar(zz, e_pos)["indice"]
    b = agregar(zz, e_neg)["indice"]
    check("orientacao -1 espelha o indice em torno de 50",
          float(((a - 50) + (b - 50)).abs().max()) < 1e-9)

    # --- 5. dado faltante redistribui peso ----------------------------------
    espec2 = EspecIndice("C", "c", [Pilar("p", 1.0)],
                         [Variavel("v1", "p", 0.7, +1), Variavel("v2", "p", 0.3, +1)])
    z2df = pd.DataFrame({
        "v1": zscore_janela_fixa(_serie_sintetica(seed=4), JANELA_REF),
        "v2": zscore_janela_fixa(_serie_sintetica(seed=5), JANELA_REF)})
    cheio = agregar(z2df, espec2)
    z_falta = z2df.copy(); z_falta.loc[z_falta.index[-6:], "v2"] = np.nan
    parcial = agregar(z_falta, espec2)
    esperado = ESCALA_A + ESCALA_B * z_falta["v1"].iloc[-1]
    check("com v2 ausente, o indice vira 100% v1",
          abs(float(parcial["indice"].iloc[-1]) - float(esperado)) < 1e-9)
    check("cobertura cai para 0,70 quando falta a variavel de peso 0,30",
          abs(float(parcial["cobertura"].iloc[-1]) - 0.70) < 1e-9,
          f"cobertura = {float(parcial['cobertura'].iloc[-1]):.2f}")
    check("cobertura cheia = 1,00", abs(float(cheio["cobertura"].iloc[-1]) - 1.0) < 1e-9)

    # --- 6. corte por cobertura minima --------------------------------------
    espec3 = EspecIndice("D", "d", [Pilar("p1", 0.5), Pilar("p2", 0.5)],
                         [Variavel("v1", "p1", 1.0, +1), Variavel("v2", "p2", 1.0, +1)])
    z3 = z2df.copy(); z3.loc[z3.index[-3:], "v2"] = np.nan
    o3 = agregar(z3, espec3)
    check("setor com cobertura 0,50 (< minimo 0,60) nao e publicado",
          bool(o3["indice"].iloc[-3:].isna().all()))

    # --- 7. validacao de especificacao --------------------------------------
    try:
        EspecIndice("E", "e", [Pilar("p", 0.9)], [Variavel("v", "p", 1.0)]).validar()
        check("especificacao com pesos de pilar invalidos e rejeitada", False)
    except ValueError:
        check("especificacao com pesos de pilar invalidos e rejeitada", True)
    try:
        ICCS.validar(); check("especificacao do ICCS e consistente", True)
    except ValueError as e:
        check("especificacao do ICCS e consistente", False, str(e))

    # --- 8. IPIA: aritmetica da paridade ------------------------------------
    idx = pd.date_range("2024-01-01", periods=3, freq="MS")
    p = ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                   frete_interno_rs_t=100.0, margem_importador=0.0)
    fob = pd.Series([500.0] * 3, index=idx)
    fr  = pd.Series([50.0] * 3, index=idx)
    seg = pd.Series([5.0] * 3, index=idx)
    cbo = pd.Series([5.0] * 3, index=idx)
    r = custo_importacao_rs_t(fob, fr, seg, cbo, p)
    # CIF = 555 USD -> 2775 BRL ; II = 277,5 ; AFRMM = 250*0,08 = 20 ; +300
    esperado_ppi = 2775 + 277.5 + 20 + 300
    check("custo de importacao confere com o calculo manual",
          abs(float(r["ppi_brl_t"].iloc[0]) - esperado_ppi) < 1e-9,
          f"calculado = {float(r['ppi_brl_t'].iloc[0]):.2f}, esperado = {esperado_ppi:.2f}")
    ix = ipia(pd.Series([esperado_ppi] * 3, index=idx), r["ppi_brl_t"])
    check("preco domestico igual a paridade => indice = 100",
          abs(float(ix.iloc[0]) - 100.0) < 1e-9)
    ix2 = ipia(pd.Series([esperado_ppi * 1.15] * 3, index=idx), r["ppi_brl_t"])
    check("domestico 15% acima da paridade => indice = 115",
          abs(float(ix2.iloc[0]) - 115.0) < 1e-9)

    # --- 8b. IPIA: antidumping soma ao custo, convertido pelo cambio --------
    p_ad = ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                      frete_interno_rs_t=100.0, margem_importador=0.0,
                      antidumping_usd_t=80.0)
    cambio5 = pd.Series([5.0] * 3, index=idx)
    r_ad = custo_importacao_rs_t(fob, fr, seg, cambio5, p_ad)
    # mesmo calculo de antes (2775+277.5+20+300=3372.5) + 80 USD/t * 5 = 400 BRL/t
    esperado_ad = esperado_ppi + 80.0 * 5.0
    check("antidumping (US$/t x cambio) soma corretamente ao custo de importacao",
          abs(float(r_ad["ppi_brl_t"].iloc[0]) - esperado_ad) < 1e-9,
          f"calculado = {float(r_ad['ppi_brl_t'].iloc[0]):.2f}, esperado = {esperado_ad:.2f}")
    check("com antidumping=0 (default), resultado nao muda vs. calculo original",
          abs(float(r["ppi_brl_t"].iloc[0]) - esperado_ppi) < 1e-9)

    # --- 8c. peso de confiabilidade: por VOLUME, nao por numero de registros -
    # mes com poucos registros mas volume grande (ex.: mercado concentrado no
    # pico de um supercycle) deve ficar com peso pleno; mes de volume pequeno,
    # mesmo com registros moderados, deve ficar com peso reduzido.
    idx_meses = pd.date_range("2021-01-01", periods=3, freq="MS")
    bruto = pd.DataFrame({
        "toneladas":   [27379.0, 1373.0, 55.0],   # alto / abaixo do limiar / muito baixo
        "preco_usd_t": [1082.0, 539.0, 656.0],
        "n_registros": [6, 6, 3],                  # dois primeiros tem o MESMO n_registros
    }, index=idx_meses)
    peso = (bruto["toneladas"] / VOLUME_MINIMO_T).clip(upper=1.0)
    check("mes de alto volume e poucos registros recebe peso pleno (nao penalizado por n_registros)",
          abs(peso.iloc[0] - 1.0) < 1e-9,
          f"peso calculado = {peso.iloc[0]:.3f} (deveria ser 1.0, volume={bruto['toneladas'].iloc[0]:.0f}t >= {VOLUME_MINIMO_T:.0f}t)")
    check("dois meses com o MESMO n_registros mas volumes diferentes recebem pesos diferentes",
          abs(peso.iloc[0] - peso.iloc[1]) > 0.5,
          f"peso[alto volume]={peso.iloc[0]:.3f} vs peso[baixo volume]={peso.iloc[1]:.3f}, ambos com n_registros=6")
    check("mes de volume muito baixo recebe peso proximo de zero",
          peso.iloc[2] < 0.02,
          f"peso calculado = {peso.iloc[2]:.4f}")

    # --- 8d. suavizacao seletiva: so meses de peso reduzido sao suavizados --
    idx_suav = pd.date_range("2021-01-01", periods=5, freq="MS")
    df_suav = pd.DataFrame({
        "preco_usd_t":         [1000.0, 1082.0, 1100.0, 600.0, 650.0],
        "peso_confiabilidade": [1.0,    1.0,    1.0,    0.011, 1.0],
    }, index=idx_suav)
    suav = suavizar_preco_importacao(df_suav)
    # caso 1: mes de peso PLENO (ex.: pico de supercycle, poucos parceiros
    # mas volume alto) mantem o publicado IDENTICO ao bruto, mesmo cercado
    # por vizinhos de preco bem diferente.
    check("mes de peso pleno mantem preco_usd_t_publicado identico ao bruto (nunca suaviza peso pleno)",
          abs(float(suav["preco_usd_t_publicado"].iloc[1]) - float(suav["preco_usd_t"].iloc[1])) < 1e-9
          and not bool(suav["suavizado"].iloc[1]))
    # caso 2: mes de peso reduzido recebe a media movel centrada de 3 (janela
    # em torno do indice 3: indices 2,3,4 = 1100, 600, 650) - e o bruto (600)
    # continua intocado na coluna preco_usd_t, disponivel para auditoria.
    esperado_suav = (1100.0 + 600.0 + 650.0) / 3
    check("mes de peso reduzido recebe media movel centrada de 3 meses no publicado",
          abs(float(suav["preco_usd_t_publicado"].iloc[3]) - esperado_suav) < 1e-6
          and bool(suav["suavizado"].iloc[3]),
          f"publicado = {float(suav['preco_usd_t_publicado'].iloc[3]):.4f}, esperado = {esperado_suav:.4f}")
    check("bruto (preco_usd_t) nunca e sobrescrito pela suavizacao",
          abs(float(suav["preco_usd_t"].iloc[3]) - 600.0) < 1e-9)

    # --- 9. diagnostico de antecedencia detecta sinal plantado --------------
    base = _serie_sintetica(n=160, seed=7, ruido=0.5)
    # alvo cujo movimento futuro responde ao sinal com defasagem: piora quando
    # o indice sobe, com 6 meses de atraso (ex.: inadimplencia do setor)
    alvo = (-base).shift(6).cumsum()
    ind = 50 + 10 * zscore_janela_fixa(base, JANELA_REF)
    diag = diagnostico_antecedencia(ind, alvo)
    melhor = float(diag["correlacao"].abs().max())
    contemp = abs(diag.attrs["correlacao_contemporanea"])
    check("correlacao a frente supera a contemporanea em sinal antecedente",
          melhor > contemp, f"a frente = {melhor:.3f} vs contemporanea = {contemp:.3f}")
    # ruido branco puro nao deve produzir antecedencia relevante
    rng = np.random.default_rng(11)
    puro = pd.Series(rng.normal(0, 1, 160), index=base.index)
    d2 = diagnostico_antecedencia(50 + 10 * zscore_janela_fixa(puro, JANELA_REF),
                                  pd.Series(rng.normal(0, 1, 160), index=base.index).cumsum())
    check("ruido branco nao gera antecedencia espuria forte",
          float(d2["correlacao"].abs().max()) < 0.45,
          f"maior |correlacao| = {float(d2['correlacao'].abs().max()):.3f}")

    # --- 10. PCA de validacao roda -----------------------------------------
    v = validar_com_pca(z2df)
    check("validacao por PCA executa e reporta variancia explicada",
          v.get("ok") and "var_explicada_pc1" in v,
          f"PC1 explica {v.get('var_explicada_pc1')}")

    # --- 11. ancora de preco domestico: carregar CSV curado -----------------
    import tempfile, os as _os
    csv_sintetico = (
        "trimestre,empresa,receita_liquida_segmento_rs,volume_vendas_t,preco_rs_t,tipo,fonte\n"
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,CSNA3,,500000,5000,proxy_segmento_aco,teste\n"
        "2026Q2,USIM5,,1200000,5100,especifico_laminado_quente,teste\n"
    )
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    try:
        with _os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(csv_sintetico)
        carregado = carregar_preco_domestico_trimestral(tmp_path)
        preco_usim_calc = float(carregado.loc[carregado["empresa"] == "USIM5", "preco_rs_t"].iloc[0])
        check("preco_rs_t calculado a partir de receita/volume quando nao vem pronto",
              abs(preco_usim_calc - 4700.0) < 1e-6, f"calculado = {preco_usim_calc:.4f}")
        preco_csn_direto = float(carregado.loc[carregado["empresa"] == "CSNA3", "preco_rs_t"].iloc[0])
        check("preco_rs_t ja vindo pronto da fonte (CSN) nao e recalculado",
              abs(preco_csn_direto - 5000.0) < 1e-9)
    finally:
        _os.remove(tmp_path)

    # --- 12. ancora de preco domestico: blend ponderado por volume ----------
    tri_teste = pd.DataFrame({
        "trimestre":       ["2026Q1", "2026Q1", "2026Q2"],
        "empresa":         ["USIM5", "CSNA3", "USIM5"],
        "preco_rs_t":      [4700.0, 5000.0, 5100.0],
        "volume_vendas_t": [1000000.0, 500000.0, 1200000.0],
        "tipo":            ["proxy_segmento_aco", "proxy_segmento_aco", "especifico_laminado_quente"],
    })
    blend = preco_domestico_ponderado(tri_teste)
    q1 = blend.loc[blend["trimestre"] == "2026Q1"].iloc[0]
    esperado_q1 = (4700.0 * 1000000.0 + 5000.0 * 500000.0) / 1500000.0
    check("blend ponderado por volume bate com a media manual",
          abs(float(q1["preco_rs_t"]) - esperado_q1) < 1e-6,
          f"calculado = {float(q1['preco_rs_t']):.4f}, esperado = {esperado_q1:.4f}")
    check("trimestre com so uma empresa preserva o tipo original (nao vira misto)",
          blend.loc[blend["trimestre"] == "2026Q2", "tipo"].iloc[0] == "especifico_laminado_quente")
    tri_misto = pd.DataFrame({
        "trimestre":       ["2026Q3", "2026Q3"],
        "empresa":         ["USIM5", "CSNA3"],
        "preco_rs_t":      [5200.0, 5100.0],
        "volume_vendas_t": [1000000.0, 500000.0],
        "tipo":            ["especifico_laminado_quente", "proxy_segmento_aco"],
    })
    blend_misto = preco_domestico_ponderado(tri_misto)
    check("trimestre com tipos diferentes entre empresas vira 'misto' (nunca finge especifico)",
          blend_misto["tipo"].iloc[0] == "misto", f"tipo = {blend_misto['tipo'].iloc[0]}")

    # --- 12b. cobertura real do CSV curado: trimestres com AS DUAS empresas -
    # Diferente dos testes acima (dado sintetico), esta checagem le o CSV
    # curado de verdade (CAMINHO_PRECO_DOMESTICO_CSV) e garante que o blend
    # ponderado por volume nao seja, na pratica, sempre uma empresa isolada
    # disfarcada de blend (ver docs/adr/0001). Piso de 4 reflete a cobertura
    # curada ate agora (2025Q2, 2025Q3, 2025Q4, 2026Q2) - suba este numero
    # conforme mais trimestres forem adicionados ao CSV, nao antes.
    COBERTURA_DUPLA_MINIMA = 4
    csv_real = carregar_preco_domestico_trimestral()
    n_empresas_por_trimestre = csv_real.groupby("trimestre")["empresa"].nunique()
    trimestres_com_ambas = n_empresas_por_trimestre[n_empresas_por_trimestre >= 2]
    check(f"CSV curado tem pelo menos {COBERTURA_DUPLA_MINIMA} trimestres com Usiminas E CSN simultaneamente",
          len(trimestres_com_ambas) >= COBERTURA_DUPLA_MINIMA,
          f"{len(trimestres_com_ambas)} trimestre(s) com blend real: {sorted(trimestres_com_ambas.index.tolist())}")

    # --- 13. ancora de preco domestico: encadeamento mensal via IPP ---------
    # So 2026Q1 esta "confirmado" (so ele esta no CSV trimestral) - abr/mai/jun
    # ainda nao tem release, entao precisam ser projetados mes a mes pelo IPP.
    tri_encad = pd.DataFrame({
        "trimestre":       ["2026Q1"],
        "preco_rs_t":      [5000.0],
        "tipo":            ["proxy_segmento_aco"],
    })
    ipp_teste = pd.Series({
        pd.Timestamp("2026-03-01"): 100.0, pd.Timestamp("2026-04-01"): 102.0,
        pd.Timestamp("2026-06-01"): 110.0,   # maio ausente de proposito (buraco)
    })
    mensal = encadear_preco_domestico_mensal(tri_encad, ipp_teste)
    check("meses dentro do trimestre confirmado usam o nivel direto (nao encadeiam)",
          mensal.loc["2026-01-01":"2026-03-01", "metodo"].eq("nivel_trimestral").all()
          and abs(float(mensal.loc["2026-02-01", "preco_rs_t"]) - 5000.0) < 1e-9)
    esperado_abr = 5000.0 * (102.0 / 100.0)
    check("mes seguinte ao trimestre confirmado encadeia pela variacao do IPP",
          mensal.loc["2026-04-01", "metodo"] == "encadeado_ipp"
          and abs(float(mensal.loc["2026-04-01", "preco_rs_t"]) - esperado_abr) < 1e-6,
          f"calculado = {float(mensal.loc['2026-04-01', 'preco_rs_t']):.4f}, esperado = {esperado_abr:.4f}")
    check("mes sem IPP publicado ainda (maio) cai em hold_flat_fallback (nao vira NaN, nao extrapola)",
          mensal.loc["2026-05-01", "metodo"] == "hold_flat_fallback"
          and abs(float(mensal.loc["2026-05-01", "preco_rs_t"])
                  - float(mensal.loc["2026-04-01", "preco_rs_t"])) < 1e-9)
    esperado_jun = 5000.0 * (110.0 / 100.0)
    check("mes seguinte, com IPP de volta a disponivel, volta a encadear (nao fica preso no fallback)",
          mensal.loc["2026-06-01", "metodo"] == "encadeado_ipp"
          and abs(float(mensal.loc["2026-06-01", "preco_rs_t"]) - esperado_jun) < 1e-6)

    # --- 14. round-trip: ancora domestica + custo de importacao -> IPIA -----
    idx_rt = pd.date_range("2026-01-01", periods=3, freq="MS")
    p_rt = ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                      frete_interno_rs_t=100.0, margem_importador=0.0)
    r_rt = custo_importacao_rs_t(pd.Series([500.0] * 3, index=idx_rt),
                                 pd.Series([50.0] * 3, index=idx_rt),
                                 pd.Series([5.0] * 3, index=idx_rt),
                                 pd.Series([5.0] * 3, index=idx_rt), p_rt)
    preco_domestico_rt = mensal["preco_rs_t"].reindex(idx_rt)
    ix_rt = ipia(preco_domestico_rt, r_rt["ppi_brl_t"])
    esperado_ix_rt = (preco_domestico_rt / r_rt["ppi_brl_t"]) * 100.0
    check("integracao ancora domestica + custo de importacao nao quebra a aritmetica do ipia()",
          bool(((ix_rt - esperado_ix_rt).abs() < 1e-9).all()))

    # --- 15. geracao de PDF do IPIA -----------------------------------------
    idx_pdf = pd.date_range("2026-01-01", periods=6, freq="MS")
    df_pdf = pd.DataFrame({
        "ipia":                          [130.4, 142.6, 143.4, 139.3, 140.1, 134.0],
        "preco_domestico_rs_t":          [5213.2, 5213.2, 5213.2, 4996.0, 4996.0, 4996.0],
        "ppi_rs_t":                      [3996.8, 3655.7, 3636.0, 3586.3, 3567.2, 3727.9],
        "tipo_dado_domestico":           ["proxy_segmento_aco"] * 6,
        "metodo_domestico":              ["nivel_trimestral"] * 6,
        "peso_confiabilidade_importacao":[1.0] * 6,
        "penetracao_importacao_planos_pct": [24.1, 20.2, 18.5, 17.9, np.nan, 17.9],
        "tipo_dado_penetracao":          ["aproximado_consumo_aparente"] * 4 + [np.nan, "oficial_mensal"],
    }, index=idx_pdf)
    tmp_pdf_fd, tmp_pdf_path = tempfile.mkstemp(suffix=".pdf")
    _os.close(tmp_pdf_fd)
    try:
        gerar_pdf_ipia(df_pdf, tmp_pdf_path, ParamsIPIA())
        tamanho = _os.path.getsize(tmp_pdf_path)
        check("PDF do IPIA e gerado sem erro e nao esta vazio",
              _os.path.exists(tmp_pdf_path) and tamanho > 0,
              f"tamanho = {tamanho} bytes")
    finally:
        _os.remove(tmp_pdf_path)

    # --- 16. taxa de penetracao: parsing da tabela 9.1 do PDF do Aco Brasil -
    # Texto real capturado do PDF "Estatistica Mensal" de jul/2026 (paginas
    # 9.1 Mensal + 9.2 Acumulado no Ano juntas, como pdfplumber extrai) -
    # confirma que a funcao pega a secao certa (9.1) e nao a errada (9.2),
    # que tem os MESMOS rotulos de produto com numeros diferentes.
    texto_pdf_teste = (
        "9.1. Taxa de Penetração das Importações Brasileiras de Produtos de Aço - Mensal\n"
        "Import Penetratrion of Steel Products - Monthly\n"
        "Unid. / Unit: Tonelada / Tonne\n"
        "Julho / July Julho / July\n"
        "2025 2026\n"
        "Produto\n"
        "Consumo/ Importação/ Consumo/ Importação/\n"
        "Product ( B / A ) ( B / A )\n"
        "Consumption Import Consumption Import\n"
        "(%) (%)\n"
        "(A) (B) (A) (B)\n"
        "Planos / Flats 1.370.203 329.812 24,1 1.361.849 244.207 17,9\n"
        "Longos / Longs 964.772 149.091 15,5 864.219 125.901 14,6\n"
        "Total 2.334.975 478.903 20,5 2.226.068 370.108 16,6\n"
        "Nota / Note: Para evitar dupla contagem, excluídas as importações diretas pelas usinas.\n"
        "Fonte / Source: Aço Brasil / MDIC\n"
        "9.2. Taxa de Penetração das Importações Brasileiras de Produtos de Aço - Acumulado no Ano\n"
        "Import Penetratrion of Steel Products - Year to Date\n"
        "Unid. / Unit: Tonelada / Tonne\n"
        "Jan-Jul / Jan-Jul Jan-Jul / Jan-Jul\n"
        "2025 2026\n"
        "Produto\n"
        "Planos/ Flats 9.723.679 2.558.850 26,3 9.362.495 2.015.832 21,5\n"
        "Longos/ Longs 6.265.458 1.096.052 17,5 5.823.250 830.313 14,3\n"
        "Total 15.989.137 3.654.902 22,9 15.185.745 2.846.145 18,7\n"
    )
    dados_penet = _parse_tabela_penetracao_pdf(texto_pdf_teste)
    check("penetracao PDF: pega o mes/ano certos (Julho/2026, nao o ano anterior)",
          dados_penet["mes_nome"] == "Julho" and dados_penet["ano"] == 2026
          and dados_penet["ano_anterior"] == 2025)
    check("penetracao PDF: pega a taxa da secao 9.1 (Mensal), nao a 9.2 (Acumulado)",
          abs(dados_penet["planos"]["taxa_penetracao_pct"] - 17.9) < 1e-9
          and abs(dados_penet["longos"]["taxa_penetracao_pct"] - 14.6) < 1e-9,
          f"planos = {dados_penet['planos']['taxa_penetracao_pct']} (9.1=17.9, 9.2=21.5 - teria pegado errado)")
    check("penetracao PDF: consumo/importacao em toneladas batem com o texto",
          abs(dados_penet["planos"]["consumo_aparente_t"] - 1361849.0) < 1e-6
          and abs(dados_penet["planos"]["importacao_t"] - 244207.0) < 1e-6)

    # --- 17. taxa de penetracao: calculo a partir do Excel 'Performance Mensal'
    # DataFrame sintetico pequeno reproduzindo o layout real (secoes
    # localizadas por texto, nao por indice de linha fixo).
    df_bruto_teste = pd.DataFrame([
        ["Especificação\nSpecification", 2025, None, None],
        [None, "Jan\nJan", "Fev\nFeb", "Mar\nMar"],
        ["Importações / Imports", None, None, None],
        ["Planos / Flats", 100.0, 110.0, 120.0],
        ["Longos / Longs", 50.0, 55.0, 60.0],
        ["Consumo Aparente / Apparent Consumption", None, None, None],
        ["Planos / Flats\n(Inclui Placas)", 500.0, 550.0, 600.0],
        ["Longos / Longs\n(Inclui Blocos)", 300.0, 330.0, 360.0],
    ])
    calc_planos = _calcular_penetracao_de_performance_mensal(df_bruto_teste, "planos")
    check("penetracao Excel: localiza as linhas certas por texto e calcula Importacao/Consumo",
          len(calc_planos) == 3
          and abs(float(calc_planos.loc["2025-01-01", "taxa_penetracao_pct"]) - 20.0) < 1e-9
          and abs(float(calc_planos.loc["2025-03-01", "taxa_penetracao_pct"]) - 20.0) < 1e-9,
          f"taxas calculadas = {calc_planos['taxa_penetracao_pct'].tolist()}")
    calc_longos = _calcular_penetracao_de_performance_mensal(df_bruto_teste, "longos")
    check("penetracao Excel: 'longos' pega uma linha diferente de 'planos' (nao confunde as duas)",
          abs(float(calc_longos.loc["2025-02-01", "taxa_penetracao_pct"]) - (55.0 / 330.0 * 100)) < 1e-6)
    try:
        _calcular_penetracao_de_performance_mensal(df_bruto_teste, "invalida")
        check("penetracao Excel: categoria invalida e rejeitada", False)
    except ValueError:
        check("penetracao Excel: categoria invalida e rejeitada", True)

    # --- 18. taxa de penetracao: combinacao oficial (PDF) + aproximado (Excel)
    # PDF cobre so o mes mais recente (jul/2026); Excel cobre mai-jul/2026,
    # incluindo o MESMO mes que o PDF - o oficial tem que vencer, nunca ser
    # sobrescrito pelo aproximado.
    idx_hist_penet = pd.date_range("2026-05-01", periods=3, freq="MS")
    df_hist_penet_teste = pd.DataFrame({
        "categoria": ["planos"] * 3,
        "taxa_penetracao_pct": [15.0, 16.0, 16.66],  # jul/2026 aproximado (o valor real via Excel)
        "tipo_dado_penetracao": ["aproximado_consumo_aparente"] * 3,
    }, index=idx_hist_penet)
    df_oficial_penet_teste = pd.DataFrame({
        "categoria": ["planos"],
        "taxa_penetracao_pct": [17.9],  # jul/2026 oficial (o valor real via PDF)
        "tipo_dado_penetracao": ["oficial_mensal"],
    }, index=[pd.Timestamp("2026-07-01")])
    combinado_penet = taxa_penetracao_importacao_planos_mensal(
        df_historico=df_hist_penet_teste, df_oficial=df_oficial_penet_teste)
    check("penetracao combinada: mes coberto pelas duas fontes fica com o valor OFICIAL",
          combinado_penet.loc["2026-07-01", "tipo_dado_penetracao"] == "oficial_mensal"
          and abs(float(combinado_penet.loc["2026-07-01", "taxa_penetracao_pct"]) - 17.9) < 1e-9)
    check("penetracao combinada: meses so no Excel ficam marcados como aproximado",
          combinado_penet.loc["2026-05-01", "tipo_dado_penetracao"] == "aproximado_consumo_aparente"
          and combinado_penet.loc["2026-06-01", "tipo_dado_penetracao"] == "aproximado_consumo_aparente")
    check("penetracao combinada: nao duplica o mes sobreposto (3 meses no total, nao 4)",
          len(combinado_penet) == 3, f"len = {len(combinado_penet)}")

    print("-" * 74)
    if falhas:
        print(f" RESULTADO: {len(falhas)} FALHA(S): {falhas}")
        return 1
    print(" RESULTADO: todos os testes passaram.")
    print("=" * 74)
    return 0


def check_sources() -> int:
    """Testa as APIs publicas e imprime os ultimos valores, para voce conferir
    o rotulo de cada serie antes de publicar qualquer coisa."""
    print("=" * 74)
    print(" CHECAGEM DE FONTES PUBLICAS")
    print("=" * 74)
    ok = True
    for nome, cod in SGS.items():
        try:
            d = _get_json(SGS_ULT.format(cod=cod, n=3))
            vals = ", ".join(f"{x['data']}={x['valor']}" for x in d)
            print(f"  [OK ] SGS {cod:>6}  {nome:<22} {vals}")
        except Exception as e:
            ok = False
            print(f"  [ERRO] SGS {cod:>6}  {nome:<22} {e}")
    ncms_bobina = sorted(sum(NCM_BOBINA_QUENTE.values(), []))
    try:
        df = comex_importacao_ncm(ncms_bobina, 2025, 2025)
        print(f"  [OK ] Comex Stat: {len(df)} linhas para os {len(ncms_bobina)} "
              f"NCMs de bobina a quente em 2025")
        if len(df) and "coNcm" in df.columns:
            contagem = df["coNcm"].value_counts()
            faltando = [n for n in ncms_bobina if n not in contagem.index]
            for n in ncms_bobina:
                print(f"          {n}  {contagem.get(n, 0):>4} linhas"
                      + ("  <- SEM DADO EM 2025, confirme se o codigo existe" if n in faltando else ""))
    except Exception as e:
        ok = False
        print(f"  [ERRO] Comex Stat (NCMs de bobina): {e}")
    try:
        s = ibge_sidra_ipp_metalurgia(periodos="-3")
        vals = ", ".join(f"{d:%Y-%m}={v:.2f}" for d, v in s.items())
        print(f"  [OK ] IBGE/SIDRA IPP metalurgia (tabela 6903): {vals}")
    except Exception as e:
        ok = False
        print(f"  [ERRO] IBGE/SIDRA IPP metalurgia: {e}")
    try:
        dados_penet = acobrasil_taxa_penetracao_pdf_mes_atual()
        linha = dados_penet.loc[dados_penet["categoria"] == "planos"].iloc[0]
        print(f"  [OK ] Aco Brasil - Taxa de Penetracao (PDF, tabela 9.1, Planos): "
              f"{linha['taxa_penetracao_pct']:.1f}% em {dados_penet.index[0]:%m/%Y}")
    except Exception as e:
        ok = False
        print(f"  [ERRO] Aco Brasil - Taxa de Penetracao (PDF): {e}")
    print("-" * 74)
    print("  SCR.data (CNAE): baixe os ZIP mensais em")
    print("     https://dadosabertos.bcb.gov.br/dataset/scr_data")
    print("     Licenca ODbL - atribuicao obrigatoria. Ver o manual antes de redistribuir.")
    print("=" * 74)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Motor de indices setoriais")
    ap.add_argument("--selftest", action="store_true", help="valida a matematica, sem rede")
    ap.add_argument("--check-sources", action="store_true", help="testa as APIs publicas")
    ap.add_argument("--spec", action="store_true", help="imprime a especificacao do ICCS")
    ap.add_argument("--preview-bobina", action="store_true",
                     help="puxa a serie mensal real de preco de importacao (USD/t) dos 13 NCMs de bobina a quente e salva em data/processed/")
    ap.add_argument("--preview-domestico", action="store_true",
                     help="encadeia o preco domestico trimestral (data/curated/) em serie mensal via IPP/IBGE e salva em data/processed/")
    ap.add_argument("--ipia", action="store_true",
                     help="calcula o IPIA completo (custo de importacao + ancora domestica) e salva em data/processed/")
    ap.add_argument("--pdf-ipia", action="store_true",
                     help="calcula o IPIA e gera relatorio PDF de 1 pagina em data/processed/ipia_relatorio.pdf")
    ap.add_argument("--ano-ini", type=int, default=2020)
    ap.add_argument("--ano-fim", type=int, default=2026)
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.check_sources:
        sys.exit(check_sources())
    if a.preview_bobina:
        print(f"Puxando Comex Stat, NCMs de bobina a quente, {a.ano_ini}-{a.ano_fim} ...")
        s = serie_mensal_preco_bobina(a.ano_ini, a.ano_fim)
        if s.empty:
            print("Nenhum dado retornado - confira o periodo ou rode --check-sources primeiro.")
            sys.exit(1)
        print(s.to_string(index=False))
        import os
        os.makedirs("data/processed", exist_ok=True)
        caminho = "data/processed/serie_bobina_quente.csv"
        s.to_csv(caminho, index=False)
        print(f"\nSalvo em {caminho} ({len(s)} meses)")
        sys.exit(0)
    if a.preview_domestico:
        print("Encadeando preco domestico trimestral (data/curated/) via IPP/IBGE ...")
        trimestral = carregar_preco_domestico_trimestral()
        blend = preco_domestico_ponderado(trimestral)
        ipp = ibge_sidra_ipp_metalurgia()
        mensal = encadear_preco_domestico_mensal(blend, ipp)
        print(mensal.to_string())
        import os
        os.makedirs("data/processed", exist_ok=True)
        caminho = "data/processed/serie_domestico_aco.csv"
        mensal.to_csv(caminho)
        print(f"\nSalvo em {caminho} ({len(mensal)} meses)")
        sys.exit(0)
    if a.ipia:
        print(f"Calculando IPIA, {a.ano_ini}-{a.ano_fim} ...")
        out = calcular_ipia_mensal(a.ano_ini, a.ano_fim)
        if out.empty:
            print("Nenhum dado de importacao retornado - confira o periodo ou rode --check-sources primeiro.")
            sys.exit(1)
        print(out.to_string())
        import os
        os.makedirs("data/processed", exist_ok=True)
        caminho = "data/processed/ipia_mensal.csv"
        out.to_csv(caminho)
        print(f"\nSalvo em {caminho} ({len(out)} meses)")
        sys.exit(0)
    if a.pdf_ipia:
        print(f"Calculando IPIA para relatorio PDF, {a.ano_ini}-{a.ano_fim} ...")
        out = calcular_ipia_mensal(a.ano_ini, a.ano_fim)
        if out.empty:
            print("Nenhum dado de importacao retornado - confira o periodo ou rode --check-sources primeiro.")
            sys.exit(1)
        import os
        os.makedirs("data/processed", exist_ok=True)
        caminho = "data/processed/ipia_relatorio.pdf"
        gerar_pdf_ipia(out, caminho, ParamsIPIA())
        print(f"Relatorio salvo em {caminho} ({len(out)} meses na serie)")
        sys.exit(0)
    if a.spec:
        ICCS.validar()
        print(f"\n{ICCS.codigo} - {ICCS.nome}")
        print(f"Janela de referencia congelada: {ICCS.janela_ref[0]} a {ICCS.janela_ref[1]}\n")
        for p in ICCS.pilares:
            print(f"  [{p.peso:>5.0%}] {p.nome.upper()}  - {p.descricao}")
            for v in [v for v in ICCS.variaveis if v.pilar == p.nome]:
                sinal = "+" if v.orientacao > 0 else "-"
                tr = f" ({v.transform})" if v.transform else ""
                print(f"          {v.peso:>5.0%} {sinal} {v.nome}{tr}")
                print(f"                  fonte: {v.fonte}")
            print()
        sys.exit(0)
    ap.print_help()


if __name__ == "__main__":
    main()
