"""Characterization tests for reporting and Aço Brasil parsers.

Externalizes selftest() sections 15, 16, 17, 18 and 19 (deterministic PDF
report smoke test, dynamic left-margin sizing for horizontal bar charts, the
PDF penetration-table parser, the Excel 'Performance Mensal' penetration
calculation, and combining official + approximate penetration series).
Uses frozen representative fixtures only; no live network calls.
"""
import os
import tempfile

import numpy as np
import pandas as pd

import indices_setoriais as m


def test_relatorio_pdf_do_ipia_e_gerado_sem_erro_e_nao_esta_vazio():
    from reporting.report_builder import gerar_relatorio_ipia

    idx_pdf = pd.date_range("2026-01-01", periods=6, freq="MS")
    df_ipia_pdf = pd.DataFrame({
        "ipia": [130.4, 142.6, 143.4, 139.3, 140.1, 134.0],
        "preco_domestico_rs_t": [5213.2, 5213.2, 5213.2, 4996.0, 4996.0, 4996.0],
        "ppi_rs_t": [3996.8, 3655.7, 3636.0, 3586.3, 3567.2, 3727.9],
        "tipo_dado_domestico": ["proxy_segmento_aco"] * 6,
        "metodo_domestico": ["nivel_trimestral"] * 6,
        "peso_confiabilidade_importacao": [1.0] * 6,
        "penetracao_importacao_planos_pct": [24.1, 20.2, 18.5, 17.9, np.nan, 17.9],
        "tipo_dado_penetracao": ["aproximado_consumo_aparente"] * 4 + [np.nan, "oficial_mensal"],
    }, index=idx_pdf)
    df_custo_pdf = pd.DataFrame({
        "fob_usd_t": [620.0, 615.0, 610.0, 605.0, 600.0, 598.0],
        "frete_usd_t": [45.0] * 6,
        "seguro_usd_t": [4.0] * 6,
        "cambio": [5.10, 5.15, 5.20, 5.18, 5.22, 5.19],
        "cif_brl_t": [3415.0, 3410.0, 3400.0, 3385.0, 3380.0, 3360.0],
        "ii_brl_t": [368.9, 368.3, 367.2, 365.6, 365.0, 362.9],
        "afrmm_brl_t": [18.4, 18.5, 18.7, 18.6, 18.8, 18.7],
        "antidumping_brl_t": [0.0] * 6,
        "despesas_porto_rs_t": [210.0] * 6,
        "frete_interno_rs_t": [140.0] * 6,
        "margem_rs_t": [125.0, 124.6, 123.6, 122.7, 122.6, 121.7],
        "ppi_brl_t": [3996.8, 3655.7, 3636.0, 3586.3, 3567.2, 3727.9],
    }, index=idx_pdf)
    df_origem_pdf = pd.DataFrame({
        "toneladas": [45000.0, 22000.0, 12000.0, 8000.0, 3000.0],
        "pct_do_volume": [50.0, 24.4, 13.3, 8.9, 3.3],
    }, index=pd.Index(["China", "Coreia do Sul", "Egito", "Vietna", "India"], name="country"))
    df_origem_pdf.attrs["mes_inicio"] = idx_pdf[-3]
    df_origem_pdf.attrs["mes_fim"] = idx_pdf[-1]

    tmp_pdf_fd, tmp_pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(tmp_pdf_fd)
    try:
        n_meses = gerar_relatorio_ipia(tmp_pdf_path, df_ipia=df_ipia_pdf,
                                        df_custo=df_custo_pdf, df_origem=df_origem_pdf)
        tamanho = os.path.getsize(tmp_pdf_path)
        assert os.path.exists(tmp_pdf_path)
        assert tamanho > 0
        assert n_meses == 6
    finally:
        os.remove(tmp_pdf_path)


def test_grafico_barras_horizontais_margem_esquerda_cresce_para_rotulo_mais_largo():
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

    try:
        assert inset_longo > inset_curto
    finally:
        plt.close(fig_rotulo_curto)
        plt.close(fig_rotulo_longo)


def test_grafico_barras_horizontais_axes_nao_invade_espaco_do_rotulo():
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["text.parse_math"] = False
    import matplotlib.pyplot as plt
    from reporting import components as rep_components
    from reporting import theme as rep_theme

    fig_rotulo_longo = plt.figure(figsize=(rep_theme.LARGURA_POL, rep_theme.ALTURA_POL))
    ax_longo = rep_components.grafico_barras_horizontais(
        fig_rotulo_longo, 0.1, 0.1, 0.8, 0.2, ["China", "Coreia do Sul"], [50.0, 24.4])
    try:
        assert ax_longo.get_position().x0 > 0.1
    finally:
        plt.close(fig_rotulo_longo)


