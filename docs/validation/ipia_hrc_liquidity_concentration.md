# IPIA-HRC — Liquidity / Concentration Hardening

**Status: VALIDATION + DIAGNOSTICS ONLY — não implementa nenhuma mudança.**
Nenhum threshold de liquidez foi criado, nenhum mês/NCM/país foi excluído,
nenhum weighting foi alterado, nenhum dado foi imputado. PPI, IPIA,
publication status, vintages e `VERSAO_METODOLOGIA` permanecem exatamente
como estavam antes desta etapa.

Reproduzir: `docker build -t steel-indicator-dev .` seguido de
`docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/analisar_ipia_hrc_liquidez.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`). Reusa integralmente
as funções de coleta/agregação de
`scripts/validar_comex_unit_value_hrc.py` (sprint anterior) — nunca
reimplementa Comex Stat, UN Comtrade ou a cesta HRC.

## Question

> Quão representativo e estável é o unit value mensal do Comex Stat em
> função de volume, número de NCMs, origens e concentração?

## 1. Executive conclusion

- **Volume**: distribuição historicamente muito ampla — mediana ≈21.930t/mês,
  mas o P5 é ≈1.660t e o mínimo observado é 55t (praticamente um único
  embarque). Um fator de ~85× separa P5 de P95.
- **NCMs ativas**: mediana de 8 dos 13 códigos da cesta oficial ativos por
  mês (nunca os 13 simultaneamente — máximo observado é 12); o código
  dominante sozinho já responde, em mediana, por 54,6% do volume do mês
  (`share_largest_ncm`).
- **Origens**: mediana de apenas 4 países ativos por mês, e o país
  dominante já responde, em mediana, por **81,7%** do volume mensal
  (`share_largest_origin`) — em 5% dos meses, um único país é praticamente
  100% da cesta.
- **HHI**: HHI_origin mediano = 0,697 (0-1) / 6.974 (0-10.000) — por
  convenção antitruste (DOJ/FTC, referência conceitual, não um contrato
  do projeto), isso já está na faixa "altamente concentrado" (>0,25) na
  maioria dos meses. HHI_ncm mediano = 0,371 — moderadamente concentrado.
  `effective_origins` mediano = **1,43** — na prática, o Brasil importa
  HRC de pouco mais de uma origem "equivalente" num mês típico.
- **Concentração × volatilidade**: relação real e **robusta** — removendo
  o mês degenerado de 2020-12 (ver abaixo), `corr(HHI_origin, |ΔUV|
  all-origin)` permanece em 0,28 (era 0,29) e `corr(HHI_ncm, |ΔUV|)`
  permanece em 0,19 (era 0,21). Concentração mais alta associa-se, de
  forma estável, a maior instabilidade mês a mês do unit value agregado.
- **Volume × instabilidade**: a relação mais forte e mais robusta de toda
  a análise — `corr(log(volume), |ΔUV| all-origin) = -0,46`, **idêntica**
  com ou sem o mês degenerado (-0,464 vs. -0,456). Mais volume, unit
  value mais estável — achado limpo, não um artefato.
- **Erro externo (China vs. UN Comtrade)**: ao contrário das duas relações
  acima, a associação entre concentração/volume e o **erro contra o
  benchmark externo** (do sprint anterior) **não é robusta** — colapsa ou
  inverte de sinal ao remover um único mês degenerado (ver Seção 8). Não
  deve ser citada como evidência de que concentração prejudica a
  comparação externa.
- **Outlier de 14kg (2020-12, origem China)**: investigado a fundo (Seção
  9) — é uma linha real do Comex Stat (1 registro, NCM 72082790, FOB
  US$600, 14kg), mas **irrelevante para a série oficial**: o total
  ALL-ORIGIN do mês foi 4.071.502kg (99,1% Rússia), então a China
  representou **0,000344%** do volume total daquele mês. O outlier
  distorce só a comparação China-específica do sprint anterior — nunca
  a série oficial (que agrega todas as origens, ponderada por volume).
- **Evidence strength**: **MODERATE** para "concentração/volume importam
  para a estabilidade do unit value oficial" (relação robusta, direção
  economicamente coerente, N=89-90 meses); **WEAK/artefato** para
  "concentração explica o erro contra o benchmark externo" (não
  sobrevive à remoção de um único ponto).

## 2. Monthly diagnostics

