# IPIA-HRC V2 PIA-based — Validação Econômica Final (Stage G3)

**Vintage analisada:** `20260827T150423Z` (imutável, criada no Stage G2, `data/processed/vintages/ipia_hrc_v2/20260827T150423Z/`)
**Metodologia:** `1.2` (`VERSAO_METODOLOGIA`, inalterada por este batch)
**Script de suporte:** `scripts/validar_ipia_hrc_v2_final.py`
**Status:** análise **retrospectiva** (backtest), não previsão. Nenhum parâmetro foi calibrado, ajustado ou recalibrado a partir desta validação.

Este documento responde às 7 perguntas do objetivo do Stage G3 e registra a evidência que sustenta a resposta. Toda a análise sobre a série OFFICIAL/PROVISIONAL foi feita sobre a **vintage congelada**, reconstruída a partir dos inputs persistidos (`import_side.csv`/`domestic_price.csv`) — nunca por nova chamada às APIs que produziram official.csv/provisional.csv. Duas seções (§6 decomposição granular e §5 ancora corporativa) fazem chamadas de rede **separadas**, exclusivamente para validação independente — nunca usadas para recalcular ou substituir a vintage.

---

## 1. A vintage e a série completa

A vintage persiste apenas OFFICIAL (48 meses) + PROVISIONAL (30 meses) — os meses `UNKNOWN` não são escritos em arquivo. Para esta validação, a série **completa** (175 meses, incluindo `UNKNOWN`) foi reconstruída a partir de `import_side.csv`+`domestic_price.csv` via `calcular_ipia_hrc_v2_pia()` — a mesma função que produziu a vintage — e confirmada bit-a-bit contra `official.csv`/`provisional.csv` (mesma contagem de linhas, mesmos valores). A série completa cobre 2012-01 a 2026-07 (import side começa em 2012 pela cesta NCM; domestic side começa em 2019 pela PIA-Produto).

Distribuição por status na série completa: 97 `UNKNOWN`, 30 `PROVISIONAL`, 27 `EXPERIMENTAL`, 21 `PUBLICATION_GRADE`.

---

## 2. Dataset analítico e auditoria de unidades

**Artefato:** `data/processed/validation/ipia_hrc_v2_final_validation.csv` (175 linhas — reference_period, ipia_hrc_v2, publication_status, preco_domestico_rs_t, ppi_rs_t, import_status, total_kg, known/unknown_policy_kg, policy_coverage, ppi_lower/upper, ppi_uncertainty_range_pct, pia_reference_year, pia_anchor_price_rs_t, ipp_series_id, domestic provenance/proxy/validation, is_provisional, last_pia_year).

**Auditoria de unidades** (nenhum erro encontrado):

| Grandeza | Unidade | Faixa observada | Checagem |
|---|---|---|---|
| `preco_domestico_rs_t` | BRL/t | 2.309–6.424 | ordem de grandeza correta para HRC |
| `ppi_rs_t` | BRL/t | 1.625–7.064 | idem |
| `ipia_hrc_v2` | adimensional × 100 | 70,06–154,13 | `ipia = domestico/ppi*100`, erro de reconstrução manual = **0,0000000000** |
| `total_kg` | kg | 55.100–142.180.892 | mediana ≈ 15.636 t/mês, plausível |
| PIA anual (`receita_liquida_mil_rs`) | **mil** reais → ×1000 → reais | 2019: R$2.406,92/t … 2023: R$4.844,33/t | conversão mil-reais→reais confirmada explicitamente; mesma ordem de grandeza dos preços mensais |
| `policy_coverage` | fração [0,1] | 0,0000–1,0000 | dentro de faixa |
| `ppi_uncertainty_range_pct` | fração decimal (não %) | 0,0000–0,0139 | máx. 1,39% — bem abaixo do limiar de 2% |

Nenhuma transformação com erro de ×100/×1000/kg↔t/mil↔reais/percentual↔decimal foi encontrada.

---

## 3. Identidade contábil do import side (reconstrução exata)

`decompor_mes()` (novo helper, `scripts/validar_ipia_hrc_v2_final.py`, testado em `tests/unit/test_validar_ipia_hrc_v2_decompor_mes.py`) reconstrói FOB/frete/seguro/câmbio/II/AFRMM/AD/porto/frete-interno/margem a partir das linhas granulares (mês×NCM×país) de `custo_importacao_bottom_up_mensal()` e soma de volta ao PPI. **Achados de processo, não de produção (dois, ambos corrigidos e testados nesta stage, nenhum tocou `src/`):**

