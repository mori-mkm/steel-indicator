"""As 4 paginas do relatorio do IPIA. Cada funcao so desenha - recebe os
DataFrames ja calculados pelo motor (`indices_setoriais.py`, nunca
recalcula nada aqui) e usa os helpers de `components.py`/tokens de
`theme.py`.
"""
from __future__ import annotations

import datetime as dt
import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import indices_setoriais as motor  # noqa: E402  (import apos sys.path, motor de calculo)

from . import theme as t
from . import components as c

MARGEM = t.MARGEM_POL / t.LARGURA_POL

_MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
_MESES_COMPLETO = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _mes_pt(data, abreviado: bool = True) -> str:
    """Nome do mes em portugues, independente do locale do sistema
    (strftime %b/%B usa o locale ativo - neste sistema cai em ingles)."""
    nomes = _MESES_ABREV if abreviado else _MESES_COMPLETO
    return f"{nomes[data.month - 1]}/{data.year}" if abreviado else f"{nomes[data.month - 1]} de {data.year}"


def _gerar_bullets_executivos(df_ipia: pd.DataFrame) -> list:
    """Funcao pura: compara o ultimo mes com o anterior em 3 metricas ja
    calculadas (IPIA, spread domestico-paridade, penetracao de
    importacao) e frasea a direcao/magnitude - nunca uma frase fixa,
    sempre derivada do dado real. Cada item ganha uma segunda frase
    explicando o que a direcao observada significa (tambem derivada do
    proprio valor, nao narrativa inventada). Se so houver 1 mes, avisa
    isso."""
    if len(df_ipia) < 2:
        return [("Histórico insuficiente para comparação",
                 "Menos de 2 meses de dado disponível na série atual.")]
    ultimo, penultimo = df_ipia.iloc[-1], df_ipia.iloc[-2]
    bullets = []

    delta_ipia = ultimo["ipia"] - penultimo["ipia"]
    direcao = "subiu" if delta_ipia > 0 else "caiu" if delta_ipia < 0 else "ficou estável"
    relacao_paridade = ("acima da paridade — importar seguiria mais caro que comprar no mercado doméstico"
                        if ultimo["ipia"] > 100 else
                        "abaixo da paridade — o produto importado seguiria mais barato que o doméstico"
                        if ultimo["ipia"] < 100 else "exatamente na paridade")
    bullets.append((
        f"IPIA {direcao} {abs(delta_ipia):.1f} pontos no mês",
        f"De {penultimo['ipia']:.1f} para {ultimo['ipia']:.1f} pontos "
        f"({_mes_pt(df_ipia.index[-2])} → {_mes_pt(df_ipia.index[-1])}). "
        f"Em {ultimo['ipia']:.1f} pontos, o índice está {relacao_paridade}."
    ))

    spread_u = ultimo["preco_domestico_rs_t"] - ultimo["ppi_rs_t"]
    spread_p = penultimo["preco_domestico_rs_t"] - penultimo["ppi_rs_t"]
    delta_spread = spread_u - spread_p
    direcao_s = "ampliou" if delta_spread > 0 else "reduziu" if delta_spread < 0 else "manteve"
    relacao_spread = ("maior vantagem de custo para o produto doméstico frente à paridade de importação"
                      if delta_spread > 0 else
                      "menor vantagem de custo para o produto doméstico frente à paridade de importação"
                      if delta_spread < 0 else "spread estável no período")
    bullets.append((
        f"Spread doméstico vs. paridade {direcao_s} R$ {abs(delta_spread):,.0f}/t",
        f"De R$ {spread_p:,.0f}/t para R$ {spread_u:,.0f}/t no mesmo período. "
        f"Na prática, isso é {relacao_spread}."
    ))

    pen_u = ultimo.get("penetracao_importacao_planos_pct")
    pen_p = penultimo.get("penetracao_importacao_planos_pct")
    if pd.notna(pen_u) and pd.notna(pen_p):
        delta_pen = pen_u - pen_p
        direcao_pen = "subiu" if delta_pen > 0 else "caiu" if delta_pen < 0 else "ficou estável"
        rotulo_tipo = "oficial" if ultimo.get("tipo_dado_penetracao") == "oficial_mensal" else "aproximado"
        relacao_pen = ("maior presença de aço importado no mercado brasileiro de planos" if delta_pen > 0 else
                       "menor presença de aço importado no mercado brasileiro de planos" if delta_pen < 0 else
                       "presença estável de aço importado no mercado brasileiro de planos")
        bullets.append((
            f"Penetração de importação (Planos) {direcao_pen} {abs(delta_pen):.1f} p.p.",
            f"De {pen_p:.1f}% para {pen_u:.1f}% ({rotulo_tipo}, ver docs/adr/0007). "
            f"Isso indica {relacao_pen}."
        ))
    else:
        bullets.append((
            "Penetração de importação sem comparação disponível",
            "Fonte (Instituto Aço Brasil) ainda não cobre os dois meses mais "
            "recentes da série para comparar a variação."
        ))
    return bullets


