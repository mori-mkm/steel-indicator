# 0015 - IPIA-HRC import parity scope — Cost core and Offer analytical layer

## Status

**Accepted.** Decisão econômica aprovada explicitamente pelo usuário no
prompt que abriu esta etapa de implementação ("IPIA-HRC — IMPORT PARITY
SCOPE: COST vs OFFER/TRADER PRICE" → decisão aprovada C — DUAL
ARCHITECTURE). `docs/validation/ipia_hrc_import_parity_scope.md` é o
registro da investigação Level 3; este ADR é a decisão formal derivada
dela — mesmo padrão já usado pela ADR 0013 em relação ao Stage G3/G4 e
pela ADR 0014 em relação ao FX Convention Sprint.

## Contexto

O PPI do IPIA-HRC sempre incluiu, desde a pesquisa metodológica original
(`references/manual_metodologico_indices_setoriais.md` §5.2/§5.5), uma
margem comercial (`ParamsIPIA.margem_importador`, 3% desde a origem do
parâmetro) aplicada multiplicativamente sobre a soma de todos os demais
componentes (CIF + II + AFRMM + AD + D_porto + D_interno):

```
PPI_t = [CIF_t·FX_t + II + AFRMM + AD + D_porto + D_interno] × (1 + margem)
```

A própria pesquisa original já identificava a ambiguidade que motivou
esta decisão, na mesma tabela que introduziu o parâmetro (§5.5):

> "Margem do importador | 3% | **Zere se quiser medir custo puro em vez
> de preço ofertado**"

Essa pergunta — o IPIA-HRC mede o custo econômico de importar (import
parity **cost**), ou o preço que um trading cobraria por entregar o
material (import parity **offer/trader price**)? — nunca foi
formalmente resolvida. `docs/validation/ipia_hrc_cost_parameter_calibration.md`
(sprint anterior) já havia registrado que nenhum benchmark público de
markup de trading de aço plano foi encontrado, e que a margem de 3%
mistura, sem decomposição, financial carrying cost, overhead, risco de
crédito, FX hedge e margem comercial pura.

`docs/validation/ipia_hrc_import_parity_scope.md` (sprint de decisão
conceitual imediatamente anterior a este ADR) investigou a pergunta a
fundo e encontrou evidência convergente a favor de Cost como núcleo
conceitual:

- o Reporting em produção (`src/reporting/pages.py`,
  `pagina_paridade_importacao_ipia_hrc`) já rotula o PPI como "Custo de
  paridade de importação", nunca como "preço ofertado" — a série oficial,
  até esta decisão, media Offer mas se apresentava como Cost;
- a âncora doméstica (V1: Usiminas/CSN receita/volume, ADR 0001; V2:
  PIA-Produto, ADR 0010) é estruturalmente um preço de produtor/mill, não
  de revenda — comparar contra um PPI com margem de trading embutida é
  assimétrico;
- práticas institucionais amplamente citadas de import parity price
  (FEWS NET/USAID, glossários de commodities/energia) definem paridade
  como landed cost — FOB+frete+seguro+tarifas+transporte interno — sem
  margem comercial, tratando o gap entre paridade e preço de mercado como
  o próprio diagnóstico de margem, não como um insumo do índice;
- `.claude/rules/methodology.md` (regra de projeto já em vigor antes
  desta decisão) já descreve o invariante conceitual do índice como
  "domestic price / import parity **cost** × 100" — a governança interna
  já presumia Cost, mesmo com o código ainda calculando Offer.

## Decisão

A partir da metodologia 1.5, a série oficial do IPIA-HRC
(`agregar_ipia_hrc_multi_ncm_mensal` → `calcular_ipia_hrc_v2_pia` →
`ipia_hrc_v2_official.csv`/`ipia_hrc_v2_provisional.csv`) usa **PPI_COST**:

```
PPI_COST_t = CIF_t·FX_t + II + AFRMM + AD + D_porto + D_interno
```

(exatamente a mesma soma de componentes de antes, **sem** o fator
`(1 + margem)`). `IPIA_HRC = preço_doméstico / PPI_COST × 100` — fórmula
do IPIA preservada, só o `PPI` do denominador muda de definição.

A margem comercial (`ParamsIPIA.margem_importador`) vira **PPI_OFFER**,
uma camada analítica opcional:

