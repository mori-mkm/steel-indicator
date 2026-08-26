"""Unit tests for Domestic Price V2 do IPIA-HRC (Stage E8): ancora trimestral
por soma(receita)/soma(volume) entre empresas qualificadas, encadeada mes a
mes pelo IPP 242-Siderurgia. Deterministic, no network: CSV e escrito num
arquivo temporario, `ipp_mensal`/`df_trimestral` sao injetados direto (mesmo
padrao ja usado pelo resto do modulo).

Prova: preco implicito = receita/volume; agregacao entre empresas e
soma(receita)/soma(volume), nunca media simples de precos; empresa com
receita/volume incompativel e rejeitada, nunca redistribuida em silencio;
Gerdau so entra quando comprovada compatibilidade (via `tipo` qualificado);
encadeamento mensal reaproveita `encadear_preco_domestico_mensal` (legado)
sem alteracao; nova ancora redefine o nivel; sem look-ahead; provenance
OBSERVADO/CALCULADO/ESTIMADO e PROXY (flag ortogonal); legado inalterado;
ancora ausente (trimestre sem empresa qualificada) nunca e preenchida.
"""
import os
import tempfile

import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.domain.provenance import NIVEL_CALCULADO, NIVEL_ESTIMADO


def _ancora_df(trimestres, precos, tipo="proxy_segmento_aco", companies="USIM5,CSNA3"):
    """Fixture de ancora ja pronta (mesmo schema que `ancora_domestica_
    ponderada_v2` produz) para injetar direto em `preco_domestico_hrc_
    mensal_v2(df_trimestral=...)` sem precisar de um CSV de verdade."""
    n = len(trimestres)
    return pd.DataFrame({
        "trimestre": trimestres, "preco_rs_t": precos,
        "receita_total_rs": [p * 1_000_000.0 for p in precos],
        "volume_total_t": [1_000_000.0] * n,
        "tipo": [tipo] * n, "companies_used": [companies] * n,
        "quantidade_empresas": [2] * n,
    })


def _csv_tmp(linhas_csv: str) -> str:
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
        f.write(linhas_csv)
    return tmp_path


HEADER = "trimestre,empresa,receita_liquida_segmento_rs,volume_vendas_t,preco_rs_t,tipo,fonte\n"


# --- 1. Preco implicito de uma empresa: receita / volume --------------------

def test_receita_e_volume_ambos_informados_e_mutuamente_inconsistentes_usa_receita():
    # linha com preco_rs_t E receita_liquida_segmento_rs informados, e
    # inconsistentes entre si (preco*volume != receita) - nenhuma linha real
    # do CSV curado faz isso hoje, mas o comportamento precisa ser explicito:
    # receita_efetiva_rs prefere a receita DADA pela fonte, nunca a
    # reconstrucao via preco*volume, quando ambas existem.
    csv = HEADER + "2026Q1,USIM5,4700000000,1000000,5000,proxy_segmento_aco,teste\n"
    path = _csv_tmp(csv)
    try:
        df = m.carregar_preco_domestico_trimestral_v2(path)
        assert df.iloc[0]["receita_efetiva_rs"] == pytest.approx(4700_000_000.0)  # a receita dada, nao 5000*1e6
        assert df.iloc[0]["preco_rs_t"] == pytest.approx(5000.0)  # preco dado tambem preservado, sem sobrescrever
    finally:
        os.remove(path)


def test_preco_implicito_empresa_receita_sobre_volume():
    csv = HEADER + "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
    path = _csv_tmp(csv)
    try:
        df = m.carregar_preco_domestico_trimestral_v2(path)
        assert df.iloc[0]["preco_rs_t"] == pytest.approx(4700.0)
        assert df.iloc[0]["receita_efetiva_rs"] == pytest.approx(4700_000_000.0)
    finally:
        os.remove(path)


# --- 2. Duas empresas: soma(receita) / soma(volume) -------------------------