1. a primeira versão deste helper ponderava a *alíquota* de II/AFRMM em vez do *valor monetário* por grupo — divergia em 0,01–0,04% quando NCMs no mesmo mês têm alíquotas diferentes (média ponderada de um produto ≠ produto das médias ponderadas). Corrigido para ponderar os valores monetários por grupo (mesma ordem de operação de `_ppi_brl_t`); o motor de produção (`custo_importacao_bottom_up_mensal`/`agregar_ipia_hrc_multi_ncm_mensal`) nunca teve esse problema — ele já pondera o `ppi_brl_t` pronto por grupo, nunca uma taxa.
2. a primeira versão também **reimplementava** o limiar de elegibilidade (cobertura ≥60% para EXPERIMENTAL) mas **esquecia** o segundo limiar já aprovado (incerteza ≤2%, `LIMIAR_INCERTEZA_EXPERIMENTAL_PCT`) — achado do code review desta stage. Corrigido eliminando a reimplementação por completo: `decompor_mes()` agora recebe o `import_status` **já calculado pelo motor de produção** para cada mês e delega 100% da decisão a ele, em vez de re-derivar limiares (fonte única de verdade, sem risco de desalinhamento futuro se os limiares forem revisados). Confirmado ao vivo: dos 131 meses no painel de decomposição granular, **0** têm `import_status` diferente de `EXPERIMENTAL`/`PUBLICATION_GRADE` — nenhum mês `UNKNOWN` vaza para a decomposição. Os 53 meses a mais que os 78 meses de IPIA composto calculável são meses onde o import side sozinho já é conhecido mas o domestic ainda não existe (pré-2019) — universo maior, mas ainda correto, nunca um vazamento de UNKNOWN.

Amostra (início, meio, último `PUBLICATION_GRADE`, último `PROVISIONAL`, mínimo IPIA, máximo IPIA) — **erro de reconstrução = 0,000000% em todos os 6 meses**:

| Mês | FOB USD/t | Frete USD/t | Câmbio | CIF BRL/t | II BRL/t (alíq.) | AFRMM BRL/t (alíq.) | PPI reconstruído | PPI na vintage |
|---|---|---|---|---|---|---|---|---|
| 2019-02 (início) | 584,50 | 51,53 | 3,6694 | 2.338,94 | 280,67 (12,0%) | 47,27 (25,0%) | 3.107,3901 | 3.107,3901 |
| 2021-11 (meio) | 914,06 | 93,93 | 5,6694 | 5.718,65 | 654,89 (11,45%) | 133,14 (25,0%) | 7.063,4612 | 7.063,4612 |
| 2023-12 (últ. PG) | 540,97 | 49,97 | 4,9191 | 2.914,62 | 305,34 (10,48%) | 19,66 (8,0%) | 3.696,8261 | 3.696,8261 |
| 2026-06 (últ. PROV) | 539,53 | 42,92 | 5,0303 | 2.935,05 | 304,41 (10,37%) | 17,27 (8,0%) | 3.716,2738 | 3.716,2738 |
| 2020-05 (mín. IPIA) | 507,63 | 28,19 | 5,4270 | 2.910,08 | 349,21 (12,0%) | 38,24 (25,0%) | 3.756,9609 | 3.756,9609 |
| 2021-05 (máx. IPIA) | 498,26 | 31,77 | 5,4036 | 2.865,05 | 343,81 (12,0%) | 42,92 (25,0%) | 3.709,8356 | 3.709,8356 |

Custos portuários (R$210/t) e frete interno (R$140/t) são **constantes fixas** de `ParamsIPIA` — não variam mês a mês nem contribuem para nenhum movimento do índice (por construção, não bug).

---

## 4. Domestic Price Validation (PIA-based vs. âncora corporativa)

Chamada de rede separada (`preco_domestico_hrc_mensal_v2()`), só validação, nunca calibração.

15 meses sobrepostos (2025-04 a 2026-06): delta_pct médio **-11,66%**, mediana -11,14%, desvio-padrão **1,49pp** (gap estável). Delta absoluto médio -603,9 BRL/t. Tendência do gap: **-0,09pp/mês** (praticamente plana — sem deriva material). Correlação de níveis: **0,8481** (forte co-movimento apesar do nível diferente).

**Interpretação:** gap negativo, estável e correlacionado é exatamente o padrão esperado se a âncora corporativa "Siderurgia" está inflada por mix de produto frente a um preço mais específico de HRC (hipótese já registrada nos ADRs 0010/0011) — as duas séries se movem juntas, só em níveis diferentes. Nenhum ajuste foi aplicado.

---

## 5. Import Side Validation (PPI V2 bottom-up vs. PPI legado)