```
PPI_OFFER = calcular_ppi_offer(PPI_COST, margem_importador) = PPI_COST × (1 + margem_importador)
```

`calcular_ppi_offer` exige `margem_importador` explicitamente (sem
default) — nunca publica 3% (ou qualquer outro valor) como markup
universal de trading. `PPI_OFFER` nunca alimenta `ipia_hrc_v2`/`ipia`;
existe só para cenários, market intelligence e sensitivity, sempre
rotulado como camada separada.

**Escopo desta decisão — o que muda e o que não muda:**

| Função | Lineage | Mudou? |
|---|---|---|
| `_ppi_cost_brl_t` (antes `_ppi_brl_t`) | V2 (série oficial/provisional) | **Sim** — não aplica mais margem |
| `custo_importacao_bottom_up_mensal` | V2 (série oficial/provisional) | **Sim** — coluna `ppi_cost_brl_t` (antes `ppi_brl_t`) |
| `agregar_ipia_hrc_multi_ncm_mensal` | V2 (série oficial/provisional) | **Sim** — `ppi_rs_t` agora é PPI_COST; nova coluna `ppi_offer_rs_t` (analítica) |
| `calcular_ppi_offer` (nova) | V2, camada analítica | Nova função — nunca alimenta a série oficial |
| `custo_importacao_rs_t` | V1 legado (`--selftest`, PDF antigo) | Não — congelado deliberadamente |
| `custo_importacao_historico_mensal` | V1 legado | Não — mesma linhagem V1 |
| `calcular_ipia_mensal` | V1 legado | Não — mesma linhagem V1 |
| `calcular_ipia_hrc_v2` (NCM único, Corporate Benchmark) | V2, desconectado, deprecated | Não — não alimenta nenhuma saída publicada |
| `D_porto`, `D_interno`, FX, II, AFRMM, antidumping, NCM basket, domestic price (Denton/PIA) | — | Não — só a margem sai do core |

A linhagem V1 permanece congelada pelo mesmo motivo já registrado na ADR
0014 (referência histórica/comparação de bug fixes, protegida por
characterization tests) — e, adicionalmente, porque preservá-la
intocada garante o caminho "Legacy/current pre-migration" pedido pela
decisão aprovada (PPI com margem de 3%, reproduzível byte-a-byte).

## Rationale

- **Simetria com o preço doméstico**: o preço doméstico usado pelo IPIA-HRC
  (V1 e V2) é um preço de produtor/mill, sem camada de distribuição/trading
  embutida — comparar contra um PPI com margem comercial adicionava uma
  assimetria estrutural entre os dois lados da razão.
- **Reprodutibilidade**: PPI_COST não depende de nenhum parâmetro sem
  fonte pública — os únicos dois parâmetros ainda `ESTIMADO`
  (D_porto/D_interno) têm posição conceitual clara (custo físico de
  internalização) e permanecem candidatos a calibração futura com
  evidência direta; a margem, que nunca teve fonte, sai do núcleo.
- **Ausência de benchmark universal de margem**: nenhuma pesquisa (este
  ADR, o sprint de decisão que o antecede, ou o sprint de calibração
  anterior) encontrou um markup de trading de aço plano publicamente
  verificável — publicar um core que depende dele contradiz o princípio
  do projeto de nunca fabricar estimativa sem evidência.
- **Clareza econômica**: o threshold 100 agora tem uma leitura única e
  auditável ("preço doméstico igual ao custo econômico de importar"),
  sem depender de uma premissa de canal comercial não observável.
- **Reporting já alinhado**: a página oficial do relatório V2 já descrevia
  o indicador como "custo de paridade de importação" antes desta decisão
  — o código agora corresponde ao que o produto já comunicava.
- **Prática institucional convergente**: FEWS NET e glossários de
  commodities/energia tratam import parity como landed cost, não como
  preço de oferta — o gap entre paridade e preço observado é o sinal de
  margem, não um insumo do índice.

## Consequences

- Mudança material em toda a série histórica calculável (78 meses,
  2019-01 a 2026-07, dos quais os meses `EXPERIMENTAL`/`PUBLICATION_GRADE`
  compõem a série `OFFICIAL`): impacto exato reportado em
  `docs/validation/ipia_hrc_cost_offer_migration.md` (comparativo antigo
  vs. novo, threshold crossings, reversões MoM, valor corrente).
