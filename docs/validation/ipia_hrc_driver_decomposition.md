# IPIA-HRC — Driver Decomposition Engine

**Status: IMPLEMENTAÇÃO CONCLUÍDA (camada analítica).** Nenhum valor
oficial do IPIA-HRC mudou. `VERSAO_METODOLOGIA` permanece `"1.5"`.
Decisão metodológica de decomposição registrada em
`docs/adr/0016-ipia-hrc-driver-decomposition-shapley-method.md`.

Reproduzir: `python scripts/gerar_ipia_hrc_driver_decomposition.py` (faz
chamadas de rede reais a Comex Stat/BCB, separadas da vintage congelada;
nunca cria vintage nova; artefatos gitignored em
`data/processed/validation/ipia_hrc_driver_decomposition/`).

## Objective

Transformar `IPIA_HRC = 128,28` em `"o IPIA mudou X pontos porque o
preço doméstico subiu, Y pontos por causa do câmbio, Z por FOB, etc."` —
decompor `ΔIPIA_t = IPIA_t - IPIA_{t-1}` (em pontos de índice) em
contribuições atribuíveis a: preço doméstico (lado doméstico); FOB,
frete, seguro, câmbio, II, AFRMM, antidumping, D_porto, D_interno (lado
importado, `PPI_COST`); e, apenas em análise `PPI_OFFER` opcional,
margem comercial.

## Mathematical identity

\[
IPIA_t = \frac{P_{dom,t}}{PPI\_COST_t} \times 100
\]

\[
PPI\_COST_t = \underbrace{(FOB_t+Frete_t+Seguro_t)}_{\text{USD/t}} \times FX_t
            + II_t + AFRMM_t + AD_t + D_{porto} + D_{interno}
\]

onde `II_t`, `AFRMM_t`, `AD_t` (em R$/t) são, eles mesmos, produtos de um
valor efetivo em USD/t pelo câmbio do mês (ver "Interaction treatment"
abaixo). A relação `IPIA_t` é **não linear** em todos os 9 drivers de
custo + 1 driver doméstico — câmbio multiplica um agregado de 6 termos
(FOB, frete, seguro, II, AFRMM, antidumping), e o preço doméstico entra
como razão (não soma) sobre o PPI_COST inteiro.

## Candidate methods

| Método | Aditividade exata | Independe de ordem | Interpretação | Reprodutibilidade | Custo computacional | Zeros/interação |
|---|---|---|---|---|---|---|
| **Sequential replacement** | Sim (por construção), mas resíduo=0 só naquela ordem especificamente | **Não** — resultado muda com a ordem escolhida | Simples, mas arbitrária | Alta | Trivial (n avaliações) | Atribui a interação inteira ao driver que "chega primeiro" |
| **Midpoint/symmetric (2 caminhos)** | Aproximada (forward+reverse ÷2) | Parcial — melhora mas não resolve para n>2 | Intuitiva | Alta | Trivial (2n avaliações) | Reduz mas não elimina o problema de atribuição para n>2 drivers |
| **Log-decomposition** | Exata **somente se `f` for produto puro** | Sim, quando aplicável | Muito clara (elasticidades) | Alta | Trivial | `PPI_COST` tem SOMA no denominador (não produto puro) — não aplicável diretamente sem reabrir o mesmo problema de atribuição dentro da soma |
| **Shapley exato (subconjuntos, 2^n)** | **Exata, sempre** (efficiency property) | **Sim, sempre** (symmetry property) | Clara (contribuição marginal média justa) | Alta (determinístico, sem seed) | `2^n` avaliações (1024 p/ n=10) — trivial | Distribui toda interação simetricamente entre os drivers envolvidos, documentado explicitamente |
| Shapley por força bruta (permutações, n!) | Exata | Sim | Idêntica ao Shapley exato | Alta, mas cara | `n!` avaliações (3.628.800 p/ n=10) — **inviável em produção**, usado só para validação cruzada em teste (n≤8) | Idêntico ao exato |
| Monte Carlo (amostra de ordens) | Aproximada | Aproximada (converge com N amostras) | Boa | Requer seed fixa para determinismo | Barato, mas introduz ruído | Aproxima a mesma distribuição, sem necessidade nesta escala |

