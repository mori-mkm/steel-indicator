# 0018 - Diagnóstico de composição atípica na importação (FOB/frete/seguro)

## Status

**Accepted.** Decisão de infraestrutura/diagnóstico analítico (não é
decisão sobre o índice econômico — IPIA/PPI_COST/Shapley permanecem
exatamente como estavam; `VERSAO_METODOLOGIA` não muda). Aprovada pelo
usuário no prompt que fechou esta tarefa: limiar `0.35` (Opção A, mais
sensível — risco assimétrico favorece detectar mais, dado que o revisor
humano mantém discricionariedade total mesmo com o diagnóstico ativo),
concentração de origem confirmada como **não-gatilho**, e marcador
tipográfico (asterisco) em vez de ícone.

## Contexto

Investigação anterior (jun/2026): o Shapley classificou "Preço FOB" como
maior driver do mês, direção "Alta" (-3,75 pts), enquanto três fontes
externas independentes mostravam o FOB de HRC chinês em **queda** no
mesmo período. A investigação (evidência real, sem suposição) mostrou:

- Cálculo, unidade e rótulo do FOB estavam corretos e consistentes entre
  si — não era bug de cálculo nem de rótulo trocado.
- O FOB blended brasileiro (`serie_mensal_preco_bobina` — soma FOB / soma
  KG de **todas** as origens e NCMs do mês) subiu porque o mix de origem
  mudou: a Coreia do Sul (origem mais barata em maio/2026) praticamente
  saiu do mix em junho (27,3% → 1,6% do volume), enquanto o volume total
  caiu 64% (44.843t → 16.281t, o mês mais baixo em 12 meses). Isolado, o
  FOB chinês de fato caiu (-2,79%), batendo com a pesquisa externa.
- Uma validação anterior já documentada
  (`docs/validation/comex_unit_value_external_hrc_validation.md`) já
  tinha quantificado isso em escala: correlação mês-a-mês do unit value
  Comex vs. benchmark externo é essencialmente zero (0,006) e acurácia
  direcional ~50-55% — divergência mensal não é anomalia nova, é o
  comportamento historicamente já esperado desta série.

Isso não é erro de cálculo — é uma limitação de dado já reconhecida em
`docs/METODOLOGIA.md` §9.7 (viés de valor unitário / composição). Mas até
esta ADR, essa limitação só existia como texto genérico e estático no
relatório (`_DISCLOSURE_BAIXA_LIQUIDEZ`), sem nenhum mecanismo que
identificasse **quais meses especificamente** são afetados, nem que
poupasse o revisor humano de narrativa de caçar uma causa de mercado para
algo que pode ser artefato estatístico.

## Decisão

### 1. Critério de detecção — só volume, nunca concentração de origem

`indices_setoriais.detectar_composicao_atipica_importacao(mes_atual, ...)`
marca um mês como `"atipico"` quando:

```
razao_volume = volume_do_mes / mediana(volume dos 12 meses anteriores)
atipico  <=>  razao_volume < 0.35
```

Só usa dado **anterior** ao mês avaliado (nunca look-ahead, mesmo espírito
de `validar_report_cutoff`). Exige pelo menos 6 meses de histórico
anterior — caso contrário devolve `"indeterminado"` (nunca finge
baseline).

**Concentração de origem foi testada com dado real e rejeitada como
gatilho** (não só assumida): historicamente (2020-2026, 79 meses), o
top-1 país já concentra uma **mediana de ~82%** do volume (P25=62%) — um
limiar do tipo "um país >60%" dispararia na **maioria** dos meses
normais, o oposto de "atípico". O mês de jun/2026 (China 46,1%, Egito
45,1%) na verdade ficou no percentil 5 do lado **oposto** (incomumente
diversificado). O maior swing de share de qualquer país mês-a-mês também
não discriminou (percentil 34 em jun/2026 — nada extremo). Concentração
de origem **continua calculada e devolvida** (top_pais/top_pais_pct),
mas só como contexto explicativo para narrativa/leitor, nunca decide o
`status`.

`LIMIAR_RAZAO_VOLUME_ATIPICO = 0.35` é **ESTIMADO** (mesmo status de
`D_porto`/`D_interno` em §9.8 — ponto de partida documentado, não
calibração definitiva), entre o P10 (0,27) e P15 (0,42) históricos da
razão — a recalibrar quando houver mais histórico. Escolhido no lado mais
sensível (não o P10 exato) porque o revisor humano mantém
discricionariedade total mesmo com o diagnóstico ativo — o custo de um
falso positivo é baixo (o revisor vê a explicação estrutural e decide se
concorda), enquanto o custo de um falso negativo é gastar tempo caçando
notícia para artefato estatístico.

