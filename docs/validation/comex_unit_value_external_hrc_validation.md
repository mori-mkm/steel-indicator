# COMEX Unit Value × External HRC Benchmark Validation

**Status: VALIDATION ONLY — não implementa nenhuma mudança.** PPI, cesta
NCM, landed cost, vintages, publicação, `VERSAO_METODOLOGIA`, pesos,
thresholds e reporting permanecem exatamente como estavam antes desta
etapa.

Reproduzir: `docker build -t steel-indicator-dev .` seguido de
`docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/validar_comex_unit_value_hrc.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`). O script cacheia as
buscas brutas (Comex Stat + UN Comtrade) em
`data/processed/validation_cache/` (gitignored) — apague os arquivos para
forçar nova busca ao vivo.

## Question

> O unit value FOB/kg observado pelo Comex Stat para importações
> brasileiras de HRC acompanha de maneira suficientemente estável um
> benchmark independente de preço FOB internacional de HRC? Quanto da
> variação do unit value parece refletir movimento real de mercado, e
> quanto pode ser composição/mix?

## Unit value methodology (extraído do código, não de uma versão simplificada)

Fonte: `_comex_bobina_bruto` → `steel_indicator/sources/comex.py::comex_importacao_ncm`
(POST `/general`, `flow=import`, `monthDetail=True`, `details=[ncm,country]`,
`metrics=[metricFOB, metricKG, metricFreight, metricInsurance]`, filtro
`ncm` = os 13 códigos de 8 dígitos de `NCM_BOBINA_QUENTE`). A resposta real
tem `coNcm` (código) e `ncm` (descrição textual) como campos distintos —
`custo_importacao_bottom_up_mensal` já documenta esse ponto (bug real
encontrado no Stage E9: resolver política contra `ncm`, a descrição, faz
todo grupo virar `UNKNOWN` em silêncio).

Agregação usada pelo motor oficial (`custo_importacao_bottom_up_mensal`,
ADR 0009 §9.5.2 — bottom-up por `(mês, NCM, país)`, nunca CIF combinado
nem NCM representativo único):

```
UV_(ncm,country,t) = 1000 × Σ metricFOB(ncm,country,t) / Σ metricKG(ncm,country,t)
```

somando sobre as linhas cruas do Comex Stat dentro da mesma célula
`(mês, NCM, país)`. Esta etapa formaliza o agregado que é efetivamente
comparado com o benchmark externo:

```
UV_China_HRC_t = 1000 × Σ_ncm metricFOB(ncm,China,t) / Σ_ncm metricKG(ncm,China,t)   [primário, Sec.4]
UV_ALL_HRC_t   = 1000 × Σ_ncm,country metricFOB(ncm,country,t) / Σ_ncm,country metricKG(ncm,country,t)  [secundário]
```

mesma fórmula (soma FOB / soma KG do mês, ponderado por volume, nunca
média simples entre NCMs) já usada em produção por
`serie_mensal_preco_bobina` para o preço agregado de todas as origens.

**Zero/missing**: grupos com `kg<=0` são descartados (peso zero não é
fabricado). O caminho bottom-up oficial (V2, o que alimenta a série
publicada) **nunca interpola nem suaviza** em nível `(mês, NCM, país)` —
ao contrário do legado V1 (`serie_mensal_preco_bobina`), que preenche
meses inteiros ausentes por interpolação linear e aplica suavização
seletiva por `peso_confiabilidade` (`VOLUME_MINIMO_T=5000`). Esta
validação usa o caminho bottom-up (dado bruto, sem suavização/interpolação
alguma) para não misturar o efeito do tratamento legado de baixa liquidez
com o teste de unit value bias em si.

**O que é comparado com o benchmark**: `UV_China_HRC_t`, mês a mês, país
fixado em "China" (string exata confirmada ao vivo no dado real do Comex
Stat) — nunca o agregado all-origin como teste principal (Sec.4 do
sprint), que entra só como checagem secundária (Sec. "Agregado all-origin"
abaixo).

## Benchmark inventory