## Selected method

**Shapley value exato via fórmula fechada de subconjuntos** (`2^n`
avaliações, não `n!` permutações) — `steel_indicator.domain.driver_decomposition.shapley_contributions`.

Motivo: para `n=10` drivers (modo Cost), `2^10=1024` avaliações de uma
função fechada (poucas operações aritméticas cada) são triviais
computacionalmente — não há motivo para recorrer a Monte
Carlo/aproximação quando o cálculo exato custa milissegundos.
`shapley_contributions_forca_bruta` (força bruta por permutações) existe
só para validação cruzada em teste (prova que a fórmula de subconjuntos
produz o mesmo resultado exato da definição original de Shapley) — nunca
usada em produção. Ver ADR 0016 para a decisão formal.

## Interaction treatment

**Problema**: câmbio multiplica FOB, frete e seguro (via CIF) e também
os valores de II/AFRMM/antidumping (que são, na fórmula de produção,
`aliquota × CIF_convertido` ou `valor_USD × câmbio`). Ao nível de
`custo_importacao_bottom_up_mensal` (agregação mês×NCM×país), a alíquota
efetiva de II pode covariar com o CIF/t entre NCMs diferentes — o que
significa que `alíquota_ii_efetiva × CIF_agregado ≠ ΣᵢNCM(alíquota_iiᵢ ×
CIFᵢ)` em geral (média de produto ≠ produto de médias, quando os fatores
covariam). Esse achado já estava documentado em `decompor_mes`
(`scripts/validar_ipia_hrc_v2_final.py`) desde a validação Stage G3.

**Solução**: os drivers `ii`/`afrmm` desta decomposição são definidos
como **valores monetários efetivos em USD/t** (não alíquotas):

```
ii_usd_efetivo     = ii_brl_t_mensal / câmbio_do_mês
afrmm_usd_efetivo  = afrmm_brl_t_mensal / câmbio_do_mês
```

onde `ii_brl_t_mensal`/`afrmm_brl_t_mensal` já vêm corretamente
reconciliados por `decompor_mes` (ponderação por KG do valor monetário
por grupo, não da alíquota). Prova algébrica de por que isso reconstrói
o `PPI_COST` oficial exatamente:

```
ii_brl_t_i = cif_brl_t_i × alíquota_ii_i = (cif_usd_t_i × FX) × alíquota_ii_i
           = FX × (cif_usd_t_i × alíquota_ii_i)
```

Como `FX` é uma constante ÚNICA por mês (não varia por NCM/país — é
resolvida uma vez por `calcular_fx_mensal`, compartilhada por todos os
grupos daquele mês), ela fatora exatamente para fora da média ponderada:

```
ii_brl_t_mensal = média_ponderada_i(FX × cif_usd_t_i × alíquota_ii_i)
                = FX × média_ponderada_i(cif_usd_t_i × alíquota_ii_i)
                = FX × ii_usd_efetivo
```

— identidade exata, sem termo residual, **porque FX não varia por
grupo dentro do mês** (só a alíquota e o CIF/t variam por NCM). O mesmo
raciocínio vale para AFRMM. Antidumping já é nativamente expresso em
USD/t na fonte (`resolver_antidumping`), sem necessidade de conversão.

Com essa reparametrização, `PPI_COST` é **linear em FX** sobre um único
agregado USD/t:

```
PPI_COST = FX × (fob + freight + insurance + ii + afrmm + antidumping) + d_porto + d_interno
```

e o Shapley distribui a interação câmbio×(agregado USD/t) de forma
simétrica entre FX e cada um dos 6 drivers em USD/t — nunca atribuindo o
cruzamento inteiro a um único driver por uma escolha arbitrária de
ordem. `D_porto`/`D_interno` são nativamente R$/t, sem interação com FX.

**Verificação empírica desta identidade**:
`tests/unit/test_ipia_hrc_driver_decomposition.py::test_ppi_cost_de_drivers_bate_exatamente_com_decompor_mes_ncms_heterogeneos`
prova, com um cenário sintético de dois NCMs com alíquotas de II
diferentes (o mesmo cenário que expôs o viés de covariância na
validação original), que `_ppi_cost_de_drivers` alimentado pelos
componentes derivados reproduz `ppi_cost_via_motor` (o valor real que o
motor de produção calcularia) com erro `<1e-9`.