Aplica-se a **fob, freight e insurance** igualmente
(`DRIVERS_VULNERAVEIS_COMPOSICAO`) — os três vêm da mesma agregação
soma/soma sobre as mesmas declarações aduaneiras do mês
(`serie_mensal_preco_bobina`), herdam a mesma vulnerabilidade.

### 2. Conexão com a narrativa mensal — dispensa a busca, não a decide

`scripts/gerar_rascunho_narrativa_mensal.py` (novo) gera o rascunho de
`docs/research/AAAA-MM-narrativa.md` **antes** da busca humana. Para
drivers vulneráveis num mês atípico, a subseção "Buscas realizadas" já
vem pré-preenchida com a explicação estrutural (números reais do
diagnóstico) em vez do placeholder de busca, com nota explícita: *"NÃO é
necessário buscar notícia de mercado para este driver neste mês... busque
apenas se quiser corroborar com evento real conhecido."*

**O diagnóstico não substitui o julgamento humano, só evita busca
inútil por padrão.** `narrativa_status` continua sempre `rascunho`
(ADR 0017 intocada) — o revisor pode adicionar achado real por cima (ex.:
o achado real do FOB chinês caindo seria uma nota complementar válida,
mesmo sem explicar o número brasileiro sozinho). O script nunca
sobrescreve um arquivo já existente (pode ter revisão em andamento ou
aprovada).

### 3. No PDF — marcador tipográfico, nunca ícone

Página 2 do Reporting V3 (`TOP 5 DRIVERS DO MÊS`): quando o mês é
atípico e um driver vulnerável está no top-5, o nome recebe um asterisco
(`"Preço FOB*"`) — nunca ícone/emoji (princípio de design já definido:
relatório não tem aparência de dashboard; mesmo espírito de como a S&P
marca "f" de forecast nos gráficos deles). Uma nota de rodapé curta
aparece só quando há marcador: *"\* Volume do mês abaixo do padrão
histórico — ver Data Confidence, pág. 3."*, apontando para o disclosure
genérico já existente (`_DISCLOSURE_BAIXA_LIQUIDEZ`) — não duplica texto.

Decisão de quais drivers marcar isolada numa função pura
(`reporting.narrative.drivers_com_marcador_atipico`), testável sem
matplotlib. Mês sem diagnóstico atípico: layout idêntico a antes desta
ADR (verificado por render).

### 4. Persistência — computado uma vez, consumido em dois lugares

`scripts/gerar_ipia_hrc_driver_decomposition.py` persiste
`diagnostico_importacao_mensal.csv` (mesmo `OUT_DIR` dos outros
artefatos de decomposição) — calculado **uma vez**, lido tanto pelo
scaffold de narrativa quanto pelo PDF
(`report_builder.carregar_diagnostico_importacao_se_disponivel`), para
nunca divergirem sobre se um mês é atípico.

## Consequências

- Meses sem histórico suficiente (`indeterminado`) nunca são marcados —
  não é falso "normal".
- O limiar `0.35` pode gerar falsos positivos ocasionais (meses de
  volume baixo por razão legítima, não composicional) — aceito, dado que
  o revisor humano decide o que fazer com o diagnóstico, nunca é
  publicado como afirmação definitiva.
- Nenhuma mudança de layout/número em meses não afetados.

## Alternativas consideradas

- **Concentração de origem como gatilho (`>60%` um país)**: rejeitada com
  evidência — dispararia na maioria dos meses normais deste mercado.
- **HHI (Herfindahl-Hirschman) de origem como métrica de concentração**:
  considerado, não implementado — o problema não é a métrica de
  concentração em si, é que concentração/fragmentação de origem não se
  mostrou um sinal robusto neste mercado (testado de duas formas
  diferentes, ambas inconclusivas); reavaliar só se surgir evidência de
  que HHI se comporta melhor que top-1 share.
- **Ícone/emoji de alerta no PDF**: rejeitado — contradiz o princípio de
  design já definido para o relatório (sem aparência de dashboard).

## Critério de revisão

Recalibrar `LIMIAR_RAZAO_VOLUME_ATIPICO` quando houver histórico
suficiente para validar a taxa de falsos positivos/negativos na prática
(mesmo espírito do critério de N ciclos da ADR 0017). Reavaliar
concentração de origem como sinal complementar se um indicador melhor
calibrado (ex. HHI com mais histórico) mostrar poder discriminante que
top-1 share não mostrou aqui.
