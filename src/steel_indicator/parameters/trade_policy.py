"""Historical Import Policy Model para IPIA-HRC: resolucao deterministica,
sem look-ahead, de II/TEC (por NCM), AFRMM e antidumping (por origem) para
qualquer data entre 2012-01 e o presente.

Decisao aprovada (Option C, Level 3): ver docs/adr/0009-*.md e
docs/research/hrc_import_policy_history.md.

  - publication-grade: 2022-04-01 em diante (todos os parametros conhecidos);
  - historical experimental: 2012-01-01 a 2022-03-31 (II individual de 9 dos
    13 NCMs de NCM_BOBINA_QUENTE nao comprovado - so uma faixa 10%-14% e
    conhecida);
  - 1997-2011: fora de escopo.

Este modulo NAO e conectado a calcular_ipia_mensal/ParamsIPIA ainda - isso e
um batch separado. Nao ha rede, arquivo ou banco aqui - apenas tabelas
literais com evidencia documentada e funcoes puras de lookup.

Nenhum valor e inventado: quando o parametro nao e conhecido para o
NCM/data pedido, o resolver retorna status UNKNOWN e aliquota/valor None -
nunca uma tarifa aproximada silenciosa.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

# =============================================================================
# Status de publicacao
# =============================================================================

STATUS_PUBLICATION_GRADE = "PUBLICATION_GRADE"
STATUS_EXPERIMENTAL = "EXPERIMENTAL"
STATUS_UNKNOWN = "UNKNOWN"
PUBLICATION_STATUSES = (STATUS_PUBLICATION_GRADE, STATUS_EXPERIMENTAL, STATUS_UNKNOWN)

PUBLICATION_GRADE_INICIO = pd.Timestamp("2022-04-01")  # ADR 0009


def _status_por_data(data: pd.Timestamp, valor_conhecido: bool) -> str:
    """O eixo PUBLICATION_GRADE/EXPERIMENTAL depende so da data (decisao
    Option C, ADR 0009) - nao da confianca da fonte que sustenta o valor
    dentro de cada trilha. UNKNOWN e reservado para "nao ha valor algum"."""
    if not valor_conhecido:
        return STATUS_UNKNOWN
    return STATUS_PUBLICATION_GRADE if data >= PUBLICATION_GRADE_INICIO else STATUS_EXPERIMENTAL


def _dentro_do_intervalo(data: pd.Timestamp, inicio: pd.Timestamp, fim: Optional[pd.Timestamp]) -> bool:
    return inicio <= data and (fim is None or data <= fim)


def status_efetivo(*statuses: str) -> str:
    """Combina os status de VARIOS parametros obrigatorios (ex.: II, AFRMM,
    antidumping) resolvidos para o MESMO NCM/data numa unica classificacao
    efetiva. `data >= 2022-04-01` define apenas a JANELA POTENCIAL
    publication-grade (ver ADR 0009) - nunca e suficiente sozinha: se
    QUALQUER parametro obrigatorio for UNKNOWN, o status efetivo e UNKNOWN,
    mesmo que os demais parametros estejam em PUBLICATION_GRADE. So retorna
    PUBLICATION_GRADE quando TODOS os parametros estiverem nesse status.
    """
    if not statuses:
        raise ValueError("status_efetivo() precisa de pelo menos um status - "
                          "lista vazia nunca deve virar PUBLICATION_GRADE por omissao")
    if any(s == STATUS_UNKNOWN for s in statuses):
        return STATUS_UNKNOWN
    if all(s == STATUS_PUBLICATION_GRADE for s in statuses):
        return STATUS_PUBLICATION_GRADE
    return STATUS_EXPERIMENTAL


# =============================================================================
# II / TEC
# =============================================================================

@dataclass
class FaixaAliquotaII:
    ncm: str
    valid_from: pd.Timestamp
    valid_to: Optional[pd.Timestamp]  # None = ainda vigente
    aliquota: float
    legal_basis: str


@dataclass
class JanelaCotaII:
    """Cota tarifaria temporaria (Res. GECEX 929/2026): dentro do
    sub-periodo, a aliquota EFETIVA depende de quanto da cota ja foi
    consumido - informacao que este modulo nao rastreia. resolver_ii()
    retorna UNKNOWN para datas dentro da janela, nunca escolhe
    silenciosamente dentro/fora da cota."""
    ncm: str
    sub_periodo_inicio: pd.Timestamp
    sub_periodo_fim: pd.Timestamp
    aliquota_dentro_cota: float
    aliquota_fora_cota: float
    legal_basis: str


@dataclass
class ResultadoII:
    ncm: str
    data: pd.Timestamp
    aliquota: Optional[float]
    status: str
    legal_basis: Optional[str]
    nota: Optional[str] = None


# 4 codigos confirmados individualmente (Res. CAMEX 94/2011, SECONDARY_REPRODUCTION,
# ver docs/research/hrc_import_policy_history.md secao 1.1) + regime atual
# (Res. GECEX 272/2021, DOC) para todos os 13.
_ALIQUOTA_2012_CONHECIDA = {
    "72083700": 0.12,
    "72083890": 0.12,
    "72083990": 0.12,
    "72083910": 0.10,  # excecao ja em 2012
}
# CORRIGIDO (sprint "Import Policy Evidence Hardening", VERIFIED): 72082610/
# 72082710/72083610/72083810 estavam em 0.108 - a planilha oficial
# consolidada (gov.br/mdic/camex, Anexo I e Anexo II - TEC) confirma 9%,
# mesma excecao "limite minimo de elasticidade 275/355 MPa" ja reconhecida
# para 72083910 (mesma posicao estrutural ".10" dentro de cada faixa de
# espessura). Ver docs/validation/hrc_import_policy_correction_migration.md.
_ALIQUOTA_2022_TODOS_OS_13 = {
    "72081000": 0.108, "72082500": 0.108, "72082610": 0.09, "72082690": 0.108,
    "72082710": 0.09, "72082790": 0.108, "72083610": 0.09, "72083690": 0.108,
    "72083700": 0.108, "72083810": 0.09, "72083890": 0.108, "72083990": 0.108,
    "72083910": 0.09,  # excecao mantida
}

_LEGAL_BASIS_2012 = "Res. CAMEX 94/2011, Anexo I (SECONDARY_REPRODUCTION)"
_LEGAL_BASIS_2022 = "Res. GECEX 272/2021, Anexo I"
_LEGAL_BASIS_2022_NAO_REVERIFICADO = "Res. GECEX 272/2021, Anexo I (nao reverificado individualmente)"
_LEGAL_BASIS_2022_CORRIGIDO = ("Res. GECEX 272/2021, Anexo I/II - planilha oficial consolidada "
                               "gov.br/mdic/camex (VERIFIED; corrige valor anterior de 10.8% para 9%)")

_NCMS_CORRIGIDOS_9PCT = ("72082610", "72082710", "72083610", "72083810")

_NCMS_COM_COTA_929_2026 = ("72083700", "72083890", "72083910", "72083990")
_SUBPERIODOS_COTA_929_2026 = (
    (pd.Timestamp("2026-06-26"), pd.Timestamp("2026-10-25")),
    (pd.Timestamp("2026-10-26"), pd.Timestamp("2027-02-25")),
    (pd.Timestamp("2027-02-26"), pd.Timestamp("2027-06-25")),
)

# NOVO (sprint "Import Policy Evidence Hardening", VERIFIED): elevacao
# tarifaria incondicional da Res. GECEX 865/2026 (Anexo IX-DCC) sobre
# 72082690/72082790 - CASE A (25% aplica-se a todo o volume durante a
# vigencia; confirmado ao vivo que a fonte oficial NAO lista colunas de
# Quota/Unidade quota para essas duas linhas, ao contrario da cota
# 929/2026 acima). Nunca misturar com o mecanismo de cota - resolucoes
# diferentes, mecanismos diferentes.
_NCMS_COM_ELEVACAO_865_2026 = ("72082690", "72082790")
_ELEVACAO_865_2026_INICIO = pd.Timestamp("2026-02-26")
_ELEVACAO_865_2026_FIM = pd.Timestamp("2027-02-25")
_ALIQUOTA_ELEVACAO_865_2026 = 0.25
_LEGAL_BASIS_865_2026 = ("Res. GECEX 865/2026, Anexo IX-DCC (elevacao tarifaria incondicional, sem "
                         "mecanismo de cota - VERIFIED)")


def _montar_tabela_ii() -> List[FaixaAliquotaII]:
    tabela: List[FaixaAliquotaII] = []
    for ncm, aliquota_2012 in _ALIQUOTA_2012_CONHECIDA.items():
        tabela.append(FaixaAliquotaII(ncm, pd.Timestamp("2012-01-01"), pd.Timestamp("2022-03-31"),
                                       aliquota_2012, _LEGAL_BASIS_2012))
    for ncm, aliquota_2022 in _ALIQUOTA_2022_TODOS_OS_13.items():
        if ncm in _ALIQUOTA_2012_CONHECIDA:
            base_legal = _LEGAL_BASIS_2022
        elif ncm in _NCMS_CORRIGIDOS_9PCT:
            base_legal = _LEGAL_BASIS_2022_CORRIGIDO
        else:
            base_legal = _LEGAL_BASIS_2022_NAO_REVERIFICADO

        if ncm in _NCMS_COM_COTA_929_2026:
            # a cota cobre 2026-06-26 a 2027-06-25; a aliquota normal vale
            # antes e depois dessa janela, nao durante.
            tabela.append(FaixaAliquotaII(ncm, pd.Timestamp("2022-04-01"), pd.Timestamp("2026-06-25"),
                                           aliquota_2022, base_legal))
            tabela.append(FaixaAliquotaII(ncm, pd.Timestamp("2027-06-26"), None,
                                           aliquota_2022, base_legal))
        elif ncm in _NCMS_COM_ELEVACAO_865_2026:
            # elevacao incondicional (Case A): aliquota normal antes/depois,
            # 25% durante a vigencia da Res. 865/2026 - nunca UNKNOWN aqui,
            # ao contrario da cota 929/2026 (nao ha ambiguidade de fluxo).
            tabela.append(FaixaAliquotaII(ncm, pd.Timestamp("2022-04-01"),
                                           _ELEVACAO_865_2026_INICIO - pd.Timedelta(days=1),
                                           aliquota_2022, base_legal))
            tabela.append(FaixaAliquotaII(ncm, _ELEVACAO_865_2026_INICIO, _ELEVACAO_865_2026_FIM,
                                           _ALIQUOTA_ELEVACAO_865_2026, _LEGAL_BASIS_865_2026))
            tabela.append(FaixaAliquotaII(ncm, _ELEVACAO_865_2026_FIM + pd.Timedelta(days=1), None,
                                           aliquota_2022, base_legal))
        else:
            tabela.append(FaixaAliquotaII(ncm, pd.Timestamp("2022-04-01"), None, aliquota_2022, base_legal))
    return tabela


def _montar_janelas_cota() -> List[JanelaCotaII]:
    janelas: List[JanelaCotaII] = []
    for ncm in _NCMS_COM_COTA_929_2026:
        aliquota_dentro = _ALIQUOTA_2022_TODOS_OS_13[ncm]
        for inicio, fim in _SUBPERIODOS_COTA_929_2026:
            janelas.append(JanelaCotaII(ncm, inicio, fim, aliquota_dentro, 0.25, "Res. GECEX 929/2026"))
    return janelas


_TABELA_II = _montar_tabela_ii()
_JANELAS_COTA = _montar_janelas_cota()


def resolver_ii(ncm: str, data: pd.Timestamp) -> ResultadoII:
    """Resolve a aliquota de II vigente para `ncm` em `data`.

    Retorna status UNKNOWN (aliquota=None) quando: (a) o NCM nao tem valor
    comprovado para essa data (os 9 NCMs nao confirmados, 2012-2022-03), ou
    (b) a data cai numa janela de cota tarifaria cuja aliquota efetiva
    depende de consumo de cota nao rastreado - nos dois casos, nenhuma
    tarifa e escolhida silenciosamente.
    """
    for j in _JANELAS_COTA:
        if j.ncm == ncm and _dentro_do_intervalo(data, j.sub_periodo_inicio, j.sub_periodo_fim):
            return ResultadoII(
                ncm=ncm, data=data, aliquota=None, status=STATUS_UNKNOWN, legal_basis=j.legal_basis,
                nota=(f"cota tarifaria vigente (dentro da cota={j.aliquota_dentro_cota:.1%}, "
                      f"fora da cota={j.aliquota_fora_cota:.1%}); consumo da cota nao rastreado por este modulo"))

    candidatas = [f for f in _TABELA_II if f.ncm == ncm and _dentro_do_intervalo(data, f.valid_from, f.valid_to)]
    if not candidatas:
        return ResultadoII(ncm=ncm, data=data, aliquota=None, status=STATUS_UNKNOWN, legal_basis=None,
                            nota="II nao comprovado para este NCM/periodo - ver docs/research/hrc_import_policy_history.md")
    faixa = candidatas[0]
    return ResultadoII(ncm=ncm, data=data, aliquota=faixa.aliquota,
                        status=_status_por_data(data, valor_conhecido=True), legal_basis=faixa.legal_basis)


# =============================================================================
# AFRMM
# =============================================================================

@dataclass
class FaixaAFRMM:
    valid_from: pd.Timestamp
    valid_to: Optional[pd.Timestamp]
    aliquota: float
    legal_basis: str


@dataclass
class ResultadoAFRMM:
    data: pd.Timestamp
    aliquota: Optional[float]
    status: str
    legal_basis: Optional[str]


_TABELA_AFRMM = [
    FaixaAFRMM(pd.Timestamp("2012-01-01"), pd.Timestamp("2022-03-24"), 0.25,
               "Lei 10.893/2004, Art. 6 I (redacao original)"),
    FaixaAFRMM(pd.Timestamp("2022-03-25"), None, 0.08,
               "Lei 14.301/2022, Art. 6 I; STF Tema 1368 / ARE 1.527.985 (2023 integral)"),
]


def resolver_afrmm(data: pd.Timestamp) -> ResultadoAFRMM:
    """Resolve a aliquota de AFRMM (navegacao de longo curso) vigente em `data`."""
    for f in _TABELA_AFRMM:
        if _dentro_do_intervalo(data, f.valid_from, f.valid_to):
            return ResultadoAFRMM(data=data, aliquota=f.aliquota,
                                   status=_status_por_data(data, valor_conhecido=True), legal_basis=f.legal_basis)
    return ResultadoAFRMM(data=data, aliquota=None, status=STATUS_UNKNOWN, legal_basis=None)


# =============================================================================
# Antidumping
# =============================================================================

@dataclass
class MedidaAntidumping:
    origin: str
    exporter: Optional[str]  # None = valor residual ("demais") ou investigacao sem produtor definido
    valid_from: pd.Timestamp
    valid_to: Optional[pd.Timestamp]
    nominal_value: Optional[float]  # US$/t; None quando ha so determinacao preliminar sem direito provisorio
    unit: str
    suspended: bool
    legal_basis: str


@dataclass
class ResultadoAntidumping:
    origin: str
    exporter: Optional[str]
    data: pd.Timestamp
    nominal_value: Optional[float]
    unit: Optional[str]
    suspended: bool
    effective_value: float
    status: str
    legal_basis: Optional[str]
    nota: Optional[str] = None


_MEDIDAS_ANTIDUMPING: List[MedidaAntidumping] = [
    MedidaAntidumping("China", "Maanshan Iron & Steel Company Ltd.", pd.Timestamp("2018-01-19"),
                       pd.Timestamp("2020-01-17"), 154.68, "US$/t", True,
                       "Res. CAMEX 2/2018; Res. CAMEX 97/2018; Res. GECEX 5/2020 (extincao)"),
    MedidaAntidumping("China", "Bengang Steel Plates Co. Ltd", pd.Timestamp("2018-01-19"),
                       pd.Timestamp("2020-01-17"), 44.08, "US$/t", True,
                       "Res. CAMEX 2/2018; Res. CAMEX 97/2018; Res. GECEX 5/2020 (extincao)"),
    MedidaAntidumping("China", "Baoshan Iron & Steel Co., Ltd", pd.Timestamp("2018-01-19"),
                       pd.Timestamp("2020-01-17"), 77.72, "US$/t", True,
                       "Res. CAMEX 2/2018; Res. CAMEX 97/2018; Res. GECEX 5/2020 (extincao)"),
    MedidaAntidumping("China", None, pd.Timestamp("2018-01-19"),
                       pd.Timestamp("2020-01-17"), 226.58, "US$/t", True,
                       "Res. CAMEX 2/2018 (residual 'demais'); Res. GECEX 5/2020 (extincao)"),
    MedidaAntidumping("Rússia", "JSC Severstal", pd.Timestamp("2018-01-19"),
                       pd.Timestamp("2020-01-17"), 118.50, "US$/t", True,
                       "Res. CAMEX 2/2018; Res. GECEX 5/2020 (extincao)"),
    MedidaAntidumping("Rússia", None, pd.Timestamp("2018-01-19"),
                       pd.Timestamp("2020-01-17"), 207.43, "US$/t", True,
                       "Res. CAMEX 2/2018 (residual 'demais'); Res. GECEX 5/2020 (extincao)"),
    MedidaAntidumping("China", None, pd.Timestamp("2025-06-03"), None, None, "US$/t", False,
                       "Circular SECEX 39/2025 (abertura); Parecer 1800/2025/MDIC (determinacao "
                       "preliminar positiva, sem direito provisorio); Circular SECEX 100/2025 (prorrogacao)"),
]


def resolver_antidumping(origin: str, data: pd.Timestamp, exporter: Optional[str] = None) -> ResultadoAntidumping:
    """Resolve o direito antidumping para `origin`/`data` (e opcionalmente
    `exporter`). Distingue nominal_value (o que a medida calcula no papel)
    de effective_value (o que efetivamente incide - zero quando suspenso
    ou quando so ha investigacao sem direito provisorio aplicado)."""
    candidatas = [m for m in _MEDIDAS_ANTIDUMPING
                  if m.origin == origin and _dentro_do_intervalo(data, m.valid_from, m.valid_to)]
    if exporter is not None:
        especificas = [m for m in candidatas if m.exporter == exporter]
        candidatas = especificas if especificas else [m for m in candidatas if m.exporter is None]
    else:
        # sem exportador especifico, usa a taxa residual ("demais") quando
        # existir - nunca escolhe arbitrariamente entre produtores nomeados.
        residuais = [m for m in candidatas if m.exporter is None]
        candidatas = residuais if residuais else candidatas

    if not candidatas:
        return ResultadoAntidumping(origin=origin, exporter=exporter, data=data, nominal_value=None, unit=None,
                                     suspended=False, effective_value=0.0,
                                     status=_status_por_data(data, valor_conhecido=True), legal_basis=None,
                                     nota="nenhuma medida antidumping vigente para esta origem/periodo")

    m = candidatas[0]
    efetivo = 0.0 if (m.suspended or m.nominal_value is None) else m.nominal_value
    nota = None
    if m.suspended:
        nota = "direito calculado mas suspenso por interesse publico - custo efetivo zero"
    elif m.nominal_value is None:
        nota = "investigacao em andamento, sem direito provisorio aplicado - custo efetivo zero"
    return ResultadoAntidumping(origin=origin, exporter=exporter, data=data, nominal_value=m.nominal_value,
                                 unit=m.unit, suspended=m.suspended, effective_value=efetivo,
                                 status=_status_por_data(data, valor_conhecido=True), legal_basis=m.legal_basis,
                                 nota=nota)
