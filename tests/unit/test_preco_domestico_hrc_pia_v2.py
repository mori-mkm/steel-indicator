"""Unit tests for Domestic Price HRC V2 - caminho PIA-Produto (Stage E10):
`denton_proporcional` (Proportional Denton, primeiras diferencas) e
`preco_domestico_hrc_pia_v2` (PIA anual + IPP 242-Siderurgia mensal, sem
splice/reancoragem contra a ancora corporativa). Deterministic, no network:
`pia_anual_df`/`ipp_mensal` sao injetados direto (mesmo padrao ja usado
pelo resto do modulo).

Prova: cada ano benchmarked satisfaz mean(preco_mensal) == preco_pia (a
menos de tolerancia numerica); quando o indicador escala exatamente por
uma constante dentro de um ano, Denton reproduz essa constante exatamente
(prova numerica fechada); nao ha degrau artificial de pro-rata simples;
serie ordenada e sem meses duplicados; sem look-ahead (ano futuro nao
contamina passado); ano sem PIA/sem IPP completo nunca vira observado;
periodo pos-ultima-PIA fica ESTIMADO/provisional; ancora corporativa nao
reancora nivel PIA (as duas funcoes sao independentes); proxy_reason
explicito; legado (`preco_domestico_hrc_mensal_v2`) e a serie corporativa
permanecem intactos.
"""
import numpy as np
import pandas as pd
import pytest

import indices_setoriais as m
from steel_indicator.domain.provenance import NIVEL_ESTIMADO


def _mensal(ano_ini: int, ano_fim: int, valores) -> pd.Series:
    idx = pd.date_range(f"{ano_ini}-01-01", f"{ano_fim}-12-01", freq="MS")
    assert len(valores) == len(idx)
    return pd.Series(valores, index=idx)


# =============================================================================
# denton_proporcional
# =============================================================================

def test_denton_indicador_constante_reproduz_media_alvo_constante():
    # indicador flat -> sem informacao de forma - a solucao mais suave que
    # bate a media anual e o proprio nivel constante em todos os meses.
    indicador = _mensal(2020, 2020, [1.0] * 12)
    alvos = pd.Series({2020: 100.0})
    resultado = m.denton_proporcional(indicador, alvos)
    assert resultado.to_numpy() == pytest.approx([100.0] * 12, abs=1e-8)


def test_denton_escala_constante_reproduz_indicador_escalado_exatamente():
    # PROVA NUMERICA FECHADA: se o indicador tem uma forma qualquer e o
    # alvo anual == k * media(indicador no ano), a solucao otima do Denton
    # proporcional e x[t] = k * i[t] para TODO t desse ano - o objetivo
    # (soma das diferencas de x/i) fica exatamente zero, que e o minimo
    # possivel (nao-negativo por construcao).
    forma = np.array([90.0, 95.0, 100.0, 105.0, 98.0, 102.0, 110.0, 108.0, 115.0, 120.0, 118.0, 125.0])
    indicador = _mensal(2020, 2020, forma)
    k = 4.8
    alvo = k * forma.mean()
    resultado = m.denton_proporcional(indicador, pd.Series({2020: alvo}))
    assert resultado.to_numpy() == pytest.approx(k * forma, rel=1e-6)


def test_denton_satisfaz_constraint_media_anual_multiplos_anos():
    forma = np.array([90.0, 95.0, 100.0, 105.0, 98.0, 102.0, 110.0, 108.0, 115.0, 120.0, 118.0, 125.0])
    indicador = _mensal(2020, 2022, np.concatenate([forma, forma * 1.1, forma * 0.9]))
    alvos = pd.Series({2020: 200.0, 2021: 250.0, 2022: 180.0})
    resultado = m.denton_proporcional(indicador, alvos)
    for ano, alvo in alvos.items():
        media_ano = resultado[resultado.index.year == ano].mean()
        assert media_ano == pytest.approx(alvo, rel=1e-6)