| Benchmark | Geography | Incoterm | Product/spec | Frequency | Historical coverage | Access | Suitability |
|---|---|---|---|---|---|---|---|
| S&P Global Platts — FOB China HRC (SS400/SAE1006) | China | FOB | SS400/SAE1006, ~3mm, 1200–2000mm | Diária | Longa (anos) | **Paywalled** | Ideal produto/geografia; acesso bloqueado |
| Fastmarkets — MB-STE-0144 (HRC export FOB main port China) | China (Tianjin) | FOB | Q235B/SS400, 1250–1800mm, 3–14mm, min. 1.000t | Diária | Longa | **Paywalled** | Ideal; acesso bloqueado |
| Argus — China HRC (base do futuro LME "Steel HRC (Argus) FOB China") | China | FOB | Metodologia ferrous Argus | Diária (liquidação mensal no LME) | Desde ~2019 (contrato LME) | **Paywalled** (LME publica specs, não histórico; agregadores mostram só janela livre de ~1 mês) | Bom; sem série sistemática gratuita |
| Kallanish — HRC China FOB, 2mm SAE1006 | China | FOB | 2mm SAE1006 (re-rolling grade) | Regular (cadência semanal aprox.) | Longa | **Paywalled** (grade completa); níveis pontuais vazam em notícias gratuitas | Ideal; só spot-check via notícia |
| SteelBenchmarker (WSD) — "World Export"/China HRC | China / mundo | Não rotulado explicitamente FOB na página pública | Bobina a quente | Quinzenal | Desde 2006 | **Freemium limitado** — tier gratuito é PDF estático com gráfico/tabela renderizada como imagem, não extraível como série numérica limpa; série limpa exige virar "Provider" (reciprocidade de dado) | Formato certo, não extraível sem virar fornecedor |
| LME (site oficial) — specs do contrato "Steel HRC FOB China (Argus)" | China | FOB | Metodologia Argus | Liquidação mensal | Desde 2019 | Specs públicas; **histórico de liquidação não publicado gratuitamente** | Confirma dependência de Argus; sem valor de dado próprio |
| **UN Comtrade — exportação da China, HS6 720810/25/26/27/36/37/38/39** | China → mundo (bilateral agregado) | N/A (China reporta exportação em base FOB — confirmado ao vivo, `cifvalue=None` para `flowCode=X`) | HS6, não uma especificação de grade | Mensal | ~2019–presente (cobertura real confirmada abaixo) | **Público/gratuito** (endpoint preview sem chave, 1 período por chamada, rate-limited; ~2,5 req/s efetivo) | **Selecionado como PRIMARY VALIDATION BENCHMARK** — independente (outra administração aduaneira), sistemático, mas herda a MESMA limitação conceitual de unit value que o próprio Comex Stat (não é um price assessment) |
| World Bank Commodity Markets (Pink Sheet) | Global | — | — | Mensal | — | Público/gratuito | Não cobre nenhum produto de aço/HRC — não utilizável |
| Trading Economics "HRC Steel" | **EUA** (confirmado: rastreia futuro CME/NYMEX HRC Midwest doméstico) | Doméstico, não FOB | HRC dos EUA | Diária | 2008–presente (gráfico); exportação de dado paga | Gráfico livre, download pago | Geografia errada (doméstico EUA, não FOB China) — desqualificado |

## Benchmark selection

**Todos os quatro provedores Tier 1 (Platts, Fastmarkets, Argus/LME,
Kallanish) são `BEST BENCHMARK — DATA ACCESS BLOCKED`** para série
histórica sistemática — confirmado por investigação de metodologia/acesso
público de cada um; nenhuma tentativa de contornar paywall foi feita.

**PRIMARY VALIDATION BENCHMARK: UN Comtrade, exportação da China
(reporterCode=156, flowCode=X=export, partnerCode=0=mundo), mesmos 8
códigos HS6 que formam o prefixo dos 13 NCMs de `NCM_BOBINA_QUENTE`.**
Critérios (Sec.9 do sprint):

1. **Produto comparável**: parcial — HS6 é um nível de agregação acima do
   NCM de 8 dígitos brasileiro; a China não expõe o desdobramento nacional
   de 8 dígitos do Brasil. Mesmo escopo conceitual ("em rolos", não
   ligado, ≥600mm) nos 8 códigos, sem normalização arbitrária.
2. **FOB comparável**: sim — a China reporta exportação em base FOB
   (`fobvalue`, confirmado ao vivo; `cifvalue=None` no flow de exportação).
3. **China/origem comparável**: sim, por construção (é a própria China
   reportando).
4. **Frequência**: mensal, compatível.
5. **Cobertura**: 2019-01 a 2024-12 confirmada ao vivo (a API não devolveu
   dado para 2025+ nesta consulta — defasagem de publicação da China, não
   erro de coleta).
