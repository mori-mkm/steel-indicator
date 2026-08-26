"""Characterization tests for the domestic-price anchor.

Externalizes selftest() sections 11, 12, 12b, 13 and 14 (curated CSV loading,
volume-weighted quarterly blend, 'misto' typing, real curated-CSV coverage,
monthly chaining via IPP with hold-flat fallback, and the domestic anchor +
import cost round-trip through ipia()).
"""
import tempfile
import os

import pandas as pd

import indices_setoriais as m


def test_preco_rs_t_calculado_a_partir_de_receita_volume_quando_ausente():
    csv_sintetico = (
        "trimestre,empresa,receita_liquida_segmento_rs,volume_vendas_t,preco_rs_t,tipo,fonte\n"
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,CSNA3,,500000,5000,proxy_segmento_aco,teste\n"
        "2026Q2,USIM5,,1200000,5100,especifico_laminado_quente,teste\n"
    )
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(csv_sintetico)
        carregado = m.carregar_preco_domestico_trimestral(tmp_path)
        preco_usim_calc = float(carregado.loc[carregado["empresa"] == "USIM5", "preco_rs_t"].iloc[0])
        assert abs(preco_usim_calc - 4700.0) < 1e-6
    finally:
        os.remove(tmp_path)


def test_preco_rs_t_ja_pronto_da_fonte_nao_e_recalculado():
    csv_sintetico = (
        "trimestre,empresa,receita_liquida_segmento_rs,volume_vendas_t,preco_rs_t,tipo,fonte\n"
        "2026Q1,USIM5,4700000000,1000000,,proxy_segmento_aco,teste\n"
        "2026Q1,CSNA3,,500000,5000,proxy_segmento_aco,teste\n"
        "2026Q2,USIM5,,1200000,5100,especifico_laminado_quente,teste\n"
    )
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(csv_sintetico)
        carregado = m.carregar_preco_domestico_trimestral(tmp_path)
        preco_csn_direto = float(carregado.loc[carregado["empresa"] == "CSNA3", "preco_rs_t"].iloc[0])
        assert abs(preco_csn_direto - 5000.0) < 1e-9
    finally:
        os.remove(tmp_path)


def _tri_teste():
    return pd.DataFrame({
        "trimestre": ["2026Q1", "2026Q1", "2026Q2"],
        "empresa": ["USIM5", "CSNA3", "USIM5"],
        "preco_rs_t": [4700.0, 5000.0, 5100.0],
        "volume_vendas_t": [1000000.0, 500000.0, 1200000.0],
        "tipo": ["proxy_segmento_aco", "proxy_segmento_aco", "especifico_laminado_quente"],
    })


def test_blend_ponderado_por_volume_bate_com_media_manual():
    blend = m.preco_domestico_ponderado(_tri_teste())
    q1 = blend.loc[blend["trimestre"] == "2026Q1"].iloc[0]
    esperado_q1 = (4700.0 * 1000000.0 + 5000.0 * 500000.0) / 1500000.0
    assert abs(float(q1["preco_rs_t"]) - esperado_q1) < 1e-6


def test_trimestre_com_uma_empresa_preserva_tipo_original():
    blend = m.preco_domestico_ponderado(_tri_teste())
    assert blend.loc[blend["trimestre"] == "2026Q2", "tipo"].iloc[0] == "especifico_laminado_quente"


def test_trimestre_com_tipos_diferentes_vira_misto():
    tri_misto = pd.DataFrame({
        "trimestre": ["2026Q3", "2026Q3"],
        "empresa": ["USIM5", "CSNA3"],
        "preco_rs_t": [5200.0, 5100.0],
        "volume_vendas_t": [1000000.0, 500000.0],
        "tipo": ["especifico_laminado_quente", "proxy_segmento_aco"],
    })
    blend_misto = m.preco_domestico_ponderado(tri_misto)
    assert blend_misto["tipo"].iloc[0] == "misto"