def _pro_rata_simples(indicador: pd.Series, alvos_anuais: pd.Series) -> pd.Series:
    """Comparador SO DE TESTE (nao e producao): pro-rata mais ingenuo
    possivel - nivel anual constante repetido nos 12 meses do ano, sem
    olhar pro formato do indicador. Usado so para provar que o Denton
    (que MINIMIZA exatamente a soma dos quadrados das diferencas de x/i)
    nunca fica pior que essa alternativa - nao para ser usado de verdade."""
    anos = indicador.index.year
    return pd.Series([alvos_anuais.loc[a] for a in anos], index=indicador.index)


def _objetivo_denton(x: np.ndarray, i: np.ndarray) -> float:
    razao = x / i
    return float(np.sum(np.diff(razao) ** 2))


def test_denton_bate_ou_supera_pro_rata_simples_no_proprio_objetivo():
    # Denton MINIMIZA sum((x/i)[t] - (x/i)[t-1])^2 sujeito as restricoes
    # anuais - qualquer outra serie que satisfaca as MESMAS restricoes
    # (como o pro-rata mais ingenuo) tem, por definicao, objetivo >= ao do
    # Denton. Prova formal de que o Denton "preserva o movimento do
    # indicador tao perto quanto permitido pelas constraints" melhor que
    # pro-rata simples - nao uma comparacao informal de magnitude.
    forma = np.array([100.0, 102.0, 101.0, 105.0, 103.0, 108.0, 110.0, 107.0, 112.0, 115.0, 111.0, 118.0])
    indicador = _mensal(2020, 2021, np.concatenate([forma, forma * 2.0]))
    alvos = pd.Series({2020: 5000.0, 2021: 5000.0})  # mesmo alvo, indicador dobra - forca dessintonia real

    denton = m.denton_proporcional(indicador, alvos)
    pro_rata = _pro_rata_simples(indicador, alvos)

    i = indicador.to_numpy()
    obj_denton = _objetivo_denton(denton.to_numpy(), i)
    obj_pro_rata = _objetivo_denton(pro_rata.to_numpy(), i)
    assert obj_denton < obj_pro_rata  # estritamente melhor, nao so igual


def test_denton_tem_salto_de_fronteira_menor_que_pro_rata_simples():
    # pro-rata simples (nivel anual constante, sem olhar pro indicador)
    # cria um degrau abrupto exatamente na fronteira do ano - o Denton,
    # que suaviza a transicao usando o formato do indicador, deve ter um
    # salto estritamente menor na mesma fronteira.
    forma = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0])
    indicador = _mensal(2020, 2021, np.concatenate([forma, forma + 20.0]))
    alvos = pd.Series({2020: 3000.0, 2021: 3400.0})

    denton = m.denton_proporcional(indicador, alvos)
    pro_rata = _pro_rata_simples(indicador, alvos)

    delta_denton = abs(denton.iloc[12] - denton.iloc[11])       # dez/2020 -> jan/2021
    delta_pro_rata = abs(pro_rata.iloc[12] - pro_rata.iloc[11])  # 3400/12 - 3000/12, degrau puro
    assert delta_denton < delta_pro_rata


def test_denton_rejeita_anos_desencontrados_entre_indicador_e_alvos():
    indicador = _mensal(2020, 2020, [100.0] * 12)
    with pytest.raises(ValueError, match="mesmos anos"):
        m.denton_proporcional(indicador, pd.Series({2021: 100.0}))


def test_denton_rejeita_indicador_nao_positivo():
    indicador = _mensal(2020, 2020, [100.0] * 11 + [0.0])
    with pytest.raises(ValueError, match="positivo"):
        m.denton_proporcional(indicador, pd.Series({2020: 100.0}))


# =============================================================================
# preco_domestico_hrc_pia_v2
# =============================================================================

def _pia_df(precos: dict) -> pd.DataFrame:
    anos = sorted(precos)
    return pd.DataFrame({
        "receita_liquida_mil_rs": [precos[a] * 1000.0 for a in anos],
        "quantidade_vendida_t": [1000.0] * len(anos),
        "preco_rs_t": [precos[a] for a in anos],
    }, index=pd.Index(anos, name="ano"))