90 meses (2019-01 a 2026-07), cálculo sobre dado bruto pré-agregação
(todas as origens — a mesma base que alimenta o PPI oficial bottom-up),
6 últimos meses como amostra (tabela completa em
`data/processed/validation/ipia_hrc_liquidity_concentration/diagnosticos_mensais.csv`):

| Mês | total_kg | n_active_ncm | n_origins | share_largest_ncm | share_largest_origin | HHI_origin | HHI_ncm |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-02 | 71.452.219 | 10 | 5 | 36,1% | 72,2% | 0,593 | 0,272 |
| 2026-03 | 72.197.254 | 11 | 3 | 40,6% | 55,7% | 0,409 | 0,270 |
| 2026-04 | 39.663.011 | 9 | 3 | 53,3% | 53,1% | 0,502 | 0,346 |
| 2026-05 | 44.843.420 | 11 | 4 | 43,3% | 48,3% | 0,367 | 0,248 |
| 2026-06 | 16.281.008 | 9 | 5 | 53,1% | 46,1% | 0,421 | 0,364 |
| 2026-07 | 54.687.409 | 5 | 5 | 73,1% | 47,6% | 0,335 | 0,572 |

**Distribuição histórica completa** (min / P5 / P10 / P25 / mediana / P75
/ P90 / P95 / max):

| Métrica | min | P5 | P10 | P25 | mediana | P75 | P90 | P95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| total_kg | 55.100 | 1.659.000 | 3.192.000 | 8.460.000 | 21.930.000 | 48.280.000 | 72.480.000 | 84.110.000 | 142.200.000 |
| n_active_ncm | 2 | 3,45 | 4 | 6 | 8 | 10 | 11 | 12 | 12 |
| n_origins | 1 | 2 | 2 | 3 | 4 | 5 | 6 | 6,55 | 8 |
| share_largest_ncm | 27,0% | 34,1% | 36,5% | 43,5% | 54,6% | 69,1% | 85,4% | 89,3% | 99,4% |
| share_top3_ncm | 68,1% | 72,7% | 76,0% | 82,3% | 89,5% | 96,2% | 99,6% | 100% | 100% |
| share_largest_origin | 34,7% | 44,7% | 50,9% | 62,5% | 81,7% | 94,3% | 99,2% | 99,4% | 100% |
| share_top3_origins | 92,2% | 97,2% | 98,8% | 99,8% | 100% | 100% | 100% | 100% | 100% |
| china_share | 0% | ~0% | 2,8% | 11,1% | 40,0% | 84,8% | 97,9% | 99,3% | 99,8% |

**Nota de nomenclatura (Sec.7/8 do sprint)**: `n_comex_rows` (registrado
no CSV completo) é o número de combinações `(NCM, país)` com `kg>0`
devolvidas pelo endpoint `/general` do Comex Stat no mês — **não** é uma
contagem de operações aduaneiras/declarações de importação reais (o
endpoint com `details=["ncm","country"]` já entrega dado agregado por
essas duas dimensões, sem granularidade de BL/declaração individual).
`exporter`/fornecedor não é um campo pedido em nenhum `details` do
payload (`steel_indicator/sources/comex.py`) — **EXPORTER CONCENTRATION
NOT OBSERVABLE** neste pipeline; nenhuma tentativa foi feita de inferir
exportador a partir de país/NCM.

## 3. HHI origin

| Escala | min | P5 | P10 | P25 | mediana | P75 | P90 | P95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0–1 | 0,329 | 0,356 | 0,407 | 0,500 | 0,697 | 0,893 | 0,983 | 0,989 | 1,000 |
| 0–10.000 | 3.288 | 3.555 | 4.066 | 5.001 | 6.974 | 8.926 | 9.832 | 9.889 | 10.000 |

`HHI_origin = Σ share_country²`, participação em KG (nunca em número de
registros). Mesmo o P25 (0,50) já está acima do limiar convencional de
"altamente concentrado" — a cesta HRC do Brasil por origem é
estruturalmente concentrada na maior parte da amostra, não só em meses
excepcionais.

## 4. HHI NCM

| Escala | min | P5 | P10 | P25 | mediana | P75 | P90 | P95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0–1 | 0,184 | 0,221 | 0,250 | 0,289 | 0,371 | 0,537 | 0,747 | 0,805 | 0,989 |
| 0–10.000 | 1.838 | 2.205 | 2.503 | 2.893 | 3.705 | 5.374 | 7.469 | 8.054 | 9.888 |