6. **Independência**: forte — administração aduaneira diferente (China,
   não Brasil/MDIC), sem overlap de sistema de coleta com o Comex Stat.
7. **Qualidade metodológica**: é outro unit value agregado (valor
   declarado / peso líquido), **não um price assessment de agência** —
   mesma limitação conceitual que está sendo testada no lado brasileiro,
   só que do lado exportador. Isto é uma limitação explícita, não
   escondida (Sec. "Limitations" abaixo).
8. **Acesso reproduzível**: sim — endpoint público, sem chave, sem termo
   de licença restritivo identificado.

Não foi escolhido por maximizar correlação — foi o único benchmark
sistemático, gratuito e de produto/origem comparável identificado antes de
qualquer cálculo de correlação.

**SteelBenchmarker** e **notícias da Kallanish** entram só como
**POINT-IN-TIME / VALIDATION REFERENCE** (Sec. "Point-in-time" abaixo) —
nunca como série sistemática, conforme Sec.8 do sprint.

## Data access

| | Ideal | Efetivamente usado |
|---|---|---|
| Benchmark | Platts/Fastmarkets/Argus/Kallanish FOB China HRC (price assessment de agência, especificação de grade fixa) | UN Comtrade — unit value de exportação da China (customs, não agência de preços) |
| Motivo do gap | Assinatura comercial não contratada nesta etapa; nenhum contorno de paywall tentado | Fonte pública, gratuita, sem chave |

`BEST BENCHMARK — DATA ACCESS BLOCKED` é o estado real de acesso aos
quatro provedores Tier 1 nesta etapa.

## Comex Stat side — construção (reproduzível)

`carregar_comex_bruto()` → `_comex_bobina_bruto(2012, 2026)` (rede real,
confirmado ao vivo, 2.198 linhas, 42 países) → `uv_grupo_mensal(df,
country="China")` → `uv_agregado_mensal(df, country="China")`. Janela
principal: `>= 2019-01` (mesma janela de publicação do IPIA-HRC V2, ADR
0013).

`UV_China_HRC_t`: **85 meses, 2019-01 a 2026-07.**

## Coverage

| Série | first_month | last_month | N_months |
|---|---|---|---:|
| Comex China (import, Brasil) | 2019-01 | 2026-07 | 85 |
| UN Comtrade China (export, mundo) | 2019-01 | 2024-12 | 72 |
| **Overlap (análise principal)** | **2019-01** | **2024-12** | **66** |

A análise principal usa só o overlap (66 meses) — bem maior que o N=4-5
do sprint IPP-242×PIA-HRC anterior, o que permite leitura estatística mais
robusta aqui.

## Achado prévio obrigatório: um mês degenerado domina as métricas brutas

Antes de reportar qualquer métrica, a inspeção de outliers (Sec.
"Outliers" abaixo) revelou que **2020-12 tem `total_kg=14`** (catorze
quilos — um único embarque residual/amostra, não um fluxo comercial real)
na origem China, produzindo `UV_China_HRC_t=42.857 US$/t` nesse mês
(spread absoluto de ~41.821 US$/t contra o benchmark). Esse único ponto
domina completamente `spread_mean`, `spread_std`, a correlação MoM e a
regressão diagnóstica quando incluído. Por isso todas as tabelas abaixo
reportam **duas versões, lado a lado**: `bruto` (todos os 66 meses, nunca
excluído por decisão de produção) e `robusto` (65 meses, excluindo só o
mês de `total_kg<1.000kg` — corte analítico desta validação, nunca um
threshold de produção, ver Sec.29/§41 do sprint). Nenhuma observação foi
apagada; a versão bruta permanece a referência primária de auditoria.

## Level comparison

| Métrica | Bruto (N=66) | Robusto, vol≥1.000kg (N=65) |
|---|---:|---:|
| spread_mean (US$/t) | 629,29 | -4,44 |
| spread_median (US$/t) | 26,61 | 24,49 |
| spread_std (US$/t) | 5.150,71 | 156,07 |
| spread P5 / P25 / P75 / P95 (US$/t) | -262,06 / -80,49 / 102,88 / 212,12 | -263,12 / -82,11 / 101,47 / 189,04 |
| spread_pct_mean | 62,80% | 1,66% |
| spread_pct_std | 4,97 | 0,196 |
| Pearson (nível) | 0,278 | 0,464 |
| Spearman (nível) | 0,450 | 0,426 |