## Exact additivity

Propriedade garantida por construção (Shapley *efficiency property*),
não uma aproximação: `Σ contribuições_driver = ΔIPIA` exatamente, para
qualquer par de meses e em qualquer um dos dois modos (Cost/Offer).

Resultados observados na série real (execução de
`scripts/gerar_ipia_hrc_driver_decomposition.py`, vintage `20260829T174456Z`,
metodologia 1.5, 78 meses calculáveis 2019-02 a 2026-06, **70 transições
mês-a-mês estritamente consecutivas**):

- **Max |residual|**: `4,97 × 10⁻¹⁴` pontos de IPIA.
- **Mean |residual|**: `6,75 × 10⁻¹⁵` pontos de IPIA.

Ambos são ruído de ponto flutuante (14-15 casas decimais abaixo do
próprio valor do IPIA) — a soma matemática é exatamente 0, exatamente
como a *efficiency property* de Shapley garante por construção.

Ambos são ruído de ponto flutuante (a soma matemática é exatamente 0 —
o resíduo reportado existe só para transparência/teste, nunca é
estruturalmente diferente de zero).

## Synthetic validation

`tests/unit/test_ipia_hrc_driver_decomposition.py` (19 testes) e
`tests/unit/test_driver_decomposition_shapley.py` (15 testes, motor
genérico) cobrem:

- **Domestic only**: 100% da variação atribuída a `domestic_price`,
  todos os demais drivers exatamente 0, resíduo `<1e-9`.
- **FX only**: 100% a `fx`, sinal correto (câmbio sobe → IPIA cai).
- **FOB/freight/insurance only**: idem, sinal correto (sobem → IPIA cai).
- **Dois drivers simultâneos** (domestic+FX): soma fecha exatamente,
  sinais econômicos coerentes, resultado idêntico em execuções repetidas.
- **D_porto/D_interno constantes**: contribuição exatamente 0 mesmo com
  outros drivers mudando — e, em cenário separado, contribuição ≠0 e com
  sinal correto caso esses parâmetros um dia se tornem time-varying (o
  motor já suporta isso sem nenhuma mudança de código).
- **Mudança regulatória (II)**: contribuição ≠0, sinal correto (II sobe
  → PPI_COST sobe → IPIA cai).
- **Cost vs Offer**: modo `cost` nunca inclui `margin` no resultado;
  modo `offer` inclui, com sinal correto quando a margem muda, e
  contribuição exatamente 0 quando a margem é constante entre os dois
  períodos (o caso real hoje, já que `margem_importador` é hold-flat).
- **Determinismo**: mesma entrada produz exatamente o mesmo resultado em
  chamadas repetidas (sem aleatoriedade em nenhum ponto do motor exato).
- **Caso analítico independente**: para `f(a,b)=a×b`, o valor de Shapley
  bate com a forma fechada conhecida (decomposição Bennet/Shapley-Owen
  de 2 fatores), verificada fora da implementação testada.
- **Equivalência exata com força bruta**: a fórmula de subconjuntos
  produz o mesmo resultado, driver a driver, que a média sobre todas as
  `n!` permutações (definição original de Shapley), para `n` pequeno.

## Real-series validation

Execução real, 2026-08-29, vintage `20260829T174456Z` (metodologia 1.5),
2158 linhas granulares mês×NCM×país buscadas ao vivo (Comex Stat+BCB),
`N=70` transições mês-a-mês decompostas (dos 78 meses calculáveis — 8
sem decomposição por não terem o mês calendário anterior calculável,
i.e., gaps na série EXPERIMENTAL/PUBLICATION_GRADE, ver Limitations §2):

| Métrica | Valor |
|---|---:|
| N transições | 70 |
| Max \|residual\| | 4,97e-14 pts |
| Mean \|residual\| | 6,75e-15 pts |

**Driver médio** (pontos de IPIA, média sobre as 70 transições):

| Driver | Contribuição média (pts) |
|---|---:|
| Preço doméstico | +0,6304 |
| FOB | +0,2012 |
| Frete internacional | +0,0197 |
| Seguro | +0,0011 |
| Câmbio | -0,2196 |
| II | +0,0472 |
| AFRMM | -0,0196 |
| Antidumping | 0,0000 |
| D_porto | 0,0000 |
| D_interno | 0,0000 |