`calcular_ipia_mensal()` (legado, alíquota fixa 10,8%/8%/AD=0, um único CIF combinado) vs. PPI V2 bottom-up, mesmo `df_bruto`. Janela comparável real: 2025-04 a 2026-06 (15 meses — limitada pela cobertura curta do CSV curado legado, já documentado desde o Stage E9).

- **MAE:** 4,96 BRL/t
- **MAPE:** 0,13%
- **Diferença percentual mediana:** -0,07%
- **Correlação:** 0,9997
- **Maiores divergências:** todas < 0,64% (2026-05: 0,63%)

Concordância muito estreita — esperada, porque no regime `PUBLICATION_GRADE` (>= 2022-04) 12 dos 13 NCMs convergem para 10,8% (só 72083910 diverge, 9%), então a constante legada é uma boa aproximação exatamente nesse período (fato já documentado no ADR 0009, agora confirmado empiricamente). Legado tratado como benchmark de comportamento, nunca autoridade metodológica — nenhum ajuste feito.

---

## 6. Outliers

**Artefato:** `data/processed/validation/ipia_hrc_v2_outliers.csv` (34 linhas).

10 menores IPIA: 2020-05 (70,06) a 2019-03 (84,68) — concentrados na janela `EXPERIMENTAL` (2019-2022), coerente com domestic/PPI ainda próximos e IPIA <100 dominante nesse período (ver §11).

10 maiores IPIA: 2021-05 (154,13) a 2021-06 (127,77) — concentrados no super-ciclo global do aço de 2021, mais 2 meses `PROVISIONAL` recentes (2026-04/05).

**Nota metodológica de processo:** o `.diff()` ingênuo sobre a série filtrada (só meses calculáveis) confundiria saltos de 2-3 meses (atravessando gaps `UNKNOWN`) com mudanças de 1 mês — corrigido para usar o calendário completo reindexado, onde o delta só existe entre meses efetivamente consecutivos.

**Maiores mudanças mensais genuínas (>2 desvios-padrão, limiar=23,36):**

| Mês | ΔIPIA | Status | Classificação |
|---|---|---|---|
| 2023-02 | +36,71 | PUBLICATION_GRADE | A/B — FOB reportado no Comex oscila em serrote (Jan=698,6 → Fev=531,0 → Abr=694,9 → Mai=546,7 USD/t) entre meses de volume moderado (8,5M–38,8M kg) — mistura de origem/NCM reportada mês a mês, não sinal de bug de cálculo |
| 2023-05 | +30,06 | PUBLICATION_GRADE | mesmo padrão acima |
| 2021-06 | +26,36 | EXPERIMENTAL | A — continuação do super-ciclo global 2021 (FOB/CIF em alta generalizada) |
| 2022-11 | +26,19 | PUBLICATION_GRADE | A — dentro do range observado no período de reversão pós-2021 |

Nenhum outlier foi excluído da série. `2023-02`/`2023-05` são o caso mais chamativo — a explicação econômica (mix de FOB reportado por NCM/país variando mês a mês) é plausível e consistente com a mecânica real de estatística de comércio exterior mensal, mas fica registrada como **B (efeito de dado/cobertura, não bug de metodologia)** para acompanhamento se o padrão persistir.

---

## 7. Gap de 2019-01

```
reference_period       2019-01-01
preco_domestico_rs_t   2.430,33 BRL/t   (BENCHMARKED, is_provisional=False)
ppi_rs_t                NaN
import_status           UNKNOWN
publication_status      UNKNOWN
policy_coverage         0,01106  (1,11%)
ppi_uncertainty_range_pct  NaN
ipia_hrc_v2              NaN
```

**Explicação definitiva, não é bug:** o lado doméstico está presente e é benchmarked. O lado import falha: `policy_coverage = 1,11%` — muito abaixo do limiar EXPERIMENTAL de 60% (regra já aprovada, ADR 0009 §9.5.2). Do volume importado em 2019-01 (1.745.000 kg), quase tudo tem NCM/país sem política comercial resolvida naquele mês específico. É exatamente a regra de publicação já aprovada operando como projetada num mês de cobertura de política baixíssima — nunca preenchido, nunca estimado. `2019-02` (primeiro mês OFFICIAL) tem coverage=90,17%, dentro da regra.

Achado colateral: o último mês da série completa (`2026-07`) também é `UNKNOWN` pelo mesmo mecanismo (coverage=4,44%, mas `total_kg=54,7M` — volume alto, cobertura baixa), plausivelmente por cair dentro da janela de cota tarifária GECEX 929/2026 (consumo de cota não rastreado, `resolver_ii` retorna UNKNOWN por desenho) somado ao fato de ser o mês mais recente da coleta (dado ainda incompleto). Mesmo mecanismo, mesma regra, nenhuma ação necessária.