Consistentemente mais baixo que HHI_origin — a cesta de 13 NCMs, mesmo
com um código tipicamente dominante, é menos concentrada que a
distribuição por país de origem. Isso é particularmente relevante dado o
unit value bias documentado no sprint anterior (`docs/METODOLOGIA.md`
§9.7): a origem geográfica concentra mais que o produto (NCM).

## 5. Effective numbers

`effective_origins = 1/HHI_origin`, `effective_ncms = 1/HHI_ncm`:

| Métrica | min | P5 | P10 | P25 | mediana | P75 | P90 | P95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| effective_origins | 1,00 | 1,01 | 1,02 | 1,12 | **1,43** | 2,00 | 2,46 | 2,81 | 3,04 |
| effective_ncms | 1,01 | 1,24 | 1,34 | 1,86 | **2,70** | 3,46 | 4,00 | 4,53 | 5,44 |

**Leitura**: mesmo no mês mais diversificado já observado, o Brasil nunca
teve mais que ~3 origens "efetivamente equivalentes" de HRC — o número
nominal de países ativos (mediana 4, Seção 2) superestima a diversidade
real de mercado, porque o volume não se distribui igualmente entre eles.

## 6. Volume diagnostics

Ver distribuição completa na Seção 2. Resumo qualitativo: a cesta HRC do
Brasil é estruturalmente um mercado de baixo volume com picos ocasionais
— a razão P95/P5 é de ~51× para `total_kg`, contra ~2× para índices de
preço bem comportados. Essa amplitude por si só já é evidência
qualitativa de que qualquer estatística de nível/variação sobre o unit
value agregado deve ser lida com cautela nos meses de cauda inferior.

## 7. Concentration vs unit value

`corr(HHI, |ΔUV| all-origin)` — com e sem o mês degenerado de 2020-12
(que, como mostrado na Seção 9, tem volume ALL-ORIGIN normal de 4,07M kg
e HHI_origin=0,983 — ele **não** é um outlier de volume no all-origin,
só na fatia China; por isso entra normalmente nesta análise, que é
all-origin):

| Associação | Pearson (com 2020-12) | Pearson (sem 2020-12) | N |
|---|---:|---:|---:|
| HHI_origin × \|ΔUV\| all-origin | 0,290 | 0,277 | 89 / 88 |
| HHI_ncm × \|ΔUV\| all-origin | 0,214 | 0,193 | 89 / 88 |
| log(volume) × \|ΔUV\| all-origin | **-0,464** | **-0,456** | 89 / 88 |

**Robusto** — nenhuma das três associações muda de sinal ou de magnitude
relevante ao remover o único mês verdadeiramente atípico da série
(2020-12, que aqui é atípico só pela fatia China, não pelo all-origin).
A associação mais forte e mais consistente é volume (não concentração)
com instabilidade — mais volume, unit value agregado mais estável.

**Quantis de volume** (bottom 25% / middle 50% / top 25%, `total_kg`):

| Grupo | N | \|ΔUV\| médio | HHI_origin médio | HHI_ncm médio | total_kg médio |
|---|---:|---:|---:|---:|---:|
| bottom25 | 23 | 17,9% | 0,785 | 0,587 | 4,1M |
| middle50 | 44 | 10,8% | 0,691 | 0,407 | 24,3M |
| top25 | 23 | 5,7% | 0,574 | 0,323 | 74,4M |

Gradiente monotônico e claro nas três colunas — quanto maior o volume,
menor a instabilidade do unit value **e** menor a concentração média.
Volume e concentração andam juntos (meses de baixo volume tendem a ser
mais concentrados), o que é esperado economicamente, não uma coincidência
estatística.

**Quantis de concentração** (bottom 25% / middle 50% / top 25% de
`HHI_origin`):

| Grupo | N | \|ΔUV\| médio | total_kg médio |
|---|---:|---:|---:|
| bottom25 (menos concentrado) | 23 | 7,7% | 41,5M |
| middle50 | 44 | 8,8% | 31,8M |
| top25 (mais concentrado) | 23 | 19,4% | 22,5M |

Mesmo padrão: o grupo mais concentrado tem instabilidade de unit value
mais que o dobro do grupo intermediário.

## 8. External-error relationship