**Leitura**: a mediana do spread é estável entre as duas versões (~25-27
US$/t) — o "typical case" não é dominado pelo outlier. A média e o desvio
padrão, sim. Mesmo na versão robusta, a correlação de nível (0,46/0,43)
não deve ser sobre-interpretada isoladamente — duas séries com tendência
comum de alta ao longo do período tendem a mostrar correlação de nível
positiva mesmo sem relação real de curto prazo (mesmo cuidado já registrado
no sprint IPP-242×PIA-HRC) — por isso a métrica principal é a variação
(seção seguinte), não o nível.

## Change comparison (MoM)

| Métrica | Bruto (N=65) | Robusto (N=64) |
|---|---:|---:|
| Pearson MoM | 0,544 | 0,006 |
| Spearman MoM | 0,143 | 0,041 |

**A correlação MoM "moderada" da versão bruta (0,544) é inteiramente
produzida pelo mês degenerado de 2020-12** (um salto de +75% no Comex
China nesse mês, ~14kg de base). Removendo-o, a correlação de variação
mensal cai para **essencialmente zero (0,006)**. Este é o achado central
desta validação.

## Directional accuracy

| | Bruto | Robusto |
|---|---:|---:|
| Directional accuracy (todos os meses) | 53,8% (n=65) | 51,6% (n=64) |
| Directional accuracy, `\|Δbenchmark\|≥3%` | 58,5% (n=41) | 55,0% (n=40) |

Em ambas as versões, a acurácia direcional está próxima de 50% — não
melhor do que uma moeda honesta. O limiar de 3% é analítico (Sec.17 do
sprint), não um contrato de produção.

## Lead/lag

| lag (meses) | Pearson (bruto*) | Pearson (robusto) |
|---:|---:|---:|
| 0 | 0,322 | 0,008 |
| 1 | 0,017 | -0,004 |
| 2 | -0,127 | 0,050 |
| 3 | — | 0,000 |

*bruto: lags 0-2 calculados sobre a série completa (não filtrada por
volume); lags 0-3 na versão robusta (mesma exclusão do mês degenerado).
Nenhum lag econômico plausível (contemporâneo, -1, -2, -3 meses)
recupera correlação na versão robusta — o Comex Stat não acompanha nem o
benchmark contemporâneo nem defasado de forma consistente nesta
comparação. Não há evidência de que a defasagem entre declaração de
exportação chinesa e desembaraço aduaneiro no Brasil (tipicamente
semanas) explique a divergência — se explicasse, um lag de 1-2 meses
deveria melhorar a correlação, o que não ocorre.

## Rolling stability

Rolling Pearson de 12 meses sobre as variações MoM (versão robusta,
N=53 janelas válidas): média **-0,044**, desvio-padrão 0,235, mínimo
-0,425, máximo 0,460. **Instável em torno de zero** — nenhuma janela de
12 meses sustenta uma correlação forte e persistente; os poucos picos
positivos (até 0,46) não se repetem na janela seguinte.

## Análise por regime

| Regime | N | Pearson MoM (robusto) | Directional accuracy (robusto) |
|---|---:|---:|---:|
| Pré-choque (2019) | 11 | 0,132 | 63,6% |
| 2020 (choque COVID) | 6 | 0,578 | 66,7% |
| 2021 (supercycle) | 11 | -0,048 | 54,5% |
| 2022-2023 (normalização) | 24 | -0,202 | 41,7% |
| 2024+ (recente) | 12 | 0,022 | 50,0% |

Nenhum regime mostra relação forte e estável. O único ponto favorável
(2020, Pearson 0,578) tem N=6 — não confiável isoladamente. 2022-2023
(o maior sub-período, N=24) mostra correlação **negativa** e a pior
acurácia direcional (41,7%) — pior que aleatório.

## NCM analysis

13 NCMs de origem China com volume ≥2019-01, ordenados por participação
de volume (tabela completa em
`data/processed/validation/comex_unit_value_hrc/ncm_analysis.csv`):

