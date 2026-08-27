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
   python indices_setoriais.py --pdf-ipia        # gera relatorio PDF de 4 paginas do IPIA

 Dependencias: pandas, numpy, requests, matplotlib  (statsmodels opcional, p/ ajuste sazonal)
=============================================================================
"""
from __future__ import annotations
import argparse, json, math, re, sys, time, datetime as dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

import numpy as np
import pandas as pd

from steel_indicator.domain.index_engine import (
    JANELA_REF, WINSOR_Z, ESCALA_A, ESCALA_B, COBERTURA_MINIMA,
    Variavel, Pilar, EspecIndice, aplicar_transform, zscore_janela_fixa,
    agregar, validar_com_pca, diagnostico_antecedencia,
)
from steel_indicator.domain.provenance import (
    NIVEL_OBSERVADO, NIVEL_CALCULADO, NIVEL_ESTIMADO, NIVEIS_DADO,
    METODO_FORMULA_ALTERNATIVA, VintageInfo, vintage_table, validar_report_cutoff,
)
from steel_indicator.sources.comex import COMEX_URL, comex_importacao_ncm
from steel_indicator.parameters.trade_policy import (
    resolver_ii, resolver_afrmm, resolver_antidumping, status_efetivo, STATUS_UNKNOWN,
    STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, PUBLICATION_GRADE_INICIO,
)
from steel_indicator.data.contracts import VALIDACAO_DOCUMENTADO, VALIDACAO_VERIFICADO
from steel_indicator.storage import vintage_store

# =============================================================================
# 0. CONFIGURACAO
# =============================================================================

VERSAO_METODOLOGIA = "1.2"  # bump manual quando a metodologia de calculo mudar
# (nao a cada commit) - referenciada em docs/METODOLOGIA.md e no painel
# "Report Information" do relatorio PDF. 1.0 = motor inicial do IPIA;
# 1.1 = suavizacao seletiva (ADR 0005) + taxa de penetracao de importacao
# (ADR 0007); 1.2 = taxonomia OBSERVADO/CALCULADO/ESTIMADO/PROXY (ADR
# 0008) + correcao do spread da decomposicao de custo, que podia misturar
# dois meses diferentes sem avisar (ver docs/adr/0008).

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
# COMEX_URL agora vive em steel_indicator/sources/comex.py (Spec 0003, Stage E1) - importado acima.
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
# Extraido para steel_indicator/domain/index_engine.py (Spec 0003, batch 1):
# Variavel, Pilar, EspecIndice, aplicar_transform, zscore_janela_fixa,
# agregar, validar_com_pca, diagnostico_antecedencia e as constantes
# JANELA_REF/WINSOR_Z/ESCALA_A/ESCALA_B/COBERTURA_MINIMA. Importados acima.

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


def custo_importacao_historico_mensal(preco_fob_usd_t: pd.Series,
                                      frete_usd_t: pd.Series,
                                      seguro_usd_t: pd.Series,
                                      cambio: pd.Series,
                                      ncm: str,
                                      origin: str = "China",
                                      exporter: Optional[str] = None,
                                      p: Optional[ParamsIPIA] = None) -> pd.DataFrame:
    """Mesma formula de `custo_importacao_rs_t`, mas com II/AFRMM/antidumping
    resolvidos MES A MES via steel_indicator.parameters.trade_policy (Stage
    E4/E4b, ADR 0009) em vez dos escalares fixos de ParamsIPIA - a formula
    economica em si (CIF -> base -> total com margem) nao muda.

    Precedencia explicita: `p.aliquota_ii`, `p.afrmm` e `p.antidumping_usd_t`
    sao IGNORADOS aqui (resolvidos por `ncm`/`origin`/`exporter`/mes via
    trade_policy). `p.despesas_porto_rs_t`, `p.frete_interno_rs_t` e
    `p.margem_importador` continuam vindo do parametro escalar - esses tres
    nao foram investigados nesta stage (fora de escopo: docs/adr/0009-*.md).

    Usa sempre `effective_value` do antidumping (nunca `nominal_value`) -
    ver `ResultadoAntidumping`. `nominal_value` fica preservado na coluna
    `antidumping_nominal_usd_t` apenas como provenance/informacao.

    Nunca preenche um mes com status_efetivo() == UNKNOWN com zero ou com o
    parametro atual como fallback: esse mes fica com `ppi_brl_t` (e as
    colunas monetarias que dependem do parametro faltante) como NaN. A
    coluna `status` registra PUBLICATION_GRADE/EXPERIMENTAL/UNKNOWN por mes.

    Nao substitui `custo_importacao_rs_t`/`calcular_ipia_mensal` (legacy,
    ParamsIPIA escalar) - ambos permanecem inalterados e continuam sendo o
    caminho usado por --selftest/CLI/relatorio ate uma decisao explicita de
    migracao.
    """
    if p is None:
        p = ParamsIPIA()
    linhas = []
    for data in preco_fob_usd_t.index:
        r_ii = resolver_ii(ncm, data)
        r_afrmm = resolver_afrmm(data)
        r_ad = resolver_antidumping(origin, data, exporter=exporter)
        status = status_efetivo(r_ii.status, r_afrmm.status, r_ad.status)

        cambio_mes = cambio.loc[data]
        cif_usd = preco_fob_usd_t.loc[data] + frete_usd_t.loc[data] + seguro_usd_t.loc[data]
        cif_brl = cif_usd * cambio_mes

        linha = {
            "data": data, "status": status,
            "aliquota_ii": r_ii.aliquota, "aliquota_afrmm": r_afrmm.aliquota,
            "antidumping_usd_t": r_ad.effective_value, "antidumping_nominal_usd_t": r_ad.nominal_value,
            "cif_usd_t": cif_usd, "cif_brl_t": cif_brl,
        }
        if status == STATUS_UNKNOWN:
            linha.update(ii_brl_t=np.nan, afrmm_brl_t=np.nan, antidumping_brl_t=np.nan, ppi_brl_t=np.nan)
        else:
            ii = cif_brl * r_ii.aliquota
            afrmm = (frete_usd_t.loc[data] * cambio_mes) * r_afrmm.aliquota
            ad_brl = r_ad.effective_value * cambio_mes
            base = cif_brl + ii + afrmm + ad_brl + p.despesas_porto_rs_t + p.frete_interno_rs_t
            total = base * (1 + p.margem_importador)
            linha.update(ii_brl_t=ii, afrmm_brl_t=afrmm, antidumping_brl_t=ad_brl, ppi_brl_t=total)
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("data")


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
# 3c. DOMESTIC PRICE V2 - ancora por soma(receita)/soma(volume) (Stage E8)
# =============================================================================
# Decisao Level 2 seguindo regras ja aprovadas: a ancora entre empresas passa
# a ser soma(receita)/soma(volume) - explicito, nunca media simples entre os
# precos das empresas (embora, nos dados curados de hoje, `preco_domestico_
# ponderado` legado ja produza o MESMO numero: receita_i = preco_i*volume_i
# para toda linha, por construcao de `carregar_preco_domestico_trimestral`,
# entao media-ponderada-por-volume dos precos == soma(receita)/soma(volume).
# A diferenca real do V2 nao esta nesse numero, e sim em (a) rejeitar
# explicitamente uma empresa cuja receita/volume seja economicamente
# incompativel, em vez de so poder incluir ou excluir a linha inteira do
# CSV, e (b) usar um IPP mais especifico para o encadeamento mensal - ver
# `ibge_sidra_ipp_siderurgia` na secao 4 e `preco_domestico_hrc_mensal_v2`
# na secao 3d. `carregar_preco_domestico_trimestral`/`preco_domestico_
# ponderado` (legado) permanecem inalterados.

TIPO_INCOMPATIVEL_DOMESTICO = "incompativel_receita_volume"
# Curador declara esse tipo quando receita e volume da linha NAO se referem
# ao mesmo universo economico (ex.: receita da companhia inteira sobre
# volume so de HRC) - mesmo padrao ja usado por "misto": um valor que o
# curador atribui deliberadamente ao ler a fonte, nao algo que o codigo
# infere sozinho a partir dos numeros. Nenhuma linha real do CSV curado usa
# esse tipo hoje (Usiminas/CSN sao compativeis - receita e volume do mesmo
# segmento "Siderurgia", mercado interno, nos dois lados).
TIPOS_DADO_DOMESTICO_V2 = TIPOS_DADO_DOMESTICO | {TIPO_INCOMPATIVEL_DOMESTICO}


def carregar_preco_domestico_trimestral_v2(caminho_csv: str = CAMINHO_PRECO_DOMESTICO_CSV) -> pd.DataFrame:
    """Mesma leitura de `carregar_preco_domestico_trimestral` (legado,
    inalterado), com duas adicoes exigidas pelo Domestic Price V2:

      - `receita_efetiva_rs`: receita_liquida_segmento_rs quando informada
        na fonte, senao reconstruida como preco_rs_t * volume_vendas_t
        (caso da CSN, que publica "Preco Medio" pronto em vez de receita) -
        e o numerador que `ancora_domestica_ponderada_v2` soma entre
        empresas;
      - `qualificado`: False quando `tipo == TIPO_INCOMPATIVEL_DOMESTICO` -
        a linha e EXCLUIDA da agregacao por `ancora_domestica_ponderada_v2`,
        nunca misturada silenciosamente.

    Nao reescreve nem reutiliza a validacao de `carregar_preco_domestico_
    trimestral` porque o conjunto de tipos aceitos e maior aqui
    (`TIPOS_DADO_DOMESTICO_V2`) - duplicar essas ~10 linhas de leitura evita
    acoplar o legado a um vocabulario que so o V2 usa.
    """
    df = pd.read_csv(caminho_csv)
    obrigatorias = {"trimestre", "empresa", "volume_vendas_t", "tipo", "fonte"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ValueError(f"CSV de preco domestico sem colunas obrigatorias: {faltando}")
    tipos_invalidos = set(df["tipo"]) - TIPOS_DADO_DOMESTICO_V2
    if tipos_invalidos:
        raise ValueError(f"tipo de dado desconhecido no CSV: {tipos_invalidos}")
    if "preco_rs_t" not in df.columns:
        df["preco_rs_t"] = np.nan
    if "receita_liquida_segmento_rs" not in df.columns:
        df["receita_liquida_segmento_rs"] = np.nan
    precisa_calcular_preco = df["preco_rs_t"].isna()
    df.loc[precisa_calcular_preco, "preco_rs_t"] = (
        df.loc[precisa_calcular_preco, "receita_liquida_segmento_rs"]
        / df.loc[precisa_calcular_preco, "volume_vendas_t"]
    )
    df["receita_efetiva_rs"] = df["receita_liquida_segmento_rs"].where(
        df["receita_liquida_segmento_rs"].notna(), df["preco_rs_t"] * df["volume_vendas_t"])
    df["qualificado"] = df["tipo"] != TIPO_INCOMPATIVEL_DOMESTICO
    return df


def ancora_domestica_ponderada_v2(df: pd.DataFrame) -> pd.DataFrame:
    """Ancora domestica por trimestre: soma(receita_efetiva)/soma(volume)
    entre empresas QUALIFICADAS - nunca media simples entre os precos das
    empresas. Empresas com `qualificado=False` (receita/volume de universos
    economicos incompativeis - ex.: uma Gerdau cujo unico dado publico
    fosse aco longo, nao bobina a quente) sao excluidas explicitamente da
    soma; a exclusao fica registrada no proprio `tipo` da linha de origem
    (CSV curado), nunca redistribuida em silencio para as demais.

    Trimestre em que NENHUMA empresa e qualificada fica de fora do
    resultado - nao vira um ponto de peso zero fingindo ser ancora
    confirmada. `encadear_preco_domestico_mensal` (legado, reaproveitado
    sem alteracao por `preco_domestico_hrc_mensal_v2`) ja trata trimestre
    ausente corretamente: carrega o ultimo trimestre confirmado adiante via
    IPP em vez de fabricar um novo nivel para o trimestre faltante.
    """
    linhas = []
    for trimestre, g in df.groupby("trimestre", sort=True):
        qualificadas = g[g["qualificado"]]
        if qualificadas.empty:
            continue
        receita_total = float(qualificadas["receita_efetiva_rs"].sum())
        volume_total = float(qualificadas["volume_vendas_t"].sum())
        tipo = qualificadas["tipo"].iloc[0] if qualificadas["tipo"].nunique() == 1 else "misto"
        linhas.append({
            "trimestre": trimestre,
            "preco_rs_t": receita_total / volume_total,
            "receita_total_rs": receita_total,
            "volume_total_t": volume_total,
            "tipo": tipo,
            "companies_used": ",".join(sorted(qualificadas["empresa"].unique())),
            "quantidade_empresas": int(qualificadas["empresa"].nunique()),
        })
    return pd.DataFrame(linhas)

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


# _post_json (helper de POST usado so pelo Comex Stat) e comex_importacao_ncm
# agora vivem em steel_indicator/sources/comex.py (Spec 0003, Stage E1) -
# comex_importacao_ncm importado acima; _post_json e privado ao adapter e
# nao e usado por mais nenhum codigo deste modulo.


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


IBGE_SIDRA_IPP_SIDERURGIA_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/6723/periodos/{periodos}/variaveis/10008"
# Tabela SIDRA 6723 ("por tipo de indice e grupos industriais selecionados"),
# variavel 10008 (numero-indice, dez/2018=100), classificacao 844[47259] =
# grupo industrial "242 SIDERURGIA". CONFIRMADA AO VIVO nesta sessao via
# .../agregados/6723/metadados: mais especifica que a tabela 6903/"24
# METALURGIA" (ibge_sidra_ipp_metalurgia, classificacao 842[46641]) porque
# exclui metalurgia de metais nao-ferrosos, ferroligas e fundicao - e a
# UNICA classificacao IPP do SIDRA (nenhuma tabela ativa quebra por CNAE de
# 4+ digitos ou por produto) mais especifica que "24 Metalurgia" disponivel
# hoje. Ainda assim e um agregado de TODA a industria siderurgica brasileira
# (nao ha bobina a quente isolada em nenhuma tabela IPP do SIDRA) - por isso
# permanece PROXY explicito no Domestic Price V2 (ver
# `preco_domestico_hrc_mensal_v2` e docs/METODOLOGIA.md).
IBGE_IPP_CLASSIFICACAO_SIDERURGIA = "844[47259]"


def ibge_sidra_ipp_siderurgia(periodos: str = "all") -> pd.Series:
    """IPP mensal do IBGE/SIDRA, grupo industrial 242 - Siderurgia (numero-
    indice, dez/2018=100) - usado para encadear a ancora trimestral do
    Domestic Price V2 (`preco_domestico_hrc_mensal_v2`). Mais especifico que
    `ibge_sidra_ipp_metalurgia` (CNAE 24, usado pelo legado), mas ainda um
    agregado de toda a siderurgia - ver nota acima.
    """
    url = IBGE_SIDRA_IPP_SIDERURGIA_URL.format(periodos=periodos)
    dados = _get_json(url, {"localidades": "N1[all]", "classificacao": IBGE_IPP_CLASSIFICACAO_SIDERURGIA})
    serie = dados[0]["resultados"][0]["series"][0]["serie"]
    s = pd.to_numeric(pd.Series(serie), errors="coerce")
    s.index = pd.to_datetime(s.index, format="%Y%m")
    return s.rename("ipp_siderurgia").sort_index()


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


# comex_importacao_ncm agora vive em steel_indicator/sources/comex.py (Spec
# 0003, Stage E1) - importado acima. _comex_bobina_bruto permanece AQUI de
# proposito: ele decide a cesta HRC (NCM_BOBINA_QUENTE), o que e premissa
# metodologica do IPIA-HRC V1, nao contrato generico do adapter Comex (ver
# docs/specs/0003-modularize-engine.md Stage E1). O nome `comex_importacao_ncm`
# e resolvido pelo namespace deste modulo em tempo de chamada (late binding),
# o que preserva o mecanismo de bloqueio de rede usado por selftest() e por
# tests/characterization/test_data_integration_current.py (reatribuir
# `indices_setoriais.comex_importacao_ncm` continua interceptando esta
# chamada - ver tests/characterization/test_comex_current.py).

def _comex_bobina_bruto(ano_ini: int, ano_fim: int) -> pd.DataFrame:
    """Busca o dado bruto de importacao (Comex Stat) dos 13 NCMs de bobina
    a quente - extraido de `serie_mensal_preco_bobina` para poder ser
    reaproveitado por outras agregacoes (ex.: `origem_importacao_bobina_por_pais`)
    sem fazer uma segunda chamada de rede para o mesmo dado.
    """
    ncms = sorted(sum(NCM_BOBINA_QUENTE.values(), []))
    return comex_importacao_ncm(ncms, ano_ini, ano_fim)


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


def serie_mensal_preco_bobina(ano_ini: int = 2020, ano_fim: int = 2026,
                              df_bruto: pd.DataFrame | None = None) -> pd.DataFrame:
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

    df_bruto aceita o dado ja buscado por `_comex_bobina_bruto` (evita nova
    chamada de rede quando outra agregacao - ex. por pais de origem -
    precisa do mesmo dado bruto) - se None, busca ao vivo.
    """
    df = df_bruto if df_bruto is not None else _comex_bobina_bruto(ano_ini, ano_fim)
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