def test_janela_benchmarked_satisfaz_constraint_anual():
    pia = _pia_df({2020: 3000.0, 2021: 3500.0})
    forma = np.linspace(95.0, 110.0, 12)
    ipp = _mensal(2020, 2021, np.concatenate([forma, forma * 1.05]))
    out = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp).set_index("reference_period")
    for ano, alvo in pia["preco_rs_t"].items():
        media = out.loc[out.index.year == ano, "preco_domestico_rs_t"].mean()
        assert media == pytest.approx(alvo, rel=1e-6)


def test_ano_sem_pia_ou_sem_ipp_completo_nunca_vira_observado():
    # PIA cobre 2019-2021; IPP so cobre 2020-2021 inteiros (2019 tem so
    # 6 meses, incompleto) - 2019 NAO pode aparecer na serie mensal.
    pia = _pia_df({2019: 2000.0, 2020: 3000.0, 2021: 3500.0})
    forma = np.linspace(95.0, 110.0, 12)
    idx_2019_parcial = pd.date_range("2019-07-01", "2019-12-01", freq="MS")
    ipp = pd.concat([
        pd.Series([100.0] * 6, index=idx_2019_parcial),
        _mensal(2020, 2021, np.concatenate([forma, forma * 1.05])),
    ])
    out = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)
    assert 2019 not in set(out["reference_period"].dt.year)
    assert set(out.loc[~out["is_provisional"], "reference_period"].dt.year) == {2020, 2021}


def test_periodo_pos_ultima_pia_fica_estimado_e_provisional():
    pia = _pia_df({2020: 3000.0})
    forma = np.linspace(95.0, 106.0, 12)
    ipp_bench = _mensal(2020, 2020, forma)
    ipp_prov = pd.Series([112.0, 115.0], index=pd.date_range("2021-01-01", "2021-02-01", freq="MS"))
    ipp = pd.concat([ipp_bench, ipp_prov])
    out = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp).set_index("reference_period")

    assert bool(out.loc["2020-12-01", "is_provisional"]) is False
    assert bool(out.loc["2021-01-01", "is_provisional"]) is True
    assert bool(out.loc["2021-02-01", "is_provisional"]) is True
    assert out.loc["2021-01-01", "provenance_level"] == NIVEL_ESTIMADO
    assert out.loc["2020-12-01", "provenance_level"] == NIVEL_ESTIMADO  # tambem estimado, ver docstring

    # encadeamento provisional: mesma formula ja usada em
    # encadear_preco_domestico_mensal (nivel_base * indicador_m/indicador_base)
    preco_dez = out.loc["2020-12-01", "preco_domestico_rs_t"]
    ipp_dez = forma[-1]
    esperado_jan = preco_dez * (112.0 / ipp_dez)
    assert out.loc["2021-01-01", "preco_domestico_rs_t"] == pytest.approx(esperado_jan)


def test_pia_reference_year_preservado_para_reprocessamento_futuro():
    pia = _pia_df({2020: 3000.0})
    ipp_bench = _mensal(2020, 2020, np.linspace(95.0, 106.0, 12))
    ipp_prov = pd.Series([112.0], index=pd.date_range("2021-01-01", "2021-01-01", freq="MS"))
    out = m.preco_domestico_hrc_pia_v2(
        pia_anual_df=pia, ipp_mensal=pd.concat([ipp_bench, ipp_prov])).set_index("reference_period")
    assert out.loc["2020-06-01", "pia_reference_year"] == 2020
    assert out.loc["2021-01-01", "pia_reference_year"] == 2020  # ano PIA que fundamenta a extensao
    assert out.loc["2021-01-01", "pia_anchor_price_rs_t"] == pytest.approx(3000.0)