_TEXTO_PDF_PENETRACAO_JUL_2026 = (
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


def test_penetracao_pdf_pega_mes_ano_certos():
    dados_penet = m._parse_tabela_penetracao_pdf(_TEXTO_PDF_PENETRACAO_JUL_2026)
    assert dados_penet["mes_nome"] == "Julho"
    assert dados_penet["ano"] == 2026
    assert dados_penet["ano_anterior"] == 2025


def test_penetracao_pdf_pega_taxa_da_secao_mensal_nao_acumulado():
    dados_penet = m._parse_tabela_penetracao_pdf(_TEXTO_PDF_PENETRACAO_JUL_2026)
    assert abs(dados_penet["planos"]["taxa_penetracao_pct"] - 17.9) < 1e-9
    assert abs(dados_penet["longos"]["taxa_penetracao_pct"] - 14.6) < 1e-9


def test_penetracao_pdf_consumo_importacao_em_toneladas_batem_com_texto():
    dados_penet = m._parse_tabela_penetracao_pdf(_TEXTO_PDF_PENETRACAO_JUL_2026)
    assert abs(dados_penet["planos"]["consumo_aparente_t"] - 1361849.0) < 1e-6
    assert abs(dados_penet["planos"]["importacao_t"] - 244207.0) < 1e-6


def _df_bruto_excel_teste():
    return pd.DataFrame([
        ["Especificação\nSpecification", 2025, None, None],
        [None, "Jan\nJan", "Fev\nFeb", "Mar\nMar"],
        ["Importações / Imports", None, None, None],
        ["Planos / Flats", 100.0, 110.0, 120.0],
        ["Longos / Longs", 50.0, 55.0, 60.0],
        ["Consumo Aparente / Apparent Consumption", None, None, None],
        ["Planos / Flats\n(Inclui Placas)", 500.0, 550.0, 600.0],
        ["Longos / Longs\n(Inclui Blocos)", 300.0, 330.0, 360.0],
    ])


def test_penetracao_excel_localiza_linhas_certas_e_calcula_taxa():
    calc_planos = m._calcular_penetracao_de_performance_mensal(_df_bruto_excel_teste(), "planos")
    assert len(calc_planos) == 3
    assert abs(float(calc_planos.loc["2025-01-01", "taxa_penetracao_pct"]) - 20.0) < 1e-9
    assert abs(float(calc_planos.loc["2025-03-01", "taxa_penetracao_pct"]) - 20.0) < 1e-9


def test_penetracao_excel_longos_pega_linha_diferente_de_planos():
    calc_longos = m._calcular_penetracao_de_performance_mensal(_df_bruto_excel_teste(), "longos")
    assert abs(float(calc_longos.loc["2025-02-01", "taxa_penetracao_pct"]) - (55.0 / 330.0 * 100)) < 1e-6


def test_penetracao_excel_categoria_invalida_e_rejeitada():
    import pytest
    with pytest.raises(ValueError):
        m._calcular_penetracao_de_performance_mensal(_df_bruto_excel_teste(), "invalida")


def _series_penetracao_combinada():
    idx_hist_penet = pd.date_range("2026-05-01", periods=3, freq="MS")
    df_hist_penet_teste = pd.DataFrame({
        "categoria": ["planos"] * 3,
        "taxa_penetracao_pct": [15.0, 16.0, 16.66],
        "tipo_dado_penetracao": ["aproximado_consumo_aparente"] * 3,
    }, index=idx_hist_penet)
    df_oficial_penet_teste = pd.DataFrame({
        "categoria": ["planos"],
        "taxa_penetracao_pct": [17.9],
        "tipo_dado_penetracao": ["oficial_mensal"],
    }, index=[pd.Timestamp("2026-07-01")])
    return m.taxa_penetracao_importacao_planos_mensal(
        df_historico=df_hist_penet_teste, df_oficial=df_oficial_penet_teste)


def test_penetracao_combinada_mes_com_duas_fontes_fica_com_valor_oficial():
    combinado_penet = _series_penetracao_combinada()
    assert combinado_penet.loc["2026-07-01", "tipo_dado_penetracao"] == "oficial_mensal"
    assert abs(float(combinado_penet.loc["2026-07-01", "taxa_penetracao_pct"]) - 17.9) < 1e-9


def test_penetracao_combinada_meses_so_no_excel_ficam_aproximados():
    combinado_penet = _series_penetracao_combinada()
    assert combinado_penet.loc["2026-05-01", "tipo_dado_penetracao"] == "aproximado_consumo_aparente"
    assert combinado_penet.loc["2026-06-01", "tipo_dado_penetracao"] == "aproximado_consumo_aparente"


def test_penetracao_combinada_nao_duplica_mes_sobreposto():
    combinado_penet = _series_penetracao_combinada()
    assert len(combinado_penet) == 3