def origem_importacao_bobina_por_pais(ano_ini: int = 2020, ano_fim: int = 2026,
                                       df_bruto: pd.DataFrame | None = None,
                                       ultimos_n_meses: int = 3) -> pd.DataFrame:
    """Top paises de origem da importacao de bobina a quente, como % do
    volume (KG) total, nos ultimos `ultimos_n_meses` meses com dado
    disponivel no Comex Stat.

    Reaproveita o campo `country` que a resposta do Comex Stat ja traz
    (confirmado ao vivo: nome do pais em texto, ex. "Coreia do Sul",
    "Egito" - nao um codigo) mas que `serie_mensal_preco_bobina` descarta
    na agregacao por mes. df_bruto aceita o mesmo dado ja buscado por
    `_comex_bobina_bruto`/`serie_mensal_preco_bobina` - se None, busca
    ao vivo (nunca duas chamadas de rede para o mesmo dado dentro do
    relatorio).
    """
    df = df_bruto if df_bruto is not None else _comex_bobina_bruto(ano_ini, ano_fim)
    if df.empty:
        return df
    df = df.copy()
    df["metricKG"] = pd.to_numeric(df["metricKG"], errors="coerce")
    df["data"] = pd.to_datetime(df["year"].astype(str) + "-"
                                + df["monthNumber"].astype(str).str.zfill(2) + "-01")
    meses_recentes = sorted(df["data"].unique())[-ultimos_n_meses:]
    recorte = df[df["data"].isin(meses_recentes)]
    por_pais = recorte.groupby("country")["metricKG"].sum().sort_values(ascending=False)
    total = por_pais.sum()
    out = pd.DataFrame({
        "toneladas": por_pais / 1000,
        "pct_do_volume": (por_pais / total * 100.0) if total > 0 else 0.0,
    })
    out.attrs["mes_inicio"] = min(meses_recentes) if len(meses_recentes) else None
    out.attrs["mes_fim"] = max(meses_recentes) if len(meses_recentes) else None
    return out


def calcular_ipia_mensal(ano_ini: int = 2020, ano_fim: int = 2026,
                         df_bruto: pd.DataFrame | None = None) -> pd.DataFrame:
    """Calcula o IPIA mensal completo: custo de importacao real (Comex Stat +
    cambio BCB) contra a ancora de preco domestico (CSV curado + IPP).

    Mesmo calculo usado pelo branch `--ipia` da CLI e pelo relatorio PDF
    (`src/reporting/`) - centralizado aqui para as duas saidas nunca
    divergirem. Retorna as colunas: ipia, preco_domestico_rs_t, ppi_rs_t,
    tipo_dado_domestico, metodo_domestico, peso_confiabilidade_importacao.

    df_bruto aceita o dado bruto do Comex Stat ja buscado (mesmo padrao de
    `custo_importacao_detalhado_mensal`/`origem_importacao_bobina_por_pais`)
    - se None, busca ao vivo. Sem isso, o relatorio PDF fazia DUAS chamadas
    de rede para o mesmo dado (uma aqui, outra em `_comex_bobina_bruto`
    chamado por report_builder para custo/origem) - quebrava a garantia que
    o proprio projeto documenta ("nunca duas chamadas de rede para o mesmo
    dado dentro do relatorio").
    """
    bobina = serie_mensal_preco_bobina(ano_ini, ano_fim, df_bruto=df_bruto)
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


def calcular_ipia_hrc_v2(ncm: str, ano_ini: int = 2020, ano_fim: int = 2026,
                         df_bruto: pd.DataFrame | None = None,
                         domestico_df: pd.DataFrame | None = None,
                         origin: str = "China", exporter: Optional[str] = None) -> pd.DataFrame:
    """Caminho V2 EXPLICITO do IPIA-HRC (Stage E5/E6, ADR 0009): mesma fonte
    de bobina (Comex) e de preco domestico do legado
    (`calcular_ipia_mensal`), mas o custo de importacao vem de
    `custo_importacao_historico_mensal()` - II/AFRMM/antidumping resolvidos
    MES A MES via steel_indicator.parameters.trade_policy, em vez do
    ParamsIPIA escalar fixo.

    NAO substitui `calcular_ipia_mensal` - os dois coexistem. O legado
    continua sendo o caminho usado por --selftest/CLI/relatorio ate uma
    decisao explicita de migracao. `ParamsIPIA.aliquota_ii`,
    `.afrmm` e `.antidumping_usd_t` nunca sao lidos aqui (mesma precedencia
    ja documentada em `custo_importacao_historico_mensal`).

    LIMITACAO CONHECIDA, NAO DECIDIDA NESTE BATCH (agregacao entre NCMs) -
    ver docs/METODOLOGIA.md secao 26 (IPIA-HRC) e docs/adr/0009-*.md:
    `serie_mensal_preco_bobina` ja soma FOB/frete/seguro dos 13 NCMs de
    `NCM_BOBINA_QUENTE` num unico CIF combinado - exatamente como o legado
    ja faz. O parametro `ncm` aqui escolhe apenas QUAL aliquota historica
    (II/AFRMM/antidumping) e aplicada a esse CIF ja combinado, SEM nenhuma
    ponderacao por volume nem verificacao de quanto esse codigo realmente
    representa da cesta naquele mes. Isto NAO e equivalente, em magnitude,
    a simplificacao que o legado ja faz: no regime 2022-04+, a constante
    `ParamsIPIA().aliquota_ii=0.108` e uma boa aproximacao porque 12 dos 13
    NCMs de fato convergem para 10,8% (so 72083910 diverge, para 9%) - erro
    pequeno e conhecido. No periodo `historical experimental`
    (2012-2022-03), os 9 NCMs nao confirmados individualmente tem alíquota
    real desconhecida dentro de uma faixa de 10%-14% (nao so 10-12%) - ou
    seja, escolher `ncm="72083700"` (12%) para representar a cesta inteira
    nesse periodo carrega um erro potencial (ate a ponta superior da faixa,
    14%) que nao tem o mesmo tipo de garantia documental que sustenta a
    aproximacao da constante legada no regime atual (2022-04+). O ADR 0009 ja
    quantifica que uma diferenca de ~4pp de II desloca o IPIA calculado em
    ~3,5-4%. Uma agregacao ponderada por NCM/volume exigiria decisao
    metodologica propria (Level 3) e NAO foi inventada aqui. Por isso,
    `calcular_ipia_hrc_v2` NAO deve ser conectado a --selftest/CLI/relatorio
    (nem tratado como substituto do legado) ate essa questao de
    representatividade ser resolvida ou explicitamente aceita como premissa
    documentada - permanece uma peca de calculo interna/testada, nao um
    caminho de publicacao.

    Preco domestico: mesma logica do legado
    (`carregar_preco_domestico_trimestral` -> `preco_domestico_ponderado`
    -> `encadear_preco_domestico_mensal`), sem alteracao - Domestic Price V2
    e proxima stage. `domestico_df` aceita o resultado ja pronto de
    `encadear_preco_domestico_mensal` (mesmo padrao de teste que `df_bruto`
    ja usa em `calcular_ipia_mensal`) - se None, usa a fonte real (CSV
    curado + IPP, sem rede para o CSV).

    Formula do IPIA preservada, sem alteracao: IPIA = preco_domestico / ppi * 100.
    Indice = reference_period (mes), mesma convencao das demais funcoes deste modulo.

    `publication_status` reflete SOMENTE os parametros de politica comercial
    resolvidos por trade_policy (PUBLICATION_GRADE/EXPERIMENTAL/UNKNOWN) -
    NAO incorpora a taxonomia de proveniencia do preco domestico
    (OBSERVADO/CALCULADO/ESTIMADO + PROXY, ja existente em
    `classificar_preco_domestico`/`VintageInfo`) - unificar as duas
    taxonomias e decisao fora de escopo deste batch. Meses com
    `publication_status == UNKNOWN` tem `ppi_rs_t`/`ipia` como NaN - nunca
    zero, nunca usando a aliquota atual como substituto.
    """
    ncms_hrc = sum(NCM_BOBINA_QUENTE.values(), [])
    if ncm not in ncms_hrc:
        raise ValueError(f"ncm {ncm!r} nao pertence a NCM_BOBINA_QUENTE: {sorted(ncms_hrc)}")

    bobina = serie_mensal_preco_bobina(ano_ini, ano_fim, df_bruto=df_bruto)
    if bobina.empty:
        return bobina
    bobina = bobina.set_index("data")
    cambio = sgs(SGS["cambio_venda"], inicio=f"01/01/{ano_ini}").reindex(bobina.index, method="ffill")
    custo = custo_importacao_historico_mensal(
        bobina["preco_usd_t_publicado"], bobina["frete_usd_t"], bobina["seguro_usd_t"],
        cambio, ncm=ncm, origin=origin, exporter=exporter)

    if domestico_df is not None:
        domestico = domestico_df
    else:
        trimestral = carregar_preco_domestico_trimestral()
        blend = preco_domestico_ponderado(trimestral)
        ipp = ibge_sidra_ipp_metalurgia()
        domestico = encadear_preco_domestico_mensal(blend, ipp)

    idx = bobina.index.intersection(domestico.index)
    preco_dom = domestico.loc[idx, "preco_rs_t"]
    ppi = custo.loc[idx, "ppi_brl_t"]
    return pd.DataFrame({
        "preco_domestico_rs_t": preco_dom,
        "ppi_rs_t": ppi,
        "ipia": ipia(preco_dom, ppi),
        "publication_status": custo.loc[idx, "status"],
        "aliquota_ii": custo.loc[idx, "aliquota_ii"],
        "aliquota_afrmm": custo.loc[idx, "aliquota_afrmm"],
        "antidumping_usd_t": custo.loc[idx, "antidumping_usd_t"],
        "ii_brl_t": custo.loc[idx, "ii_brl_t"],
        "afrmm_brl_t": custo.loc[idx, "afrmm_brl_t"],
        "antidumping_brl_t": custo.loc[idx, "antidumping_brl_t"],
        "tipo_dado_domestico": domestico.loc[idx, "tipo_dado"],
        "metodo_domestico": domestico.loc[idx, "metodo"],
    })


# =============================================================================
# 3c. IPIA-HRC V2 - agregador bottom-up multi-NCM (Stage E7, ADR 0009)
# =============================================================================
# `calcular_ipia_hrc_v2` (acima) aplica a aliquota de UM NCM escolhido pelo
# chamador ao CIF ja combinado dos 13 NCMs - e a limitacao de representati-
# vidade documentada no adendo Stage E6 do ADR 0009. As funcoes abaixo
# implementam a decisao Level 3 aprovada para resolver isso: resolve
# II (por NCM)/AFRMM (por mes)/antidumping (por pais) ANTES de agregar,
# por (mes, ncm, pais) - nunca "NCM representativo", nunca media simples,
# nunca uma unica aliquota aplicada ao CIF ja combinado.

# ADR 0009: unico intervalo documentado (Nota Tecnica 1/2018) para os 9 NCMs
# de NCM_BOBINA_QUENTE sem II individual comprovado entre 2012-01 e 2022-03 -
# nunca um ponto central (12%) tratado como valor conhecido.
FAIXA_II_NAO_CONFIRMADO_HISTORICO = (0.10, 0.14)
LIMIAR_COBERTURA_EXPERIMENTAL = 0.60      # decisao Level 3 aprovada
LIMIAR_INCERTEZA_EXPERIMENTAL_PCT = 0.02  # decisao Level 3 aprovada
TOL_COBERTURA_PUBLICATION_GRADE = 1e-6    # tolerancia numerica para "100% do kg observado com politica conhecida"


def _ppi_brl_t(cif_brl_t, aliquota_ii, frete_usd_t, cambio_mes, aliquota_afrmm, antidumping_usd_t, p: ParamsIPIA):
    """Mesma formula de custo de internacao de `custo_importacao_rs_t`/
    `custo_importacao_historico_mensal` (CIF -> base -> total com margem),
    fatorada para aceitar uma aliquota_ii hipotetica - usada tambem pela
    faixa de incerteza (ppi_lower/ppi_upper) do periodo experimental."""
    ii = cif_brl_t * aliquota_ii
    afrmm = (frete_usd_t * cambio_mes) * aliquota_afrmm
    ad_brl = antidumping_usd_t * cambio_mes
    base = cif_brl_t + ii + afrmm + ad_brl + p.despesas_porto_rs_t + p.frete_interno_rs_t
    return base * (1 + p.margem_importador)


