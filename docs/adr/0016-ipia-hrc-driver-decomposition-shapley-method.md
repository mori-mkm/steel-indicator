# 0016 - IPIA-HRC Driver Decomposition — exact Shapley method

## Status

**Accepted.** Escopo estritamente metodológico da DECOMPOSIÇÃO ANALÍTICA
(como explicar `ΔIPIA` em contribuições por driver) — **não é uma decisão
sobre o índice econômico** (IPIA/PPI_COST/PPI_OFFER, fórmula, parâmetros
ou publicação permanecem exatamente como estavam; `VERSAO_METODOLOGIA`
não muda). Decisão aprovada explicitamente pelo usuário no prompt que
abriu o sprint "IPIA-HRC — DRIVER DECOMPOSITION ENGINE" (preferência
inicial por Shapley/symmetric decomposition, condicionada a avaliação
comparativa — feita em
`docs/validation/ipia_hrc_driver_decomposition.md`).

## Contexto

O IPIA-HRC hoje publica um único número por mês (`IPIA = preço_doméstico
/ PPI_COST × 100`). O Reporting V3 (futuro, fora do escopo desta etapa)
precisa explicar *por que* o índice mudou mês a mês, em contribuições
atribuíveis a: preço doméstico, FOB, frete, seguro, câmbio, II, AFRMM,
antidumping, D_porto, D_interno (e, em análise `PPI_OFFER` opcional,
margem comercial).

A relação `IPIA = P_dom / PPI_COST × 100` é **não linear** — o
denominador (`PPI_COST`) é ele mesmo uma soma de termos onde câmbio
multiplica FOB, frete, seguro, o valor efetivo de II, AFRMM e
antidumping. Uma decomposição ingênua (somar `Δdomestic - ΔPPI` driver a
driver, sem tratar as interações cruzadas) produziria um resíduo grande
e um método sensível à ordem escolhida para "isolar" cada driver.

## Decisão

A decomposição oficial de drivers do IPIA-HRC usa **Shapley value exato**,
calculado via a fórmula fechada de subconjuntos (`2^n` avaliações da
função, não `n!` permutações) — ver
`steel_indicator.domain.driver_decomposition.shapley_contributions`.

Para `n=10` drivers (modo Cost: preço doméstico + FOB + frete + seguro +
câmbio + II + AFRMM + antidumping + D_porto + D_interno) isso é `2^10 =
1024` avaliações por transição mês-a-mês — computacionalmente trivial
(nenhuma aproximação Monte Carlo necessária). Para `n=11` (modo Offer,
inclui margem) é `2^11 = 2048`.

## Rationale

Comparação completa em
`docs/validation/ipia_hrc_driver_decomposition.md` § "Candidate methods".
Resumo:

- **Sequential replacement**: rejeitado — resultado depende da ordem
  arbitrária escolhida para introduzir os drivers; a interação cruzada
  inteira (ex.: câmbio × FOB) é sempre atribuída ao driver que "chega
  primeiro" na ordem escolhida.
- **Log-decomposition** (`Δlog(IPIA) = Δlog(P_dom) - Δlog(PPI)`): exata e
  aditiva apenas quando a função é um produto puro de fatores positivos.
  `PPI_COST` tem uma SOMA de componentes no denominador (CIF+II+AFRMM+AD+
  D_porto+D_interno), não um produto — decompor essa soma internamente
  via log teria exatamente o mesmo problema de atribuição de interação
  que motivou a escolha do Shapley.
- **Shapley value (aprovado)**: única regra que satisfaz simultaneamente
  *efficiency* (soma das contribuições = `ΔIPIA` exatamente, resíduo ≈0
  por construção — a "efficiency property" de Shapley, não uma
  propriedade aproximada), *symmetry* (dois drivers com o mesmo efeito
  marginal em toda ordem recebem a mesma contribuição) e *linearity* —
  resultado matemático clássico (Shapley 1953), já aplicado a
  decomposição de índices/desigualdade em economia (Shorrocks 2013).
- **Custo computacional**: a formulação por permutações (`n!`) seria cara
  (`10! = 3.628.800`); a formulação equivalente por subconjuntos (`2^n =
  1024`) é a mesma resposta exata, ~3.500× mais barata — trivial nesta
  escala. Nenhuma aproximação Monte Carlo foi necessária.

## Interaction treatment

Ver `docs/validation/ipia_hrc_driver_decomposition.md` § "Interaction
treatment" para a prova algébrica completa. Resumo: o câmbio multiplica
FOB, frete e seguro (via CIF) e também os valores efetivos de II, AFRMM
e antidumping (via a conversão USD→BRL de cada um) — a decomposição
reparametriza esses dois últimos como valores monetários efetivos em
USD/t (não alíquotas), o que preserva reconstrução EXATA do `PPI_COST`
oficial mesmo com NCMs heterogêneos agregados no mês (evita o mesmo viés
de covariância entre alíquota e CIF/t por NCM já documentado em
`decompor_mes`, `scripts/validar_ipia_hrc_v2_final.py`). O Shapley então
distribui a interação câmbio×(FOB+frete+seguro+II+AFRMM+antidumping) de
forma simétrica entre os drivers envolvidos, nunca atribuindo o cruzamento
inteiro a um único driver por escolha arbitrária de ordem.

## Consequences

- **Nenhum valor oficial muda.** `PPI_COST`, `PPI_OFFER`, `IPIA`,
  `VERSAO_METODOLOGIA` (permanece "1.5"), parâmetros e vintages
  permanecem exatamente como estavam. A decomposição é uma camada
  analítica DERIVADA da vintage já publicada, nunca uma nova fonte de
  verdade econômica.
- **Nenhuma vintage nova é criada** por esta decisão nem pelo script que
  a executa (`scripts/gerar_ipia_hrc_driver_decomposition.py`).
- API reutilizável introduzida:
  `steel_indicator.domain.driver_decomposition.shapley_contributions`
  (motor genérico, sem premissa de IPIA — reusável para ICCS/ICS no
  futuro) e `indices_setoriais.decompor_variacao_ipia_hrc` (wrapper
  específico do IPIA-HRC). Reporting V3 deve consumir esta API, nunca
  reimplementar a matemática em `pages.py` (`.claude/rules/reporting.md`).
- Margem comercial nunca aparece na decomposição oficial (`modo="cost"`)
  — só em análise `PPI_OFFER` opcional (`modo="offer"`), nunca misturada
  com a série oficial.
- Resultado inclui `residual` explícito por transição (deve ser ≈0 por
  construção — reportado, nunca omitido, mesmo sendo tipicamente ruído de
  ponto flutuante).

## Alternatives considered

Ver Rationale acima (sequential replacement, log-decomposition) — ambas
rejeitadas por não satisfazerem independência de ordem/aditividade exata
sem uma regra de atribuição de interação adicional e arbitrária.

## Documentos relacionados

- `docs/validation/ipia_hrc_driver_decomposition.md` — investigação
  completa, prova algébrica, validação sintética e sobre a série real.
- `docs/adr/0015-ipia-hrc-import-parity-scope-cost-core-offer-layer.md` —
  decisão Cost/Offer que esta decomposição respeita (nunca mistura
  margem no modo oficial).
- `src/steel_indicator/domain/driver_decomposition.py` — motor genérico.
- `src/indices_setoriais.py` (seção "3j. IPIA-HRC - Driver Decomposition")
  — wrapper específico do IPIA-HRC.
- `scripts/validar_ipia_hrc_v2_final.py::decompor_mes` — reconstrução
  granular reusada (não reimplementada) para derivar os componentes por
  mês.