| NCM | Share volume | UV médio (US$/t) | Spread médio vs. benchmark (US$/t) | Volatilidade MoM (std) |
|---|---:|---:|---:|---:|
| 72083990 | 44,7% | 606,22 | 44,54 | 0,133 |
| 72083910 | 21,2% | 644,26 | -8,14 | 0,153 |
| 72083890 | 11,3% | 608,15 | 37,97 | 0,098 |
| 72083700 | 7,2% | 654,77 | 32,13 | 0,129 |
| 72082790 | 4,4% | 2.354,73 | 1.734,88 | 11,19 |
| 72081000 | 3,0% | 4.403,06 | 7.074,86 | 0,204 |
| 72082500 | 2,7% | 5.484,18 | 666,43 | 47,61 |
| 72082690 | 2,3% | 844,77 | 29,59 | 1,657 |
| ... (5 NCMs restantes, share < 1,5% cada) | | | | |

**Os 4 NCMs dominantes (86,8% do volume: 72083990/72083910/72083890/
72083700) têm UV médio consistente entre si (606-655 US$/t) e spread
médio pequeno e estável (-8 a +45 US$/t) frente ao benchmark.** Os NCMs
de baixo volume (72082790, 72081000, 72082500 — juntos ~10% do volume)
têm UV médio implausivelmente alto (2.355 a 5.484 US$/t, várias vezes o
nível dos NCMs dominantes) e volatilidade MoM extrema (até 47,6) — sinal
claro de que unit values calculados sobre volume fino são dominados por
poucas transações não representativas, não por preço de mercado. Isso é
consistente com, e reforça, a limitação já documentada em
`docs/METODOLOGIA.md` §9.7/§11.1 (baixa liquidez, NO THRESHOLD/DISCLOSURE
ONLY) — nenhum NCM foi excluído desta análise.

## Mix decomposition

Decomposição shift-share (`ΔUV_total ≈ within_price + mix_between +
interação`, só sobre HS6 com volume>0 em ambos os períodos do par —
nunca inventa preço para um código ausente) em **duas granularidades**:

**Mensal** (`mix_decomposicao.csv`, 84 pares): extremamente ruidosa —
muitos meses têm só 1-2 códigos HS6 ativos em comum, o que torna a
decomposição não computável ou dominada por interação residual em
diversos meses (ex.: 2025-11, `within=+30.506` compensado por
`interação=-30.547` — artefato de denominador fino, não sinal
econômico). **A granularidade mensal não sustenta uma leitura estável.**

**Anual** (year-over-year, 7 transições, 2019→2026): muito mais estável —

| Transição | ΔUV_total | within (preço) | mix (composição) | interação |
|---|---:|---:|---:|---:|
| 2019→2020 | -57,39 | -43,34 | -58,51 | +4,57 |
| 2020→2021 | +287,71 | +232,40 | -155,07 | +80,27 |
| 2021→2022 | +22,38 | +85,57 | **-116,79** | +53,59 |
| 2022→2023 | -248,70 | -222,77 | -21,24 | -4,68 |
| 2023→2024 | -53,67 | -53,06 | -11,03 | +10,42 |
| 2024→2025 | -68,37 | -69,86 | +0,16 | +1,34 |
| 2025→2026 | -17,69 | -27,59 | +33,94 | -21,11 |

**Leitura**: em 4 das 7 transições (2022→2023, 2023→2024, 2024→2025,
2025→2026), o efeito `within` (preço dentro do mesmo NCM) domina e tem o
mesmo sinal do total — a variação agregada reflete majoritariamente preço
real, não composição. Mas em **2020→2021 e 2021→2022** (a janela
COVID/supercycle), o efeito `mix` é **grande e de sinal oposto** ao efeito
`within` — em 2021→2022, o mix (-117) chega a ser maior em magnitude que
o próprio preço (+86), quase revertendo o sinal do total observado
(+22, pequeno, resultado de dois efeitos grandes se cancelando). **Nos
períodos de maior estresse de mercado (justamente onde o unit value
importa mais para interpretação econômica), a composição de NCMs
importados mudou o suficiente para distorcer materialmente a leitura do
agregado.**

## Origin composition

Participação da China no volume total de HRC importado pelo Brasil, por
ano (`origem.csv`, janela ≥2019):