- **Nenhuma mudança de `publication_status`** — a arquitetura Cost/Offer
  afeta somente o valor de `ppi_rs_t`/`ipia_hrc_v2`, nunca a classificação
  `PUBLICATION_GRADE`/`EXPERIMENTAL`/`PROVISIONAL`/`UNKNOWN` (regras de
  cobertura/incerteza de política comercial inalteradas).
- **Bump de `VERSAO_METODOLOGIA`**: `"1.4" → "1.5"` — muda valores
  publicados, portanto qualifica como bump segundo `docs/METODOLOGIA.md`
  §24.
- **Nova vintage, vintage anterior preservada**: a série revisada foi
  persistida como uma NOVA vintage append-only
  (`indices_setoriais.salvar_vintage_ipia_hrc_v2`) — a vintage anterior
  permanece intacta, imutável e totalmente reproduzível em
  `data/processed/vintages/ipia_hrc_v2/<vintage_id_antiga>/`. Ver
  `docs/validation/ipia_hrc_cost_offer_migration.md` para o comparativo
  completo antigo-vs-novo e os IDs de vintage envolvidos.
- **D_porto/D_interno não recalibrados**: permanecem R$210/t e R$140/t,
  `ESTIMADO`, com as mesmas limitações já documentadas
  (`docs/validation/ipia_hrc_cost_parameter_calibration.md`) — esta
  decisão remove somente a margem do core, não toca nenhum outro
  parâmetro/fonte/fórmula.
- **`ParamsIPIA.margem_importador` preservado por compatibilidade**
  (default `0.03`, inalterado) — o campo continua existindo e é usado
  explicitamente por `calcular_ppi_offer`/pelo motor V1 legado, mas o core
  V2 (`_ppi_cost_brl_t`) o ignora deliberadamente.
- `docs/METODOLOGIA.md` §9.4/§9.8/§9.9 foram atualizados para descrever
  PPI_COST (core) e PPI_OFFER (camada analítica) — a descrição anterior
  (PPI com margem embutida) permanece válida apenas para a linhagem V1
  legada.

## Alternatives considered

- **A — Core = Cost, remover a camada Offer inteiramente**: rejeitada
  como escolha principal — descartaria uma pergunta de negócio legítima
  ("quanto eu pagaria via trading?") que o projeto pode querer responder
  no futuro, mesmo sem calibração pronta hoje. `PPI_OFFER` é mantido como
  camada opcional de baixo custo (uma função pura, `calcular_ppi_offer`),
  não uma segunda série publicada.
- **B — Core = Offer, buscar calibração de margem real**: rejeitada — vai
  contra a evidência mais forte do sprint de decisão: nenhum benchmark
  público de margem foi encontrado (nem nesta etapa nem na anterior), a
  prática institucional mais citada não inclui margem na definição de
  paridade, e a âncora doméstica atual (preço de produtor) não é
  comparável a um preço com margem embutida. Fixar o core institucional
  numa variável sem fonte contradiz `docs/METODOLOGIA.md`/`CLAUDE.md`
  (nunca fabricar estimativa sem evidência).
- **D — Inconclusive/não decidir agora**: rejeitada pelo próprio usuário
  ao aprovar explicitamente a Opção C nesta etapa.

## Documentos relacionados

- `docs/validation/ipia_hrc_import_parity_scope.md` — investigação
  conceitual completa (Cost vs. Offer), evidência, matriz de decisão.
- `docs/validation/ipia_hrc_cost_offer_migration.md` — execução da
  migração, IDs de vintage, comparativo antigo-vs-novo, threshold
  crossings, reversões MoM.
- `docs/validation/ipia_hrc_cost_parameter_calibration.md` — auditoria
  anterior de D_porto/D_interno/margem (evidência pública, ausência de
  benchmark de margem, elasticidade normalizada).
- `docs/METODOLOGIA.md` §9.4, §9.8, §9.9 — descrição metodológica
  atualizada.
- `references/manual_metodologico_indices_setoriais.md` §5.5 — origem da
  ambiguidade Cost/Offer, nunca resolvida até esta decisão.
- ADR 0001 (âncora doméstica Usiminas/CSN), ADR 0009 (janela
  publication-grade), ADR 0010 (PIA-Produto benchmark), ADR 0012
  (vintages append-only), ADR 0013 (publication contract), ADR 0014
  (convenção cambial do PPI) — mecanismos reutilizados sem alteração por
  esta decisão.