---

## 8. Fronteiras de status (EXPERIMENTAL / PUBLICATION_GRADE / PROVISIONAL)

| Janela | Meses | IPIA média | IPIA mediana | IPIA std | Domestic média | PPI média | total_kg mediana |
|---|---|---|---|---|---|---|---|
| A. EXPERIMENTAL (2019-02–2022-03) | 27 | 99,07 | 87,69 | 21,61 | 3.908,9 | 3.897,3 | 12.758.608 |
| B. PUBLICATION_GRADE (2022-04–2023-12) | 21 | 104,33 | 102,87 | 18,11 | 5.075,3 | 5.043,4 | 23.298.191 |
| C. PROVISIONAL (2024-01–presente) | 30 | 115,18 | 113,37 | 8,04 | 4.696,3 | 4.099,9 | 53.458.752 |

**Fronteira EXPERIMENTAL→PUBLICATION_GRADE (2022-03→04):** ambos os meses caem dentro de um gap `UNKNOWN` pré-existente (2022-02/03, mesmo mecanismo de baixa cobertura de política do §7) — o salto exato na fronteira **não é diretamente observável** porque a fronteira cai dentro de um gap de dado, não de metodologia. Comparando os meses calculáveis mais próximos de cada lado (não adjacentes no calendário): último EXPERIMENTAL = 2022-01 (83,71), primeiro PUBLICATION_GRADE = 2022-04 (91,62) — diferença de 7,91 pontos ao longo de **3 meses de calendário** (≈2,6 pts/mês), abaixo da mediana de movimento mensal ordinário (6,38) — **sem evidência de salto artificial**.

Episódio econômico real identificado exatamente nessa transição: a alíquota de AFRMM caiu de 25% para 8% em 2022-03-25 (Lei 14.301/2022, já documentada em `trade_policy.py`) — confirmado empiricamente no painel de decomposição (AFRMM: R$170,2/t em 2022-01 → R$44,6/t em 2022-04) simultaneamente a uma apreciação do câmbio (5,58→4,70 BRL/USD). O PPI caiu de 6.755 para 6.181 BRL/t **apesar do FOB ter subido** (846,7→959,7 USD/t) — o domestic ficou praticamente estável (5.654,8→5.662,5) — o IPIA subiu como consequência direta e explicável de política+câmbio, não de um artefato de fronteira de status.

**Fronteira PUBLICATION_GRADE→PROVISIONAL (2023-12→2024-01):** salto = **4,74 pontos**, **menor** que a mediana de movimento mensal ordinário da série inteira (6,38) — dentro do range típico, sem evidência de descontinuidade introduzida pela mudança de regime de publicação.

---

## 9. Validação do Denton (fronteiras dezembro→janeiro)

Mudança mensal ordinária (não-fronteira) do domestic price benchmarked: mediana **88,73 BRL/t**. Mudança na fronteira dez→jan: mediana **139,71 BRL/t** (razão 1,57×).

| Fronteira | Δ (BRL/t) |
|---|---|
| 2020-01 | 78,81 |
| 2021-01 | **294,39** |
| 2022-01 | 200,61 |
| 2023-01 | 31,38 |

**2021-01 é a maior fronteira e explica a razão elevada:** o alvo PIA anual salta de R$2.840,67/t (2020) para R$5.644,69/t (2021), **+99%** — o super-ciclo global do aço de 2021, evento de mercado real e amplamente documentado, não artefato de Denton. **Excluindo 2021, a razão fronteira/ordinário cai para 0,89×** — abaixo de 1, ou seja, **sem evidência de step artificial** nas demais fronteiras.

**Restrição anual (`mean(preço mensal do ano) == alvo PIA`)** — verificada empiricamente para os 5 anos benchmarked:

| Ano | Média mensal | Alvo PIA | Erro |
|---|---|---|---|
| 2019 | 2.406,9181 | 2.406,9181 | +0,00000000% |
| 2020 | 2.840,6651 | 2.840,6651 | +0,00000000% |
| 2021 | 5.644,6906 | 5.644,6906 | -0,00000000% |
| 2022 | 5.393,3126 | 5.393,3126 | +0,00000000% |
| 2023 | 4.844,3297 | 4.844,3297 | +0,00000000% |

Restrição batida numericamente exata em todos os anos — nenhuma reimplementação do Denton foi necessária (já estava correto).

---

## 10. Market-Logic Check

Painel de 78 meses (decomposição granular + IPIA calculável), correlações de **nível**:

| Relação | Correlação | Sinal esperado (ceteris paribus) | Resultado |
|---|---|---|---|
| FX × PPI | +0,471 | positivo | ✅ |
| FX × IPIA | +0,328 | negativo | ❌ (nível) |
| FOB × PPI | +0,944 | positivo | ✅ |
| FOB × IPIA | -0,295 | negativo | ✅ |
| Domestic × IPIA | +0,456 | positivo | ✅ |

Correlações de **variação mensal** (delta a delta — isola melhor o efeito mecânico, menos sujeito a confundidor de ciclo comum):

| Relação | Correlação |
|---|---|
| ΔFX × ΔPPI | +0,336 |
| **ΔFX × ΔIPIA** | **-0,302** ✅ |
| ΔFOB × ΔPPI | +0,875 |
| ΔFOB × ΔIPIA | -0,798 ✅ |

**Interpretação:** FOB tem o sinal correto em nível E em variação, com magnitude forte — o driver dominante do PPI é claramente o preço internacional. FX em **nível** aparece com sinal contrário ao ingênuo "ceteris paribus" porque FX e domestic price NÃO são independentes na amostra real (ambos correlacionados ao ciclo global de commodities — BRL tende a se depreciar exatamente quando o mercado global de aço está em alta, e o domestic price sobe junto) — um confundidor macro clássico, não um erro de cálculo. Em **variação mensal** (que isola melhor o efeito mecânico de curto prazo, sem depender tanto do nível de longo prazo), o sinal de FX inverte para o esperado (-0,302). Correlação usada estritamente como sanity check de sinal, nunca como causalidade — conforme instruído.

---

## 11. Sensitivity / Stress

Choques aplicados sobre 2019-02 (mês inicial, PPI base = 3.107,39 BRL/t), reconstrução exata via `_ppi_brl_t`:

| Choque | ΔPPI | ΔIPIA |
|---|---|---|
| FX +10% | +8,84% | -8,84% |
| FX -10% | -8,84% | +8,84% |
| FOB +10% | +7,96% | -7,96% |
| FOB -10% | -7,96% | +7,96% |
| Frete internacional +20% | +1,72% | -1,72% |
| Custo portuário +20% | +1,39% | -1,39% |
| Frete interno +20% | +0,93% | -0,93% |
| Margem importador +5pp | +4,85% | -4,85% |

Todos os sinais **econômicos corretos** (choque positivo em custo de importação → PPI sobe → IPIA cai, sempre); elasticidades ordenadas por materialidade de forma plausível (FX > FOB > margem > frete internacional > custo portuário > frete interno). Nenhum parâmetro default foi alterado — apenas simulação.

---

## 12. Volume / Liquidez

Correlação entre `total_kg` e |Δ mensal do IPIA| (meses consecutivos): **-0,189** — fraca a moderada, no sentido esperado (menor volume associado a mais volatilidade), mas não dominante.

8 meses de baixo volume (percentil 10, ≤6,69M kg): 2019-03, 2019-06, 2019-09, 2020-12, 2021-05, 2021-08, 2022-06, 2022-08. **5 desses 8 meses também aparecem entre os 20 valores mais extremos de IPIA** (2019-03, 2019-09, 2021-05, 2021-08, 2022-08) — uma sobreposição material, embora não sistemática (nem todo extremo é baixo volume, nem todo baixo volume é extremo).

Nenhuma suavização legada foi reaplicada ao V2 bottom-up nesta validação. **Recomendação (não implementada):** a sobreposição parcial entre baixa liquidez e outliers de nível é evidência suficiente para justificar uma decisão Level 3 futura sobre se/como tratar baixa liquidez no V2 (ex.: um limiar mínimo de volume, ponderação por confiabilidade análoga à legada, ou aceitar os extremos como dado real) — não implementada silenciosamente aqui.

---

## 13. Policy Coverage — verificação empírica

**EXPERIMENTAL** (27 meses): coverage min=67,8%, mediana=90,1%, max=99,8%; uncertainty_range_pct min=0,007%, mediana=0,364%, max=1,214%. **Violações da regra (coverage≥60% E uncertainty≤2%): 0** — regra respeitada empiricamente em 100% dos meses.

**PUBLICATION_GRADE** (21 meses): coverage min=100,0000%, max=100,0000%. **Violações da regra (100% do volume observado com política resolvida): 0**.

Ambas as regras já aprovadas (ADR 0009) foram confirmadas empiricamente sem exceção na vintage real.

---

## 14. Qualidade do Provisional (2024+)

Transição 2023-12→2024-01: domestic +2,63% (4.561,5→4.681,5), PPI +6,73% (3.696,8→3.945,7), IPIA -4,74 pontos (123,39→118,65) — PPI subiu mais que o domestic, movimento coerente e consistente com o range ordinário (§8).

