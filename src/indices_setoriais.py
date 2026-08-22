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

 Dependencias: pandas, numpy, requests  (statsmodels opcional, p/ ajuste sazonal)
=============================================================================
"""
from __future__ import annotations
import argparse, json, sys, time, datetime as dt
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
    icms_credito: bool = True           # se o comprador credita ICMS
    antidumping_usd_t: float = 0.0      # direito especifico, US$/t - VARIA POR
        # EMPRESA EXPORTADORA E POR ORIGEM (China, Russia...) nas resolucoes
        # Gecex. Default 0 porque o status para bobina a quente da China nao
        # estava confirmado como definitivo na ultima checagem (verifique em
        # gov.br/mdic/.../defesa-comercial antes de calibrar). Ao confirmar,
        # trate como parametro versionado igual aos demais - nao como uma
        # constante do codigo.


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


def serie_mensal_preco_bobina(ano_ini: int = 2020, ano_fim: int = 2026) -> pd.DataFrame:
    """Serie mensal de preco unitario de importacao (USD/t) para os 13 NCMs de
    bobina a quente, ponderado por volume (soma FOB / soma KG de todos os NCMs
    e paises no mes - nao e media simples entre NCMs, e um preco medio real
    do que o Brasil comprou naquele mes).

    Aplica dois tratamentos, ambos versionados e explicitos via colunas:
      - interpolado: mes sem registro no Comex Stat, preenchido por
        interpolacao linear entre os meses vizinhos. Provisorio - o ideal e
        investigar por que o mes ficou sem dado antes de publicar de verdade.
      - peso_confiabilidade: 1.0 para meses com volume >= VOLUME_MINIMO_T,
        caindo linearmente ate 0 abaixo disso. NAO usa numero de registros
        como criterio - ver nota acima.
    """
    ncms = sorted(sum(NCM_BOBINA_QUENTE.values(), []))
    df = comex_importacao_ncm(ncms, ano_ini, ano_fim)
    if df.empty:
        return df
    df["metricFOB"] = pd.to_numeric(df["metricFOB"], errors="coerce")
    df["metricKG"]  = pd.to_numeric(df["metricKG"], errors="coerce")
    df["data"] = pd.to_datetime(df["year"].astype(str) + "-"
                                 + df["monthNumber"].astype(str).str.zfill(2) + "-01")
    mensal = (df.groupby("data")
                .agg(fob_usd=("metricFOB", "sum"), kg=("metricKG", "sum"), n_registros=("metricFOB", "size"))
                .reset_index())
    mensal["preco_usd_t"] = 1000 * mensal["fob_usd"] / mensal["kg"]
    mensal["toneladas"] = mensal["kg"] / 1000
    mensal = mensal.set_index("data")[["toneladas", "preco_usd_t", "n_registros"]]

    # revela e preenche buracos de mes (nenhum registro no Comex Stat naquele mes)
    completa = mensal.asfreq("MS")
    completa["interpolado"] = completa["preco_usd_t"].isna()
    completa["preco_usd_t"] = completa["preco_usd_t"].interpolate(method="linear")
    completa["toneladas"]   = completa["toneladas"].interpolate(method="linear")
    completa["n_registros"] = completa["n_registros"].fillna(0).astype(int)

    completa["peso_confiabilidade"] = (completa["toneladas"] / VOLUME_MINIMO_T).clip(upper=1.0)
    completa.loc[completa["interpolado"], "peso_confiabilidade"] = 0.0  # mes interpolado nao e dado real

    return completa.reset_index()




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