D_porto/D_interno/antidumping em 0,0000 confirma empiricamente o
comportamento esperado (Seção 12 do sprint): parâmetros constantes ao
longo de toda a série contribuem exatamente zero.

## Driver ranking

**Top drivers por FREQUÊNCIA de dominância** (`dominant_driver`, maior
|contribuição| absoluta na transição):

| Driver | N meses dominante | % das transições |
|---|---:|---:|
| FOB | 47 | 67,1% |
| Preço doméstico | 12 | 17,1% |
| Câmbio | 6 | 8,6% |
| Frete internacional | 3 | 4,3% |
| II | 2 | 2,9% |

**Top drivers por CONTRIBUIÇÃO ABSOLUTA MÉDIA** (`mean(|contribuição|)`
sobre as 70 transições):

| Driver | \|Contribuição\| média (pts) |
|---|---:|
| FOB | 6,6773 |
| Preço doméstico | 2,5556 |
| Câmbio | 2,1137 |
| Frete internacional | 1,5489 |
| II | 0,9143 |
| AFRMM | 0,1858 |
| Seguro | 0,0452 |
| Antidumping / D_porto / D_interno | 0,0000 |

**Resumo por ano** (`driver_mais_frequente` = maior contagem de
`dominant_driver` naquele ano — leitura estritamente
`mathematically dominant contribution`, nenhuma causalidade externa
inferida):

| Ano | N transições | Driver mais frequente | Frequência | Mean ΔIPIA (pts) |
|---|---:|---|---:|---:|
| 2019 | 8 | FOB | 6 | +0,9535 |
| 2020 | 1 | FOB | 1 | -7,0447 |
| 2021 | 10 | Preço doméstico | 8 | +1,2036 |
| 2022 | 9 | FOB | 8 | -0,2345 |
| 2023 | 12 | FOB | 10 | +2,9194 |
| 2024 | 12 | FOB | 8 | -2,4410 |
| 2025 | 12 | FOB | 9 | +1,0900 |
| 2026 (parcial) | 6 | FOB | 3 | +2,8153 |

**Leitura**: FOB domina matematicamente a maioria das transições em
quase todos os anos — 2021 é a exceção, com preço doméstico dominante em
8 de 10 transições daquele ano. Nenhuma causa macroeconômica externa é
inferida ou pesquisada aqui — apenas qual componente da fórmula moveu
mais o número em cada mês.

## Threshold crossings

**8 cruzamentos do threshold 100** identificados nas 70 transições
decompostas (série real pós-metodologia 1.5, não relacionados à migração
Cost/Offer do sprint anterior — esses já haviam sido cobertos em
`docs/validation/ipia_hrc_cost_offer_migration.md`):

| Mês | IPIA antes → depois | ΔIPIA (pts) | Dominant driver | Residual |
|---|---|---:|---|---:|
| 2021-11 | 106,77 → 90,69 | -16,09 | Preço doméstico | ~0 |
| 2022-05 | 93,31 → 100,70 | +7,39 | FOB | ~0 |
| 2022-06 | 100,70 → 85,74 | -14,96 | FOB | ~0 |
| 2022-11 | 78,02 → 100,60 | +22,59 | FOB | ~0 |
| 2022-12 | 100,60 → 92,57 | -8,03 | FOB | ~0 |
| 2023-02 | 98,19 → 133,33 | +35,15 | FOB | ~0 |
| 2024-12 | 110,82 → 98,31 | -12,51 | FOB | ~0 |
| 2025-01 | 98,31 → 118,92 | +20,61 | FOB | ~0 |

**Leitura aceitável** (`mathematically dominant contribution`, sem
narrativa causal externa): 6 dos 8 cruzamentos foram matematicamente
dominados por FOB; o cruzamento de 2021-11 foi dominado por preço
doméstico (contribuição -4,50 pts, quase empatada com FOB -4,30 e frete
-4,42 — uma transição com três drivers de magnitude similar, nenhum
isoladamente esmagador). Nenhuma causa externa (decisão de banco central,
notícia de mercado) é inferida — isso fica fora deste pipeline.