Trajetória 2024-2026 (30 meses PROVISIONAL): IPIA vai de 118,65 a 126,74, mínimo 95,64 (2024-12), máximo 131,32 (2026-05), **std=8,04** — **visivelmente menos volátil** que o OFFICIAL como um todo (std=20,12). Esperado: o provisional é encadeado mês a mês pelo IPP (variação suave de índice de preços), não resolvido pelo Denton mês a mês contra uma âncora anual observada — a suavidade extra é uma propriedade mecânica do método de extensão, não um sinal de manipulação.

**Nenhuma promoção provisional→official foi feita nesta validação** — consistente com a regra já aprovada.

---

## 15. Cross-check com evidência de mercado independente

Reaproveitando `docs/adr/0009-*`/`docs/research/hrc_import_policy_history.md`/`trade_policy.py` (nenhuma pesquisa externa nova foi necessária):

- **PROJECT DATA:** AFRMM caiu de 25%→8% em 2022-03-25 (Lei 14.301/2022) — confirmado empiricamente no painel de decomposição (§8), coincide exatamente com a data de vigência documentada.
- **PROJECT DATA:** investigação antidumping de HRC chinês aberta em 2025-06-03 (Circular SECEX 39/2025), sem direito provisório aplicado — confirmado empiricamente: `ad_brl_t=0,00` em TODOS os meses da amostra, incluindo os mais recentes (2026-06) — reflete corretamente que a investigação está em curso mas ainda não gerou direito aplicável.
- **INFERENCE (bem documentada externamente, não pesquisa nova):** o pico de IPIA em 2021 (máx. 154,13 em 2021-05) coincide com o super-ciclo global de preços do aço de 2021 (recuperação pós-COVID + restrição de oferta), evento amplamente conhecido e já referenciado na literatura de mercado — usado aqui só como checagem de ordem de grandeza, não como benchmark comercial.

Nenhuma fonte paga/inacessível foi usada como se fosse dado reproduzível.

---

## 16. Episódios econômicos principais

1. **2019-02 a 2020-07 (EXPERIMENTAL, nível baixo):** IPIA entre 70-94, domestic e PPI próximos, ambos baixos em nível absoluto — início da série, mercado relativamente equilibrado.
2. **2020-05 (mínimo absoluto, IPIA=70,06):** FOB baixo (507,6 USD/t) mas domestic ainda mais baixo relativamente — combinação de choque de demanda doméstica (início da pandemia) com custo de importação já em recuperação.
3. **2021 (super-ciclo global do aço):** CIF/FOB dispara (FOB chega a ~914-960 USD/t vs. ~500-580 na série inicial), IPIA atinge o máximo da série completa (154,13 em 2021-05) e oscila fortemente (127-154) ao longo do ano — evento de mercado real, claramente visível na decomposição (dominado por CIF, não por política).
4. **2022-03/04 (transição EXPERIMENTAL→PUBLICATION_GRADE + corte do AFRMM):** AFRMM cai de 25% para 8% (Lei 14.301/2022), câmbio aprecia, IPIA sobe de 83,71 para 91,62 ao longo de 3 meses — mudança de política real coincidindo com (mas não causando artificialmente) a transição de status.
5. **2023-02/05 (maiores saltos mensais genuínos):** FOB reportado no Comex oscila em serrote entre meses de volume moderado — efeito de mix de dado, não bug (ver §6).
6. **2023-12→2024-01 (transição PUBLICATION_GRADE→PROVISIONAL):** salto de 4,74 pontos, menor que o movimento mensal típico — transição suave, sem artefato.
7. **2024-2026 (janela PROVISIONAL corrente):** IPIA oscila entre 95,64 e 131,32, terminando em 126,74 (2026-06) — trajetória menos volátil que o histórico oficial, refletindo a mecânica de encadeamento por IPP.

---

## 17. Backtest distribution

**Artefato:** `data/processed/validation/ipia_hrc_v2_validation_summary.csv`.

| Janela | n | Média | Mediana | Std | p10 | p25 | p75 | p90 | %<90 | %90-100 | %100-110 | %>110 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TODOS | 78 | 106,68 | 110,00 | 17,81 | 84,24 | 90,87 | 118,01 | 128,85 | 24,4% | 11,5% | 14,1% | 50,0% |
| A. EXPERIMENTAL | 27 | 99,07 | 87,69 | 21,61 | 79,36 | 84,71 | 110,36 | 131,76 | 51,9% | 11,1% | 11,1% | 25,9% |
| B. PUBLICATION_GRADE | 21 | 104,33 | 102,87 | 18,11 | 84,47 | 90,62 | 114,85 | 131,74 | 23,8% | 23,8% | 9,5% | 42,9% |
| C. PROVISIONAL | 30 | 115,18 | 113,37 | 8,04 | 107,47 | 110,19 | 122,13 | 126,80 | 0,0% | 3,3% | 20,0% | 76,7% |