def test_csv_curado_tem_cobertura_dupla_minima_usiminas_e_csn():
    """Pisos refletem a cobertura curada até agora (ver comentário em selftest()
    seção 12b) — suba COBERTURA_DUPLA_MINIMA quando o CSV curado ganhar mais
    trimestres com as duas empresas, não antes."""
    cobertura_dupla_minima = 4
    csv_real = m.carregar_preco_domestico_trimestral()
    n_empresas_por_trimestre = csv_real.groupby("trimestre")["empresa"].nunique()
    trimestres_com_ambas = n_empresas_por_trimestre[n_empresas_por_trimestre >= 2]
    assert len(trimestres_com_ambas) >= cobertura_dupla_minima


def _mensal_encadeado():
    tri_encad = pd.DataFrame({
        "trimestre": ["2026Q1"],
        "preco_rs_t": [5000.0],
        "tipo": ["proxy_segmento_aco"],
    })
    ipp_teste = pd.Series({
        pd.Timestamp("2026-03-01"): 100.0, pd.Timestamp("2026-04-01"): 102.0,
        pd.Timestamp("2026-06-01"): 110.0,  # maio ausente de proposito (buraco)
    })
    return m.encadear_preco_domestico_mensal(tri_encad, ipp_teste)


def test_meses_dentro_do_trimestre_confirmado_usam_nivel_direto():
    mensal = _mensal_encadeado()
    assert mensal.loc["2026-01-01":"2026-03-01", "metodo"].eq("nivel_trimestral").all()
    assert abs(float(mensal.loc["2026-02-01", "preco_rs_t"]) - 5000.0) < 1e-9


def test_mes_seguinte_ao_trimestre_confirmado_encadeia_pela_variacao_do_ipp():
    mensal = _mensal_encadeado()
    esperado_abr = 5000.0 * (102.0 / 100.0)
    assert mensal.loc["2026-04-01", "metodo"] == "encadeado_ipp"
    assert abs(float(mensal.loc["2026-04-01", "preco_rs_t"]) - esperado_abr) < 1e-6


def test_mes_sem_ipp_publicado_cai_em_hold_flat_fallback():
    mensal = _mensal_encadeado()
    assert mensal.loc["2026-05-01", "metodo"] == "hold_flat_fallback"
    assert abs(float(mensal.loc["2026-05-01", "preco_rs_t"])
               - float(mensal.loc["2026-04-01", "preco_rs_t"])) < 1e-9


def test_mes_seguinte_com_ipp_de_volta_disponivel_volta_a_encadear():
    mensal = _mensal_encadeado()
    esperado_jun = 5000.0 * (110.0 / 100.0)
    assert mensal.loc["2026-06-01", "metodo"] == "encadeado_ipp"
    assert abs(float(mensal.loc["2026-06-01", "preco_rs_t"]) - esperado_jun) < 1e-6


def test_ancora_domestica_e_custo_de_importacao_round_trip_no_ipia():
    mensal = _mensal_encadeado()
    idx_rt = pd.date_range("2026-01-01", periods=3, freq="MS")
    p_rt = m.ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                         frete_interno_rs_t=100.0, margem_importador=0.0)
    r_rt = m.custo_importacao_rs_t(pd.Series([500.0] * 3, index=idx_rt),
                                    pd.Series([50.0] * 3, index=idx_rt),
                                    pd.Series([5.0] * 3, index=idx_rt),
                                    pd.Series([5.0] * 3, index=idx_rt), p_rt)
    preco_domestico_rt = mensal["preco_rs_t"].reindex(idx_rt)
    ix_rt = m.ipia(preco_domestico_rt, r_rt["ppi_brl_t"])
    esperado_ix_rt = (preco_domestico_rt / r_rt["ppi_brl_t"]) * 100.0
    assert bool(((ix_rt - esperado_ix_rt).abs() < 1e-9).all())
