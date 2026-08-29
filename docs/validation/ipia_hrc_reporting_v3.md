# IPIA-HRC — Reporting V3

**Status: IMPLEMENTADO.** Redesign da camada de apresentação (PDF) do
IPIA-HRC — nenhum valor de IPIA/PPI mudou, nenhuma vintage nova foi
criada, `VERSAO_METODOLOGIA` permanece `"1.5"`. `--pdf-ipia` passa a
gerar o relatório V3 por padrão; o caminho V2
(`reporting.report_builder.gerar_relatorio_ipia_hrc`) permanece intacto
e testado, disponível para quem precisar reproduzi-lo diretamente.

Reproduzir: `python src/indices_setoriais.py --pdf-ipia` (usa a última
vintage publicada + o artefato de decomposição de
`scripts/gerar_ipia_hrc_driver_decomposition.py`, se disponível — nunca
busca rede nem recalcula metodologia).

## Information architecture

Princípio central (ordem de leitura, não de implementação): **o que
aconteceu → o que significa → por que aconteceu matematicamente → qual
o grau de confiança → o que acompanhar a seguir.**

| Página | Nome | Responde |
|---|---|---|
| 1 | Market View | O que aconteceu + o que significa (headline executivo, sinal de paridade, principais drivers do mês) |
| 2 | Import Parity & Drivers | Por que aconteceu matematicamente (waterfall Shapley, top 5 drivers, composição do PPI_COST) |
| 3 | History & Confidence | Contexto histórico + grau de confiança (série completa, posição histórica, data confidence, disclosures) |
| 4 | Methodology & Watchlist | Metodologia resumida + o que acompanhar a seguir (glossário, watchlist, data cut) |

## Page structure

- **Page 1 (Market View)**: hero number (IPIA-HRC, tipografia serif
  grande) + Δ MoM/Δ YoY em pontos + IMPORT PARITY SIGNAL (Domestic
  Premium / Import-Cost Premium / At Parity, com distância exata em
  pontos — nunca uma faixa "near parity" com corte numérico arbitrário)
  + headline/interpretação determinística + "O que mudou no mês" (até 3
  drivers) + report info strip.
- **Page 2 (Import Parity & Drivers)**: PPI_COST headline + nota
  PPI_OFFER secundária (cenário 3%, nunca headline) + waterfall
  `IPIA_{t-1} → IPIA_t` (Shapley exato, fecha exatamente) + tabela top 5
  drivers + composição do PPI_COST (barra empilhada).
- **Page 3 (History & Confidence)**: série completa (gaps reais em
  UNKNOWN, cores distintas por status) + posição histórica (percentil/
  mediana/min/max) + painel de confiança (status traduzido + disclosures
  de proxy doméstico/baixa liquidez/unit-value bias).
- **Page 4 (Methodology & Watchlist)**: diagrama de metodologia em 3
  linhas + glossário (6 termos) + watchlist (FOB/FX/frete/doméstico,
  direção atual + contribuição recente) + data cut.

## Narrative rules

Função determinística principal: `reporting.narrative.gerar_resumo_executivo_ipia(
ipia_atual, ipia_anterior, decomposicao, publication_status)`.

- **Vocabulário fechado**: toda palavra vem de templates fixos +
  `indices_setoriais.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC` — nunca texto
  livre injetado, nunca um LLM. Testado explicitamente
  (`test_narrativa_nunca_contem_causalidade_externa`) contra uma lista
  de termos proibidos (Fed, China, guerra, juros, governo, minério,
  demanda, geopolítica, banco central, OPEP, estímulo) — nenhum aparece
  na saída em nenhum cenário testado.
- **Direção do valor a partir da polaridade conhecida da fórmula**: uma
  contribuição negativa de um driver de custo significa que o valor
  subjacente SUBIU (PPI_COST mais caro reduz o IPIA) — para
  `domestic_price`, a relação é direta. Isso é matemática, não
  causalidade externa (`direcao_valor_driver`).
- **Ranking por `abs(contribuição)`** (nunca percentual líquido —
  cancelamentos gerariam percentuais sem sentido), separando drivers na
  MESMA direção do movimento (líderes) do de direção OPOSTA
  (compensador) — no máximo 3 drivers citados na sentença principal.