def test_sem_look_ahead_provisional_nunca_depende_de_ipp_futuro():
    # A extensao PROVISIONAL (pos-ultima-PIA) encadeia estritamente PRA
    # FRENTE a partir do ultimo mes benchmarked (formula de
    # `encadear_preco_domestico_mensal`) - o preco provisional de um mes M
    # nunca pode depender de nenhum valor de IPP POSTERIOR a M. Prova:
    # truncar o IPP logo apos M e recalcular da o MESMO preco em M.
    pia = _pia_df({2020: 3000.0})
    ipp_bench = _mensal(2020, 2020, np.linspace(95.0, 106.0, 12))
    ipp_prov_completo = pd.Series(
        [108.0, 110.0, 115.0, 118.0], index=pd.date_range("2021-01-01", "2021-04-01", freq="MS"))

    completo = m.preco_domestico_hrc_pia_v2(
        pia_anual_df=pia, ipp_mensal=pd.concat([ipp_bench, ipp_prov_completo])
    ).set_index("reference_period")
    truncado_em_fevereiro = m.preco_domestico_hrc_pia_v2(
        pia_anual_df=pia, ipp_mensal=pd.concat([ipp_bench, ipp_prov_completo.loc[:"2021-02-01"]])
    ).set_index("reference_period")

    assert completo.loc["2021-01-01", "preco_domestico_rs_t"] == pytest.approx(
        truncado_em_fevereiro.loc["2021-01-01", "preco_domestico_rs_t"])
    assert completo.loc["2021-02-01", "preco_domestico_rs_t"] == pytest.approx(
        truncado_em_fevereiro.loc["2021-02-01", "preco_domestico_rs_t"])
    # mar/abr so existem na versao completa - confirma que truncar o
    # futuro so remove meses futuros, nunca muda os meses ja calculados.
    assert "2021-03-01" not in truncado_em_fevereiro.index
    assert "2021-04-01" not in truncado_em_fevereiro.index


def test_janela_benchmarked_conjunta_pode_revisar_anos_antigos_quando_novo_ano_pia_e_somado():
    # Propriedade CONHECIDA e ESPERADA do Denton conjunto (nao um bug):
    # como a otimizacao e feita sobre TODA a janela benchmarked de uma vez
    # (para poder suavizar a fronteira entre anos - ver teste de salto de
    # fronteira acima), adicionar um novo ano PIA e recalcular PODE mudar
    # levemente os meses de anos anteriores ja benchmarked, se o novo alvo
    # anual romper a tendencia que o indicador vinha sugerindo. Isso e
    # pratica padrao de temporal benchmarking (IMF QNA Manual cap. 6) e e
    # exatamente o que autoriza a re-execucao ao publicar uma nova PIA
    # (secao 7 da decisao Level 3) - registrado aqui como comportamento
    # documentado, nao verificado como ausente (seria o oposto do
    # benchmarking conjunto que a propria decisao pede).
    forma = np.linspace(95.0, 110.0, 12)
    ipp_2020 = _mensal(2020, 2020, forma)
    ipp_2021 = _mensal(2021, 2021, forma * 1.2)

    so_2020 = m.preco_domestico_hrc_pia_v2(
        pia_anual_df=_pia_df({2020: 3000.0}), ipp_mensal=ipp_2020).set_index("reference_period")
    com_2021 = m.preco_domestico_hrc_pia_v2(
        pia_anual_df=_pia_df({2020: 3000.0, 2021: 9999.0}),
        ipp_mensal=pd.concat([ipp_2020, ipp_2021])).set_index("reference_period")

    # a media de 2020 continua batendo o alvo de 2020 nos dois casos (a
    # garantia que realmente importa - ver test_janela_benchmarked_satisfaz_constraint_anual)
    assert so_2020["preco_domestico_rs_t"].mean() == pytest.approx(3000.0, rel=1e-6)
    assert com_2021.loc["2020-01-01":"2020-12-01", "preco_domestico_rs_t"].mean() == pytest.approx(3000.0, rel=1e-6)
    # mas os MESES individuais de 2020 podem diferir entre as duas execucoes
    assert not np.allclose(
        so_2020["preco_domestico_rs_t"].to_numpy(),
        com_2021.loc["2020-01-01":"2020-12-01", "preco_domestico_rs_t"].to_numpy())