def test_duas_empresas_soma_receita_sobre_soma_volume():
    csv = HEADER + (
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,CSNA3,,500000,5000,proxy_segmento_aco,teste\n"
    )
    path = _csv_tmp(csv)
    try:
        df = m.carregar_preco_domestico_trimestral_v2(path)
        ancora = m.ancora_domestica_ponderada_v2(df)
        esperado = (4700_000_000.0 + 5000.0 * 500_000.0) / (1_000_000.0 + 500_000.0)
        assert ancora.iloc[0]["preco_rs_t"] == pytest.approx(esperado)
        assert ancora.iloc[0]["receita_total_rs"] == pytest.approx(4700_000_000.0 + 2_500_000_000.0)
        assert ancora.iloc[0]["volume_total_t"] == pytest.approx(1_500_000.0)
        assert ancora.iloc[0]["quantidade_empresas"] == 2
    finally:
        os.remove(path)


# --- 3. Prova de que NAO e media simples dos precos -------------------------

def test_agregacao_nao_e_media_simples_dos_precos():
    # precos individuais: USIM5=4700, CSNA3=5000 -> media simples = 4850.
    # sum/sum ponderado por volume (1000000 vs 500000) puxa para perto de 4700.
    csv = HEADER + (
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,CSNA3,,500000,5000,proxy_segmento_aco,teste\n"
    )
    path = _csv_tmp(csv)
    try:
        df = m.carregar_preco_domestico_trimestral_v2(path)
        ancora = m.ancora_domestica_ponderada_v2(df)
        media_simples = (4700.0 + 5000.0) / 2.0
        assert ancora.iloc[0]["preco_rs_t"] != pytest.approx(media_simples)
        assert ancora.iloc[0]["preco_rs_t"] < media_simples  # puxado pro lado do maior volume (USIM5)
    finally:
        os.remove(path)


# --- 4. Empresa com receita/volume incompativel: rejeitada ------------------

def test_empresa_incompativel_e_rejeitada_sem_redistribuir():
    csv = HEADER + (
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,CSNA3,,500000,5000,proxy_segmento_aco,teste\n"
        "2026Q1,GGBR4,9000000000,100000,,incompativel_receita_volume,receita da companhia inteira sobre volume so de HRC\n"
    )
    path = _csv_tmp(csv)
    try:
        df = m.carregar_preco_domestico_trimestral_v2(path)
        assert bool(df.loc[df["empresa"] == "GGBR4", "qualificado"].iloc[0]) is False
        ancora = m.ancora_domestica_ponderada_v2(df)
        esperado_sem_gerdau = (4700_000_000.0 + 5000.0 * 500_000.0) / (1_000_000.0 + 500_000.0)
        assert ancora.iloc[0]["preco_rs_t"] == pytest.approx(esperado_sem_gerdau)
        assert "GGBR4" not in ancora.iloc[0]["companies_used"]
        assert ancora.iloc[0]["quantidade_empresas"] == 2
    finally:
        os.remove(path)


# --- 5. Gerdau so entra quando compatibilidade for comprovada ---------------

def test_gerdau_so_entra_quando_tipo_qualificado():
    # Cenario A: Gerdau com tipo incompativel (situacao real hoje - Gerdau
    # Brasil so reporta aco longo, nao HRC) -> excluida.
    csv_incompativel = HEADER + (
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,GGBR4,9000000000,100000,,incompativel_receita_volume,teste\n"
    )
    path = _csv_tmp(csv_incompativel)
    try:
        ancora = m.ancora_domestica_ponderada_v2(m.carregar_preco_domestico_trimestral_v2(path))
        assert ancora.iloc[0]["quantidade_empresas"] == 1
        assert "GGBR4" not in ancora.iloc[0]["companies_used"]
    finally:
        os.remove(path)

    # Cenario B (hipotetico): SE um dia existir uma fonte comprovadamente
    # compativel (tipo qualificado), Gerdau passa a ser incluida
    # automaticamente - nao ha allowlist de nomes de empresa no codigo.
    csv_compativel = HEADER + (
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,GGBR4,470000000,100000,,proxy_segmento_aco,teste\n"
    )
    path2 = _csv_tmp(csv_compativel)
    try:
        ancora2 = m.ancora_domestica_ponderada_v2(m.carregar_preco_domestico_trimestral_v2(path2))
        assert ancora2.iloc[0]["quantidade_empresas"] == 2
        assert "GGBR4" in ancora2.iloc[0]["companies_used"]
    finally:
        os.remove(path2)


# --- 6. Encadeamento mensal pelo IPP -----------------------------------------