- **Linguagem auditável**: "principal contribuição do mês", "segunda
  maior contribuição", "parcialmente compensado por" — nunca "forte"/
  "fraco"/"pressão significativa" sem regra quantitativa.

## Driver presentation

A decomposição Shapley (`indices_setoriais.decompor_variacao_ipia_hrc`,
sprint anterior) é lida de um artefato JÁ PERSISTIDO
(`scripts/gerar_ipia_hrc_driver_decomposition.py` →
`data/processed/validation/ipia_hrc_driver_decomposition/decomposicao_mensal.csv`),
**nunca recalculada dentro do reporting** — consistente com o contrato
"report-from-vintage" já estabelecido para o V2. Se o artefato não
existir ou não corresponder à vintage/período sendo relatado
(`vintage_id` diferente), o relatório degrada graciosamente (sem
waterfall/narrativa de driver, nunca fabrica um número) — testado
explicitamente
(`test_decomposicao_de_vintage_diferente_e_ignorada_nunca_misturada`).

A composição absoluta do PPI_COST (Page 2, "onde está o custo") exigiu
um NOVO artefato (`componentes_mensais.csv`, níveis absolutos por mês —
não apenas as transições MoM que `decomposicao_mensal.csv` já tinha) —
extensão mínima do script de decomposição existente (os componentes já
eram calculados em memória, só passaram a ser persistidos).

Waterfall: contribuições abaixo de 0.05 pt são agrupadas visualmente em
"Outros" (`reporting.narrative.agrupar_para_waterfall`, testado
isoladamente) — a soma do que é desenhado nunca diverge da soma real;
nenhum driver é descartado do CSV/audit trail subjacente, só do desenho.

## Confidence presentation

`publication_status` é traduzido por template fixo
(`montar_confidence_sentence`) — nunca o jargão técnico exposto cru
("PROVISIONAL" vira uma frase explicando o que isso significa em
termos de PIA/IPP). Disclosures de proxy doméstico, baixa liquidez e
unit-value bias são reaproveitados/resumidos dos textos já aprovados em
`reporting.pages` (`_DISCLOSURE_PROXY_DOMESTICO`/`_DISCLOSURE_BAIXA_LIQUIDEZ`),
nunca reescritos.

Diagnósticos de liquidez granulares (NCMs ativos, número de origens,
HHI de origem) **não foram integrados** ao relatório — ver Limitations.

## Chart inventory

| Gráfico | Página | Componente novo? |
|---|---|---|
| Import Parity Signal (callout) | 1 | Não (texto) |
| Waterfall Shapley `IPIA_{t-1}→IPIA_t` | 2 | **Sim** — `components.grafico_waterfall` |
| Composição do PPI_COST (barra empilhada) | 2 | Não — reusa `grafico_barras_empilhadas` (V1) |
| Histórico completo com gaps/status | 3 | Não — reusa o padrão de `pagina_dinamica_historica_ipia_hrc` (V2) |
| Diagrama de metodologia (3 linhas) | 4 | Não (texto) |

Todo gráfico tem título factual + leitura interpretativa (via
`components.cabecalho_grafico`, já existente) — nenhum gráfico órfão.

## Design decisions

- **Fontes portáveis** (Sec.39): `theme.FONTE_SANS`/`FONTE_SERIF`
  resolvidos UMA VEZ, na importação, para o primeiro nome de uma lista
  de preferência que esteja de fato instalado
  (`matplotlib.font_manager.fontManager.ttflist`) — nunca uma lista
  passada direto a `fontfamily=[...]` (medido empiricamente nesta
  etapa: isso faz o matplotlib emitir um warning `findfont: ... not
  found` por candidato ausente ANTES de resolver, o que pioraria o
  ruído de log que a correção pretendia eliminar). Preferência:
  Arial/Georgia → Liberation Sans/Serif → DejaVu Sans/Serif (bundled
  com o próprio matplotlib, garantia de zero warning em qualquer
  ambiente). Verificado: geração completa do relatório real produz
  **zero** warnings de fonte.
- **`--pdf-ipia` aponta para V3 por padrão** (não uma nova flag) — este
  é um projeto de pesquisa independente sem consumidor externo do
  arquivo PDF em si (README, seção Disclaimer); o V2
  (`gerar_relatorio_ipia_hrc`) permanece intacto e com sua suíte de
  testes original protegendo-o, disponível para chamada direta.