**Persistência** (sequências de meses calendário-consecutivos, gap quebra a sequência): 4 sequências acima de 100 (duração média 12,5 meses, máx 22 meses), 4 sequências abaixo de 100 (duração média 7,0 meses, máx 13 meses).

**Leitura econômica:** a distribuição desloca-se progressivamente de abaixo-da-paridade (EXPERIMENTAL, mediana 87,69) para acima-da-paridade (PROVISIONAL, mediana 113,37) — coerente com a narrativa geral de aumento de pressão de paridade de importação ao longo do tempo (câmbio, custo, e domestic evoluindo de formas diferentes), sem indicar comportamento erracional.

---

## 18. Paridade = 100

Confirmado: **100 não é uma normalização estatística** (a série nunca foi rebasada ou ajustada para centrar em 100) — é a identidade econômica `Domestic Price == Import Parity Price`. A série oscila livremente acima e abaixo de 100 conforme a evidência (ver §17), com médias e medianas materialmente diferentes de 100 em cada janela de status — prova de que 100 não foi artificialmente imposto como centro.

---

## 19. Quality Scorecard

### IMPORT SIDE
| Dimensão | Nota | Justificativa |
|---|---|---|
| Qualidade da fonte | 🟢 GREEN | Comex Stat oficial, `/general` POST estruturado, granularidade mês×NCM×país |
| Qualidade da política histórica | 🟡 YELLOW | Publication-grade só a partir de 2022-04 (ADR 0009); janela experimental 2012-2022-03 tem II não confirmado para 9/13 NCMs (faixa 10-14%, nunca ponto central) |
| Granularidade | 🟢 GREEN | Bottom-up por (mês, NCM, país), II/AFRMM/AD resolvidos antes de qualquer soma — decomposição reconstruída com erro 0% |
| Reprodutibilidade | 🟢 GREEN | Reconstrução exata confirmada a partir de `import_side.csv` persistido, sem nova chamada de API |
| Limitações | custos portuários/frete interno são constantes fixas (não time-varying); antidumping documentado mas ainda 0 no período recente (investigação em curso) |

### DOMESTIC SIDE
| Dimensão | Nota | Justificativa |
|---|---|---|
| Especificidade de produto | 🟡 YELLOW | PIA-Produto é HRC-específico (melhor que a âncora "Siderurgia"), mas mistura mercado interno+exportação (12-43% exposição, ADR 0010) — PROXY explícito |
| Frequência temporal | 🟡 YELLOW | Ancora ANUAL distribuída via Denton — nível exato só no fechamento anual, meses individuais são estimados |
| Risco de proxy | 🟡 YELLOW | IPP 242-Siderurgia (movimento mensal) também não é específico de HRC — dois PROXYs empilhados, ambos rotulados explicitamente |
| Risco de revisão | 🟢 GREEN | Mecanismo de congelamento (Stage G2) garante que OFFICIAL nunca muda; PROVISIONAL revisável por design, nunca escondido |
| Reprodutibilidade | 🟢 GREEN | Restrição anual bate exatamente (erro 0,00000000%) em todos os 5 anos benchmarked |

### COMPOSITE IPIA
| Dimensão | Nota | Justificativa |
|---|---|---|
| Interpretabilidade econômica | 🟢 GREEN | Sinais de sensitivity 100% corretos; decomposição transparente; FOB é o driver dominante, como esperado |
| Estabilidade | 🟢 GREEN | Nenhum salto artificial nas fronteiras de status; restrição Denton exata; congelamento comprovado imutável |
| Qualidade de outliers | 🟡 YELLOW | Todos explicáveis (evento real 2021, política 2022, mix de FOB 2023) — nenhum suspeito, mas o mix de FOB de 2023-02/05 merece acompanhamento |
| Cobertura histórica | 🟡 YELLOW | 48 meses OFFICIAL (2019-02 a 2023-12) + 30 PROVISIONAL — curta comparada à ambição de "maior série historicamente comparável" (2020-presente é o mínimo, aqui atingido, não superado) |
| Qualidade do valor corrente | 🟡 YELLOW | PROVISIONAL, nunca promovido, propriamente rotulado — não é um problema de qualidade, é uma limitação de design já aceita |