| Ano | Share China | HHI (países) | Top-3 |
|---|---:|---:|---|
| 2019 | 13,0% | 0,274 | Rússia 44,6%; Ucrânia 18,9%; Venezuela 13,4% |
| 2020 | 14,1% | 0,548 | Rússia 71,5%; China 14,1%; Ucrânia 12,8% |
| 2021 | 27,4% | 0,450 | Rússia 60,1%; China 27,4%; Ucrânia 11,8% |
| 2022 | 66,6% | 0,490 | China 66,6%; Rússia 17,1%; Coreia do Sul 13,1% |
| 2023 | 58,5% | 0,407 | China 58,5%; Coreia do Sul 23,3%; Venezuela 8,1% |
| 2024 | 86,9% | 0,762 | China 86,9%; Egito 6,7%; Coreia do Sul 3,1% |
| 2025 | 36,2% | 0,342 | Coreia do Sul 42,3%; China 36,2%; Egito 17,5% |
| 2026* | 23,5% | 0,340 | Coreia do Sul 47,0%; Egito 24,8%; China 23,5% |

*2026 parcial (até jul/2026 na data desta execução).

**A representatividade de "China" como benchmark de origem varia
enormemente ano a ano** — de 13% (2019, quando a Rússia dominava) a 87%
(2024). Isso significa que uma validação restrita à origem China é
proporcionalmente mais relevante para o agregado all-origin em alguns
anos (2022-2024) do que em outros (2019-2020, 2025-2026) — uma limitação
adicional que se soma às já registradas.

## Agregado all-origin (SECUNDÁRIO)

Comparado contra o mesmo benchmark China (Sec.27 do sprint — classificado
explicitamente como `SECONDARY / GLOBAL MARKET PROXY CHECK`, nunca
validação direta): N=71, Pearson nível=0,321, **Pearson MoM=0,0085**
(também essencialmente nulo), directional accuracy=55,7%, spread_pct
médio=-7,07%. **O resultado é consistente com a comparação China-only** —
a fraqueza da relação MoM não é um artefato específico do recorte por
origem.

## Outliers

**Top |spread| (nível)** — `outliers_nivel.csv`:

| Mês | \|spread\| (US$/t) | total_kg | HS6 dominante | Evento |
|---|---:|---:|---|---|
| 2020-12 | 41.821 | **14** | 720827=100% | (mês degenerado, ver acima) |
| 2019-05 | 536 | 2.436.120 | 720827=92% | China: AD suspenso (2018-01→2020-01) |
| 2021-01 | 411 | 1.051.020 | 720839=92% | — |
| 2021-04 | 366 | 1.976.080 | 720839=53% | — |
| 2022-11 | 293 | 11.135.772 | 720837=33% | — |

**Top |ΔComex − Δbenchmark|**: dominado pelo mesmo mês degenerado
(2020-12, `d_comex=+75,1%` vs. `d_benchmark=+0,9%`); os demais meses
(2019-05, 2021-01, 2021-09, 2019-06...) têm divergências de magnitude bem
menor (0,2-1,1 p.p. em termos de variação percentual) e não coincidem
sistematicamente com nenhuma janela de política comercial conhecida, exceto
2019-05/2019-06, que caem dentro da janela de suspensão do antidumping
chinês (2018-01-19 a 2020-01-17) — mas essa janela cobre a maior parte de
2018-2020 inteira, então a coincidência não é distintiva. **Nenhum outlier
foi removido desta validação** — a única observação tratada de forma
diferenciada (mês de `total_kg<1.000kg`) está claramente sinalizada como
corte de robustez analítico, nunca uma exclusão silenciosa.

## Liquidity diagnostics

`corr(volume mensal China, |erro percentual vs. benchmark|)` = **-0,098**
(N=66); `corr(nº de HS6 ativos no mês, |erro percentual|)` = **-0,188**
(N=66). Ambas fracas, mas de sinal consistente com a hipótese de liquidez
(mais volume/mais códigos ativos → erro tende a ser um pouco menor) — e a
própria existência do mês de `total_kg=14` como o outlier absoluto de toda
a série é, por si, a evidência mais direta desta seção: o erro extremo da
série inteira ocorre exatamente no mês de volume mais baixo. Nenhum
threshold foi implementado — mesma decisão já fechada em ADR 0013 (NO
THRESHOLD / DISCLOSURE ONLY) permanece válida; esta seção só adiciona
evidência quantitativa à disclosure existente.

## Point-in-time (SteelBenchmarker / Kallanish) — spot-checks, não série

Referências pontuais encontradas na pesquisa de benchmark (não uma série
sistemática, Sec.8 do sprint):

- Kallanish: HRC 2mm SAE1006, **US$470-480/t FOB China** (9/jan, ano
  recente ~2026 pelo contexto da busca).
