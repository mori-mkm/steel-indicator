"""Unit test for `decompor_mes()` (scripts/validar_ipia_hrc_v2_final.py,
Stage G3): reconstrucao volume-weighted EXATA dos componentes de custo de
importacao (FOB/frete/seguro/cambio/II/AFRMM/AD/porto/frete interno/margem)
a partir das linhas granulares (mes x NCM x pais) de
`custo_importacao_bottom_up_mensal`.

Deterministic, no network - grupos sinteticos injetados direto. Prova duas
propriedades que motivaram correcoes reais durante a validacao G3:

1. quando NCMs diferentes tem aliquota de II DIFERENTE dentro do mesmo mes,
   a soma dos componentes reconstruidos (CIF+II+AFRMM+AD+custos fixos) -
   SEM margem desde a metodologia 1.5/ADR 0015, ver docstring de
   `_ppi_cost_brl_t` - precisa bater EXATAMENTE (nao aproximadamente) com
   o PPI_COST que `custo_importacao_bottom_up_mensal` ja calcula via
   volume-weighted average do `ppi_cost_brl_t` pronto por grupo (ate a
   1.4, esta coluna se chamava `ppi_brl_t` e incluia a margem) - a
   primeira versao deste helper ponderava a ALIQUOTA (nao o valor
   monetario) e divergia em ~0.01-0.04% exatamente nesse cenario;

2. elegibilidade (EXPERIMENTAL/PUBLICATION_GRADE/UNKNOWN) e delegada
   INTEIRAMENTE ao `import_status` ja calculado pelo motor de producao
   (`agregar_ipia_hrc_multi_ncm_mensal`, ja testado em
   tests/unit/test_ipia_hrc_v2_multi_ncm.py) - `decompor_mes()` nunca
   re-deriva limiares de cobertura/incerteza. A primeira versao deste
   helper reimplementava so o limiar de cobertura (60%) e esquecia o
   limiar de incerteza (2%) do regime EXPERIMENTAL, divergindo em
   silencio da regra oficial (achado do code review desta stage).
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import indices_setoriais as m  # noqa: E402  (garante que 'src' esta no sys.path antes do script)

_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "validar_ipia_hrc_v2_final.py")
_spec = importlib.util.spec_from_file_location("validar_ipia_hrc_v2_final", _SCRIPT_PATH)
_validar = importlib.util.module_from_spec(_spec)
sys.modules["validar_ipia_hrc_v2_final"] = _validar
_spec.loader.exec_module(_validar)  # so define funcoes/constantes - o bloco __main__ nao roda ao importar
decompor_mes = _validar.decompor_mes

STATUS_EXPERIMENTAL = "EXPERIMENTAL"
STATUS_PUBLICATION_GRADE = "PUBLICATION_GRADE"
STATUS_UNKNOWN = "UNKNOWN"


def _grupos_sinteticos(data, linhas):
    """`linhas`: lista de dicts com fob_usd, frete_usd, seguro_usd, kg,
    cambio_mes, aliquota_ii, aliquota_afrmm, antidumping_usd_t, status -
    calcula cif_usd_t/cif_brl_t/frete_usd_t/ppi_cost_brl_t exatamente como
    `custo_importacao_bottom_up_mensal` faria, para nao duplicar logica
    de producao dentro do fixture de teste. `ppi_cost_brl_t` (metodologia
    1.5/ADR 0015) e SEM margem comercial - ate a 1.4 esta coluna se
    chamava `ppi_brl_t` e incluia a margem."""
    p = m.ParamsIPIA()
    linhas_completas = []
    for linha in linhas:
        l = dict(linha)
        l["data"] = data
        l["frete_usd_t"] = 1000 * l["frete_usd"] / l["kg"]
        l["cif_usd_t"] = 1000 * (l["fob_usd"] + l["frete_usd"] + l["seguro_usd"]) / l["kg"]
        l["cif_brl_t"] = l["cif_usd_t"] * l["cambio_mes"]
        l["ppi_cost_brl_t"] = m._ppi_cost_brl_t(l["cif_brl_t"], l["aliquota_ii"], l["frete_usd_t"], l["cambio_mes"],
                                                 l["aliquota_afrmm"], l["antidumping_usd_t"], p)
        linhas_completas.append(l)
    return pd.DataFrame(linhas_completas)


def test_reconstrucao_exata_com_aliquotas_de_ii_heterogeneas_entre_ncms():
    # dois grupos NCM com aliquota de II DIFERENTE (10% e 14%) e volumes
    # diferentes - o cenario exato que expunha o bug de ponderar a taxa em
    # vez do valor monetario.
    data = pd.Timestamp("2024-06-01")
    grupos = _grupos_sinteticos(data, [
        dict(coNcm="72083700", country="China", fob_usd=500_000.0, frete_usd=40_000.0, seguro_usd=1_000.0,
            kg=100_000.0, cambio_mes=5.0, aliquota_ii=0.10, aliquota_afrmm=0.08, antidumping_usd_t=0.0,
            status=STATUS_PUBLICATION_GRADE),
        dict(coNcm="72083910", country="Coreia do Sul", fob_usd=300_000.0, frete_usd=25_000.0, seguro_usd=600.0,
            kg=50_000.0, cambio_mes=5.0, aliquota_ii=0.14, aliquota_afrmm=0.08, antidumping_usd_t=0.0,
            status=STATUS_PUBLICATION_GRADE),
    ])
    dec = decompor_mes(grupos, data, m.ParamsIPIA(), STATUS_PUBLICATION_GRADE)
    assert dec is not None
    ppi_cost_esperado = float(np.average(grupos["ppi_cost_brl_t"], weights=grupos["kg"]))
    assert dec["ppi_cost_reconstruido"] == pytest.approx(ppi_cost_esperado, abs=1e-9)
    assert dec["ppi_cost_via_motor"] == pytest.approx(ppi_cost_esperado, abs=1e-9)
    # a soma dos componentes precisa bater EXATAMENTE com o PPI_COST (identidade
    # contabil) - SEM margem (metodologia 1.5/ADR 0015): ate a 1.4 esta soma
    # precisava ser multiplicada por (1+margem) para bater com o PPI oficial.
    soma_componentes = (dec["cif_brl_t"] + dec["ii_brl_t"] + dec["afrmm_brl_t"] + dec["ad_brl_t"]
                        + dec["despesas_porto_rs_t"] + dec["frete_interno_rs_t"])
    assert soma_componentes == pytest.approx(ppi_cost_esperado, abs=1e-9)

    # PPI_OFFER (camada analitica) reproduz exatamente o comportamento
    # PRE-1.5 (PPI_COST * (1 + margem)) - nunca usado para reconstruir o
    # PPI oficial, mas precisa continuar disponivel para compatibilidade/
    # cenarios (Sec.6/22 da decisao aprovada).
    margem = m.ParamsIPIA().margem_importador
    assert dec["ppi_offer_reconstruido"] == pytest.approx(ppi_cost_esperado * (1 + margem), abs=1e-9)
    assert m.calcular_ppi_offer(dec["ppi_cost_reconstruido"], margem) == pytest.approx(
        dec["ppi_offer_reconstruido"], abs=1e-9)


def test_import_status_unknown_devolve_none_mesmo_com_grupos_presentes():
    # elegibilidade e SO o import_status ja calculado pelo motor - um mes
    # UNKNOWN nunca produz um ponto de custo, mesmo que `grupos` tenha
    # linhas com aparencia valida para aquele mes (nunca re-deriva a
    # regra de cobertura/incerteza aqui, delega 100% ao motor).
    data = pd.Timestamp("2024-06-01")
    grupos = _grupos_sinteticos(data, [
        dict(coNcm="72083700", country="China", fob_usd=500_000.0, frete_usd=40_000.0, seguro_usd=1_000.0,
            kg=100_000.0, cambio_mes=5.0, aliquota_ii=0.10, aliquota_afrmm=0.08, antidumping_usd_t=0.0,
            status=STATUS_PUBLICATION_GRADE),
    ])
    assert decompor_mes(grupos, data, m.ParamsIPIA(), STATUS_UNKNOWN) is None


def test_mes_ausente_do_grupo_devolve_none():
    grupos = _grupos_sinteticos(pd.Timestamp("2024-06-01"), [
        dict(coNcm="72083700", country="China", fob_usd=500_000.0, frete_usd=40_000.0, seguro_usd=1_000.0,
            kg=100_000.0, cambio_mes=5.0, aliquota_ii=0.10, aliquota_afrmm=0.08, antidumping_usd_t=0.0,
            status=STATUS_PUBLICATION_GRADE),
    ])
    assert decompor_mes(grupos, pd.Timestamp("2024-07-01"), m.ParamsIPIA(), STATUS_PUBLICATION_GRADE) is None


def test_mes_experimental_usa_so_grupos_com_status_de_grupo_conhecido():
    # import_status="EXPERIMENTAL" (ja decidido pelo motor, ja atende
    # coverage>=60% e uncertainty<=2% la) -> decompor_mes usa so os
    # GRUPOS individuais com status conhecido (peso redistribuido entre
    # eles), mesma regra de `agregar_ipia_hrc_multi_ncm_mensal`.
    data = pd.Timestamp("2020-06-01")
    grupos = _grupos_sinteticos(data, [
        dict(coNcm="72083700", country="China", fob_usd=500_000.0, frete_usd=40_000.0, seguro_usd=1_000.0,
            kg=80_000.0, cambio_mes=5.0, aliquota_ii=0.12, aliquota_afrmm=0.25, antidumping_usd_t=0.0,
            status=STATUS_EXPERIMENTAL),
        dict(coNcm="72081000", country="India", fob_usd=100_000.0, frete_usd=8_000.0, seguro_usd=200.0,
            kg=20_000.0, cambio_mes=5.0, aliquota_ii=np.nan, aliquota_afrmm=0.25, antidumping_usd_t=0.0,
            status=STATUS_UNKNOWN),
    ])
    dec = decompor_mes(grupos, data, m.ParamsIPIA(), STATUS_EXPERIMENTAL)
    assert dec is not None
    assert dec["n_grupos_usados"] == 1  # so o grupo conhecido (China) entra no ponto estimado
    conhecido = grupos[grupos["status"] == STATUS_EXPERIMENTAL]
    ppi_cost_esperado = float(np.average(conhecido["ppi_cost_brl_t"], weights=conhecido["kg"]))
    assert dec["ppi_cost_via_motor"] == pytest.approx(ppi_cost_esperado, abs=1e-9)


def test_nao_reimplementa_limiar_de_cobertura_ou_incerteza():
    # documenta o contrato pos-code-review: decompor_mes NUNCA decide
    # elegibilidade sozinho a partir de coverage/uncertainty - confia
    # inteiramente no import_status do chamador. Um mes com coverage
    # BEM abaixo do limiar de producao (60%) ainda produz um ponto aqui
    # se o chamador afirmar EXPERIMENTAL - a responsabilidade de nunca
    # fazer isso incorretamente e do motor de producao (ja testado), nao
    # deste helper de validacao.
    data = pd.Timestamp("2020-06-01")
    grupos = _grupos_sinteticos(data, [
        dict(coNcm="72083700", country="China", fob_usd=500_000.0, frete_usd=40_000.0, seguro_usd=1_000.0,
            kg=10_000.0, cambio_mes=5.0, aliquota_ii=0.12, aliquota_afrmm=0.25, antidumping_usd_t=0.0,
            status=STATUS_EXPERIMENTAL),
        dict(coNcm="72081000", country="India", fob_usd=900_000.0, frete_usd=70_000.0, seguro_usd=1_800.0,
            kg=90_000.0, cambio_mes=5.0, aliquota_ii=np.nan, aliquota_afrmm=0.25, antidumping_usd_t=0.0,
            status=STATUS_UNKNOWN),
    ])
    # coverage real = 10_000 / 100_000 = 10%, bem abaixo dos 60% exigidos
    # pela regra oficial - decompor_mes ainda calcula, pois confia no
    # import_status informado (aqui deliberadamente "errado" so para
    # provar que nao ha logica propria de gate).
    dec = decompor_mes(grupos, data, m.ParamsIPIA(), STATUS_EXPERIMENTAL)
    assert dec is not None
    assert dec["coverage"] == pytest.approx(0.10)
