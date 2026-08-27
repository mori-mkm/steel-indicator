# 0008 - Taxonomia OBSERVADO/CALCULADO/ESTIMADO + PROXY e vintage por variável

## Contexto

O relatório PDF (`--pdf-ipia`) já tinha marcadores de proveniência
fragmentados — `tipo_dado_domestico` (`proxy_segmento_aco`/
`especifico_laminado_quente`/`misto`, ver ADR 0003) e
`tipo_dado_penetracao` (`oficial_mensal`/`aproximado_consumo_aparente`,
ver ADR 0007) — cada um com seu próprio vocabulário, sem selo visual
consistente no PDF e sem nenhum conceito de "até quando cada número é
válido" (`report_cutoff`) nem de "qual é o mês real de cada número"
(`reference_period` por variável, não por página).

## Investigação — o problema já estava acontecendo, com dado real

Antes de propor qualquer estrutura nova, verifiquei se o relatório já
misturava períodos sob rótulos genéricos como "atual" — não assumi que
sim ou que não. Rodando o motor com dado real (2020-2026):

```
df_ipia  último mês: 2026-06-01   (IPIA=140.4, preço_doméstico, ppi_rs_t)
df_custo último mês: 2026-07-01   (ppi_brl_t — MÊS DIFERENTE)
df_origem janela:    2026-05 a 2026-07
```

`calcular_ipia_mensal()` intersecta `bobina.index` (Comex Stat) com
`domestico.index` (encadeamento via IPP/IBGE, mais defasado — ver ADR
0002), então seu índice fica limitado ao lado mais lento.
`custo_importacao_detalhado_mensal()` **não faz essa interseção** — usa
só `bobina.index`, que vai um mês além.

A página de decomposição de custo (`pages.pagina_decomposicao_custo`)
usava `df_custo.iloc[-1]` (Julho) junto de `df_ipia.iloc[-1]` (Junho)
como se fossem o mesmo mês, imprimindo **um único** "Mês de referência:
Julho de 2026" para a página inteira. O spread calculado
(`preco_domestico_rs_t` de Junho − `ppi_brl_t` de Julho) dava
**R$ 1.429/t** — um número que não corresponde a nenhum mês real e que
**divergia** do spread já mostrado na capa (R$ 1.508/t, calculado
corretamente dentro de `df_ipia`, mesmo mês nos dois lados). Bug real,
já publicado, não hipotético.

## Decisão

### 1. `report_cutoff` + `reference_period` por variável (não por página)

Cada número exibido ganha seu próprio `reference_period` (mês/janela
real daquele dado específico) em vez de uma noção implícita de "atual"
compartilhada pela página inteira. Variáveis diferentes **podem
legitimamente divergir** — Comex Stat, IPP/IBGE e Aço Brasil têm
defasagens próprias, já documentadas em `docs/METODOLOGIA.md` seção 7 —
e o relatório deve deixar isso visível, não escondê-lo atrás de um
rótulo único.

Duas regras de remediação, aplicadas de acordo com o tipo de exibição:

- **KPIs independentes lado a lado** (linha de KPI da capa; linha de KPI
  da página 3 — IPIA/SPREAD/PENETRAÇÃO de `df_ipia`, CÂMBIO de
  `df_custo`): cada tile mantém seu próprio mês mais fresco, sempre
  rotulado (`periodo=` em `kpi_tile`) — nunca "atual" sozinho, mesmo que
  os tiles da mesma linha acabem mostrando meses diferentes entre si
  (ex.: página 3 mostra Jun/2026 para IPIA/SPREAD/PENETRAÇÃO e Jul/2026
  para CÂMBIO — visível, não escondido).
- **Uma métrica que combina matematicamente dois valores** (o spread da
  página de decomposição, que SOMA preço doméstico + custo de
  internação): os dois lados **têm que vir do mesmo mês**, sempre — isso
  não é preferência de design, é correção aritmética. Corrigido usando
  `df_custo.loc[df_ipia.index[-1]]` em vez de `df_custo.iloc[-1]` só
  nessa combinação específica. O waterfall de decomposição (uma soma
  fechada, sem dependência do lado doméstico) **continua** usando o mês
  mais fresco disponível de `df_custo` — jogar fora dado real só por
  simetria visual seria pior, não melhor; cada bloco da página agora
  imprime seu próprio mês no título do gráfico, em vez de um "Mês de
  referência" único que mentia para metade da página.

Estrutura de dados (`src/indices_setoriais.py`): `VintageInfo`
(dataclass), `classificar_ipia`/`classificar_preco_domestico`/
`classificar_custo_internacao`/`classificar_cambio`/
`classificar_penetracao`/`classificar_origem_importacao`,
`montar_tabela_vintage()` (uma linha por variável — não exibida como
tabela no PDF, é a base que os selos visuais e os selftests consultam),
`validar_report_cutoff()` (detecta `reference_period` posterior ao
cutoff — look-ahead). Fica no motor, não em `reporting/`, porque
interpreta colunas que só o motor conhece (`tipo_dado_domestico`,
`metodo_domestico`, `tipo_dado_penetracao`) — `VintageInfo` não carrega
nenhuma formatação de apresentação (isso é `reporting/components.py`).

### 2. Taxonomia de DOIS EIXOS independentes, não uma escala de 4 degraus

- **`nivel`** (mutuamente exclusivo — quanto processamento o número
  sofreu): `OBSERVADO` (valor direto da fonte) → `CALCULADO` (fórmula
  sobre observados, sem estimativa) → `ESTIMADO` (interpolado,
  encadeado ou suavizado).