- Kallanish: **US$515-525/t FOB China** (8/mai/2026), mills em
  US$520-530/t, traders menores perto de US$510/t.
- Investing.com (futuro LME Steel HRC FOB China, snapshot livre):
  **US$461,50**, faixa de 52 semanas US$439,00-480,00 (sem data-âncora
  confiável além de "recente").

Comparação qualitativa: `UV_China_HRC_t` (Comex Stat) no início de 2026
ficou em 518 (jan), 485 (fev), 491 (mar), 498 (abr), 516 (mai), 502 (jun),
414 (jul) US$/t — **na mesma ordem de grandeza** dos níveis Kallanish
(470-530) e do range do futuro LME (439-480), com o Comex tipicamente
20-40 US$/t acima nos meses centrais e caindo abaixo em julho/2026. Isto é
consistente com o achado de nível (spread mediano robusto ≈+25 US$/t) —
um spot-check qualitativo, não uma validação estatística adicional.

## Limitations

1. **Tier 1 (Platts/Fastmarkets/Argus/Kallanish) permanece
   `DATA ACCESS BLOCKED`** — o teste definitivo contra um price assessment
   de agência não foi feito nesta etapa.
2. **O benchmark usado (UN Comtrade) é outro unit value, não um price
   assessment** — herda conceitualmente a mesma limitação de composição
   que está sendo testada no Comex Stat, só do lado exportador. Um
   resultado nulo pode refletir tanto "o Comex Stat não acompanha preço de
   mercado" quanto "nenhum dos dois lados acompanha preço de mercado" —
   esta validação não consegue separar as duas hipóteses.
3. **Cobertura do benchmark termina em 2024-12** — não cobre 2025-2026
   (defasagem de publicação da China na API pública), 19 meses da série
   Comex ficam sem checagem externa nesta validação.
4. **Granularidade HS6 vs. NCM de 8 dígitos**: a China não expõe o
   desdobramento de 8 dígitos usado pelo Brasil — o benchmark é
   estruturalmente um nível de agregação de produto acima da cesta oficial
   do projeto.
5. **Timing**: nenhuma correção de defasagem entre declaração de
   exportação chinesa e desembaraço aduaneiro brasileiro foi validada
   contra uma fonte de trânsito real — os lags testados (0-3 meses) são
   hipóteses econômicas plausíveis, não medidos diretamente.
6. **Um único mês (2020-12, 14kg) domina todas as métricas brutas** —
   tratado com transparência (duas versões lado a lado), mas é uma
   limitação de dado real: unit values sobre volume extremamente fino não
   são informativos, disclosure já existente (§11.1) permanece a resposta
   correta, não um novo threshold.
7. **Mix decomposition mensal não é estável** — só a granularidade anual
   produziu leitura defensável.
8. **N=66 é grande para os padrões deste projeto (vs. N=4-5 do sprint
   PIA×IPP), mas o resultado nulo de MoM não pode, isoladamente, ser
   promovido a "prova" de que o unit value bias é severo** — falta o
   benchmark ideal para essa conclusão forte.

## Decision matrix

Escala qualitativa (Forte/Moderado/Fraco/Insuficiente), versão robusta
(vol≥1.000kg) como referência principal:

| Critério | Resultado | Avaliação |
|---|---|---|
| Level relationship | Pearson 0,46, Spearman 0,43 — mas confundido por tendência comum | Moderado (nominal), pouco informativo isolado |
| MoM correlation | 0,006 (essencialmente zero) | **Fraco** |
| Directional accuracy | 51,6% (praticamente aleatório) | **Fraco** |
| Lag-adjusted relationship | Nenhum lag (0-3m) recupera sinal | **Fraco** |
| Spread stability | Mediana estável (~25 US$/t), mas cauda larga (P5/P95 ±260/190) | Moderado |
| Rolling stability | Média -0,04, instável em torno de zero | **Fraco** |
| NCM mix sensitivity | 4 NCMs dominantes consistentes; NCMs finos com UV/volatilidade extremos | Moderado (composição importa nas margens) |
| Volume sensitivity | Correlações fracas mas no sinal esperado; outlier absoluto no mês de menor volume | Moderado |
| China representativeness | 13%-87% do volume total, ano a ano | **Fraco/instável** |
| External benchmark quality | UN Comtrade gratuito, independente, mas é unit value, não price assessment; Tier 1 bloqueado | **Insuficiente** para conclusão forte |