## Current-period decomposition

Transição mais recente calculável: **2026-05 → 2026-06**
(`ΔIPIA = -7,4078 pts`):

| Driver | Contribuição (pts) |
|---|---:|
| Preço doméstico | +1,5452 |
| FOB | -3,7536 |
| Frete internacional | -0,4289 |
| Seguro | -0,1690 |
| Câmbio | -3,3847 |
| II | -1,1824 |
| AFRMM | -0,0343 |
| Antidumping | 0,0000 |
| D_porto | 0,0000 |
| D_interno | 0,0000 |
| **Residual** | **+3,55e-15** |

`dominant_driver` = FOB. Leitura: o IPIA caiu 7,41 pontos em junho/2026
majoritariamente por FOB (-3,75 pts) e câmbio (-3,38 pts) — ambos
encarecendo a importação — parcialmente compensados pelo preço doméstico
(+1,55 pts).

**Cost vs Offer, mesma transição** (Seção 30): modo `cost` (oficial,
`ΔIPIA=-7,4078`) não inclui `margin` no resultado; modo `offer`
(analítico, margem 3% constante em ambos os períodos, `ΔIPIA=-7,1920`)
inclui `margin` com contribuição `0,0000` (margem não mudou nesta
transição — comportamento esperado, Seção 11/12). O nível de `ΔIPIA`
difere entre os dois modos porque `PPI_OFFER` inclui a margem em ambos
os períodos (afeta o nível de PPI, não a decomposição da variação) — são
duas séries conceitualmente diferentes por design (ADR 0015), nunca
misturadas.

## Limitations

1. A decomposição granular (FOB/frete/seguro/FX/II/AFRMM/antidumping por
   NCM×país) exige dado bruto do Comex Stat re-buscado ao vivo — a
   vintage persistida só guarda o `PPI_COST`/`PPI_OFFER` já agregado por
   mês, não a granularidade mês×NCM×país. O script de geração faz essa
   busca separadamente (mesmo padrão já usado por
   `scripts/validar_ipia_hrc_v2_final.py`/`scripts/migrar_ipia_hrc_cost_offer.py`),
   nunca recalcula nem substitui o valor oficial já publicado.
2. A decomposição MoM só é calculada entre meses CALENDÁRIO
   estritamente consecutivos (`t = t-1 + 1 mês`) — um gap (mês UNKNOWN
   entre dois meses calculáveis) não produz uma linha de decomposição,
   por design (misturar múltiplos meses de mudança numa única
   "transição" perderia a interpretação limpa de MoM pedida no sprint).
3. O preço doméstico entra como UM driver (`domestic_price`) nesta
   etapa — não decomposto em PIA/IPP/Denton (decomposição de segundo
   nível, explicitamente fora de escopo, candidata a um sprint futuro).
4. D_porto/D_interno contribuem 0 em toda a série real hoje (são
   hold-flat desde a origem do parâmetro) — o motor já suporta atribuir
   contribuição a eles caso um dia se tornem time-varying, mas isso não
   foi observado empiricamente nesta série.
5. `MAX_DRIVERS_EXATO=20` é um guard-rail conservador — o IPIA-HRC usa
   10 (Cost) ou 11 (Offer) drivers, bem abaixo do limite; ICCS/ICS
   futuros que reusarem este motor devem reavaliar o guard-rail se
   precisarem de mais drivers.
6. Nenhuma narrativa causal externa (ex.: "o dólar subiu por causa do
   Fed") é produzida ou pesquisada — a decomposição é estritamente
   `mathematically dominant contribution`, nunca uma explicação
   macroeconômica.

## References

- `docs/adr/0016-ipia-hrc-driver-decomposition-shapley-method.md` —
  decisão formal do método.
- `docs/adr/0015-ipia-hrc-import-parity-scope-cost-core-offer-layer.md` —
  decisão Cost/Offer que esta decomposição respeita.
- `scripts/validar_ipia_hrc_v2_final.py::decompor_mes` — reconstrução
  granular reusada (não reimplementada).
- Shapley, L. S. (1953). "A value for n-person games."
- Shorrocks, A. (2013). "Decomposition procedures for distributional
  analysis: a unified framework based on the Shapley value."