- **`proxy`** (booleano, ortogonal — o escopo bate com o rótulo?): pode
  coexistir com qualquer nível. Preço doméstico num trimestre confirmado
  é `CALCULADO + PROXY`; no mesmo trimestre encadeado por IPP vira
  `ESTIMADO + PROXY` — dois problemas diferentes, nunca fundidos num
  único degrau.

Forçar tudo numa escala linear perderia informação real: um valor
`CALCULADO` de escopo errado não é "pior" nem "melhor" que um valor
`ESTIMADO` de escopo certo — são problemas distintos que o leitor
precisa distinguir.

### 3. Mapeamento dos marcadores existentes

| Campo hoje | `nivel` | `proxy` |
|---|---|---|
| Câmbio PTAX (BCB/SGS) | OBSERVADO | não |
| `tipo_dado_penetracao="oficial_mensal"` | OBSERVADO | não |
| `preco_domestico_rs_t` / `ipia` (qualquer trimestre) | CALCULADO | **sim**, sempre (100% do dado carregado hoje é `proxy_segmento_aco`, ver ADR 0003) |
| `metodo_domestico="nivel_trimestral"` | CALCULADO | herda de `tipo_dado_domestico` |
| `interpolado=True` / `suavizado=True` (lado importação) | ESTIMADO | não |
| `metodo_domestico∈{encadeado_ipp, hold_flat_fallback}` | ESTIMADO | herda |
| `tipo_dado_domestico="misto"` | — (é sobre proxy, não nível) | **sim** |
| Origem por país (Comex Stat, agregado) | CALCULADO (soma/percentual é fórmula) | não |

### 4. O caso discutido — `aproximado_consumo_aparente`

Não é `ESTIMADO` (não há interpolação, encadeamento nem suavização — é
uma fórmula direta, Importação/Consumo Aparente, sobre dado real do
mês). Também não é `PROXY` (o alvo conceitual é o mesmo — penetração de
Planos —, não um escopo diferente). É uma **fórmula alternativa/não
oficial para o MESMO alvo**, com divergência documentada (~1,2 p.p.,
ADR 0007) contra a fonte canônica — mesmo Instituto Aço Brasil nos dois
casos (PDF e Excel), então o problema não é confiabilidade da fonte, é
a fórmula usada.

**Decisão**: classificado como `CALCULADO` (é o que a definição
realmente descreve) + `metodo=METODO_FORMULA_ALTERNATIVA` (constante
`"formula_alternativa"` — nome escolhido deliberadamente para não
sugerir "fonte duvidosa", já que a fonte é a mesma; o problema é a
fórmula). Texto visível associado (`metodo_motivo`), renderizado por
extenso na página 4 (nota sobre a coluna Penetração) e resumido na
legenda da página 3: *"Cálculo próprio (Importação/Consumo Aparente)
sobre dado do Aço Brasil — diverge ~1,2 p.p. do número oficial por
METODOLOGIA (fórmula diferente da usada no PDF oficial), não por
confiabilidade da fonte: é o mesmo Instituto nos dois casos. Ver
docs/adr/0007."*

## Alternativas consideradas

- **Escala única de 4 níveis (OBSERVADO/CALCULADO/ESTIMADO/PROXY como
  degraus sequenciais)**: descartada — colapsaria dois problemas
  ortogonais (quanto foi processado vs. escopo correto) numa única
  dimensão, obrigando a escolher um só rótulo quando ambos se aplicam
  (ex.: preço doméstico hoje é simultaneamente CALCULADO e PROXY).
- **Forçar `aproximado_consumo_aparente` em ESTIMADO**: mantém só 4
  rótulos totais, mas ESTIMADO passaria a significar duas coisas
  diferentes (derivação temporal vs. fonte/fórmula alternativa para o
  mesmo alvo) — descartada por diluir o significado do rótulo.
- **Alinhar todo o relatório num único mês por edição** (em vez de
  `reference_period` por variável): mais simples de ler, mas jogaria
  fora dado real disponível (ex.: câmbio de julho, penetração oficial
  mais recente) só por uniformidade visual — descartada; o princípio já
  em vigor no projeto é nunca esconder dado real disponível.

## Consequências

- `VERSAO_METODOLOGIA` de `"1.1"` para `"1.2"`.
- `calcular_ipia_mensal()` ganhou parâmetro `df_bruto` (não tinha —
  fazia uma segunda chamada de rede ao Comex Stat que
  `custo_importacao_detalhado_mensal`/`origem_importacao_bobina_por_pais`
  já evitavam; corrigido e testado com `comex_importacao_ncm`
  bloqueado no selftest).
- `kpi_tile()` ganhou `periodo=`/`selo=`; novo `selo_dado_texto()` em
  `reporting/components.py` (vazio para OBSERVADO puro sem proxy — esse
  é o caso "normal", que não precisa de aviso).
- Novos selftests (seção 21-22): reconciliação do spread + contraprova
  do padrão antigo, detecção de `reference_period` posterior ao cutoff,
  selo nunca omite PROXY/ESTIMADO quando a classificação indica isso,
  classificação de `formula_alternativa`.
- Limitação conhecida: `custo_importacao_detalhado_mensal()` ainda não
  expõe `interpolado`/`suavizado` por linha (só existem em `bobina`,
  internos a `serie_mensal_preco_bobina`) — FOB/frete/seguro na página 2
  são classificados como `CALCULADO` mesmo em meses efetivamente
  suavizados. Não bloqueante para esta versão (nenhum mês do histórico
  atual tem `antidumping` ou suavização ativa no período mais recente),
  mas registrado para não ser esquecido se um mês de baixo volume
  aparecer na decomposição de custo.