def test_encadeamento_mensal_pelo_ipp_242_siderurgia():
    ancora = _ancora_df(["2026Q1"], [4800.0])
    ipp = pd.Series({pd.Timestamp("2026-03-01"): 100.0, pd.Timestamp("2026-04-01"): 103.0})
    mensal = m.preco_domestico_hrc_mensal_v2(df_trimestral=ancora, ipp_mensal=ipp)
    linha_abr = mensal.set_index("reference_period").loc["2026-04-01"]
    assert linha_abr["preco_domestico_rs_t"] == pytest.approx(4800.0 * (103.0 / 100.0))
    assert linha_abr["ipp_series_id"] == m.IPP_SIDERURGIA_SERIES_ID
    assert linha_abr["provenance_level"] == NIVEL_ESTIMADO


# --- 7. Nova ancora trimestral redefine o nivel corretamente -----------------

def test_nova_ancora_trimestral_redefine_nivel():
    ancora = _ancora_df(["2026Q1", "2026Q2"], [4800.0, 5200.0])
    ipp = pd.Series({pd.Timestamp("2026-03-01"): 100.0, pd.Timestamp("2026-06-01"): 110.0})
    mensal = m.preco_domestico_hrc_mensal_v2(df_trimestral=ancora, ipp_mensal=ipp).set_index("reference_period")
    assert mensal.loc["2026-04-01", "preco_domestico_rs_t"] == pytest.approx(5200.0)  # nivel direto, nao encadeado
    assert mensal.loc["2026-04-01", "anchor_reference_period"] == "2026Q2"
    assert mensal.loc["2026-03-01", "anchor_reference_period"] == "2026Q1"


# --- 8. Ausencia de look-ahead -----------------------------------------------

def test_sem_look_ahead_trimestre_futuro_nao_contamina_passado():
    # marco/2026 esta DENTRO do Q1 - adicionar o Q2 (futuro em relacao a
    # marco) nao pode mudar o numero de marco. Abril esta DENTRO do Q2, entao
    # usar o Q2 para abril nao e look-ahead (e o proprio trimestre de abril),
    # so a ausencia de contaminacao do PASSADO (marco) que prova a garantia.
    ancora_so_q1 = _ancora_df(["2026Q1"], [4800.0])
    ancora_q1_e_q2 = _ancora_df(["2026Q1", "2026Q2"], [4800.0, 9999.0])
    ipp = pd.Series({pd.Timestamp("2026-02-01"): 99.0, pd.Timestamp("2026-03-01"): 100.0})
    so_q1 = m.preco_domestico_hrc_mensal_v2(df_trimestral=ancora_so_q1, ipp_mensal=ipp).set_index("reference_period")
    com_q2 = m.preco_domestico_hrc_mensal_v2(df_trimestral=ancora_q1_e_q2, ipp_mensal=ipp).set_index("reference_period")
    assert so_q1.loc["2026-02-01", "preco_domestico_rs_t"] == pytest.approx(
        com_q2.loc["2026-02-01", "preco_domestico_rs_t"])
    assert com_q2.loc["2026-02-01", "anchor_reference_period"] == "2026Q1"  # nao pula pro Q2 antes do tempo


# --- 9. Provenance OBSERVADO/CALCULADO/ESTIMADO ------------------------------

def test_provenance_calculado_no_nivel_trimestral_estimado_no_encadeado():
    ancora = _ancora_df(["2026Q1"], [4800.0])
    ipp = pd.Series({pd.Timestamp("2026-03-01"): 100.0, pd.Timestamp("2026-04-01"): 103.0})
    mensal = m.preco_domestico_hrc_mensal_v2(df_trimestral=ancora, ipp_mensal=ipp).set_index("reference_period")
    assert mensal.loc["2026-03-01", "provenance_level"] == NIVEL_CALCULADO   # nivel_trimestral
    assert mensal.loc["2026-04-01", "provenance_level"] == NIVEL_ESTIMADO    # encadeado_ipp


# --- 10. PROXY e uma flag ortogonal a provenance -----------------------------