## Recommendation

**Evidence strength: WEAK** para o que pôde ser testado (correlação MoM
essencialmente nula, acurácia direcional em torno de 50%, nenhum lag
recupera sinal, instabilidade em regime e em janela rolling) — **mas com
uma ressalva estrutural que impede tratar isso como prova definitiva**: o
único benchmark sistemático acessível (UN Comtrade) é ele mesmo um unit
value, não um price assessment, e o teste ideal (Platts/Fastmarkets/
Argus/Kallanish) permanece bloqueado por acesso.

**E — INCONCLUSIVE quanto a uma decisão definitiva de fonte/agregação.**
A evidência não é forte o suficiente, nem limpa o suficiente (dado o
benchmark substituto ser conceitualmente similar ao que está sendo
testado), para justificar `C — REVIEW AGGREGATION` ou `D — REVIEW SOURCE`
agora — isso exigiria o benchmark Tier 1 (price assessment de agência)
para separar "unit value bias real" de "limitação do benchmark
substituto". Também não é forte o suficiente para `A — KEEP` sem
ressalva, dado o achado NCM/mix e a instabilidade por regime.

**Consequência prática recomendada: manter a postura `B — KEEP WITH
LIMITATION`** já adotada no sprint IPP-242×PIA-HRC (nenhuma fonte melhor
foi validada nesta etapa) — a agregação bottom-up por `(mês, NCM, país)`
(ADR 0009 §9.5.2) já é a prática correta contra composição *entre*
categorias; nenhuma evidência aqui aponta defeito nessa agregação em si.
O achado de maior valor é reforçar, com números, o disclosure já existente
em `docs/METODOLOGIA.md` §9.7 (unit value bias) e §11.1 (baixa liquidez) —
não mudar a fonte ou a fórmula.

**Dado a adquirir antes de uma decisão C/D**: assinatura de um price
assessment de agência FOB China HRC (Platts `STHRZ02`/`STHSA00`,
Fastmarkets `MB-STE-0144`, ou Kallanish) com histórico mensal 2019+. Sem
isso, qualquer decisão de trocar/recalibrar o unit value seria baseada em
evidência mais fraca que a atual, não mais forte.

## Confidence

**LOW.** O resultado estatístico em si (correlação MoM nula, N=64-66) é
razoavelmente claro dentro do que foi testado, mas a confiança na
**interpretação** (unit value bias real vs. limitação do benchmark
substituto) é baixa porque a única fonte sistemática disponível tem a
mesma limitação conceitual do lado que está sendo validado. Não é
`MEDIUM`/`HIGH` porque isso exigiria o benchmark Tier 1 blqueado.

## References

- `docs/METODOLOGIA.md` §9.5.2 (agregação bottom-up), §9.7 (unit value
  bias, já documentado antes desta validação), §9.8 (tabela de
  proveniência do PPI), §11.1 (baixa liquidez, NO THRESHOLD/DISCLOSURE
  ONLY).
- ADR 0009 (janela publication-grade e agregação bottom-up multi-NCM),
  ADR 0013 (contrato de publicação, decisão de baixa liquidez).
- UN Comtrade Data API — <https://comtradeapi.un.org/public/v1/preview/C/M/HS>
  (endpoint público, sem chave, usado nesta validação).
- S&P Global Platts — [Specifications Guide Global Steel](https://www.spglobal.com/content/dam/spglobal/ci/en/documents/platts/en/our-methodology/methodology-specifications/metals/steel-ferrous-specifications.pdf).
- Fastmarkets — [MB-STE-0144, Steel HRC index export, FOB main port China](https://www.fastmarkets.com/commodity-prices/steel-hot-rolled-coil-index-export-fob-main-port-china-dollar-tonne-mb-ste-0144/).
- Argus — [Argus China HRC methodology](https://www.argusmedia.com/en/methodology/key-commodity-prices/argus-china-hrc).
- LME — [Steel HRC FOB China (Argus) contract specifications](https://www.lme.com/en/metals/ferrous/lme-steel-hrc-fob-china-argus/contract-specifications).
- Kallanish — [HRC / China FOB USD/t](https://www.kallanish.com/en/prices/details/hot-rolled-coil-china-fob-usdt/).
- SteelBenchmarker — <https://steelbenchmarker.com/history.pdf>.
