"""Characterization tests for IPIA arithmetic and import-side confidence treatment.

Externalizes selftest() sections 8, 8b, 8c and 8d (import cost/parity math,
antidumping addition, volume-based confidence weight, selective smoothing).
"""
import pandas as pd

import indices_setoriais as m


def _idx3():
    return pd.date_range("2024-01-01", periods=3, freq="MS")


def test_custo_importacao_confere_com_calculo_manual():
    idx = _idx3()
    p = m.ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                      frete_interno_rs_t=100.0, margem_importador=0.0)
    fob = pd.Series([500.0] * 3, index=idx)
    fr = pd.Series([50.0] * 3, index=idx)
    seg = pd.Series([5.0] * 3, index=idx)
    cbo = pd.Series([5.0] * 3, index=idx)
    r = m.custo_importacao_rs_t(fob, fr, seg, cbo, p)
    esperado_ppi = 2775 + 277.5 + 20 + 300
    assert abs(float(r["ppi_brl_t"].iloc[0]) - esperado_ppi) < 1e-9


def test_preco_domestico_igual_a_paridade_da_indice_100():
    idx = _idx3()
    p = m.ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                      frete_interno_rs_t=100.0, margem_importador=0.0)
    r = m.custo_importacao_rs_t(pd.Series([500.0] * 3, index=idx), pd.Series([50.0] * 3, index=idx),
                                 pd.Series([5.0] * 3, index=idx), pd.Series([5.0] * 3, index=idx), p)
    esperado_ppi = 2775 + 277.5 + 20 + 300
    ix = m.ipia(pd.Series([esperado_ppi] * 3, index=idx), r["ppi_brl_t"])
    assert abs(float(ix.iloc[0]) - 100.0) < 1e-9


def test_domestico_15pct_acima_da_paridade_da_indice_115():
    idx = _idx3()
    p = m.ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                      frete_interno_rs_t=100.0, margem_importador=0.0)
    r = m.custo_importacao_rs_t(pd.Series([500.0] * 3, index=idx), pd.Series([50.0] * 3, index=idx),
                                 pd.Series([5.0] * 3, index=idx), pd.Series([5.0] * 3, index=idx), p)
    esperado_ppi = 2775 + 277.5 + 20 + 300
    ix2 = m.ipia(pd.Series([esperado_ppi * 1.15] * 3, index=idx), r["ppi_brl_t"])
    assert abs(float(ix2.iloc[0]) - 115.0) < 1e-9


def test_antidumping_soma_ao_custo_convertido_pelo_cambio():
    idx = _idx3()
    p_ad = m.ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                         frete_interno_rs_t=100.0, margem_importador=0.0,
                         antidumping_usd_t=80.0)
    fob = pd.Series([500.0] * 3, index=idx)
    fr = pd.Series([50.0] * 3, index=idx)
    seg = pd.Series([5.0] * 3, index=idx)
    cambio5 = pd.Series([5.0] * 3, index=idx)
    r_ad = m.custo_importacao_rs_t(fob, fr, seg, cambio5, p_ad)
    esperado_ppi = 2775 + 277.5 + 20 + 300
    esperado_ad = esperado_ppi + 80.0 * 5.0
    assert abs(float(r_ad["ppi_brl_t"].iloc[0]) - esperado_ad) < 1e-9


def test_antidumping_zero_default_nao_muda_resultado():
    idx = _idx3()
    p = m.ParamsIPIA(aliquota_ii=0.10, afrmm=0.08, despesas_porto_rs_t=200.0,
                      frete_interno_rs_t=100.0, margem_importador=0.0)
    fob = pd.Series([500.0] * 3, index=idx)
    fr = pd.Series([50.0] * 3, index=idx)
    seg = pd.Series([5.0] * 3, index=idx)
    cbo = pd.Series([5.0] * 3, index=idx)
    r = m.custo_importacao_rs_t(fob, fr, seg, cbo, p)
    esperado_ppi = 2775 + 277.5 + 20 + 300
    assert abs(float(r["ppi_brl_t"].iloc[0]) - esperado_ppi) < 1e-9


def _bruto_volume():
    idx_meses = pd.date_range("2021-01-01", periods=3, freq="MS")
    return pd.DataFrame({
        "toneladas": [27379.0, 1373.0, 55.0],
        "preco_usd_t": [1082.0, 539.0, 656.0],
        "n_registros": [6, 6, 3],
    }, index=idx_meses)


def test_alto_volume_com_poucos_registros_recebe_peso_pleno():
    bruto = _bruto_volume()
    peso = (bruto["toneladas"] / m.VOLUME_MINIMO_T).clip(upper=1.0)
    assert abs(peso.iloc[0] - 1.0) < 1e-9


def test_mesmo_n_registros_volumes_diferentes_recebem_pesos_diferentes():
    bruto = _bruto_volume()
    peso = (bruto["toneladas"] / m.VOLUME_MINIMO_T).clip(upper=1.0)
    assert abs(peso.iloc[0] - peso.iloc[1]) > 0.5


def test_volume_muito_baixo_recebe_peso_proximo_de_zero():
    bruto = _bruto_volume()
    peso = (bruto["toneladas"] / m.VOLUME_MINIMO_T).clip(upper=1.0)
    assert peso.iloc[2] < 0.02


def _df_suav():
    idx_suav = pd.date_range("2021-01-01", periods=5, freq="MS")
    return pd.DataFrame({
        "preco_usd_t": [1000.0, 1082.0, 1100.0, 600.0, 650.0],
        "peso_confiabilidade": [1.0, 1.0, 1.0, 0.011, 1.0],
    }, index=idx_suav)


def test_mes_de_peso_pleno_mantem_publicado_identico_ao_bruto():
    suav = m.suavizar_preco_importacao(_df_suav())
    assert abs(float(suav["preco_usd_t_publicado"].iloc[1]) - float(suav["preco_usd_t"].iloc[1])) < 1e-9
    assert not bool(suav["suavizado"].iloc[1])


def test_mes_de_peso_reduzido_recebe_media_movel_centrada_de_3():
    suav = m.suavizar_preco_importacao(_df_suav())
    esperado_suav = (1100.0 + 600.0 + 650.0) / 3
    assert abs(float(suav["preco_usd_t_publicado"].iloc[3]) - esperado_suav) < 1e-6
    assert bool(suav["suavizado"].iloc[3])


def test_bruto_nunca_e_sobrescrito_pela_suavizacao():
    suav = m.suavizar_preco_importacao(_df_suav())
    assert abs(float(suav["preco_usd_t"].iloc[3]) - 600.0) < 1e-9