def test_serie_ordenada_sem_meses_duplicados():
    pia = _pia_df({2020: 3000.0, 2021: 3500.0})
    forma = np.linspace(95.0, 110.0, 12)
    ipp = _mensal(2020, 2021, np.concatenate([forma, forma * 1.05]))
    out = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)
    assert out["reference_period"].is_monotonic_increasing
    assert not out["reference_period"].duplicated().any()


def test_ano_pia_sem_12_meses_ipp_fica_de_fora_sem_forcar_serie():
    # PIA existe para 2019 mas o IPP so tem 3 meses desse ano - nao gera
    # nenhuma linha mensal artificial para 2019.
    pia = _pia_df({2019: 2000.0})
    ipp = pd.Series([100.0, 101.0, 102.0], index=pd.date_range("2019-01-01", "2019-03-01", freq="MS"))
    out = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)
    assert out.empty


def test_buraco_no_meio_da_janela_benchmarked_levanta_erro_explicito():
    # PIA existe para 2019, 2020 e 2021, mas o IPP so tem os 12 meses
    # completos de 2019 e 2021 (2020 fica incompleto, so 3 meses) - a
    # janela 2019-2021 NAO e continua. Nunca preenche o buraco em
    # silencio (nem interpola, nem pula o ano incompleto escondendo isso)
    # - levanta erro explicito, decisao de como tratar fica para Level 3.
    pia = _pia_df({2019: 2000.0, 2020: 2500.0, 2021: 3000.0})
    forma = np.linspace(95.0, 110.0, 12)
    ipp = pd.concat([
        _mensal(2019, 2019, forma),
        pd.Series([100.0, 101.0, 102.0], index=pd.date_range("2020-01-01", "2020-03-01", freq="MS")),
        _mensal(2021, 2021, forma * 1.1),
    ])
    with pytest.raises(ValueError, match="nao e continua"):
        m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)


def test_proxy_reason_explicito_destination_mix():
    pia = _pia_df({2020: 3000.0})
    ipp = _mensal(2020, 2020, np.linspace(95.0, 106.0, 12))
    out = m.preco_domestico_hrc_pia_v2(pia_anual_df=pia, ipp_mensal=ipp)
    assert (out["is_proxy"] == True).all()  # noqa: E712
    assert (out["proxy_reason"] == m.PROXY_REASON_DESTINATION_MIX).all()
    assert (out["ipp_series_id"] == m.IPP_SIDERURGIA_SERIES_ID).all()


# =============================================================================
# Ancora corporativa como benchmark, nunca como reancoragem
# =============================================================================

def test_preco_domestico_hrc_pia_v2_e_independente_da_ancora_corporativa():
    # preco_domestico_hrc_pia_v2 nao aceita nem consulta nenhum parametro
    # relacionado a ancora corporativa (Usiminas/CSN) - garantia estrutural
    # de que a decisao Level 3 (nao fazer splice/reancoragem) e respeitada
    # pela propria assinatura da funcao, nao so por convencao de uso.
    import inspect
    assinatura = inspect.signature(m.preco_domestico_hrc_pia_v2)
    assert set(assinatura.parameters) == {"pia_anual_df", "ipp_mensal"}


def test_legado_corporativo_permanece_intacto():
    # preco_domestico_hrc_mensal_v2 (Stage E8, ancora corporativa) continua
    # funcionando exatamente como antes - nao foi tocado por este batch.
    ancora = pd.DataFrame({
        "trimestre": ["2026Q1"], "preco_rs_t": [4800.0],
        "receita_total_rs": [4800.0 * 1_000_000.0], "volume_total_t": [1_000_000.0],
        "tipo": ["proxy_segmento_aco"], "companies_used": ["USIM5,CSNA3"],
        "quantidade_empresas": [2],
    })
    ipp = pd.Series({pd.Timestamp("2026-03-01"): 100.0, pd.Timestamp("2026-04-01"): 103.0})
    mensal = m.preco_domestico_hrc_mensal_v2(df_trimestral=ancora, ipp_mensal=ipp)
    assert mensal.set_index("reference_period").loc["2026-04-01", "preco_domestico_rs_t"] == pytest.approx(
        4800.0 * (103.0 / 100.0))