- **Reporting nunca recalcula decomposição** — a matemática (Shapley)
  vive em `indices_setoriais`/`steel_indicator.domain`; o script de
  geração (`scripts/gerar_ipia_hrc_driver_decomposition.py`) persiste o
  resultado; o reporting só lê e apresenta (`.claude/rules/reporting.md`).
- **QA visual real** (Sec.52): o PDF gerado foi rasterizado
  página-a-página via PyMuPDF (`fitz`) e inspecionado visualmente nesta
  etapa — 3 problemas reais encontrados e corrigidos: (1) o diagrama de
  metodologia em 3 linhas estava sendo concatenado numa única linha
  corrida (fix: 3 `fig.text` separados); (2) definições do glossário
  eram cortadas na borda da tabela (fix: definições encurtadas para
  caber numa linha, `tabela_simples` não quebra texto); (3) o bloco
  "Data Cut" colidia visualmente com o rodapé da página 4 (fix: y
  ajustado com folga generosa). Nenhum destes seria pego só verificando
  "o arquivo foi criado".

## Limitations

1. **Diagnósticos de liquidez granulares (NCMs ativos, origens, HHI) não
   estão no relatório** — calculá-los exigiria dado bruto do Comex Stat
   não persistido na vintage (mesmo motivo já documentado para a
   decomposição de drivers), e o script existente que os calcula
   (`scripts/analisar_ipia_hrc_liquidez.py`) é puramente de validação,
   não persiste um artefato pronto para consumo do reporting. Manter o
   relatório estritamente "report-from-artefato-já-persistido" (Sec.49)
   pesou mais do que adicionar mais uma dependência de rede ao
   reporting nesta etapa — fica como trabalho futuro caso o script de
   liquidez seja estendido a persistir um artefato análogo ao da
   decomposição.
2. **HTML não implementado** — avaliado (Sec.44), mas a mesma camada de
   dados (`preparar_dados_relatorio_ipia_hrc_v3`) já está isolada de
   matplotlib o suficiente para permitir isso no futuro sem retrabalho
   de dados, só uma nova camada de apresentação — não implementado
   nesta etapa por seguir a preferência explícita "PDF é prioridade".
3. **Whitespace inferior nas páginas 1 e 3**: o conteúdo determinístico
   de cada mês não preenche a página inteira, deixando espaço em branco
   considerável na parte inferior. Avaliado como aceitável (não um bug)
   dado o objetivo explícito de design "clean, sóbrio, não dashboard" —
   nenhuma seção foi inflada artificialmente só para preencher espaço,
   o que violaria a regra "não duplicar conteúdo" (Sec.42). Se o
   inventário de conteúdo crescer no futuro (ex. sparkline de 12 meses
   reintroduzida da Page 1 do V2), esse espaço tem onde absorver.
4. **Decomposição exige geração prévia do artefato** — se
   `scripts/gerar_ipia_hrc_driver_decomposition.py` nunca foi rodado
   para a vintage atual, `--pdf-ipia` emite um aviso explícito no
   terminal e gera o relatório sem waterfall/narrativa de driver (nunca
   falha, nunca fabrica número) — o operador precisa rodar os dois
   scripts em sequência para o relatório completo.
5. **PPI_OFFER só aparece como nota secundária na Page 2** — nunca como
   headline, conforme decisão aprovada (ADR 0015) — se uma futura
   decisão quiser destacar cenários de margem, isso é uma extensão da
   Page 2, não uma mudança de escopo desta etapa.

## References

- ADR 0015 (Cost/Offer scope), ADR 0016 (Shapley decomposition method).
- `docs/validation/ipia_hrc_driver_decomposition.md` — decomposição
  reusada por este relatório.
- `src/reporting/narrative.py`, `src/reporting/pages_v3.py`,
  `src/reporting/report_builder.py` (funções V3), `src/reporting/theme.py`
  (fontes portáveis), `src/reporting/components.py` (`grafico_waterfall`).
- `tests/unit/test_reporting_narrative.py`, `tests/unit/test_reporting_v3.py`.