**Aqui a relação NÃO é robusta** — ao contrário da Seção 7:

| Associação | Pearson (com 2020-12) | Pearson (sem 2020-12) | N |
|---|---:|---:|---:|
| HHI_origin × \|erro externo\| China | 0,162 | **-0,312** (inverte de sinal) | 66 / 65 |
| HHI_ncm × \|erro externo\| China | 0,226 | **0,012** (colapsa) | 66 / 65 |
| log(volume) × \|erro externo\| China | -0,149 | **-0,017** (colapsa) | 66 / 65 |

E nos quantis de HHI_origin, o grupo mais concentrado (`top25`) tem erro
externo médio de **250%** com o mês incluído, caindo para **12,8%** sem
ele — quase 20× de diferença por causa de um único ponto.

**Conclusão desta seção**: a aparente relação entre concentração/volume e
"pior tracking do benchmark externo" observada informalmente no sprint
anterior era, na maior parte, um artefato do mês de 14kg — não deve ser
citada como achado робusto. A relação real e robusta (Seção 7) é sobre a
**instabilidade interna** do unit value all-origin, não sobre o erro
contra a UN Comtrade.

## 9. Outliers

Revisitando os 10 outliers já identificados no sprint anterior (todos na
fatia China, dado all-origin do mesmo mês em parênteses):

| Mês | total_kg (all-origin) | n_active_ncm | n_origins | HHI_ncm | HHI_origin | largest_ncm | largest_origin |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2020-12 | 4.071.502 | 5 | 4 | 0,796 | **0,983** | 88,5% | **99,1%** |
| 2019-05 | 16.290.474 | 7 | 7 | 0,536 | 0,354 | 70,7% | 41,2% |
| 2021-01 | 41.841.280 | 5 | 3 | 0,749 | 0,568 | 85,9% | 70,2% |
| 2021-04 | 11.862.356 | 8 | 5 | 0,692 | 0,388 | 82,6% | 51,2% |
| 2022-11 | 31.205.494 | 10 | 6 | 0,320 | 0,356 | 52,6% | 42,5% |
| 2022-10 | 18.318.290 | 8 | 4 | 0,293 | 0,711 | 41,5% | 83,8% |
| 2021-06 | 25.690.597 | 8 | 5 | 0,267 | 0,515 | 34,7% | 60,7% |
| 2021-03 | 39.425.045 | 7 | 5 | 0,454 | 0,714 | 62,5% | 83,3% |
| 2021-08 | 4.000.840 | 4 | 2 | 0,671 | 0,894 | 80,6% | 94,4% |
| 2022-08 | 5.136.674 | 7 | 3 | 0,268 | 0,932 | 38,1% | 96,5% |

**Leitura**: 6 dos 10 outliers têm `HHI_origin>0,5` (concentração
"moderada a alta" pela convenção antitruste) — consistente com, mas não
prova de, a hipótese de que estrutura de mercado concentrada coincide com
outliers de unit value. Os outros 4 (2019-05, 2021-04, 2022-11, 2021-06)
têm `HHI_origin<0,52` — outliers de unit value **também ocorrem em meses
de origem diversificada**, então concentração não é condição necessária
nem suficiente para explicar um outlier isoladamente.

## Caso dedicado: o mês de 14kg (2020-12, origem China)

Linha crua exata do Comex Stat:

| coNcm | country | metricFOB (US$) | metricKG |
|---|---|---:|---:|
| 72082790 | China | 600 | **14** |

- **Referência temporal**: 2020-12.
- **NCM**: 72082790 (decapada, ver `NCM_BOBINA_QUENTE`).
- **Origem**: China.
- **FOB**: US$600 — implica UV=US$42.857/t se tratado como unit value
  representativo, o que não é (é literalmente um único embarque de 14kg,
  provavelmente amostra comercial ou erro de arredondamento de unidade na
  fonte, não um fluxo de mercado real).
- **Participação no agregado**: **0,000344%** do volume ALL-ORIGIN do mês
  (4.071.502kg) — o mês de dezembro/2020 foi 99,1% Rússia
  (4.036.750kg), não China.
- **Por que apareceu na análise externa**: o sprint anterior comparou
  especificamente `UV_China_HRC_t` (só origem China) contra o benchmark
  UN Comtrade — nessa fatia isolada, 14kg *é* o volume total do mês, então
  um único registro de FOB baixo domina o unit value calculado daquele
  mês inteiro.