def test_proxy_e_ortogonal_a_provenance():
    ancora = _ancora_df(["2026Q1"], [4800.0])
    ipp = pd.Series({pd.Timestamp("2026-03-01"): 100.0, pd.Timestamp("2026-04-01"): 103.0})
    mensal = m.preco_domestico_hrc_mensal_v2(df_trimestral=ancora, ipp_mensal=ipp).set_index("reference_period")
    # nivel_trimestral (CALCULADO) e encadeado_ipp (ESTIMADO) sao ambos PROXY
    # aqui (ancora "proxy_segmento_aco" E o IPP 242-Siderurgia nao sao
    # especificos de HRC) - PROXY nao muda com o nivel de provenance.
    assert bool(mensal.loc["2026-03-01", "is_proxy"]) is True
    assert bool(mensal.loc["2026-04-01", "is_proxy"]) is True
    assert mensal.loc["2026-03-01", "provenance_level"] != mensal.loc["2026-04-01", "provenance_level"]


# --- 11. Legado permanece inalterado -----------------------------------------

def test_legado_carregar_e_ponderar_permanecem_inalterados():
    csv = HEADER + (
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,CSNA3,,500000,5000,proxy_segmento_aco,teste\n"
    )
    path = _csv_tmp(csv)
    try:
        tri_legado = m.carregar_preco_domestico_trimestral(path)
        assert "receita_efetiva_rs" not in tri_legado.columns  # legado nao ganhou coluna nova
        assert "qualificado" not in tri_legado.columns
        blend_legado = m.preco_domestico_ponderado(tri_legado)
        # legado ja da o MESMO numero que soma(receita)/soma(volume) hoje
        # (ver comentario na secao 3c) - a prova de que o legado nao mudou
        # e que ele continua aceitando o CSV padrao (tipos legados) sem
        # erro e sem precisar da coluna "incompativel_receita_volume".
        esperado = (4700_000_000.0 + 5000.0 * 500_000.0) / 1_500_000.0
        assert blend_legado.iloc[0]["preco_rs_t"] == pytest.approx(esperado)
    finally:
        os.remove(path)


def test_legado_rejeita_tipo_incompativel_v2_por_design():
    # O legado NUNCA deve aceitar silenciosamente o novo tipo do V2 - ele
    # continua validando so contra TIPOS_DADO_DOMESTICO (sem o V2).
    csv = HEADER + "2026Q1,GGBR4,9000000000,100000,,incompativel_receita_volume,teste\n"
    path = _csv_tmp(csv)
    try:
        with pytest.raises(ValueError, match="tipo de dado desconhecido"):
            m.carregar_preco_domestico_trimestral(path)
    finally:
        os.remove(path)


# --- 12. Ancora ausente (trimestre sem empresa qualificada) nunca e preenchida

def test_trimestre_sem_empresa_qualificada_fica_ausente_nao_preenchida():
    csv = HEADER + (
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q2,GGBR4,9000000000,100000,,incompativel_receita_volume,teste\n"  # unica empresa do Q2, incompativel
        "2026Q3,CSNA3,,500000,5300,proxy_segmento_aco,teste\n"
    )
    path = _csv_tmp(csv)
    try:
        df = m.carregar_preco_domestico_trimestral_v2(path)
        ancora = m.ancora_domestica_ponderada_v2(df)
        # 2026Q2 nao aparece na ancora - nao virou um ponto fabricado
        assert list(ancora["trimestre"]) == ["2026Q1", "2026Q3"]

        ipp = pd.Series({pd.Timestamp("2026-03-01"): 100.0, pd.Timestamp("2026-04-01"): 102.0,
                         pd.Timestamp("2026-05-01"): 104.0, pd.Timestamp("2026-06-01"): 106.0,
                         pd.Timestamp("2026-09-01"): 112.0})
        mensal = m.preco_domestico_hrc_mensal_v2(df_trimestral=ancora, ipp_mensal=ipp).set_index("reference_period")
        # abril/maio/junho (dentro do Q2, sem ancora propria) sao encadeados
        # a partir do Q1 confirmado - nao usam o Q2 (nunca existiu) nem
        # pulam adiantado pro Q3 (ainda no futuro para esses meses).
        assert mensal.loc["2026-04-01", "anchor_reference_period"] == "2026Q1"
        assert mensal.loc["2026-06-01", "anchor_reference_period"] == "2026Q1"
        assert mensal.loc["2026-04-01", "preco_domestico_rs_t"] == pytest.approx(4700.0 * (102.0 / 100.0))
    finally:
        os.remove(path)