Nenhuma média foi calculada — o scorecard é qualitativo, por dimensão, como instruído.

---

## 20. DECISÃO FINAL

### FACT
- Todas as identidades numéricas (fórmula do IPIA, decomposição do PPI, restrição anual do Denton) batem exatamente (erro 0,000000%) contra a vintage congelada.
- As duas regras de publication_status já aprovadas (coverage≥60%/uncertainty≤2% para EXPERIMENTAL; coverage=100% para PUBLICATION_GRADE) foram confirmadas empiricamente sem nenhuma exceção.
- Nenhum salto artificial foi encontrado em nenhuma fronteira de status.
- Todos os sinais de sensitivity/market-logic são economicamente corretos.
- A comparação contra dois benchmarks independentes (âncora corporativa, PPI legado) mostra diferenças estáveis e explicáveis, nunca usadas para calibrar a série PIA-based.
- O gap de 2019-01 está definitivamente explicado (cobertura de política, não bug).

### EVIDENCE
Ver seções 1-19 acima, com artefatos em `data/processed/validation/` e `docs/validation/ipia_hrc_v2_final_validation.md` (este documento).

### OPTIONS
- **A. READY FOR PUBLICATION WIRING** — rejeitada: os 4 bloqueantes de projeto do IPIA V2 (`docs/METODOLOGIA.md` §15 — validação ao vivo do Comex POST, cobertura histórica de frete/seguro, validade de NCM por período, Excel estruturado do Aço Brasil) não foram objeto desta validação e não foram formalmente fechados aqui; wiring de CLI/PDF estava explicitamente fora de escopo deste batch.
- **B. READY WITH DISCLOSED LIMITATIONS** — a mais defensável: a economia do índice é sólida, reprodutível e sem defeito de metodologia encontrado; as limitações (cobertura histórica curta do domestic, dois PROXYs empilhados no domestic, tratamento de baixa liquidez ainda não decidido, bloqueantes de projeto §15 ainda abertos) são conhecidas e já documentadas — não impedem que o índice avance para a próxima etapa de decisão, desde que essas limitações sejam explicitamente divulgadas.
- **C. NEEDS LIMITED TECHNICAL FIXES** — rejeitada: nenhum bug de produção foi encontrado (o único bug encontrado estava no script de validação novo, corrigido e testado nesta mesma stage).
- **D. METHODOLOGY DECISION REQUIRED** — parcialmente aplicável apenas ao item de baixa liquidez (§12), não ao índice como um todo — registrado como recomendação, não como bloqueio.
- **E. NOT DEFENSIBLE** — rejeitada: a evidência é extensa, positiva e reprodutível.

### RECOMMENDATION
**B. READY WITH DISCLOSED LIMITATIONS.**

O IPIA-HRC V2 PIA-based passa nesta validação econômica final: a fórmula, a decomposição, as regras de status e a mecânica do Denton estão corretas e reproduzíveis; os movimentos históricos são majoritariamente explicáveis por eventos de mercado e política reais e documentados; não há evidência de tuning para aproximar de 100 nem de calibração contra o corporate. Antes de qualquer wiring de publicação (fora de escopo deste batch), duas coisas devem ser explicitamente resolvidas, ambas via decisão Level 3 futura, não implementadas aqui:

1. fechar (ou reafirmar como já fechados) os 4 bloqueantes de projeto do `docs/METODOLOGIA.md` §15;
2. decidir se/como tratar a sobreposição parcial entre baixa liquidez e outliers de nível (§12) — ou aceitar explicitamente que não requer tratamento.

---

## 21. Metodologia deste documento

- **Reprodutibilidade:** toda a análise sobre a série oficial/provisional foi feita exclusivamente a partir da vintage `20260827T150423Z` (imutável) — nenhuma chamada de rede alterou ou recalculou official.csv/provisional.csv.
- **Validação independente separada:** duas fontes externas (âncora corporativa, decomposição granular via novo fetch do Comex/BCB) foram consultadas exclusivamente para comparação — nunca para substituir a vintage.
- **"Reproduzir uma vintage do IPIA" ≠ "reconstruir o estado histórico exato das APIs externas":** a decomposição granular usada nesta validação foi buscada AO VIVO nesta stage (não persistida na vintage) — se o Comex Stat ou o BCB revisarem retroativamente seus próprios dados entre a criação da vintage (2026-08-27) e a data desta validação, a decomposição granular pode não ser byte-idêntica ao que produziu a vintage, mesmo que a vintage em si permaneça imutável e correta para os inputs que ela persiste. Esta distinção já está registrada no ADR 0012/`docs/METODOLOGIA.md` §12.12 e se aplica igualmente aqui.