- **Afeta a série oficial?** **Não.** O PPI oficial (`agregar_ipia_hrc_multi_ncm_mensal`,
  §9.5.2) pondera por KG **todas** as origens simultaneamente — o peso de
  14kg dentro de um total de ~4,07 milhões de kg é estatisticamente nulo
  (0,000344%). Este caso afeta **exclusivamente** a comparação
  China-específica construída no sprint de validação externa, nunca o
  PPI/IPIA publicados.

## 10. Regimes

| Ano | N meses | total_kg médio | n_active_ncm médio | n_origins médio | HHI_ncm médio | HHI_origin médio | china_share médio | \|ΔUV\| médio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 12 | 9,7M | 6,17 | 4,67 | 0,592 | 0,678 | 29,5% | 8,8% |
| 2020 | 11 | 6,9M | 4,73 | 2,73 | 0,614 | **0,911** | 29,6% | **26,5%** |
| 2021 | 12 | 24,4M | 6,75 | 3,67 | 0,532 | 0,698 | 35,2% | 10,7% |
| 2022 | 12 | 12,9M | 7,17 | 3,67 | 0,368 | 0,674 | 68,6% | 14,1% |
| 2023 | 12 | 41,4M | 9,17 | 3,50 | 0,327 | 0,612 | 53,2% | 12,0% |
| 2024 | 12 | 50,3M | 10,00 | 3,92 | 0,341 | 0,793 | 85,7% | 4,8% |
| 2025 | 12 | 66,7M | 10,33 | 5,25 | 0,307 | 0,589 | 42,6% | 7,4% |
| 2026* | 7 | 47,7M | 9,14 | 4,43 | 0,352 | 0,446 | 25,6% | 3,9% |

*2026 parcial (até jul/2026).

**Leitura**: **2020 é o ano mais concentrado por origem (HHI_origin médio
0,911) e o mais instável (`|ΔUV|` médio 26,5%, mais que o dobro de
qualquer outro ano)** — coerente com o choque COVID e a dominância
temporária da Rússia (71,5% do volume em 2020, ver sprint anterior).
`n_active_ncm` cresce de forma quase monotônica ao longo do tempo (6,2 em
2019 → 10,3 em 2025) — a cesta ficou mais diversificada por produto.
`HHI_ncm` cai na mesma direção (0,59 → 0,31) — o mesmo padrão de
diversificação. `HHI_origin`, ao contrário, **não** mostra tendência
monotônica — oscila entre 0,45 e 0,91 ano a ano, refletindo trocas de
origem dominante (Rússia → China → Coreia do Sul, já documentadas no
sprint anterior) mais do que uma tendência estrutural de
diversificação/concentração.

## Recommendation

**B — DISCLOSURE ONLY.**

Justificativa: a relação robusta encontrada (volume/concentração ×
instabilidade do unit value all-origin, Seção 7) é real, mas de magnitude
moderada (Pearson -0,46 e +0,28-0,29) — não atinge o patamar que
justificaria uma regra de publicação nova (`C`/`D`), e a decisão já
fechada em ADR 0013 (NO THRESHOLD/DISCLOSURE ONLY) permanece a resposta
correta: `total_kg`, `n_active_ncm`, `n_origins` já são publicados como
observados, sem transformação. O achado quantitativo desta etapa (Seção
7, robusto) e a distinção entre a relação robusta (volume/HHI × unit
value) e a relação frágil/artefato (concentração × erro externo, Seção 8)
merecem entrar no disclosure textual como reforço de evidência — não como
novo mecanismo. `A — NO ACTION` seria insuficiente porque ignoraria um
achado robusto e quantificado; `C`/`D` seriam prematuros porque a
correlação, mesmo robusta, é moderada (não explica a maior parte da
variância — R² implícito ≈0,21 para a associação mais forte) e nenhum
outlier revisitado foi economicamente indefensável (Seção 9).

## References

- `docs/validation/comex_unit_value_external_hrc_validation.md` (sprint
  anterior — fonte do benchmark externo e dos outliers revisitados).
- `docs/METODOLOGIA.md` §9.5.2 (agregação bottom-up), §9.7 (unit value
  bias), §11.1 (baixa liquidez, NO THRESHOLD/DISCLOSURE ONLY).
- ADR 0009, ADR 0013.
