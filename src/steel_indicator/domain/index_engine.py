"""Motor generico de indice: padronizacao, agregacao e diagnostico.

Extraido de src/indices_setoriais.py (Spec 0003, batch 1) sem alteracao de
comportamento. Nenhuma funcao aqui faz rede ou I/O de arquivo; tudo opera
sobre Series/DataFrame explicitamente recebidos.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

JANELA_REF = ("2013-01-01", "2019-12-31")   # janela de padronizacao CONGELADA
WINSOR_Z   = 3.0                            # corte de outlier, em desvios
ESCALA_A   = 50.0                           # ancora: 50 = media da janela de ref.
ESCALA_B   = 10.0                           # 1 desvio-padrao = 10 pontos
COBERTURA_MINIMA = 0.60                     # abaixo disso, nao publique o setor


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