def pagina_capa(fig, df_ipia: pd.DataFrame, data_geracao: dt.datetime) -> None:
    c.banda_topo(fig, "IPIA — RELATÓRIO MENSAL")
    c.titulo_serif(fig, MARGEM, 0.905, "IPIA", fontsize=34)
    fig.text(MARGEM, 0.865, "Índice de Paridade de Importação do Aço — Bobina Laminada a Quente",
             transform=fig.transFigure, fontsize=12, color=t.COR_TEXTO_PRINCIPAL,
             fontfamily=t.FONTE_SERIF, va="top")

    ultimo = df_ipia.iloc[-1]
    delta_total = df_ipia["ipia"].iloc[-1] - df_ipia["ipia"].iloc[0]
    tendencia = "alta" if delta_total > 0 else "queda" if delta_total < 0 else "estabilidade"
    deck = (f"Paridade em {ultimo['ipia']:.0f} pontos — {tendencia} de "
           f"{abs(delta_total):.1f} pts em {len(df_ipia)} meses (série completa abaixo)")
    fig.text(MARGEM, 0.838, deck, transform=fig.transFigure, fontsize=10.5,
             color=t.COR_ACCENT_2, fontfamily=t.FONTE_SANS, fontstyle="italic", va="top")

    # box "o que o IPIA mede" - linguagem simples, sem duplicar METODOLOGIA.md.
    # altura calculada a partir do texto (ver caixa_texto) - nunca estoura
    # nem sobra espaco vazio.
    y_apos_box = c.caixa_texto(
        fig, MARGEM, 0.780, 1 - 2 * MARGEM,
        "O IPIA compara o custo de importar bobina laminada a quente com o preço "
        "praticado no mercado brasileiro. Acima de 100, importar teria compensado; "
        "abaixo de 100, o produto nacional está mais barato que a paridade de importação.",
        cor_borda=t.COR_ACCENT_1)

    # sparkline (no lugar da foto) - ultimos 12 meses, com titulo + legenda
    # de interpretacao no estilo classico de sparkline (inline, sem
    # eixos/grade completos) - nao e so decorativo, tem numero real.
    janela = df_ipia.tail(12)
    fig.text(MARGEM, y_apos_box - 0.018, "IPIA — ÚLTIMOS 12 MESES", transform=fig.transFigure,
             fontsize=8, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS,
             fontweight="bold", va="top")
    altura_spark = 0.075
    topo_spark = y_apos_box - 0.038
    ax_spark = fig.add_axes((MARGEM, topo_spark - altura_spark, 1 - 2 * MARGEM, altura_spark))
    ax_spark.plot(janela.index, janela["ipia"], color=t.COR_ACCENT_2, linewidth=1.8)
    ax_spark.fill_between(janela.index, janela["ipia"], janela["ipia"].min(),
                          color=t.COR_ACCENT_2, alpha=0.10)
    ax_spark.scatter([janela.index[-1]], [janela["ipia"].iloc[-1]], color=t.COR_ACCENT_2, s=18, zorder=5)
    ax_spark.axis("off")
    legenda_spark = (f"IPIA, {_mes_pt(janela.index[0])}–{_mes_pt(janela.index[-1])}: "
                     f"de {janela['ipia'].min():.0f} a {janela['ipia'].max():.0f} pontos "
                     f"(fechou em {janela['ipia'].iloc[-1]:.0f}).")
    y_legenda_spark = topo_spark - altura_spark - 0.016
    fig.text(MARGEM, y_legenda_spark, legenda_spark, transform=fig.transFigure,
             fontsize=8, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS,
             fontstyle="italic", va="top")

    # KPIs - cada um com periodo (mes real desse numero especifico, nunca
    # "atual" sozinho) e selo de proveniencia (OBSERVADO/CALCULADO/
    # ESTIMADO + PROXY, ver docs/adr/0008). Os 3 KPIs desta pagina vem da
    # MESMA linha de df_ipia, entao hoje compartilham o mesmo periodo -
    # ainda assim cada um mostra o seu, pela mesma regra usada na pagina 3
    # (onde podem legitimamente divergir).
    periodo_kpi = _mes_pt(ultimo.name)
    v_ipia = motor.classificar_ipia(ultimo)
    v_preco = motor.classificar_preco_domestico(ultimo)
    v_penet = motor.classificar_penetracao(ultimo)

    y_kpi = y_legenda_spark - 0.033
    c.kpi_tile(fig, MARGEM, y_kpi, 0.25, "IPIA ATUAL", f"{ultimo['ipia']:.1f}",
              cor_valor=t.COR_ACCENT_2, periodo=periodo_kpi,
              nota=f"{'▲' if delta_total >= 0 else '▼'} {abs(delta_total):.1f} pts no período",
              selo=c.selo_dado_texto(v_ipia.nivel, v_ipia.proxy))
    spread_atual = ultimo["preco_domestico_rs_t"] - ultimo["ppi_rs_t"]
    c.kpi_tile(fig, MARGEM + 0.32, y_kpi, 0.25, "SPREAD (DOM. VS. PARIDADE)",
              f"R$ {spread_atual:,.0f}/t", periodo=periodo_kpi,
              selo=c.selo_dado_texto(v_preco.nivel, v_preco.proxy))
    penet = ultimo.get("penetracao_importacao_planos_pct")
    tipo_penet = ultimo.get("tipo_dado_penetracao")
    if pd.notna(penet):
        rotulo = "oficial" if tipo_penet == "oficial_mensal" else "aproximado"
        c.kpi_tile(fig, MARGEM + 0.64, y_kpi, 0.25, "PENETRAÇÃO (PLANOS)",
                  f"{penet:.1f}%", nota=rotulo, periodo=periodo_kpi,
                  selo=c.selo_dado_texto(v_penet.nivel, v_penet.proxy) if v_penet else None)
    else:
        c.kpi_tile(fig, MARGEM + 0.64, y_kpi, 0.25, "PENETRAÇÃO (PLANOS)",
                  "n/d", nota="sem dado neste mês", periodo=periodo_kpi)

    # limitacao material em texto corrido (fora de qualquer caixa isolada -
    # a caixa de ressalvas da pagina 2 continua existindo, mas a pagina 1
    # tambem precisa deixar isso visivel no corpo, nao so ali)
    y_disclosure = c.texto_corrido(
        fig, MARGEM, y_kpi - 0.085, 1 - 2 * MARGEM,
        "IPIA e preço doméstico usam uma âncora que é proxy do segmento \"Siderurgia\" de "
        "Usiminas/CSN (selo CALCULADO · PROXY acima), não específica de bobina a quente — "
        "detalhe completo na decomposição de custo, página 2.",
        fontsize=8, cor=t.COR_TEXTO_SECUNDARIO)

    y_secao = y_disclosure - 0.025
    c.secao_titulo(fig, MARGEM, y_secao, "O QUE MUDOU")
    y_apos_callout = c.callout_numerado(fig, MARGEM, y_secao - 0.03, 1 - 2 * MARGEM,
                                        _gerar_bullets_executivos(df_ipia))

    # Report Information - posicionado a partir da borda inferior REAL do
    # callout acima (altura do callout e dinamica, depende do conteudo -
    # uma posicao fixa aqui colidia com o callout quando os bullets
    # cresciam, ver bug corrigido em components.callout_numerado)
    info = [
        ("Período", f"{_mes_pt(df_ipia.index.min())} – {_mes_pt(df_ipia.index.max())}"),
        ("Frequência", "Mensal"),
        ("Versão da metodologia", motor.VERSAO_METODOLOGIA),
        ("Última atualização", f"{data_geracao:%d/%m/%Y %H:%M}"),
    ]
    y = y_apos_callout - 0.028
    fig.text(MARGEM, y + 0.018, "REPORT INFORMATION", transform=fig.transFigure, fontsize=8,
             color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
    largura_bloco = (1 - 2 * MARGEM) / len(info)
    for i, (rotulo, valor) in enumerate(info):
        x = MARGEM + i * largura_bloco
        fig.text(x, y - 0.004, rotulo, transform=fig.transFigure, fontsize=7.5,
                 color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(x, y - 0.020, valor, transform=fig.transFigure, fontsize=9,
                 color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    c.rodape_pagina(fig,
                    "Fontes: Comex Stat, BCB/SGS, releases trimestrais Usiminas/CSN, "
                    "IBGE/SIDRA, Instituto Aço Brasil. Ver docs/METODOLOGIA.md para a "
                    "metodologia completa.",
                    pagina_num=1, data_geracao=data_geracao)


def pagina_decomposicao_custo(fig, df_ipia: pd.DataFrame, df_custo: pd.DataFrame,
                              data_geracao: dt.datetime, pagina_num: int) -> None:
    c.cabecalho_pagina_interna(fig, "IPIA — Relatório Mensal")
    c.titulo_serif(fig, MARGEM, 0.90, "Decomposição do Custo de Importação", fontsize=19)
    ultimo = df_custo.iloc[-1]
    ultimo_ipia = df_ipia.iloc[-1]
    # bug real corrigido (ver docs/adr/0008): esta pagina usava
    # df_custo.iloc[-1] (mes mais fresco do lado importacao) junto de
    # df_ipia.iloc[-1] (mes mais fresco da INTERSECCAO bobina x
    # domestico) como se fossem o mesmo mes, e imprimia UM "Mes de
    # referencia" so - quando os dois lados divergem (import mais fresco
    # que o encadeamento IPP do lado domestico), o spread misturava dois
    # meses diferentes sem avisar. Agora: o waterfall usa o mes mais
    # fresco disponivel (df_custo, self-contido, soma bate sozinha); a
    # COMPARACAO usa o mes de df_ipia dos dois lados (nunca combina dois
    # meses numa mesma formula) - cada bloco imprime seu proprio mes no
    # titulo do grafico, nunca um rotulo unico para a pagina inteira.
    ultimo_custo_mes_ipia = df_custo.loc[df_ipia.index[-1]]

    fob_brl_t = ultimo["fob_usd_t"] * ultimo["cambio"]
    frete_brl_t = ultimo["frete_usd_t"] * ultimo["cambio"]
    seguro_brl_t = ultimo["seguro_usd_t"] * ultimo["cambio"]
    componentes = [
        ("FOB (China)", fob_brl_t, t.COR_ACCENT_2),
        ("Frete internacional", frete_brl_t, t.PALETA_CATEGORICA[0]),
        ("Seguro", seguro_brl_t, t.PALETA_CATEGORICA[2]),
        ("Imposto de Importação", ultimo["ii_brl_t"], "#6B4226"),
        ("AFRMM", ultimo["afrmm_brl_t"], "#8C6E4A"),
        ("Antidumping", ultimo["antidumping_brl_t"], t.COR_NEGATIVO),
        ("Despesas de porto", ultimo["despesas_porto_rs_t"], "#7F8C8D"),
        ("Frete interno", ultimo["frete_interno_rs_t"], "#95A5A6"),
        ("Margem do importador", ultimo["margem_rs_t"], t.COR_ACCENT_1),
    ]
    total = sum(v for _, v, _ in componentes)
    maior = max(componentes, key=lambda item: item[1])

    y_top_wf = c.cabecalho_grafico(
        fig, MARGEM, 0.800, 1 - 2 * MARGEM,
        f"Do FOB ao custo de internação (R$/t) — {_mes_pt(ultimo.name, abreviado=False)}",
        interpretacao=(f"Maior componente: {maior[0]} (R$ {maior[1]:,.0f}/t, "
                       f"{maior[1] / total * 100:.0f}% do custo de internação)."))
    altura_wf = 0.10
    ax_wf = fig.add_axes((MARGEM, y_top_wf - altura_wf, 1 - 2 * MARGEM, altura_wf))
    c.grafico_barras_empilhadas(ax_wf, "Custo de\ninternação", componentes)

    # spread SEMPRE no mesmo mes dos dois lados (df_ipia.index[-1]) - uma
    # formula que soma dois valores nao pode vir de meses diferentes, ao
    # contrario de KPIs independentes lado a lado (ver nota acima)
    spread = ultimo_ipia["preco_domestico_rs_t"] - ultimo_custo_mes_ipia["ppi_brl_t"]
    direcao_spread_txt = ("favorável à importação (custo de internação abaixo do preço doméstico)"
                          if spread > 0 else
                          "favorável ao produto doméstico (custo de internação acima do preço doméstico)"
                          if spread < 0 else "neutro")
    v_preco_pag2 = motor.classificar_preco_domestico(ultimo_ipia)
    selo_preco = c.selo_dado_texto(v_preco_pag2.nivel, v_preco_pag2.proxy)
    y_top_cmp = c.cabecalho_grafico(
        fig, MARGEM, y_top_wf - altura_wf - 0.05, 1 - 2 * MARGEM,
        f"Preço doméstico vs. custo de internação — {_mes_pt(df_ipia.index[-1], abreviado=False)}",
        interpretacao=(f"Spread de R$ {abs(spread):,.0f}/t, {direcao_spread_txt}. Preço doméstico: "
                       f"{selo_preco}." if selo_preco else f"Spread de R$ {abs(spread):,.0f}/t, {direcao_spread_txt}."))
    altura_cmp = 0.10
    c.grafico_barras_horizontais(
        fig, MARGEM, y_top_cmp - altura_cmp, 1 - 2 * MARGEM, altura_cmp,
        ["Preço doméstico", "Custo de internação"],
        [ultimo_ipia["preco_domestico_rs_t"], ultimo_custo_mes_ipia["ppi_brl_t"]],
        cor=t.COR_ACCENT_2, formato_valor="R$ {:,.0f}/t")
    y_apos_spread = c.texto_corrido(
        fig, MARGEM, y_top_cmp - altura_cmp - 0.022, 1 - 2 * MARGEM,
        f"O spread entre preço doméstico e custo de internação (gráfico acima, ambos de "
        f"{_mes_pt(df_ipia.index[-1])}) é de R$ {spread:,.0f}/t, equivalente a "
        f"{ultimo_ipia['ipia'] - 100:+.1f} pts em relação à paridade (IPIA={ultimo_ipia['ipia']:.1f}).",
        bold=True)

    linhas_tabela = [[nome, f"{valor:,.0f}", f"{valor / total * 100:.1f}%"]
                     for nome, valor, _ in componentes]
    linhas_tabela.append(["Total (custo de internação)", f"{total:,.0f}", "100,0%"])
    # altura calculada a partir do numero de linhas (cabecalho + componentes
    # + total), nao um valor fixo escolhido a dedo - antes ficava a uma
    # posicao absoluta fixa na pagina, que colidia com o grafico acima
    # sempre que o cabecalho do grafico (titulo+interpretacao, agora fora
    # do axes) empurrava o conteudo mais para baixo.
    altura_linha_tabela_pt = 13.0
    altura_tabela = (len(linhas_tabela) + 1) * altura_linha_tabela_pt / (t.ALTURA_POL * 72)
    y_topo_tabela = y_apos_spread - 0.015
    c.tabela_simples(fig, (MARGEM, y_topo_tabela - altura_tabela, 1 - 2 * MARGEM, altura_tabela),
                     ["Componente", "R$/t", "% do total"], linhas_tabela,
                     alinhar_direita_a_partir_de=1)

    # so o mes de referencia (ultimo) importa aqui - checar a serie inteira
    # (`.any()`) e um bug: o primeiro mes do historico fica NaN (cambio sem
    # valor anterior para o ffill), e NaN != 0 e True no pandas, o que fazia
    # a checagem dar positivo mesmo com antidumping sempre zerado.
    antidumping_confirmado = pd.notna(ultimo["antidumping_brl_t"]) and ultimo["antidumping_brl_t"] != 0
    nota_antidumping = ("valor real aplicado no período." if antidumping_confirmado else
                        "não confirmado como definitivo — default zerado até confirmação, ver docs/adr da checagem mais recente.")
    c.caixa_texto(
        fig, MARGEM, y_topo_tabela - altura_tabela - 0.015, 1 - 2 * MARGEM,
        f"RESSALVAS: preço doméstico é proxy do segmento \"Siderurgia\" "
        f"({ultimo_ipia['tipo_dado_domestico']}), não específico de bobina a quente "
        f"(ver docs/adr/0003). Antidumping: {nota_antidumping}",
        cor_borda=t.COR_ACCENT_1)

    c.rodape_pagina(fig,
                    "Fonte: Comex Stat (FOB/frete/seguro), BCB/SGS (câmbio). Componentes "
                    "calculados por custo_importacao_rs_t() — nenhum valor recalculado "
                    "neste relatório.",
                    pagina_num=pagina_num, data_geracao=data_geracao)


def pagina_series_temporais(fig, df_ipia: pd.DataFrame, df_custo: pd.DataFrame,
                            data_geracao: dt.datetime, pagina_num: int) -> None:
    """Pagina 3: evolucao mensal (IPIA, penetracao, cambio). Separada da
    pagina de indicadores/origem (pagina 4) porque sao leituras diferentes
    do mesmo relatorio - aqui e "como cada serie andou no tempo", la e
    "onde estamos agora e de onde vem a importacao" - misturar as duas
    numa pagina so deixava a pagina densa demais (3 graficos de linha +
    KPIs + barras + rodape espremidos num unico A4)."""
    c.cabecalho_pagina_interna(fig, "IPIA — Relatório Mensal")
    c.titulo_serif(fig, MARGEM, 0.90, "Séries Temporais", fontsize=19)
    fig.text(MARGEM, 0.868, "Evolução mensal do IPIA, da penetração de importação e do câmbio.",
             transform=fig.transFigure, fontsize=9.5, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, va="top")

    ultimo = df_ipia.iloc[-1]
    spread = ultimo["preco_domestico_rs_t"] - ultimo["ppi_rs_t"]
    penet = ultimo.get("penetracao_importacao_planos_pct")
    tipo_penet = ultimo.get("tipo_dado_penetracao")
    cambio_atual = df_custo["cambio"].iloc[-1] if len(df_custo) else float("nan")

    # cada KPI mostra o PROPRIO periodo mais fresco (ver docs/adr/0008) -
    # IPIA/SPREAD/PENETRACAO vem de df_ipia (intersecao bobina x
    # domestico), CAMBIO vem de df_custo (so bobina) - podem legitimamente
    # divergir (o lado domestico costuma ficar mais atras, ver
    # docs/METODOLOGIA.md secao 7), e cada tile deixa isso visivel em vez
    # de um "atual" generico que esconderia a diferenca.
    periodo_ipia = _mes_pt(ultimo.name)
    periodo_cambio = _mes_pt(df_custo.index[-1]) if len(df_custo) else None
    v_ipia = motor.classificar_ipia(ultimo)
    v_preco = motor.classificar_preco_domestico(ultimo)
    v_penet = motor.classificar_penetracao(ultimo)

    y_kpi = 0.815
    c.kpi_tile(fig, MARGEM, y_kpi, 0.22, "IPIA", f"{ultimo['ipia']:.1f}", cor_valor=t.COR_ACCENT_2,
              periodo=periodo_ipia, selo=c.selo_dado_texto(v_ipia.nivel, v_ipia.proxy))
    c.kpi_tile(fig, MARGEM + 0.24, y_kpi, 0.22, "SPREAD", f"R$ {spread:,.0f}/t",
              periodo=periodo_ipia, selo=c.selo_dado_texto(v_preco.nivel, v_preco.proxy))
    if pd.notna(penet):
        rotulo = "oficial" if tipo_penet == "oficial_mensal" else "aproximado"
        c.kpi_tile(fig, MARGEM + 0.48, y_kpi, 0.22, "PENETRAÇÃO (PLANOS)", f"{penet:.1f}%", nota=rotulo,
                  periodo=periodo_ipia, selo=c.selo_dado_texto(v_penet.nivel, v_penet.proxy) if v_penet else None)
    else:
        c.kpi_tile(fig, MARGEM + 0.48, y_kpi, 0.22, "PENETRAÇÃO (PLANOS)", "n/d", periodo=periodo_ipia)
    c.kpi_tile(fig, MARGEM + 0.72, y_kpi, 0.22, "CÂMBIO (PTAX)", f"R$ {cambio_atual:.2f}",
              periodo=periodo_cambio)  # OBSERVADO puro, sem proxy - selo vazio por definicao (ver selo_dado_texto)

    # IPIA
    delta_periodo = df_ipia["ipia"].iloc[-1] - df_ipia["ipia"].iloc[0]
    interp_ipia = (f"De {df_ipia['ipia'].iloc[0]:.1f} a {df_ipia['ipia'].iloc[-1]:.1f} pontos em "
                   f"{len(df_ipia)} meses ({'alta' if delta_periodo >= 0 else 'queda'} de "
                   f"{abs(delta_periodo):.1f} pts). Linha tracejada em 100 = paridade.")
    y_top1 = c.cabecalho_grafico(fig, MARGEM, 0.740, 1 - 2 * MARGEM, "IPIA — série histórica",
                                 interpretacao=interp_ipia)
    altura1 = 0.110
    ax_ipia = fig.add_axes((MARGEM, y_top1 - altura1, 1 - 2 * MARGEM, altura1))
    c.grafico_linha(ax_ipia, df_ipia.index, df_ipia["ipia"], cor=t.COR_ACCENT_2,
                    ylabel="Pontos (100 = paridade)", linha_ref=100.0)

    # Penetracao
    tem_penet = ("penetracao_importacao_planos_pct" in df_ipia.columns
                and df_ipia["penetracao_importacao_planos_pct"].notna().any())
    if tem_penet:
        serie_pen = df_ipia.dropna(subset=["penetracao_importacao_planos_pct"])
        pmin = serie_pen["penetracao_importacao_planos_pct"].min()
        pmax = serie_pen["penetracao_importacao_planos_pct"].max()
        interp_pen = f"Variação de {pmin:.1f}% a {pmax:.1f}% no período coberto pela série."
        # texto completo do metodo_motivo (quando o mes mais recente e
        # aproximado_consumo_aparente) fica na pagina 4, que tem espaco de
        # sobra - aqui so a legenda ja distingue oficial/aproximado, ver
        # docs/adr/0008.
        legenda_pen = [
            (t.COR_APROXIMADO, "--", "o", "Aproximado (Excel — ver docs/adr/0007)"),
            (t.COR_ACCENT_2, "none", "D", "Oficial (PDF Aço Brasil)"),
        ]
    else:
        interp_pen = "Sem dado disponível na série atual."
        legenda_pen = None
    y_top2 = c.cabecalho_grafico(fig, MARGEM, 0.540, 1 - 2 * MARGEM,
                                 "Penetração de importação (Planos) — Instituto Aço Brasil",
                                 interpretacao=interp_pen, legenda=legenda_pen)
    altura2 = 0.135
    ax_pen = fig.add_axes((MARGEM, y_top2 - altura2, 1 - 2 * MARGEM, altura2))
    if tem_penet:
        ax_pen.plot(serie_pen.index, serie_pen["penetracao_importacao_planos_pct"],
                   color=t.COR_APROXIMADO, linestyle="--", linewidth=1.3, marker="o", markersize=3)
        oficiais = serie_pen[serie_pen["tipo_dado_penetracao"] == "oficial_mensal"]
        if len(oficiais):
            ax_pen.scatter(oficiais.index, oficiais["penetracao_importacao_planos_pct"],
                          color=t.COR_ACCENT_2, s=32, zorder=5, marker="D")
        for spine in ("top", "right", "left"):
            ax_pen.spines[spine].set_visible(False)
        ax_pen.spines["bottom"].set_color(t.COR_LINHA_GRADE)
        ax_pen.grid(axis="y", color=t.COR_LINHA_GRADE, linewidth=0.7)
        ax_pen.set_axisbelow(True)
        ax_pen.tick_params(labelsize=7.5, colors=t.COR_TEXTO_SECUNDARIO, length=0)
        ax_pen.set_ylabel("%", fontsize=8, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS)
    else:
        ax_pen.axis("off")
        ax_pen.text(0.02, 0.5, "Penetração de importação: sem dado disponível na série atual.",
                   transform=ax_pen.transAxes, fontsize=9, color=t.COR_TEXTO_SECUNDARIO,
                   fontfamily=t.FONTE_SANS)

    # Cambio - o primeiro mes do historico pode ficar NaN (ffill sem valor
    # anterior para encadear, ver comentario em pagina_decomposicao_custo)
    # - usa so os meses com valor real para a interpretacao, nunca "R$ nan".
    cambio_valido = df_custo["cambio"].dropna()
    if len(cambio_valido):
        delta_cambio = cambio_valido.iloc[-1] - cambio_valido.iloc[0]
        interp_cambio = (f"De R$ {cambio_valido.iloc[0]:.2f} a R$ {cambio_valido.iloc[-1]:.2f} "
                         f"({'alta' if delta_cambio >= 0 else 'queda'} de R$ {abs(delta_cambio):.2f} no período).")
    else:
        interp_cambio = "Sem dado disponível."
    y_top3 = c.cabecalho_grafico(fig, MARGEM, y_top2 - altura2 - 0.045, 1 - 2 * MARGEM,
                                 "Câmbio (PTAX venda) — série histórica", interpretacao=interp_cambio)
    altura3 = 0.110
    ax_cambio = fig.add_axes((MARGEM, y_top3 - altura3, 1 - 2 * MARGEM, altura3))
    if len(df_custo):
        c.grafico_linha(ax_cambio, df_custo.index, df_custo["cambio"], cor=t.PALETA_CATEGORICA[2],
                        ylabel="R$/US$")
    else:
        ax_cambio.axis("off")

    c.rodape_pagina(fig,
                    "Fontes: Comex Stat (importação), BCB/SGS (câmbio), Instituto Aço Brasil "
                    "(penetração de importação, Planos).",
                    pagina_num=pagina_num, data_geracao=data_geracao)


def pagina_indicadores_origem(fig, df_ipia: pd.DataFrame, df_custo: pd.DataFrame,
                              df_origem: pd.DataFrame, data_geracao: dt.datetime,
                              pagina_num: int) -> None:
    """Pagina 4: onde estamos agora - origem geografica da importacao (com
    espaco de sobra, ao contrario da versao espremida na antiga pagina
    unica de dashboard) e uma tabela de recapitulacao dos ultimos meses.
    """
    c.cabecalho_pagina_interna(fig, "IPIA — Relatório Mensal")
    c.titulo_serif(fig, MARGEM, 0.90, "Indicadores e Origem das Importações", fontsize=19)
    fig.text(MARGEM, 0.868, "De onde vem o aço importado e como os principais indicadores "
             "evoluíram nos últimos meses.",
             transform=fig.transFigure, fontsize=9.5, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, va="top")

    if df_origem is not None and len(df_origem):
        top = df_origem.head(5)
        mi, mf = df_origem.attrs.get("mes_inicio"), df_origem.attrs.get("mes_fim")
        periodo = f"{_mes_pt(mi)}–{_mes_pt(mf)}" if mi is not None and mf is not None else ""
        maior_pais = top.index[0]
        interp_origem = (f"{maior_pais} lidera com {top['pct_do_volume'].iloc[0]:.1f}% do volume "
                         f"importado no período. Os {len(top)} países listados somam "
                         f"{top['pct_do_volume'].sum():.1f}% do total.")
        y_top = c.cabecalho_grafico(fig, MARGEM, 0.795, 1 - 2 * MARGEM,
                                    f"Origem das importações — top países ({periodo})",
                                    interpretacao=interp_origem)
        altura_origem = 0.26
        c.grafico_barras_horizontais(fig, MARGEM, y_top - altura_origem, 1 - 2 * MARGEM, altura_origem,
                                     list(top.index), list(top["pct_do_volume"]),
                                     cor=t.COR_ACCENT_1)
        y_apos_origem = y_top - altura_origem
    else:
        c.cabecalho_grafico(fig, MARGEM, 0.795, 1 - 2 * MARGEM, "Origem das importações",
                            interpretacao="Sem dado disponível.")
        y_apos_origem = 0.50

    # tabela de recapitulacao - ultimos N meses, mesmos dados ja usados nos
    # graficos acima, so reformatados em tabela (nenhum calculo novo)
    n_meses = min(6, len(df_ipia))
    recorte = df_ipia.tail(n_meses)
    linhas = []
    for data_ref, linha in recorte.iterrows():
        spread_mes = linha["preco_domestico_rs_t"] - linha["ppi_rs_t"]
        pen_mes = linha.get("penetracao_importacao_planos_pct")
        pen_txt = f"{pen_mes:.1f}%" if pd.notna(pen_mes) else "n/d"
        cambio_mes = df_custo.loc[data_ref, "cambio"] if data_ref in df_custo.index else float("nan")
        cambio_txt = f"R$ {cambio_mes:.2f}" if pd.notna(cambio_mes) else "n/d"
        linhas.append([_mes_pt(data_ref), f"{linha['ipia']:.1f}", f"R$ {spread_mes:,.0f}/t",
                       pen_txt, cambio_txt])

    c.secao_titulo(fig, MARGEM, y_apos_origem - 0.035, f"ÚLTIMOS {n_meses} MESES")
    y_tabela_bottom = y_apos_origem - 0.05 - 0.033 * (n_meses + 1)
    c.tabela_simples(fig, (MARGEM, y_tabela_bottom, 1 - 2 * MARGEM, 0.033 * (n_meses + 1)),
                     ["Mês", "IPIA", "Spread", "Penetração", "Câmbio"], linhas,
                     alinhar_direita_a_partir_de=1)

    # nota sobre a coluna Penetracao quando o mes mais recente usa formula
    # propria (nao a oficial) - texto completo aqui, onde ha espaco de
    # sobra (a pagina 3 so cabe a versao curta na legenda, ver
    # docs/adr/0008)
    v_penet_pag4 = motor.classificar_penetracao(df_ipia.iloc[-1])
    if v_penet_pag4 is not None and v_penet_pag4.metodo_motivo:
        c.texto_corrido(fig, MARGEM, y_tabela_bottom - 0.025, 1 - 2 * MARGEM,
                        f"Nota sobre a coluna Penetração: {v_penet_pag4.metodo_motivo}",
                        fontsize=7.5, cor=t.COR_TEXTO_SECUNDARIO)

    c.rodape_pagina(fig,
                    "Fontes: Comex Stat (importação, origem), BCB/SGS (câmbio), releases "
                    "trimestrais Usiminas/CSN (preço doméstico), IBGE/SIDRA IPP (encadeamento "
                    "mensal), Instituto Aço Brasil (penetração de importação, Planos).",
                    pagina_num=pagina_num, data_geracao=data_geracao)