def custo_importacao_bottom_up_mensal(df_bruto: pd.DataFrame, cambio: pd.Series,
                                       p: Optional[ParamsIPIA] = None,
                                       exporter: Optional[str] = None) -> pd.DataFrame:
    """Uma linha por (mes, ncm, pais) com custo de internacao unitario (R$/t)
    e status, resolvendo II/AFRMM/antidumping via trade_policy ANTES de
    qualquer soma entre NCMs ou paises (ADR 0009, decisao Level 3 do
    agregador bottom-up). `df_bruto` e o dado cru do Comex Stat (mesmo
    formato de `_comex_bobina_bruto`: colunas year/monthNumber/coNcm/ncm/
    country/metricFOB/metricKG/metricFreight/metricInsurance) - `coNcm`/
    `country` sao preservados aqui, ao contrario de
    `serie_mensal_preco_bobina`, que os descarta na agregacao mensal.

    IMPORTANTE: o campo do CODIGO do NCM na resposta real da Comex Stat e
    `coNcm` (ex.: "72083700") - `ncm` e a DESCRICAO textual do produto
    (ex.: "Produtos laminados planos..."), nunca o codigo. Resolver
    II/AFRMM/antidumping contra `ncm` (a descricao) nunca bate com nenhuma
    entrada de `trade_policy.py` e faz TODO grupo virar UNKNOWN em
    silencio - bug real encontrado na primeira geracao end-to-end (Stage
    E9) com dado real do Comex Stat; os testes desta funcao usavam uma
    fixture sintetica que colocava o codigo direto em `ncm` (nunca testou
    contra o schema real de 2 campos). Corrigido para usar `coNcm`.

    Grupos com kg<=0 ou cujo mes nao tem cambio disponivel em `cambio` sao
    descartados (peso zero ou dado faltante nunca e fabricado).
    """
    if p is None:
        p = ParamsIPIA()
    df = df_bruto.copy()
    for col in ("metricFOB", "metricKG", "metricFreight", "metricInsurance"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["data"] = pd.to_datetime(df["year"].astype(str) + "-"
                                 + df["monthNumber"].astype(str).str.zfill(2) + "-01")
    g = (df.groupby(["data", "coNcm", "country"], as_index=False)
           .agg(fob_usd=("metricFOB", "sum"), kg=("metricKG", "sum"),
                frete_usd=("metricFreight", "sum"), seguro_usd=("metricInsurance", "sum")))
    g = g[(g["kg"] > 0) & g["data"].isin(cambio.index)].reset_index(drop=True)
    if g.empty:
        return g

    g["cambio_mes"] = cambio.reindex(g["data"]).to_numpy()
    g["frete_usd_t"] = 1000 * g["frete_usd"] / g["kg"]
    g["cif_usd_t"] = 1000 * (g["fob_usd"] + g["frete_usd"] + g["seguro_usd"]) / g["kg"]
    g["cif_brl_t"] = g["cif_usd_t"] * g["cambio_mes"]

    res_ii = [resolver_ii(r.coNcm, r.data) for r in g.itertuples()]
    res_afrmm = [resolver_afrmm(r.data) for r in g.itertuples()]
    res_ad = [resolver_antidumping(r.country, r.data, exporter=exporter) for r in g.itertuples()]
    g["aliquota_ii"] = [r.aliquota for r in res_ii]
    g["aliquota_afrmm"] = [r.aliquota for r in res_afrmm]
    g["antidumping_usd_t"] = [r.effective_value for r in res_ad]
    g["status"] = [status_efetivo(a.status, b.status, c.status)
                   for a, b, c in zip(res_ii, res_afrmm, res_ad)]

    conhecido = g["status"] != STATUS_UNKNOWN
    g["ppi_brl_t"] = np.nan
    if conhecido.any():
        # guarda necessaria: quando NENHUM grupo do df de entrada e
        # conhecido (ex.: um mes real onde todos os NCMs importados caem
        # em cota/II nao confirmado), g.loc[conhecido, ...] fica vazio e
        # `_ppi_brl_t` devolve um array vazio de dtype object - atribuir
        # isso a uma coluna float64 levanta LossySetitemError nesta versao
        # do pandas. O resultado correto (nenhuma linha calculada, todas
        # ja NaN pela linha acima) e o mesmo com ou sem a guarda - ela so
        # evita o crash quando nao ha nada a atribuir.
        g.loc[conhecido, "ppi_brl_t"] = _ppi_brl_t(
            g.loc[conhecido, "cif_brl_t"], g.loc[conhecido, "aliquota_ii"],
            g.loc[conhecido, "frete_usd_t"], g.loc[conhecido, "cambio_mes"],
            g.loc[conhecido, "aliquota_afrmm"], g.loc[conhecido, "antidumping_usd_t"], p)
    return g


def agregar_ipia_hrc_multi_ncm_mensal(ano_ini: int = 2020, ano_fim: int = 2026,
                                       df_bruto: pd.DataFrame | None = None,
                                       domestico_df: pd.DataFrame | None = None,
                                       p: Optional[ParamsIPIA] = None,
                                       exporter: Optional[str] = None) -> pd.DataFrame:
    """IPIA-HRC V2 bottom-up multi-NCM (Stage E7, ADR 0009): agrega os 13
    NCMs de NCM_BOBINA_QUENTE por (mes, ncm, pais) - II por NCM, AFRMM por
    mes, antidumping por pais, todos resolvidos ANTES de agregar - e so
    entao pondera o PPI resultante por KG. Nao substitui `calcular_ipia_mensal`
    (legado) nem `calcular_ipia_hrc_v2` (NCM unico) - os tres coexistem;
    nenhum e alterado por este batch. Como os demais caminhos V2, NAO e
    conectado a --selftest/CLI/relatorio.

    Duas politicas de publicacao (decisao Level 3 aprovada, ADR 0009):
      - PUBLICATION_GRADE (>= 2022-04-01): so calcula se
        known_policy_kg == total_kg do mes (tolerancia
        TOL_COBERTURA_PUBLICATION_GRADE) - QUALQUER kg observado com
        politica desconhecida (ex.: cota GECEX 929/2026 com consumo nao
        rastreado) torna o mes inteiro UNKNOWN, SEM redistribuir peso.
      - EXPERIMENTAL (2012-01-01 a 2022-03-31): calculavel so se
        coverage >= LIMIAR_COBERTURA_EXPERIMENTAL (60%) E o range de
        incerteza do II nao confirmado (aplicando a faixa documentada
        FAIXA_II_NAO_CONFIRMADO_HISTORICO so a PARTE desconhecida do
        volume) for <= LIMIAR_INCERTEZA_EXPERIMENTAL_PCT (2%). Quando
        calculavel, o ponto estimado usa SO os grupos conhecidos, com
        peso redistribuido proporcionalmente entre eles - a faixa
        10%-14% nunca vira o valor do ponto central.

    Datas fora de 2012-01-01 em diante ja voltam UNKNOWN diretamente de
    `resolver_ii` (sem entrada nas tabelas de trade_policy) - nao ha ramo
    especial de "fora de escopo" aqui.

    Saida (uma linha por mes calculavel, `reference_period` = inicio do
    mes): reference_period, preco_domestico_rs_t, ppi_rs_t, ipia,
    publication_status, total_kg, known_policy_kg, unknown_policy_kg,
    policy_coverage, ppi_lower, ppi_upper, ppi_uncertainty_range_pct.
    Meses UNKNOWN mantem ppi_rs_t/ipia como NaN - nunca zero, nunca a
    aliquota atual como substituto. `preco_domestico_rs_t` continua
    publicado mesmo em meses UNKNOWN (nao depende do lado de importacao).
    """
    if p is None:
        p = ParamsIPIA()
    df = df_bruto if df_bruto is not None else _comex_bobina_bruto(ano_ini, ano_fim)
    if df.empty:
        return df
    datas = pd.to_datetime(df["year"].astype(str) + "-"
                            + df["monthNumber"].astype(str).str.zfill(2) + "-01")
    idx_mensal = pd.date_range(datas.min(), datas.max(), freq="MS")
    cambio = sgs(SGS["cambio_venda"], inicio=f"01/01/{ano_ini}").reindex(idx_mensal, method="ffill")

    grupos = custo_importacao_bottom_up_mensal(df, cambio, p=p, exporter=exporter)
    if grupos.empty:
        return grupos

    linhas = []
    for data, g in grupos.groupby("data"):
        total_kg = g["kg"].sum()
        known_kg = g.loc[g["status"] != STATUS_UNKNOWN, "kg"].sum()
        unknown_kg = total_kg - known_kg
        coverage = known_kg / total_kg

        linha = {"data": data, "total_kg": total_kg, "known_policy_kg": known_kg,
                 "unknown_policy_kg": unknown_kg, "policy_coverage": coverage,
                 "ppi_lower": np.nan, "ppi_upper": np.nan, "ppi_uncertainty_range_pct": np.nan,
                 "ppi_rs_t": np.nan, "publication_status": STATUS_UNKNOWN}

        if data >= PUBLICATION_GRADE_INICIO:
            if total_kg - known_kg <= TOL_COBERTURA_PUBLICATION_GRADE * total_kg:
                ppi = float(np.average(g["ppi_brl_t"], weights=g["kg"]))
                linha.update(ppi_rs_t=ppi, ppi_lower=ppi, ppi_upper=ppi,
                             ppi_uncertainty_range_pct=0.0, publication_status=STATUS_PUBLICATION_GRADE)
            # senao: fica UNKNOWN/NaN acima - nunca redistribui peso no regime publication-grade
        elif coverage >= LIMIAR_COBERTURA_EXPERIMENTAL:
            conhecidos = g[g["status"] != STATUS_UNKNOWN]
            ponto_estimado = float(np.average(conhecidos["ppi_brl_t"], weights=conhecidos["kg"]))
            if unknown_kg > 0:
                desconhecidos = g[g["status"] == STATUS_UNKNOWN]
                lo, up = FAIXA_II_NAO_CONFIRMADO_HISTORICO
                ppi_lower_desc = _ppi_brl_t(desconhecidos["cif_brl_t"], lo, desconhecidos["frete_usd_t"],
                                             desconhecidos["cambio_mes"], desconhecidos["aliquota_afrmm"],
                                             desconhecidos["antidumping_usd_t"], p)
                ppi_upper_desc = _ppi_brl_t(desconhecidos["cif_brl_t"], up, desconhecidos["frete_usd_t"],
                                             desconhecidos["cambio_mes"], desconhecidos["aliquota_afrmm"],
                                             desconhecidos["antidumping_usd_t"], p)
                soma_conhecido = (conhecidos["ppi_brl_t"] * conhecidos["kg"]).sum()
                ppi_lower = (soma_conhecido + (ppi_lower_desc * desconhecidos["kg"]).sum()) / total_kg
                ppi_upper = (soma_conhecido + (ppi_upper_desc * desconhecidos["kg"]).sum()) / total_kg
                range_pct = (ppi_upper - ppi_lower) / ppi_lower if ppi_lower else np.nan
            else:
                ppi_lower = ppi_upper = ponto_estimado
                range_pct = 0.0

            linha.update(ppi_lower=ppi_lower, ppi_upper=ppi_upper, ppi_uncertainty_range_pct=range_pct)
            if range_pct <= LIMIAR_INCERTEZA_EXPERIMENTAL_PCT:
                linha.update(ppi_rs_t=ponto_estimado, publication_status=STATUS_EXPERIMENTAL)
            # senao: fica UNKNOWN/NaN acima (ppi_lower/upper/range_pct ficam preservados p/ auditoria)
        # coverage < LIMIAR_COBERTURA_EXPERIMENTAL: fica UNKNOWN/NaN acima

        linhas.append(linha)

    mensal = pd.DataFrame(linhas).set_index("data").sort_index()

    if domestico_df is not None:
        domestico = domestico_df
    else:
        trimestral = carregar_preco_domestico_trimestral()
        blend = preco_domestico_ponderado(trimestral)
        ipp = ibge_sidra_ipp_metalurgia()
        domestico = encadear_preco_domestico_mensal(blend, ipp)

    idx = mensal.index.intersection(domestico.index)
    out = mensal.loc[idx].copy()
    out["preco_domestico_rs_t"] = domestico.loc[idx, "preco_rs_t"]
    out["ipia"] = ipia(out["preco_domestico_rs_t"], out["ppi_rs_t"])
    out.index.name = "reference_period"  # Index.intersection() descarta o nome
        # do indice quando o outro lado (domestico_df) nao tem indice nomeado -
        # sem isso, reset_index() abaixo criaria uma coluna "index", nao
        # "reference_period".
    out = out.reset_index()
    cols = ["reference_period", "preco_domestico_rs_t", "ppi_rs_t", "ipia", "publication_status",
            "total_kg", "known_policy_kg", "unknown_policy_kg", "policy_coverage",
            "ppi_lower", "ppi_upper", "ppi_uncertainty_range_pct"]
    return out[cols]


# =============================================================================
# 3d. Domestic Price V2 - orquestrador mensal (Stage E8)
# =============================================================================

IPP_SIDERURGIA_SERIES_ID = "ibge_sidra_6723_844_47259_siderurgia"

_VALIDACAO_ANCORA_CSV_CURADO = VALIDACAO_DOCUMENTADO
# O CSV curado (data/curated/preco_domestico_aco.csv) e lido e conferido por
# citacao de pagina do release oficial (curadoria manual - ver comentario no
# topo da secao "3b. ANCORA DE PRECO DOMESTICO"): confirmado em documentacao
# oficial, mas nao executado como coletor automatizado contra uma fonte ao
# vivo. Corresponde a DOCUMENTADO (docs/METODOLOGIA.md secao 5.2), nao
# VERIFICADO (reservado para fontes executadas programaticamente, como
# `ibge_sidra_ipp_siderurgia`). Uma unica constante e suficiente hoje porque
# todas as linhas do CSV curado compartilham a mesma base de evidencia -
# quando isso deixar de ser verdade, o status passa a ser por linha, nao
# global.


def preco_domestico_hrc_mensal_v2(caminho_csv: str = CAMINHO_PRECO_DOMESTICO_CSV,
                                   df_trimestral: pd.DataFrame | None = None,
                                   ipp_mensal: pd.Series | None = None) -> pd.DataFrame:
    """Domestic Price V2 do IPIA-HRC (Stage E8, decisao Level 2 seguindo
    regras de metodologia ja aprovadas): ancora trimestral por
    soma(receita)/soma(volume) entre empresas qualificadas (nunca media
    simples entre precos - ver `ancora_domestica_ponderada_v2`), encadeada
    mes a mes pelo IPP 242-Siderurgia (`ibge_sidra_ipp_siderurgia`, mais
    especifico que o 24-Metalurgia do legado, mas ainda PROXY - nunca
    especifico de bobina a quente). Caminho explicito e paralelo - NAO
    substitui `carregar_preco_domestico_trimestral`/`preco_domestico_
    ponderado`/`encadear_preco_domestico_mensal` (legado, inalterados; a
    expansao mensal REAPROVEITA `encadear_preco_domestico_mensal` sem
    nenhuma modificacao - a regra de encadeamento/hold-flat/sem-look-ahead
    ja estava correta).

    Gerdau NAO esta na cesta hoje: seus segmentos publicos (aco longo,
    Brasil) nao reportam receita/volume compativeis com bobina a quente -
    incluir Gerdau exigiria antes confirmar uma fonte com escopo
    compativel, o que nao existe hoje. Isso nao e uma allowlist de nomes de
    empresa no codigo: se e quando essa evidencia existir, uma linha no CSV
    curado com `tipo` qualificado (nao `TIPO_INCOMPATIVEL_DOMESTICO`) passa
    a ser incluida automaticamente por `ancora_domestica_ponderada_v2`.

    `df_trimestral` (mesmo formato de `ancora_domestica_ponderada_v2`) e
    `ipp_mensal` aceitam dado ja pronto (mesmo padrao de injecao de teste
    do resto do modulo) - se None, busca a fonte real (CSV curado local +
    IBGE/SIDRA ao vivo).

    Saida mensal com pelo menos: reference_period, preco_domestico_rs_t,
    anchor_reference_period, anchor_price_rs_t, companies_used,
    ipp_series_id, provenance_level, is_proxy, validation_status (mais
    receita_total/volume_total/quantidade_empresas). `is_proxy` e True
    quando a ancora e escopo "Siderurgia" (nao especifico de HRC) OU o mes
    foi encadeado pelo IPP (tambem um agregado de siderurgia, nunca
    especifico) - hoje isso cobre essencialmente todos os meses, porque
    nenhuma das duas fontes e HRC-especifica ainda (ver
    docs/METODOLOGIA.md).

    NAO conectado a --selftest/CLI/relatorio nesta stage - mesmo status dos
    demais caminhos V2 (peca de calculo interna, testada).
    """
    if df_trimestral is None:
        bruto = carregar_preco_domestico_trimestral_v2(caminho_csv)
        ancora = ancora_domestica_ponderada_v2(bruto)
    else:
        ancora = df_trimestral
    if ancora.empty:
        return ancora
    if ipp_mensal is None:
        ipp_mensal = ibge_sidra_ipp_siderurgia()

    mensal = encadear_preco_domestico_mensal(ancora[["trimestre", "preco_rs_t", "tipo"]], ipp_mensal)
    ancora_por_trimestre = ancora.set_index("trimestre")

    linhas = []
    for data, linha in mensal.iterrows():
        base = ancora_por_trimestre.loc[linha["trimestre_base"]]
        vintage = classificar_preco_domestico(pd.Series(
            {"tipo_dado_domestico": linha["tipo_dado"], "metodo_domestico": linha["metodo"]}, name=data))
        is_proxy = bool(vintage.proxy) or (linha["metodo"] == "encadeado_ipp")
        linhas.append({
            "reference_period": data,
            "preco_domestico_rs_t": linha["preco_rs_t"],
            "anchor_reference_period": linha["trimestre_base"],
            "anchor_price_rs_t": float(base["preco_rs_t"]),
            "companies_used": base["companies_used"],
            "ipp_series_id": IPP_SIDERURGIA_SERIES_ID,
            "provenance_level": vintage.nivel,
            "is_proxy": is_proxy,
            "validation_status": _VALIDACAO_ANCORA_CSV_CURADO,
            "receita_total": float(base["receita_total_rs"]),
            "volume_total": float(base["volume_total_t"]),
            "quantidade_empresas": int(base["quantidade_empresas"]),
        })
    out = pd.DataFrame(linhas)
    cols = ["reference_period", "preco_domestico_rs_t", "anchor_reference_period", "anchor_price_rs_t",
            "companies_used", "ipp_series_id", "provenance_level", "is_proxy", "validation_status",
            "receita_total", "volume_total", "quantidade_empresas"]
    return out[cols]


# =============================================================================
# 3e. IPIA-HRC V2 completo - integracao import side + Domestic Price V2 (Stage E9)
# =============================================================================

_COLS_IMPORT_SIDE_V2 = ["reference_period", "ppi_rs_t", "publication_status", "total_kg",
                        "known_policy_kg", "unknown_policy_kg", "policy_coverage",
                        "ppi_lower", "ppi_upper", "ppi_uncertainty_range_pct"]


def calcular_serie_ipia_hrc_v2(ppi_mensal_df: pd.DataFrame | None = None,
                               preco_domestico_df: pd.DataFrame | None = None,
                               ano_ini: int = 2012, ano_fim: int = 2026,
                               df_bruto: pd.DataFrame | None = None) -> pd.DataFrame:
    """IPIA-HRC V2 completo (Stage E9): integra o agregador bottom-up
    multi-NCM (import side, `agregar_ipia_hrc_multi_ncm_mensal` - Stage E7)
    com o Domestic Price V2 (`preco_domestico_hrc_mensal_v2` - Stage E8) por
    `reference_period`, aplicando IPIA = preco_domestico_v2/ppi_v2*100
    somente quando os dois lados forem validos no mesmo mes.

    NAO recalcula II/AFRMM/antidumping, a agregacao por KG, nem
    soma(receita)/soma(volume) - essas contas ja vem prontas nos DataFrames
    de entrada; esta funcao SO faz merge por `reference_period` + regra de
    status conjunta + a formula do IPIA. `ppi_mensal_df`/`preco_domestico_df`
    aceitam o resultado ja pronto das duas funcoes V2 (mesmo padrao de
    injecao de teste do resto do modulo) - se None, gera ao vivo com
    `ano_ini`/`ano_fim`/`df_bruto` (`preco_domestico_df` sempre usa a fonte
    real de `preco_domestico_hrc_mensal_v2`, que nao aceita `ano_ini`/
    `ano_fim` - a cobertura dela vem do CSV curado e do IPP, nao de um
    intervalo pedido pelo chamador).

    As colunas `preco_domestico_rs_t`/`ipia` que `agregar_ipia_hrc_multi_ncm_mensal`
    devolve por padrao (calculadas contra o preco domestico LEGADO, quando
    `ppi_mensal_df` e gerado aqui sem `domestico_df` proprio) sao
    DESCARTADAS antes do merge - `_COLS_IMPORT_SIDE_V2` mantem so as colunas
    especificas do lado de importacao. O preco domestico final vem SEMPRE
    de `preco_domestico_df` (V2), nunca do legado.

    Regra de status conjunta (segue a decisao ja aprovada, nao reaberta
    aqui):
      - import side UNKNOWN -> IPIA UNKNOWN;
      - preco domestico V2 ausente no mes (sem ancora - nunca inventado,
        nunca forward-fill alem do que `preco_domestico_hrc_mensal_v2` ja
        fizer) -> IPIA UNKNOWN;
      - import EXPERIMENTAL + domestico presente -> IPIA EXPERIMENTAL;
      - import PUBLICATION_GRADE + domestico presente -> IPIA
        PUBLICATION_GRADE;
      - qualquer outra combinacao -> UNKNOWN.

    `domestic_is_proxy` (a ancora "Siderurgia" e o IPP 242-Siderurgia nao
    serem especificos de HRC) e uma flag SEPARADA, ortogonal a
    `publication_status` - PROXY nunca vira sinonimo de UNKNOWN nem de
    EXPERIMENTAL aqui.
    """
    if ppi_mensal_df is None:
        # `agregar_ipia_hrc_multi_ncm_mensal` faz seu PROPRIO merge interno
        # com preco domestico quando `domestico_df` nao e passado (usando o
        # CSV curado LEGADO como default) - isso recortaria o import side
        # so aos meses onde o CSV legado tem cobertura (hoje, so 2025Q2 em
        # diante), apagando toda a serie 2012-2025 antes mesmo de chegar ao
        # merge com o Domestic Price V2 real, alguns paragrafos abaixo.
        # Um domestico "curinga" com cobertura total evita esse recorte
        # prematuro sem alterar `agregar_ipia_hrc_multi_ncm_mensal` - seu
        # preco_rs_t nunca e usado: `_COLS_IMPORT_SIDE_V2` descarta as
        # colunas preco_domestico_rs_t/ipia que essa chamada devolveria.
        domestico_curinga = pd.DataFrame(
            {"preco_rs_t": 1.0}, index=pd.date_range(f"{ano_ini}-01-01", f"{ano_fim}-12-01", freq="MS"))
        ppi_mensal_df = agregar_ipia_hrc_multi_ncm_mensal(
            ano_ini=ano_ini, ano_fim=ano_fim, df_bruto=df_bruto, domestico_df=domestico_curinga)
    if preco_domestico_df is None:
        preco_domestico_df = preco_domestico_hrc_mensal_v2()

    imp = ppi_mensal_df[_COLS_IMPORT_SIDE_V2].rename(columns={"publication_status": "import_status"})
    dom = preco_domestico_df.rename(columns={
        "provenance_level": "domestic_provenance_level",
        "is_proxy": "domestic_is_proxy",
        "validation_status": "domestic_validation_status",
    })

    merged = imp.merge(dom, on="reference_period", how="outer", validate="one_to_one")
    merged = merged.sort_values("reference_period").reset_index(drop=True)

    domestico_presente = merged["preco_domestico_rs_t"].notna()
    import_status = merged["import_status"]
    status = pd.Series(STATUS_UNKNOWN, index=merged.index)
    status[domestico_presente & (import_status == STATUS_EXPERIMENTAL)] = STATUS_EXPERIMENTAL
    status[domestico_presente & (import_status == STATUS_PUBLICATION_GRADE)] = STATUS_PUBLICATION_GRADE
    merged["publication_status"] = status

    calculavel = status != STATUS_UNKNOWN
    merged["ipia_hrc_v2"] = np.nan
    merged.loc[calculavel, "ipia_hrc_v2"] = ipia(
        merged.loc[calculavel, "preco_domestico_rs_t"], merged.loc[calculavel, "ppi_rs_t"])

    cols = ["reference_period", "preco_domestico_rs_t", "ppi_rs_t", "ipia_hrc_v2", "publication_status",
            "import_status",
            "total_kg", "known_policy_kg", "unknown_policy_kg", "policy_coverage",
            "ppi_lower", "ppi_upper", "ppi_uncertainty_range_pct",
            "anchor_reference_period", "anchor_price_rs_t", "companies_used", "ipp_series_id",
            "domestic_provenance_level", "domestic_is_proxy", "domestic_validation_status",
            "receita_total", "volume_total", "quantidade_empresas"]
    return merged[cols]


# =============================================================================
# 3f. Domestic Price V2 - PIA-Produto benchmark (Stage E10)
# =============================================================================
# Decisao Level 3 aprovada (docs/research/hrc_domestic_price_sources.md):
# adota a IBGE PIA-Produto (tabela SIDRA 7752, categoria 54849 = Prodlist
# 2422.2020 "Bobinas a quente de acos ao carbono, nao revestidos") como
# BENCHMARK ANUAL de nivel do Domestic Price HRC V2 - especifico de HRC
# (ao contrario da ancora corporativa "Siderurgia" de
# `preco_domestico_hrc_mensal_v2`), mas mistura mercado interno +
# exportacao (confirmado contra a nota tecnica oficial do IBGE: nenhuma
# variavel do produto separa destino - e o proprio desenho da pesquisa,
# pensada para ser cruzada com Comex, nao para ja vir separada). Por isso
# a PIA tambem e PROXY, so que por outro motivo
# (`PROXY_REASON_DESTINATION_MIX`, nao `PROXY_REASON_PRODUCT_AGGREGATION`
# da ancora corporativa/IPP) - ver o adendo de pesquisa em
# docs/research/hrc_domestic_price_sources.md para a evidencia completa
# (exposicao a exportacao medida: 12%-43% do volume, mediana 26,2%,
# 2014-2023).
#
# A cesta anual (PIA) e encadeada mes a mes pelo movimento do IPP
# 242-Siderurgia (`ibge_sidra_ipp_siderurgia`, ja existente, reaproveitada
# sem alteracao) via **Proportional Denton** (primeiras diferencas - IMF
# Quarterly National Accounts Manual, cap. 6): preserva ao maximo o
# movimento relativo mes a mes do IPP, sujeito a
# mean(preco_mensal do ano) == preco_pia_hrc daquele ano - nunca
# forward-fill anual, nunca interpolacao linear simples, nunca degrau em
# janeiro (ver `denton_proporcional`).
#
# Este caminho NAO substitui `preco_domestico_hrc_mensal_v2` (ancora
# corporativa Usiminas+CSN, Stage E8) - os dois coexistem. A ancora
# corporativa continua disponivel so como BENCHMARK/sanity-check contra
# esta serie (comparacao feita em scripts/gerar_domestic_price_hrc_pia_v2.py),
# NUNCA usada para fazer splice/reancorar a serie PIA (decisao Level 3:
# nao ha janela de sobreposicao suficiente entre as duas fontes para
# calibrar uma transicao, e o mix de produto e diferente).
#
# NAO conectado a --selftest/CLI/relatorio nesta stage - mesmo status dos
# demais caminhos V2 (peca de calculo interna, testada).

IBGE_SIDRA_PIA_PRODUTO_URL = ("https://servicodados.ibge.gov.br/api/v3/agregados/7752"
                              "/periodos/all/variaveis/864|1982")
IBGE_SIDRA_PIA_PRODUTO_METADADOS_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/7752/metadados"
# Categoria 54849 na classificacao 1264 (Prodlist 2016/2019/2022) da tabela
# SIDRA 7752 = "2422.2020 Bobinas a quente de acos ao carbono, nao
# revestidos" - confirmada ao vivo (unidade "Toneladas") em
# docs/research/hrc_domestic_price_sources.md. Variavel 864 = Receita
# liquida de vendas (Mil Reais); variavel 1982 = Quantidade vendida
# (Toneladas).
PIA_CATEGORIA_HRC = 54849

PROXY_REASON_DESTINATION_MIX = "DESTINATION_MIX"          # PIA: mistura mercado interno + exportacao
PROXY_REASON_PRODUCT_AGGREGATION = "PRODUCT_AGGREGATION"  # IPP 242-Siderurgia: agregado de toda a siderurgia


def ibge_sidra_pia_hrc_anual() -> pd.DataFrame:
    """Serie ANUAL do preco implicito HRC (IBGE/SIDRA, PIA-Produto, tabela
    7752, categoria `PIA_CATEGORIA_HRC`) - receita liquida de vendas /
    quantidade vendida, ambas do MESMO codigo Prodlist (nunca numerador e
    denominador de escopos diferentes).

    HRC-especifica (ao contrario da ancora corporativa "Siderurgia"), mas
    MISTURA mercado interno + exportacao - confirmado contra a nota
    tecnica oficial da PIA-Produto (nenhuma variavel do produto separa
    destino). Todo consumidor desta funcao deve tratar o resultado como
    PROXY (`PROXY_REASON_DESTINATION_MIX`) - nunca como preco domestico
    puro. Ver docs/research/hrc_domestic_price_sources.md para a evidencia
    completa e a medicao de materialidade da exposicao a exportacao.

    Valida a unidade da categoria (`Toneladas`) contra o metadado ao vivo
    antes de calcular o preco - nunca confia que a categoria/tabela nao
    mudou de forma silenciosa.

    Retorna DataFrame indexado por ano (int), colunas
    receita_liquida_mil_rs, quantidade_vendida_t, preco_rs_t.
    """
    meta = _get_json(IBGE_SIDRA_PIA_PRODUTO_METADADOS_URL)
    classificacao = next(c for c in meta["classificacoes"] if c["id"] == 1264)
    categoria = next(c for c in classificacao["categorias"] if c["id"] == PIA_CATEGORIA_HRC)
    if categoria["unidade"] != "Toneladas":
        raise ValueError(f"unidade inesperada para a categoria PIA HRC: {categoria['unidade']!r} "
                         f"(esperado 'Toneladas') - categoria/tabela pode ter mudado, revisar antes de usar")

    variaveis = _get_json(IBGE_SIDRA_PIA_PRODUTO_URL,
                          {"localidades": "N1[all]", "classificacao": f"1264[{PIA_CATEGORIA_HRC}]"})
    series = {}
    for var in variaveis:
        serie = var["resultados"][0]["series"][0]["serie"]
        series[str(var["id"])] = {int(ano): float(v) for ano, v in serie.items()}

    out = pd.DataFrame({
        "receita_liquida_mil_rs": pd.Series(series["864"]),
        "quantidade_vendida_t": pd.Series(series["1982"]),
    }).sort_index()
    out.index.name = "ano"
    out["preco_rs_t"] = out["receita_liquida_mil_rs"] * 1000.0 / out["quantidade_vendida_t"]
    return out


def denton_proporcional(indicador: pd.Series, alvos_anuais: pd.Series) -> pd.Series:
    """Proportional Denton, variante de primeiras diferencas (IMF Quarterly
    National Accounts Manual, cap. 6): distribui um indicador mensal em
    torno de niveis anuais observados, preservando ao maximo o MOVIMENTO
    relativo mes a mes do indicador - nunca um degrau/pro-rata simples na
    fronteira do ano.

    Minimiza:
        sum_t [ x[t]/i[t] - x[t-1]/i[t-1] ]^2
    sujeito a, para cada ano y:
        sum(x[t] para t no ano y) == alvos_anuais[y] * (numero de meses de y em `indicador`)
    (equivalente a mean(x[t] no ano y) == alvos_anuais[y]).

    Resolvido via sistema linear KKT (numpy puro - sem scipy.optimize nem
    biblioteca de disaggregation temporal; a matriz e pequena, algumas
    dezenas de meses/restricoes no uso deste modulo).

    `indicador`: Series mensal (index = mes, DatetimeIndex), estritamente
    positiva, cobrindo EXATAMENTE os anos de `alvos_anuais` (nenhum mes
    fora deles, nenhum ano de `alvos_anuais` ausente do indicador) - erro
    explicito se nao cobrir, nunca completa em silencio.
    `alvos_anuais`: Series indexada por ano (int).

    Retorna Series mensal (mesmo index de `indicador`).
    """
    if indicador.empty or alvos_anuais.empty:
        raise ValueError("indicador e alvos_anuais nao podem ser vazios")
    if (indicador <= 0).any():
        raise ValueError("indicador deve ser estritamente positivo (Denton proporcional divide por ele)")

    anos_indicador = pd.Index(indicador.index.year)
    anos_alvo = sorted(alvos_anuais.index)
    if set(anos_indicador) != set(anos_alvo):
        raise ValueError(
            f"indicador e alvos_anuais devem cobrir exatamente os mesmos anos - "
            f"indicador tem {sorted(set(anos_indicador))}, alvos_anuais tem {anos_alvo}")

    n = len(indicador)
    i = indicador.to_numpy(dtype=float)

    diferenca = np.zeros((n - 1, n))
    for k in range(n - 1):
        diferenca[k, k] = -1.0
        diferenca[k, k + 1] = 1.0
    escala = np.diag(1.0 / i)
    m_objetivo = escala @ diferenca.T @ diferenca @ escala  # (n, n), semidefinida positiva

    restricao = np.zeros((len(anos_alvo), n))
    alvo_vetor = np.zeros(len(anos_alvo))
    for linha, ano in enumerate(anos_alvo):
        mascara = (anos_indicador == ano)
        restricao[linha, mascara] = 1.0
        alvo_vetor[linha] = alvos_anuais.loc[ano] * mascara.sum()

    zeros = np.zeros((len(anos_alvo), len(anos_alvo)))
    kkt = np.block([[2.0 * m_objetivo, restricao.T], [restricao, zeros]])
    lado_direito = np.concatenate([np.zeros(n), alvo_vetor])
    solucao = np.linalg.solve(kkt, lado_direito)
    return pd.Series(solucao[:n], index=indicador.index, name="preco_rs_t")


def preco_domestico_hrc_pia_v2(pia_anual_df: pd.DataFrame | None = None,
                               ipp_mensal: pd.Series | None = None) -> pd.DataFrame:
    """Domestic Price HRC V2 - caminho PIA (Stage E10, decisao Level 3
    aprovada em docs/research/hrc_domestic_price_sources.md): benchmarking
    temporal (Proportional Denton) entre a ancora ANUAL da PIA-Produto
    (`ibge_sidra_pia_hrc_anual`) e o movimento MENSAL do IPP 242-Siderurgia
    (`ibge_sidra_ipp_siderurgia`, ja existente, reaproveitada sem
    alteracao).

    NAO substitui `preco_domestico_hrc_mensal_v2` (ancora corporativa
    Usiminas+CSN) - os dois coexistem e NUNCA sao combinados por
    splice/reancoragem (decisao Level 3: mix de produto diferente, sem
    janela de sobreposicao suficiente para calibrar uma transicao). A
    ancora corporativa so entra como benchmark de validacao externa,
    calculada separadamente (scripts/gerar_domestic_price_hrc_pia_v2.py),
    nunca dentro desta funcao.

    Regras de cobertura (decisao Level 3):
      - Anos da PIA SEM os 12 meses do IPP disponiveis nao geram serie
        mensal artificial - ficam de fora do resultado (continuam
        acessiveis via `ibge_sidra_pia_hrc_anual()` como benchmark anual
        isolado, para validacao).
      - Para a janela onde PIA anual + IPP mensal completo coexistem
        (esperado ~2019-2023): serie mensal BENCHMARKED via
        `denton_proporcional`. `is_provisional=False`.
      - Apos o ultimo ano PIA observado: extensao PROVISIONAL - encadeia a
        partir da ultima relacao preco-benchmarked/IPP observada (mesma
        formula de encadeamento por variacao de indice ja usada em
        `encadear_preco_domestico_mensal`, so que a partir do ultimo mes
        Denton em vez de uma ancora trimestral direta). `is_provisional=True`.
        NUNCA promovida a publication-grade automaticamente (decisao de
        quem integra com o import side, fora desta funcao) e NUNCA
        misturada silenciosamente com a janela benchmarked - a flag
        `is_provisional` distingue as duas o tempo todo.
      - `pia_reference_year` (ano da PIA que fundamenta aquele mes) e
        preservado em toda linha - campo minimo necessario para, no
        futuro, reprocessar os meses provisorios quando uma nova PIA sair
        (mecanismo de revisao em si NAO implementado aqui - so o campo que
        permite implementar depois, por instrucao explicita da decisao
        Level 3).

    PROPRIEDADE CONHECIDA (nao um bug, ver
    tests/unit/test_preco_domestico_hrc_pia_v2.py::
    test_janela_benchmarked_conjunta_pode_revisar_anos_antigos_quando_novo_ano_pia_e_somado):
    o Denton e resolvido JUNTO para toda a janela benchmarked de uma vez
    (para poder suavizar a fronteira entre anos - e o proprio motivo de
    usar Denton em vez de pro-rata). Isso significa que, quando um NOVO
    ano de PIA for publicado e a janela benchmarked reprocessada do zero,
    meses de anos MAIS ANTIGOS podem mudar levemente perto da nova
    fronteira - pratica padrao de temporal benchmarking (IMF QNA Manual
    cap. 6), nao uma falha de look-ahead. A media anual de cada ano
    continua batendo exatamente o alvo PIA daquele ano em qualquer
    reprocessamento (essa e a garantia que nao muda). Ja a extensao
    PROVISIONAL nunca olha para frente: cada mes provisional so depende do
    ultimo mes benchmarked e do IPP ate aquele proprio mes, nunca de IPP
    futuro (verificado em teste dedicado).

    Toda linha mensal (benchmarked ou provisional) e uma estimativa
    derivada de um nivel anual observado (a PIA em si, preservada em
    `pia_anchor_price_rs_t`) - nenhuma e um dado bruto mensal observado,
    entao `provenance_level=NIVEL_ESTIMADO` para todas (mesmo criterio ja
    usado por `classificar_preco_domestico`: encadeado/interpolado =
    ESTIMADO).

    Saida mensal com: reference_period, preco_domestico_rs_t,
    pia_reference_year, pia_anchor_price_rs_t, ipp_series_id,
    provenance_level, is_proxy, proxy_reason, is_provisional,
    validation_status.
    """
    cols = ["reference_period", "preco_domestico_rs_t", "pia_reference_year", "pia_anchor_price_rs_t",
            "ipp_series_id", "provenance_level", "is_proxy", "proxy_reason", "is_provisional",
            "validation_status"]
    if pia_anual_df is None:
        pia_anual_df = ibge_sidra_pia_hrc_anual()
    if ipp_mensal is None:
        ipp_mensal = ibge_sidra_ipp_siderurgia()

    ipp_mensal = pd.to_numeric(ipp_mensal, errors="coerce").dropna().sort_index()
    if ipp_mensal.empty or pia_anual_df.empty:
        return pd.DataFrame(columns=cols)

    anos_ipp_completos = {ano for ano, g in ipp_mensal.groupby(ipp_mensal.index.year) if len(g) == 12}
    anos_benchmarked = sorted(set(pia_anual_df.index) & anos_ipp_completos)
    if not anos_benchmarked:
        # nenhum ano com PIA + 12 meses de IPP disponiveis simultaneamente -
        # nunca fabrica serie mensal so com um dos dois (regra explicita da
        # decisao Level 3).
        return pd.DataFrame(columns=cols)

    primeiro_ano, ultimo_ano = min(anos_benchmarked), max(anos_benchmarked)
    anos_esperados = set(range(primeiro_ano, ultimo_ano + 1))
    if set(anos_benchmarked) != anos_esperados:
        faltando = sorted(anos_esperados - set(anos_benchmarked))
        raise ValueError(
            f"janela PIA+IPP nao e continua entre {primeiro_ano} e {ultimo_ano} - "
            f"ano(s) sem cobertura completa: {faltando}. Comportamento para buraco no meio da "
            f"janela benchmarked nao foi decidido (escalar para Level 3 se isso ocorrer com dado real).")

    indicador_bench = ipp_mensal.loc[f"{primeiro_ano}-01-01": f"{ultimo_ano}-12-31"]
    alvos = pia_anual_df.loc[primeiro_ano:ultimo_ano, "preco_rs_t"]
    precos_bench = denton_proporcional(indicador_bench, alvos)

    linhas = pd.DataFrame({
        "reference_period": indicador_bench.index,
        "preco_domestico_rs_t": precos_bench.to_numpy(),
        "pia_reference_year": indicador_bench.index.year,
    })
    linhas["pia_anchor_price_rs_t"] = linhas["pia_reference_year"].map(alvos)
    linhas["is_provisional"] = False

    ultimo_mes_bench = indicador_bench.index.max()
    meses_provisionais = ipp_mensal.loc[ipp_mensal.index > ultimo_mes_bench]
    if not meses_provisionais.empty:
        preco_base = precos_bench.iloc[-1]
        ipp_base = indicador_bench.iloc[-1]
        precos_prov = preco_base * (meses_provisionais / ipp_base)
        linhas_prov = pd.DataFrame({
            "reference_period": meses_provisionais.index,
            "preco_domestico_rs_t": precos_prov.to_numpy(),
            "pia_reference_year": ultimo_ano,  # ultimo ano PIA que fundamenta a extensao
            "pia_anchor_price_rs_t": float(alvos.loc[ultimo_ano]),
            "is_provisional": True,
        })
        linhas = pd.concat([linhas, linhas_prov], ignore_index=True)

    linhas["ipp_series_id"] = IPP_SIDERURGIA_SERIES_ID
    linhas["provenance_level"] = NIVEL_ESTIMADO
    linhas["is_proxy"] = True
    linhas["proxy_reason"] = PROXY_REASON_DESTINATION_MIX
    linhas["validation_status"] = VALIDACAO_VERIFICADO

    return linhas[cols].sort_values("reference_period").reset_index(drop=True)


# =============================================================================
# 3g. IPIA-HRC V2 PIA-based - integracao oficial + provisional (Stage E11, ADR 0011)
# =============================================================================
# Decisao Level 3 aprovada: integra o import side bottom-up multi-NCM
# (Stage E7) com o Domestic Price V2 caminho PIA (`preco_domestico_hrc_pia_v2`,
# Stage E10/ADR 0010) - NUNCA a ancora corporativa Usiminas+CSN
# (`preco_domestico_hrc_mensal_v2`), que continua existindo so como
# benchmark independente (ADR 0010 item 2). Mesmo padrao de merge/formula
# de `calcular_serie_ipia_hrc_v2` (Stage E9, acima) - a novidade desta
# secao e o QUARTO status (PROVISIONAL) e a separacao explicita entre
# saida oficial e saida provisional.

STATUS_PROVISIONAL = "PROVISIONAL"
# Vive aqui, nao em steel_indicator.parameters.trade_policy, porque NAO e um
# status de politica comercial (import side) - trade_policy.status_efetivo()
# nunca deve devolver PROVISIONAL, so PUBLICATION_GRADE/EXPERIMENTAL/UNKNOWN
# (isso continua correto e nao muda aqui). PROVISIONAL existe so no nivel
# COMPOSTO (IPIA = domestico x import), quando o lado domestico e a
# extensao provisional pos-ultima-PIA de `preco_domestico_hrc_pia_v2`.

_COLS_IPIA_HRC_V2_PIA_OFICIAL = [
    "reference_period", "preco_domestico_rs_t", "ppi_rs_t", "ipia_hrc_v2", "publication_status",
    "domestic_is_proxy",
    "import_status", "total_kg", "known_policy_kg", "unknown_policy_kg", "policy_coverage",
    "ppi_lower", "ppi_upper", "ppi_uncertainty_range_pct",
    "pia_reference_year", "pia_anchor_price_rs_t", "ipp_series_id",
    "domestic_provenance_level", "domestic_proxy_reason", "domestic_validation_status",
]
_COLS_IPIA_HRC_V2_PIA_PROVISIONAL = _COLS_IPIA_HRC_V2_PIA_OFICIAL + ["is_provisional", "last_pia_year"]


def calcular_ipia_hrc_v2_pia(ppi_mensal_df: pd.DataFrame | None = None,
                              pia_domestico_df: pd.DataFrame | None = None,
                              ano_ini: int = 2012, ano_fim: int = 2026,
                              df_bruto: pd.DataFrame | None = None,
                              congelado_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """IPIA-HRC V2 PIA-based (Stage E11): mesmo import side de
    `calcular_serie_ipia_hrc_v2` (agregador bottom-up multi-NCM), mas o
    preco domestico vem de `preco_domestico_hrc_pia_v2()` (PIA-Produto +
    IPP via Denton), nunca da ancora corporativa. `ppi_mensal_df`/
    `pia_domestico_df` aceitam o resultado ja pronto das duas funcoes
    (mesmo padrao de injecao de teste do resto do modulo); se None, gera
    ao vivo. Mesma tecnica de `domestico_df` "curinga" que
    `calcular_serie_ipia_hrc_v2` ja usa, pela mesma razao: evitar que
    `agregar_ipia_hrc_multi_ncm_mensal` recorte o import side pelo
    preco domestico LEGADO antes do merge real, abaixo, com o Domestic
    Price V2 PIA.

    Regra de status conjunta (decisao Level 3 aprovada, secao 2 da
    decisao - QUATRO status, nunca so os tres do import side):
      - domestico ausente no mes OU import UNKNOWN -> IPIA UNKNOWN;
      - domestico BENCHMARKED (`is_provisional=False`) + import
        EXPERIMENTAL -> IPIA EXPERIMENTAL;
      - domestico BENCHMARKED + import PUBLICATION_GRADE -> IPIA
        PUBLICATION_GRADE;
      - domestico PROVISIONAL (`is_provisional=True`) + import calculavel
        (EXPERIMENTAL OU PUBLICATION_GRADE) -> IPIA PROVISIONAL, SEMPRE -
        PROVISIONAL nunca vira sinonimo de "PUBLICATION_GRADE com uma flag
        is_provisional=True" (proibido explicitamente pela decisao).

    `domestic_is_proxy` continua uma flag ortogonal a `publication_status`
    (mesma regra de `calcular_serie_ipia_hrc_v2`) - a serie PIA e SEMPRE
    proxy (`PROXY_REASON_DESTINATION_MIX`), em qualquer um dos quatro
    status.

    `last_pia_year` (o ultimo ano PIA benchmarked, calculado dinamicamente
    a partir de `pia_domestico_df` - nunca hardcoded) e anexado em TODA
    linha do resultado, para permitir a um chamador identificar a fronteira
    benchmarked/provisional sem reabrir `preco_domestico_hrc_pia_v2`.

    `congelado_df` (opcional): saida OFICIAL (EXPERIMENTAL/PUBLICATION_GRADE)
    de uma execucao ANTERIOR desta mesma funcao. Quando informado, todo
    `reference_period` presente em `congelado_df` tem suas colunas
    sobrescritas pelos valores CONGELADOS, ignorando o que o recalculo
    desta execucao produziria para esses meses - implementa a regra
    "BENCHMARKED publicado -> congelado no fluxo normal" (secao 5 da
    decisao) sem precisar reabrir o Denton conjunto de
    `preco_domestico_hrc_pia_v2` nem construir infraestrutura de vintage:
    qualquer mudanca upstream (revisao do IPP, novo ano de PIA reprocessando
    o Denton conjunto - ver a "propriedade conhecida" documentada em
    `preco_domestico_hrc_pia_v2`/ADR 0010) e simplesmente descartada para
    os meses ja congelados. Meses NAO presentes em `congelado_df` (novos
    meses provisional, ou meses provisional promovidos a benchmarked por
    uma nova PIA) usam sempre o valor fresco desta execucao - e assim que
    o provisional avanca mes a mes e e promovido quando uma nova PIA chega.
    Nao e um mecanismo de vintage completo (nao persiste nada sozinho, nao
    resolve as duas excecoes futuras de revisao de fonte/mudanca
    metodologica - decisao explicita de nao implementar isso ainda) - so a
    peca minima que torna o congelamento no fluxo normal possivel para quem
    orquestrar as execucoes (ver `scripts/gerar_ipia_hrc_v2_pia.py`).

    Formula preservada, sem alteracao: IPIA = preco_domestico / ppi * 100.
    """
    if ppi_mensal_df is None:
        # mesmo motivo/tecnica documentada em calcular_serie_ipia_hrc_v2:
        # sem isso, agregar_ipia_hrc_multi_ncm_mensal faria seu proprio
        # merge interno com o preco domestico LEGADO e recortaria o import
        # side para a cobertura (curta) do CSV curado legado, antes mesmo
        # de chegar no merge real com o Domestic Price V2 PIA abaixo.
        domestico_curinga = pd.DataFrame(
            {"preco_rs_t": 1.0}, index=pd.date_range(f"{ano_ini}-01-01", f"{ano_fim}-12-01", freq="MS"))
        ppi_mensal_df = agregar_ipia_hrc_multi_ncm_mensal(
            ano_ini=ano_ini, ano_fim=ano_fim, df_bruto=df_bruto, domestico_df=domestico_curinga)
    if pia_domestico_df is None:
        pia_domestico_df = preco_domestico_hrc_pia_v2()

    imp = ppi_mensal_df[_COLS_IMPORT_SIDE_V2].rename(columns={"publication_status": "import_status"})
    dom = pia_domestico_df.rename(columns={
        "provenance_level": "domestic_provenance_level",
        "is_proxy": "domestic_is_proxy",
        "proxy_reason": "domestic_proxy_reason",
        "validation_status": "domestic_validation_status",
    })

    merged = imp.merge(dom, on="reference_period", how="outer", validate="one_to_one")
    merged = merged.sort_values("reference_period").reset_index(drop=True)

    domestico_presente = merged["preco_domestico_rs_t"].notna()
    domestico_provisional = domestico_presente & merged["is_provisional"].fillna(False).astype(bool)
    domestico_benchmarked = domestico_presente & ~domestico_provisional
    import_status = merged["import_status"]
    import_calculavel = import_status.isin([STATUS_EXPERIMENTAL, STATUS_PUBLICATION_GRADE])

    status = pd.Series(STATUS_UNKNOWN, index=merged.index)
    status[domestico_benchmarked & (import_status == STATUS_EXPERIMENTAL)] = STATUS_EXPERIMENTAL
    status[domestico_benchmarked & (import_status == STATUS_PUBLICATION_GRADE)] = STATUS_PUBLICATION_GRADE
    status[domestico_provisional & import_calculavel] = STATUS_PROVISIONAL
    merged["publication_status"] = status

    calculavel = status != STATUS_UNKNOWN
    merged["ipia_hrc_v2"] = np.nan
    merged.loc[calculavel, "ipia_hrc_v2"] = ipia(
        merged.loc[calculavel, "preco_domestico_rs_t"], merged.loc[calculavel, "ppi_rs_t"])

    if not pia_domestico_df.empty:
        benchmarked_pia = pia_domestico_df.loc[~pia_domestico_df["is_provisional"], "pia_reference_year"]
        last_pia_year = int(benchmarked_pia.max()) if not benchmarked_pia.empty else None
    else:
        last_pia_year = None
    merged["last_pia_year"] = last_pia_year

    if congelado_df is not None and not congelado_df.empty:
        # sobrescreve TODAS as colunas compartilhadas (exceto reference_period,
        # a chave, e last_pia_year, valor de execucao corrente/global, nunca
        # congelado) com o valor congelado - nunca so publication_status/ipia,
        # para nao deixar colunas auxiliares (ex. ppi_lower/upper) inconsistentes
        # com um valor congelado que nao bate mais com o recalculo fresco.
        congelado = congelado_df.set_index("reference_period")

        # um mes congelado que o recalculo fresco NAO produz mais (ex.:
        # janela de import_side recomputada mais estreita, fonte fora do
        # ar naquele mes especifico) nunca pode simplesmente desaparecer
        # do resultado - isso violaria a mesma garantia de congelamento
        # que a sobrescrita abaixo protege, so que por omissao em vez de
        # por valor errado. Reinsere a linha congelada inteira antes de
        # sobrescrever.
        ausentes = congelado.index.difference(merged["reference_period"])
        if len(ausentes) > 0:
            linhas_ausentes = pd.DataFrame({"reference_period": ausentes})
            for col in merged.columns:
                if col == "reference_period":
                    continue
                elif col == "last_pia_year":
                    linhas_ausentes[col] = last_pia_year
                elif col == "is_provisional":
                    linhas_ausentes[col] = False  # congelado_df so guarda saida OFICIAL, nunca provisional
                elif col in congelado.columns:
                    linhas_ausentes[col] = linhas_ausentes["reference_period"].map(congelado[col])
                else:
                    linhas_ausentes[col] = np.nan
            merged = pd.concat([merged, linhas_ausentes], ignore_index=True)
            merged = merged.sort_values("reference_period").reset_index(drop=True)

        cols_congelar = [c for c in congelado.columns if c in merged.columns
                         and c not in ("reference_period", "last_pia_year")]
        meses_congelados = merged["reference_period"].isin(congelado.index)
        for col in cols_congelar:
            merged.loc[meses_congelados, col] = merged.loc[meses_congelados, "reference_period"].map(congelado[col])

    cols = ["reference_period", "preco_domestico_rs_t", "ppi_rs_t", "ipia_hrc_v2", "publication_status",
            "import_status",
            "total_kg", "known_policy_kg", "unknown_policy_kg", "policy_coverage",
            "ppi_lower", "ppi_upper", "ppi_uncertainty_range_pct",
            "pia_reference_year", "pia_anchor_price_rs_t", "ipp_series_id",
            "domestic_provenance_level", "domestic_is_proxy", "domestic_proxy_reason", "domestic_validation_status",
            "is_provisional", "last_pia_year"]
    return merged[cols]


def separar_ipia_hrc_v2_oficial_provisional(serie: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa a saida de `calcular_ipia_hrc_v2_pia` em DUAS series
    explicitas (secao 3 da decisao Level 3 aprovada) - NUNCA concatenadas
    automaticamente de volta:

      - OFICIAL: so EXPERIMENTAL/PUBLICATION_GRADE (nunca PROVISIONAL,
        nunca UNKNOWN - um mes UNKNOWN nao e "dado oficial com buraco", e
        simplesmente ausencia, tratada pelo consumidor/visualizacao como
        gap real, nunca uma linha com NaN no arquivo publicado);
      - PROVISIONAL: so PROVISIONAL, com os campos adicionais
        `is_provisional`/`last_pia_year` (o arquivo oficial nao precisa
        deles - todo mes oficial ja e, por definicao, nao-provisional).

    Nenhum recalculo acontece aqui - so filtro e selecao de colunas.
    """
    oficial = serie[serie["publication_status"].isin([STATUS_EXPERIMENTAL, STATUS_PUBLICATION_GRADE])]
    provisional = serie[serie["publication_status"] == STATUS_PROVISIONAL]
    return (oficial[_COLS_IPIA_HRC_V2_PIA_OFICIAL].reset_index(drop=True),
            provisional[_COLS_IPIA_HRC_V2_PIA_PROVISIONAL].reset_index(drop=True))


# =============================================================================
# 3h. IPIA-HRC V2 - vintages de publicacao append-only (Stage G2, ADR 0012)
# =============================================================================
# Persistencia local/imutavel de CADA execucao de calcular_ipia_hrc_v2_pia()
# como uma "vintage" (conceito D de manifest.py, ate aqui nao implementado)
# - mecanica generica (ID, escrita atomica, hash, indice, carga) delegada a
# steel_indicator.storage.vintage_store; este bloco so contem a integracao
# ECONOMICA especifica do IPIA-HRC V2 (quais colunas comparar para
# `revised`, quais campos entram no manifest) - nenhuma logica generica de
# storage e duplicada aqui.

VINTAGE_PRODUTO_IPIA_HRC_V2 = "ipia_hrc_v2"
VINTAGE_BASE_DIR_PADRAO = "data/processed/vintages"

_COLS_REVISED_NUMERICAS = ("preco_domestico_rs_t", "ppi_rs_t", "ipia_hrc_v2")


def calcular_revised(serie_atual: pd.DataFrame, serie_anterior: Optional[pd.DataFrame],
                      tol_abs: float = 1e-6, tol_rel: float = 1e-9) -> pd.Series:
    """Compara `serie_atual` (oficial OU provisional de UMA vintage, com
    `reference_period`) contra `serie_anterior` - a uniao (oficial +
    provisional) da vintage IMEDIATAMENTE anterior, ou None na primeira
    vintage (tudo False nesse caso).

    Regra (decisao Level 3 aprovada, secao "REVISED"):
      - `reference_period` nao existia na vintage anterior -> False (mes
        novo, nao e uma revisao);
      - existia e `preco_domestico_rs_t`/`ppi_rs_t`/`ipia_hrc_v2`
        (`math.isclose`, tolerante a ruido de ponto flutuante) E
        `publication_status` (igualdade exata de string) permanecem
        iguais -> False;
      - existia e qualquer um desses quatro campos mudou -> True
        (inclui promocao PROVISIONAL -> EXPERIMENTAL/PUBLICATION_GRADE,
        que sempre muda publication_status).

    NUNCA compara `data_vintage`/`source_vintage_id` - mudar so o
    identificador de execucao nunca conta como revisao (exigencia
    explicita da decisao aprovada).
    """
    if serie_anterior is None or serie_anterior.empty:
        return pd.Series(False, index=serie_atual.index)

    anterior_por_mes = (serie_anterior.drop_duplicates("reference_period", keep="last")
                        .set_index("reference_period"))
    revisado = pd.Series(False, index=serie_atual.index)
    for i, linha in serie_atual.iterrows():
        rp = linha["reference_period"]
        if rp not in anterior_por_mes.index:
            continue  # mes novo -> False (ja e o default)
        anterior = anterior_por_mes.loc[rp]
        if linha["publication_status"] != anterior["publication_status"]:
            revisado.loc[i] = True
            continue
        for col in _COLS_REVISED_NUMERICAS:
            va, vb = linha[col], anterior[col]
            a_nan, b_nan = pd.isna(va), pd.isna(vb)
            if a_nan and b_nan:
                continue
            if a_nan != b_nan or not math.isclose(float(va), float(vb), rel_tol=tol_rel, abs_tol=tol_abs):
                revisado.loc[i] = True
                break
    return revisado


def preparar_series_para_vintage(oficial: pd.DataFrame, provisional: pd.DataFrame, vintage_id: str,
                                  vintage_anterior: Optional[dict] = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Anexa `data_vintage`/`source_vintage_id`/`methodology_version`/
    `revised` a `oficial`/`provisional` (saida de
    `separar_ipia_hrc_v2_oficial_provisional`), deixando-as prontas para
    persistir como uma vintage. Funcao PURA - nao grava nada em disco (a
    escrita fica em `salvar_vintage_ipia_hrc_v2`).

    `source_vintage_id` usa o proprio `vintage_id` - a decisao aprovada
    permite isso explicitamente ("pode ser igual ao vintage_id se isso
    simplificar"): cada vintage desta stage sempre recalcula os inputs do
    zero numa unica execucao, entao publication vintage e source vintage
    coincidem; reaproveitar um bundle de inputs entre duas publication
    vintages diferentes exigiria distinguir os dois - fora de escopo aqui.

    `methodology_version` reusa `VERSAO_METODOLOGIA` (mecanismo ja
    existente no projeto) - este batch nao muda a formula economica do
    IPIA, entao nenhum bump acontece so por adicionar persistencia.

    `vintage_anterior` (dict no formato de `carregar_vintage_ipia_hrc_v2`,
    ou None na primeira vintage) fornece a base de comparacao para
    `revised` - a UNIAO de `official`+`provisional` da vintage
    imediatamente anterior, nunca so o mesmo arquivo: um mes provisional
    promovido a oficial precisa ser comparado contra onde ele estava
    antes (provisional.csv da vintage anterior), nao contra um
    official.csv anterior que nunca o continha.
    """
    serie_anterior_combinada = None
    if vintage_anterior is not None:
        serie_anterior_combinada = pd.concat(
            [vintage_anterior["official"], vintage_anterior["provisional"]], ignore_index=True)

    def _preparar(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["data_vintage"] = vintage_id
        df["source_vintage_id"] = vintage_id
        df["methodology_version"] = VERSAO_METODOLOGIA
        df["revised"] = calcular_revised(df, serie_anterior_combinada).to_numpy()
        return df

    return _preparar(oficial), _preparar(provisional)


def _iso_data_ou_none(ts) -> Optional[str]:
    if ts is None or pd.isna(ts):
        return None
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _montar_manifest_extra_ipia_hrc_v2(serie: pd.DataFrame, oficial: pd.DataFrame, provisional: pd.DataFrame,
                                        criado_em_utc: pd.Timestamp, previous_vintage_id: Optional[str],
                                        sources_fetch_at_utc: Optional[dict] = None) -> dict:
    """Monta os campos do manifest ESPECIFICOS do IPIA-HRC V2 (`vintage_id`/
    `files`/`hashes` sao automaticos, adicionados por
    `vintage_store.criar_vintage`). Funcao PURA - nenhum I/O.

    `sources_fetch_at_utc` (opcional, dict com `pia_fetch_at_utc`/
    `ipp_fetch_at_utc`/`comex_fetch_at_utc`/`bcb_fetch_at_utc`) e
    capturado pelo CHAMADOR (o script de orquestracao, unico lugar que
    efetivamente consulta essas fontes) no momento de cada chamada de
    rede - "quando esta execucao consultou a fonte", nunca uma data de
    publicacao da fonte em si (que este projeto nao inventa quando a
    fonte nao a expoe). Quando None/ausente, os campos ficam None -
    nunca um timestamp fabricado."""
    sources_fetch_at_utc = sources_fetch_at_utc or {}
    last_pia_year = None
    if not serie.empty and serie["last_pia_year"].notna().any():
        last_pia_year = int(serie["last_pia_year"].dropna().iloc[0])
    contagem = serie["publication_status"].value_counts() if not serie.empty else pd.Series(dtype=int)
    return {
        "created_at_utc": criado_em_utc.isoformat(),
        "previous_vintage_id": previous_vintage_id,
        "methodology_version": VERSAO_METODOLOGIA,
        "series": {"official": "official.csv", "provisional": "provisional.csv"},
        "coverage": {
            "official_first_period": _iso_data_ou_none(oficial["reference_period"].min() if not oficial.empty else None),
            "official_last_period": _iso_data_ou_none(oficial["reference_period"].max() if not oficial.empty else None),
            "provisional_first_period": _iso_data_ou_none(
                provisional["reference_period"].min() if not provisional.empty else None),
            "provisional_last_period": _iso_data_ou_none(
                provisional["reference_period"].max() if not provisional.empty else None),
        },
        "counts": {
            "experimental": int(contagem.get(STATUS_EXPERIMENTAL, 0)),
            "publication_grade": int(contagem.get(STATUS_PUBLICATION_GRADE, 0)),
            "provisional": int(contagem.get(STATUS_PROVISIONAL, 0)),
            "unknown_complete_series": int(contagem.get(STATUS_UNKNOWN, 0)),
        },
        "sources": {
            "pia_last_observed_year": last_pia_year,
            "pia_fetch_at_utc": sources_fetch_at_utc.get("pia_fetch_at_utc"),
            "ipp_fetch_at_utc": sources_fetch_at_utc.get("ipp_fetch_at_utc"),
            "comex_fetch_at_utc": sources_fetch_at_utc.get("comex_fetch_at_utc"),
            "bcb_fetch_at_utc": sources_fetch_at_utc.get("bcb_fetch_at_utc"),
        },
    }


def salvar_vintage_ipia_hrc_v2(serie: pd.DataFrame, import_side_df: pd.DataFrame, domestic_price_df: pd.DataFrame,
                                vintage_anterior: Optional[dict] = None,
                                base_dir: str = VINTAGE_BASE_DIR_PADRAO,
                                vintage_id: Optional[str] = None,
                                sources_fetch_at_utc: Optional[dict] = None) -> dict:
    """Separa `serie` (saida completa de `calcular_ipia_hrc_v2_pia`) em
    oficial/provisional, anexa os metadados de vintage
    (`preparar_series_para_vintage`), monta o manifest
    (`_montar_manifest_extra_ipia_hrc_v2`) e persiste tudo atomicamente
    (`vintage_store.criar_vintage`).

    `import_side_df`/`domestic_price_df` sao os INPUTS PROCESSADOS
    efetivamente usados no calculo - exatamente o que foi passado como
    `ppi_mensal_df`/`pia_domestico_df` para `calcular_ipia_hrc_v2_pia` ao
    produzir `serie` (responsabilidade do chamador manter essa
    correspondencia - ver `scripts/gerar_ipia_hrc_v2_pia.py`). Isso
    permite reproduzir o calculo economico da vintage sem depender de uma
    nova chamada as APIs externas - NAO e uma promessa de reconstruir o
    estado historico dessas APIs caso elas revisem seus proprios dados
    (ver `docs/METODOLOGIA.md`).

    Unica funcao deste bloco que faz I/O de disco (delegado a
    `vintage_store`) - as demais funcoes deste bloco sao puras. O
    congelamento do OFFICIAL (`congelado_df` de `calcular_ipia_hrc_v2_pia`)
    e responsabilidade de QUEM CHAMA esta funcao (o script de
    orquestracao), nao dela - `serie` ja deve chegar aqui calculada com o
    `congelado_df` correto aplicado, mesma decisao ja documentada em
    `calcular_ipia_hrc_v2_pia` (congelamento nunca escondido numa funcao
    de baixo nivel).

    `vintage_id`: injecao explicita para testes deterministicos (mesmo
    padrao do resto do modulo); se None, gera um novo via
    `vintage_store.novo_vintage_id()`.

    Retorna o manifest persistido (dict, com `vintage_id`/`files`/
    `hashes` ja preenchidos por `vintage_store.criar_vintage`).
    """
    vintage_id = vintage_id or vintage_store.novo_vintage_id()
    criado_em_utc = vintage_store.timestamp_de_vintage_id(vintage_id)
    previous_vintage_id = vintage_anterior["manifest"]["vintage_id"] if vintage_anterior is not None else None

    oficial, provisional = separar_ipia_hrc_v2_oficial_provisional(serie)
    oficial, provisional = preparar_series_para_vintage(oficial, provisional, vintage_id, vintage_anterior)

    manifest_extra = _montar_manifest_extra_ipia_hrc_v2(
        serie, oficial, provisional, criado_em_utc, previous_vintage_id, sources_fetch_at_utc)

    arquivos = {"official": oficial, "provisional": provisional,
                "import_side": import_side_df, "domestic_price": domestic_price_df}
    index_extra = {
        "created_at_utc": criado_em_utc.isoformat(),
        "methodology_version": VERSAO_METODOLOGIA,
        "last_pia_year": manifest_extra["sources"]["pia_last_observed_year"],
        "official_first_period": manifest_extra["coverage"]["official_first_period"],
        "official_last_period": manifest_extra["coverage"]["official_last_period"],
        "provisional_first_period": manifest_extra["coverage"]["provisional_first_period"],
        "provisional_last_period": manifest_extra["coverage"]["provisional_last_period"],
    }
    return vintage_store.criar_vintage(base_dir, VINTAGE_PRODUTO_IPIA_HRC_V2, vintage_id,
                                       arquivos, manifest_extra, index_extra)


_COLS_VINTAGE_TEXTO = ("data_vintage", "source_vintage_id", "methodology_version")


def carregar_vintage_ipia_hrc_v2(vintage_id: str, base_dir: str = VINTAGE_BASE_DIR_PADRAO) -> dict:
    """Carrega manifest + official/provisional/import_side/domestic_price
    de uma vintage ja persistida (`vintage_store.carregar_vintage`, que
    nao conhece o schema do IPIA-HRC V2).

    Forca `_COLS_VINTAGE_TEXTO` de volta a string apos o round-trip por
    CSV: `methodology_version` (ex. `"1.2"`) e um valor que PARECE
    numerico para o inferenciador de dtype do pandas - sem isso, viraria
    `float 1.2` na leitura (e uma futura versao como `"1.10"` perderia o
    zero a direita silenciosamente). `vintage_id`/`data_vintage` ja nao
    sofrem isso hoje (contem letras, ex. `20260101T000000Z`), mas ficam na
    lista por seguranca - sao identificadores, nunca numeros."""
    dados = vintage_store.carregar_vintage(base_dir, VINTAGE_PRODUTO_IPIA_HRC_V2, vintage_id)
    for chave in ("official", "provisional"):
        if chave not in dados:
            continue
        for col in _COLS_VINTAGE_TEXTO:
            if col in dados[chave].columns:
                dados[chave][col] = dados[chave][col].astype(str)
    return dados


def listar_vintages_ipia_hrc_v2(base_dir: str = VINTAGE_BASE_DIR_PADRAO) -> List[str]:
    """Vintage IDs do IPIA-HRC V2 em ordem cronologica."""
    return vintage_store.listar_vintages(base_dir, VINTAGE_PRODUTO_IPIA_HRC_V2)


def ultima_vintage_ipia_hrc_v2(base_dir: str = VINTAGE_BASE_DIR_PADRAO) -> Optional[str]:
    """Vintage mais recente do IPIA-HRC V2, ou None se ainda nao existe
    nenhuma (primeira execucao - sem congelado_df)."""
    return vintage_store.ultima_vintage(base_dir, VINTAGE_PRODUTO_IPIA_HRC_V2)


def custo_importacao_detalhado_mensal(ano_ini: int = 2020, ano_fim: int = 2026,
                                       df_bruto: pd.DataFrame | None = None,
                                       params: ParamsIPIA | None = None) -> pd.DataFrame:
    """Mesmo dado de entrada de `calcular_ipia_mensal` (bobina + cambio),
    mas devolve o DETALHAMENTO completo do custo de importacao - o que
    `custo_importacao_rs_t` ja calcula mas `calcular_ipia_mensal` descarta
    fora do total (`ppi_rs_t`). Nenhuma formula nova - so expoe o que ja
    existe, para o relatorio PDF (decomposicao de custo) usar sem
    recalcular nada.

    Colunas: fob_usd_t, frete_usd_t, seguro_usd_t, cambio, cif_brl_t,
    ii_brl_t, afrmm_brl_t, antidumping_brl_t, despesas_porto_rs_t,
    frete_interno_rs_t (as duas ultimas sao constantes de ParamsIPIA,
    repetidas por linha para facilitar o uso no relatorio), margem_rs_t
    (=ppi_brl_t - base; a margem e multiplicativa sobre a base, entao o
    "componente" dela na decomposicao e essa diferenca, nao uma fracao
    fixa) e ppi_brl_t (custo de internacao total).

    df_bruto aceita o dado bruto do Comex Stat ja buscado (evita nova
    chamada de rede quando chamado junto de `origem_importacao_bobina_por_pais`
    no mesmo relatorio) - se None, busca ao vivo.
    """
    p = params or ParamsIPIA()
    bobina = serie_mensal_preco_bobina(ano_ini, ano_fim, df_bruto=df_bruto)
    if bobina.empty:
        return bobina
    bobina = bobina.set_index("data")
    cambio = sgs(SGS["cambio_venda"], inicio=f"01/01/{ano_ini}").reindex(bobina.index, method="ffill")
    custo = custo_importacao_rs_t(bobina["preco_usd_t_publicado"], bobina["frete_usd_t"],
                                  bobina["seguro_usd_t"], cambio, p)
    base = custo["cif_brl_t"] + custo["ii_brl_t"] + custo["afrmm_brl_t"] + custo["antidumping_brl_t"] \
         + p.despesas_porto_rs_t + p.frete_interno_rs_t
    return pd.DataFrame({
        "fob_usd_t": bobina["preco_usd_t_publicado"],
        "frete_usd_t": bobina["frete_usd_t"],
        "seguro_usd_t": bobina["seguro_usd_t"],
        "cambio": cambio,
        "cif_brl_t": custo["cif_brl_t"],
        "ii_brl_t": custo["ii_brl_t"],
        "afrmm_brl_t": custo["afrmm_brl_t"],
        "antidumping_brl_t": custo["antidumping_brl_t"],
        "despesas_porto_rs_t": p.despesas_porto_rs_t,
        "frete_interno_rs_t": p.frete_interno_rs_t,
        "margem_rs_t": custo["ppi_brl_t"] - base,
        "ppi_brl_t": custo["ppi_brl_t"],
    })


# =============================================================================
# 5. TAXONOMIA E VINTAGE (OBSERVADO/CALCULADO/ESTIMADO + PROXY)
# =============================================================================
# Ver docs/adr/0008. Dois eixos INDEPENDENTES para qualquer numero exibido
# no relatorio - nao uma escala linear de 4 degraus:
#   - `nivel` (mutuamente exclusivo): quanto processamento o numero sofreu.
#   - `proxy` (booleano, ortogonal): o escopo bate com o rotulo? Pode
#     coexistir com qualquer nivel (ex.: preco domestico num trimestre
#     confirmado e CALCULADO + PROXY; num mes encadeado e ESTIMADO + PROXY).
#
# O contrato generico (NIVEL_*, NIVEIS_DADO, METODO_FORMULA_ALTERNATIVA,
# VintageInfo, vintage_table, validar_report_cutoff) foi extraido para
# steel_indicator/domain/provenance.py (Spec 0003, batch 2) - importado
# acima. As funcoes classificar_* abaixo permanecem AQUI de proposito: elas
# decidem nivel/proxy a partir de vocabulario especifico do IPIA-HRC V1
# (tipo_dado_domestico, metodo_domestico, tipo_dado_penetracao), que a
# metodologia ja marca como nao-permanente (ver docs/METODOLOGIA.md secao
# 12.5/26). Mover essa decisao para o contrato compartilhado do domain
# encodaria premissa do IPIA V1 como se fosse contrato generico de
# ICCS/ICS - ver docs/specs/0003-modularize-engine.md secao 3.

_PROXY_MOTIVO_DOMESTICO = ('Ancora domestica e proxy do segmento "Siderurgia", nao especifica '
                           "de bobina a quente (ver docs/adr/0003).")


def classificar_ipia(linha: pd.Series) -> VintageInfo:
    """linha: uma linha (Series) de `calcular_ipia_mensal()`, indexada
    pelo mes (`linha.name`)."""
    proxy = linha["tipo_dado_domestico"] in ("proxy_segmento_aco", "misto")
    estimado = linha["metodo_domestico"] in ("encadeado_ipp", "hold_flat_fallback")
    return VintageInfo(
        variavel="ipia", reference_period=linha.name,
        fonte="Comex Stat + BCB/SGS + CSV curado (Usiminas/CSN) + IBGE/SIDRA IPP",
        nivel=NIVEL_ESTIMADO if estimado else NIVEL_CALCULADO,
        proxy=proxy, proxy_motivo=_PROXY_MOTIVO_DOMESTICO if proxy else None,
        metodo=linha["metodo_domestico"])


def classificar_preco_domestico(linha: pd.Series) -> VintageInfo:
    """linha: uma linha de `calcular_ipia_mensal()` (usa tipo_dado_domestico
    e metodo_domestico) OU qualquer Series com essas duas chaves."""
    proxy = linha["tipo_dado_domestico"] in ("proxy_segmento_aco", "misto")
    estimado = linha["metodo_domestico"] in ("encadeado_ipp", "hold_flat_fallback")
    return VintageInfo(
        variavel="preco_domestico_rs_t", reference_period=linha.name,
        fonte="Releases trimestrais Usiminas/CSN + IBGE/SIDRA IPP (encadeamento mensal)",
        nivel=NIVEL_ESTIMADO if estimado else NIVEL_CALCULADO,
        proxy=proxy, proxy_motivo=_PROXY_MOTIVO_DOMESTICO if proxy else None,
        metodo=linha["metodo_domestico"])


def classificar_custo_internacao(linha: pd.Series) -> VintageInfo:
    """linha: uma linha de `custo_importacao_detalhado_mensal()`."""
    return VintageInfo(
        variavel="ppi_brl_t", reference_period=linha.name,
        fonte="Comex Stat (FOB/frete/seguro) + BCB/SGS (cambio)",
        nivel=NIVEL_CALCULADO, proxy=False)


def classificar_cambio(linha: pd.Series) -> VintageInfo:
    """linha: uma linha de `custo_importacao_detalhado_mensal()` (usa a
    coluna `cambio`, PTAX venda lida direto do BCB/SGS - sem formula
    nossa em cima)."""
    return VintageInfo(
        variavel="cambio", reference_period=linha.name,
        fonte="BCB/SGS (PTAX venda)", nivel=NIVEL_OBSERVADO, proxy=False)


def classificar_penetracao(linha: pd.Series) -> Optional[VintageInfo]:
    """linha: uma linha de `calcular_ipia_mensal()`. Retorna None quando o
    mes nao tem dado de penetracao (NaN) - nao ha o que classificar."""
    tipo = linha.get("tipo_dado_penetracao")
    if tipo == "oficial_mensal":
        return VintageInfo(
            variavel="penetracao_importacao_planos_pct", reference_period=linha.name,
            fonte="Instituto Aço Brasil (PDF oficial, tabela 9.1)",
            nivel=NIVEL_OBSERVADO, proxy=False, metodo="oficial_mensal")
    if tipo == "aproximado_consumo_aparente":
        return VintageInfo(
            variavel="penetracao_importacao_planos_pct", reference_period=linha.name,
            fonte="Instituto Aço Brasil (Excel \"Performance Mensal\", cálculo próprio)",
            nivel=NIVEL_CALCULADO, proxy=False, metodo=METODO_FORMULA_ALTERNATIVA,
            metodo_motivo=(
                "Cálculo próprio (Importação/Consumo Aparente) sobre dado do Aço Brasil "
                "— diverge ~1,2 p.p. do número oficial por METODOLOGIA (fórmula diferente "
                "da usada no PDF oficial), não por confiabilidade da fonte: é o mesmo "
                "Instituto nos dois casos. Ver docs/adr/0007."))
    return None


def classificar_origem_importacao(df_origem: Optional[pd.DataFrame]) -> Optional[VintageInfo]:
    """df_origem: saida de `origem_importacao_bobina_por_pais()`. Retorna
    None se vazio/sem janela definida."""
    if df_origem is None or df_origem.empty:
        return None
    mes_fim = df_origem.attrs.get("mes_fim")
    mes_inicio = df_origem.attrs.get("mes_inicio")
    if mes_fim is None:
        return None
    return VintageInfo(
        variavel="origem_importacao_pct", reference_period=mes_fim,
        fonte="Comex Stat (agregado por país)", nivel=NIVEL_CALCULADO, proxy=False,
        periodo_texto=(f"{mes_inicio:%Y-%m} a {mes_fim:%Y-%m}" if mes_inicio is not None else None))


def montar_tabela_vintage(df_ipia: Optional[pd.DataFrame] = None,
                          df_custo: Optional[pd.DataFrame] = None,
                          df_origem: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Uma linha por variavel exibida no relatorio, com reference_period,
    fonte, nivel e proxy - a estrutura que substitui a nocao implicita de
    "atual" por um periodo real e qualificado POR VARIAVEL (variaveis
    diferentes podem legitimamente ter meses de referencia diferentes,
    dado que Comex Stat/IPP/Aco Brasil tem defasagens proprias - ver
    docs/METODOLOGIA.md secao 7). Nao e exibida como tabela no PDF; e a
    base que os selos visuais e os selftests de reconciliacao/cutoff
    consultam. Cada DataFrame e opcional - usa o que for passado.
    """
    linhas: List[VintageInfo] = []
    if df_ipia is not None and len(df_ipia):
        ultimo = df_ipia.iloc[-1]
        linhas.append(classificar_ipia(ultimo))
        linhas.append(classificar_preco_domestico(ultimo))
        pen = classificar_penetracao(ultimo)
        if pen is not None:
            linhas.append(pen)
    if df_custo is not None and len(df_custo):
        ultimo_custo = df_custo.iloc[-1]
        linhas.append(classificar_custo_internacao(ultimo_custo))
        linhas.append(classificar_cambio(ultimo_custo))
    origem_info = classificar_origem_importacao(df_origem)
    if origem_info is not None:
        linhas.append(origem_info)
    return vintage_table(linhas)


def checar_reconciliacao_spread(df_ipia: pd.DataFrame, df_custo: pd.DataFrame) -> bool:
    """O spread mostrado na decomposicao de custo (preco domestico - custo
    de internacao) tem que bater com o mesmo calculo dentro de
    `df_ipia`, no MESMO mes - nunca comparar `df_ipia.iloc[-1]` com
    `df_custo.iloc[-1]` as cegas (podem ser meses diferentes, ja que
    `calcular_ipia_mensal` intersecta bobina x domestico enquanto
    `custo_importacao_detalhado_mensal` nao). Retorna False (incluindo)
    se o mes de `df_ipia` nem existir em `df_custo`.
    """
    if df_ipia.empty:
        return False
    mes = df_ipia.index[-1]
    if mes not in df_custo.index:
        return False
    spread_ipia = df_ipia.loc[mes, "preco_domestico_rs_t"] - df_ipia.loc[mes, "ppi_rs_t"]
    spread_custo = df_ipia.loc[mes, "preco_domestico_rs_t"] - df_custo.loc[mes, "ppi_brl_t"]
    return abs(float(spread_ipia) - float(spread_custo)) < 1e-6


def _serie_sintetica(n=180, seed=0, tendencia=0.0, nivel=10.0, ruido=1.0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2012-01-01", periods=n, freq="MS")
    saz = 0.8 * np.sin(2 * np.pi * np.arange(n) / 12)
    return pd.Series(nivel + tendencia * np.arange(n) + saz +
                     rng.normal(0, ruido, n), index=idx)


def selftest() -> int:
    # declarado no topo porque a secao 20 monkeypatcha e restaura esses
    # nomes de modulo temporariamente (Python exige global antes de
    # qualquer uso do nome na funcao, e as secoes anteriores ja usam
    # taxa_penetracao_importacao_planos_mensal)
    global comex_importacao_ncm, sgs, ibge_sidra_ipp_metalurgia, taxa_penetracao_importacao_planos_mensal
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

    # --- 15. geracao do relatorio PDF do IPIA (4 paginas, src/reporting/) ---
    from reporting.report_builder import gerar_relatorio_ipia
    idx_pdf = pd.date_range("2026-01-01", periods=6, freq="MS")
    df_ipia_pdf = pd.DataFrame({
        "ipia":                          [130.4, 142.6, 143.4, 139.3, 140.1, 134.0],
        "preco_domestico_rs_t":          [5213.2, 5213.2, 5213.2, 4996.0, 4996.0, 4996.0],
        "ppi_rs_t":                      [3996.8, 3655.7, 3636.0, 3586.3, 3567.2, 3727.9],
        "tipo_dado_domestico":           ["proxy_segmento_aco"] * 6,
        "metodo_domestico":              ["nivel_trimestral"] * 6,
        "peso_confiabilidade_importacao":[1.0] * 6,
        "penetracao_importacao_planos_pct": [24.1, 20.2, 18.5, 17.9, np.nan, 17.9],
        "tipo_dado_penetracao":          ["aproximado_consumo_aparente"] * 4 + [np.nan, "oficial_mensal"],
    }, index=idx_pdf)
    df_custo_pdf = pd.DataFrame({
        "fob_usd_t":          [620.0, 615.0, 610.0, 605.0, 600.0, 598.0],
        "frete_usd_t":        [45.0] * 6,
        "seguro_usd_t":       [4.0] * 6,
        "cambio":             [5.10, 5.15, 5.20, 5.18, 5.22, 5.19],
        "cif_brl_t":          [3415.0, 3410.0, 3400.0, 3385.0, 3380.0, 3360.0],
        "ii_brl_t":           [368.9, 368.3, 367.2, 365.6, 365.0, 362.9],
        "afrmm_brl_t":        [18.4, 18.5, 18.7, 18.6, 18.8, 18.7],
        "antidumping_brl_t":  [0.0] * 6,
        "despesas_porto_rs_t":[210.0] * 6,
        "frete_interno_rs_t": [140.0] * 6,
        "margem_rs_t":        [125.0, 124.6, 123.6, 122.7, 122.6, 121.7],
        "ppi_brl_t":          [3996.8, 3655.7, 3636.0, 3586.3, 3567.2, 3727.9],
    }, index=idx_pdf)
    df_origem_pdf = pd.DataFrame({
        "toneladas":     [45000.0, 22000.0, 12000.0, 8000.0, 3000.0],
        "pct_do_volume": [50.0, 24.4, 13.3, 8.9, 3.3],
    }, index=pd.Index(["China", "Coreia do Sul", "Egito", "Vietna", "India"], name="country"))
    df_origem_pdf.attrs["mes_inicio"] = idx_pdf[-3]
    df_origem_pdf.attrs["mes_fim"] = idx_pdf[-1]
    tmp_pdf_fd, tmp_pdf_path = tempfile.mkstemp(suffix=".pdf")
    _os.close(tmp_pdf_fd)
    try:
        n_meses = gerar_relatorio_ipia(tmp_pdf_path, df_ipia=df_ipia_pdf,
                                       df_custo=df_custo_pdf, df_origem=df_origem_pdf)
        tamanho = _os.path.getsize(tmp_pdf_path)
        check("relatorio PDF do IPIA (4 paginas) e gerado sem erro e nao esta vazio",
              _os.path.exists(tmp_pdf_path) and tamanho > 0 and n_meses == 6,
              f"tamanho = {tamanho} bytes, n_meses = {n_meses}")
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

    # --- 19. grafico_barras_horizontais: margem esquerda dinamica ------------
    # bug real de producao: "Coreia do Sul" (rotulo longo) era cortado na
    # borda da pagina porque a margem esquerda do grafico de origem das
    # importacoes era um deslocamento fixo, sem relacao com o rotulo mais
    # largo de fato presente na edicao. Testa que o inset cresce quando um
    # rotulo mais largo aparece nos dados - a correcao mede o rotulo de
    # verdade (TextPath), nao chuta um numero fixo.
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["text.parse_math"] = False
    import matplotlib.pyplot as plt
    from reporting import components as rep_components
    from reporting import theme as rep_theme

    fig_rotulo_curto = plt.figure(figsize=(rep_theme.LARGURA_POL, rep_theme.ALTURA_POL))
    ax_curto = rep_components.grafico_barras_horizontais(
        fig_rotulo_curto, 0.1, 0.1, 0.8, 0.2, ["China", "Egito"], [50.0, 13.3])
    inset_curto = ax_curto.get_position().x0 - 0.1

    fig_rotulo_longo = plt.figure(figsize=(rep_theme.LARGURA_POL, rep_theme.ALTURA_POL))
    ax_longo = rep_components.grafico_barras_horizontais(
        fig_rotulo_longo, 0.1, 0.1, 0.8, 0.2, ["China", "Coreia do Sul"], [50.0, 24.4])
    inset_longo = ax_longo.get_position().x0 - 0.1
    rotulo_mais_largo_pt = rep_components._largura_texto_pt("Coreia do Sul", 8.5, rep_theme.FONTE_SANS)

    check("grafico_barras_horizontais: margem esquerda cresce para rotulo mais largo "
          "('Coreia do Sul' vs. 'Egito')",
          inset_longo > inset_curto,
          f"inset_curto={inset_curto:.4f}, inset_longo={inset_longo:.4f}")
    check("grafico_barras_horizontais: axes nao invade o espaco reservado ao rotulo "
          "mais largo ('Coreia do Sul' cabe sem cortar)",
          ax_longo.get_position().x0 > 0.1,
          f"x0={ax_longo.get_position().x0:.4f}, rotulo_pt={rotulo_mais_largo_pt:.1f}")
    plt.close(fig_rotulo_curto)
    plt.close(fig_rotulo_longo)

    # --- 20. calcular_ipia_mensal(df_bruto=...) nao chama o Comex Stat de
    # novo -------------------------------------------------------------
    # bug real: calcular_ipia_mensal nao repassava df_bruto para
    # serie_mensal_preco_bobina, entao o relatorio PDF buscava o MESMO
    # dado bruto do Comex Stat duas vezes (uma aqui, outra em
    # _comex_bobina_bruto para custo/origem) - quebrava a garantia que o
    # proprio docstring de report_builder promete ("nunca duas chamadas de
    # rede para o mesmo dado"). Bloqueia comex_importacao_ncm (deve
    # explodir se for chamado) e substitui sgs/ibge/penetracao por stubs
    # sinteticos so para isolar esse teste de rede real - CSV curado
    # continua sendo o real (nao e rede, e arquivo versionado).
    _comex_original = comex_importacao_ncm
    _sgs_original = sgs
    _ibge_original = ibge_sidra_ipp_metalurgia
    _penet_original = taxa_penetracao_importacao_planos_mensal
    _chamadas_comex = {"n": 0}

    def _comex_bloqueado(ncm, ano_ini, ano_fim):
        _chamadas_comex["n"] += 1
        raise AssertionError("comex_importacao_ncm nao deveria ser chamado com df_bruto fornecido")

    def _sgs_stub(codigo, inicio="01/01/2010"):
        return pd.Series([5.10], index=[pd.Timestamp("2020-01-01")], name=f"sgs_{codigo}")

    def _ibge_stub(periodos="all"):
        return pd.Series(dtype=float)

    def _penet_stub(ano_ini=2013, ano_fim=None, df_historico=None, df_oficial=None):
        return pd.DataFrame({"taxa_penetracao_pct": pd.Series(dtype=float),
                             "tipo_dado_penetracao": pd.Series(dtype=object)})

    df_bruto_teste = pd.DataFrame({
        "year":            [2026, 2026, 2026],
        "monthNumber":     [6, 6, 6],
        "metricFOB":       [600000.0, 610000.0, 590000.0],
        "metricKG":        [1000000.0, 1020000.0, 980000.0],
        "metricFreight":   [40000.0, 41000.0, 39000.0],
        "metricInsurance": [4000.0, 4100.0, 3900.0],
        "country":         ["China", "Coreia do Sul", "Egito"],
    })

    comex_importacao_ncm = _comex_bloqueado
    sgs = _sgs_stub
    ibge_sidra_ipp_metalurgia = _ibge_stub
    taxa_penetracao_importacao_planos_mensal = _penet_stub
    try:
        resultado_dedup = calcular_ipia_mensal(2026, 2026, df_bruto=df_bruto_teste)
    finally:
        comex_importacao_ncm = _comex_original
        sgs = _sgs_original
        ibge_sidra_ipp_metalurgia = _ibge_original
        taxa_penetracao_importacao_planos_mensal = _penet_original

    check("calcular_ipia_mensal(df_bruto=...) nunca chama comex_importacao_ncm de novo "
          "(evita a 2a chamada de rede que o relatorio PDF fazia)",
          _chamadas_comex["n"] == 0, f"chamadas = {_chamadas_comex['n']}")
    check("calcular_ipia_mensal(df_bruto=...) ainda produz resultado valido com o dado injetado",
          not resultado_dedup.empty and pd.Timestamp("2026-06-01") in resultado_dedup.index,
          f"len = {len(resultado_dedup)}")

    # --- 21. vintage: reconciliacao do spread + deteccao de cutoff violado
    # (ver docs/adr/0008) -------------------------------------------------
    # bug historico real (pagina 2 do relatorio, corrigido nesta versao):
    # usar df_custo.iloc[-1] junto de df_ipia.iloc[-1] sem checar se e o
    # MESMO mes produzia um "spread" que somava dois meses diferentes -
    # df_custo tem um mes A MAIS (julho) que df_ipia nao tem, porque
    # calcular_ipia_mensal intersecta bobina x domestico (mais lento) e
    # custo_importacao_detalhado_mensal nao intersecta nada.
    idx_reconc = pd.date_range("2026-05-01", periods=2, freq="MS")
    df_ipia_reconc = pd.DataFrame({
        "preco_domestico_rs_t": [5000.0, 5236.0],
        "ppi_rs_t": [3600.0, 3728.0],
        "ipia": [138.9, 140.4],
        "tipo_dado_domestico": ["proxy_segmento_aco", "proxy_segmento_aco"],
        "metodo_domestico": ["nivel_trimestral", "nivel_trimestral"],
    }, index=idx_reconc)
    idx_custo_reconc = pd.date_range("2026-05-01", periods=3, freq="MS")  # 1 mes a mais que df_ipia
    df_custo_reconc = pd.DataFrame({
        "ppi_brl_t": [3600.0, 3728.0, 3806.0],
    }, index=idx_custo_reconc)

    check("(a) reconciliacao: spread usando df_custo.loc[mesmo mes de df_ipia] bate com o proprio df_ipia",
          checar_reconciliacao_spread(df_ipia_reconc, df_custo_reconc))

    spread_correto = df_ipia_reconc["preco_domestico_rs_t"].iloc[-1] - df_ipia_reconc["ppi_rs_t"].iloc[-1]
    spread_do_bug_antigo = df_ipia_reconc["preco_domestico_rs_t"].iloc[-1] - df_custo_reconc["ppi_brl_t"].iloc[-1]
    check("(a) contraprova: o padrao antigo (iloc[-1] em cada DataFrame, sem casar o mes) de fato NAO reconciliava",
          abs(spread_correto - spread_do_bug_antigo) > 1.0,
          f"spread correto={spread_correto:.1f}, spread do bug antigo={spread_do_bug_antigo:.1f}")

    tabela_vintage_teste = montar_tabela_vintage(df_ipia_reconc, df_custo_reconc)
    cutoff_valido = pd.Timestamp("2026-07-15")  # cobre o mes mais recente de QUALQUER variavel (df_custo vai ate julho)
    check("(b) validar_report_cutoff: nenhum problema quando reference_period <= cutoff",
          len(validar_report_cutoff(tabela_vintage_teste, cutoff_valido)) == 0,
          f"problemas={validar_report_cutoff(tabela_vintage_teste, cutoff_valido)}")

    cutoff_anterior = pd.Timestamp("2026-05-15")  # anterior ao mes de df_ipia (2026-06) -> look-ahead
    problemas_cutoff = validar_report_cutoff(tabela_vintage_teste, cutoff_anterior)
    check("(b) validar_report_cutoff: detecta reference_period posterior ao cutoff (look-ahead)",
          len(problemas_cutoff) > 0, f"problemas={problemas_cutoff}")

    # --- 22. selo visual nunca omite PROXY/ESTIMADO quando a classificacao
    # do motor indica isso (ver docs/adr/0008) - end-to-end: classificacao
    # real -> texto do selo, nao so testa o renderizador isolado ---------
    from reporting import components as rep_components2

    linha_proxy_teste = pd.Series(
        {"tipo_dado_domestico": "proxy_segmento_aco", "metodo_domestico": "nivel_trimestral"},
        name=pd.Timestamp("2026-06-01"))
    v_proxy = classificar_preco_domestico(linha_proxy_teste)
    check("(c) selo nunca omite PROXY quando tipo_dado_domestico e proxy_segmento_aco",
          "PROXY" in rep_components2.selo_dado_texto(v_proxy.nivel, v_proxy.proxy),
          f"selo='{rep_components2.selo_dado_texto(v_proxy.nivel, v_proxy.proxy)}'")

    linha_estimado_teste = pd.Series(
        {"tipo_dado_domestico": "especifico_laminado_quente", "metodo_domestico": "hold_flat_fallback"},
        name=pd.Timestamp("2026-07-01"))
    v_estimado = classificar_preco_domestico(linha_estimado_teste)
    check("(d) selo nunca omite ESTIMADO quando metodo_domestico e hold_flat_fallback",
          "ESTIMADO" in rep_components2.selo_dado_texto(v_estimado.nivel, v_estimado.proxy),
          f"selo='{rep_components2.selo_dado_texto(v_estimado.nivel, v_estimado.proxy)}'")

    linha_observado_teste = pd.Series({"tipo_dado_penetracao": "oficial_mensal"},
                                      name=pd.Timestamp("2026-07-01"))
    v_observado = classificar_penetracao(linha_observado_teste)
    check("selo fica vazio (sem aviso) para OBSERVADO puro sem proxy - caso normal nao precisa de selo",
          rep_components2.selo_dado_texto(v_observado.nivel, v_observado.proxy) == "")

    linha_formula_alt_teste = pd.Series({"tipo_dado_penetracao": "aproximado_consumo_aparente"},
                                        name=pd.Timestamp("2026-06-01"))
    v_formula_alt = classificar_penetracao(linha_formula_alt_teste)
    check("(d) formula_alternativa (aproximado_consumo_aparente) classifica como CALCULADO, nao ESTIMADO nem PROXY "
          "(nao ha interpolacao/encadeamento aqui, e o mesmo alvo conceitual do oficial - so formula diferente)",
          v_formula_alt.nivel == NIVEL_CALCULADO and not v_formula_alt.proxy
          and v_formula_alt.metodo == METODO_FORMULA_ALTERNATIVA,
          f"nivel={v_formula_alt.nivel}, proxy={v_formula_alt.proxy}, metodo={v_formula_alt.metodo}")

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
                     help="calcula o IPIA e gera relatorio PDF de 4 paginas em data/processed/ipia_relatorio.pdf")
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
        print(f"Gerando relatorio PDF do IPIA (4 paginas), {a.ano_ini}-{a.ano_fim} ...")
        # import local: reporting/ importa deste modulo (indices_setoriais.py
        # e so o motor de calculo, nunca importa reporting no nivel de modulo -
        # evita import circular, mesmo padrao ja usado para matplotlib/requests).
        from reporting.report_builder import gerar_relatorio_ipia
        import os
        os.makedirs("data/processed", exist_ok=True)
        caminho = "data/processed/ipia_relatorio.pdf"
        try:
            n_meses = gerar_relatorio_ipia(caminho, a.ano_ini, a.ano_fim)
        except ValueError as e:
            print(f"Nao foi possivel gerar o relatorio: {e}")
            sys.exit(1)
        print(f"Relatorio salvo em {caminho} ({n_meses} meses na serie)")
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
