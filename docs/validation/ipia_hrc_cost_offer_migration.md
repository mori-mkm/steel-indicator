# IPIA-HRC — Cost/Offer Migration (metodologia 1.4 → 1.5)

**Status: IMPLEMENTAÇÃO APROVADA E EXECUTADA.** Decisão do usuário: **C —
DUAL ARCHITECTURE** (core oficial = `PPI_COST`, `PPI_OFFER` = camada
analítica opcional). Ver `docs/validation/ipia_hrc_import_parity_scope.md`
(investigação Level 3) e
`docs/adr/0015-ipia-hrc-import-parity-scope-cost-core-offer-layer.md`
(decisão formal).

Reproduzir: `python scripts/migrar_ipia_hrc_cost_offer.py` (faz chamadas
de rede reais a Comex Stat/BCB/IBGE-SIDRA; persiste uma nova vintage
append-only e não sobrescreve nenhuma vintage anterior).

## Previous behavior

Até a metodologia 1.4, a série oficial do IPIA-HRC
(`agregar_ipia_hrc_multi_ncm_mensal` → `calcular_ipia_hrc_v2_pia`) usava:

```
PPI_t = [CIF_t·FX_t + II + AFRMM + AD + D_porto + D_interno] × (1 + margem)
```

com `margem = ParamsIPIA.margem_importador = 0.03` (3%), aplicada sobre a
soma de todos os demais componentes, incluindo tributos e custos
logísticos — decisão nunca formalizada além do valor default do código,
com origem direta na pesquisa metodológica original
(`references/manual_metodologico_indices_setoriais.md` §5.5).

## New architecture

A partir da metodologia 1.5:

- **`PPI_COST`** (`_ppi_cost_brl_t`, antes `_ppi_brl_t`) — mesma soma de
  componentes, **sem** o fator `(1 + margem)`. É o `ppi_rs_t` que
  alimenta `ipia_hrc_v2`/`ipia` na série oficial.
- **`PPI_OFFER`** (`calcular_ppi_offer(ppi_cost, margem_importador)`) —
  camada analítica opcional: `PPI_OFFER = PPI_COST × (1 + margem)`.
  `margem_importador` é sempre explícito (sem default) — nunca publica
  3% como markup universal. Nova coluna `ppi_offer_rs_t` (calculada com
  `p.margem_importador`, hoje ainda 0.03 por compatibilidade) é
  persistida junto de `ppi_rs_t` em toda vintage a partir desta migração,
  mas **nunca** alimenta `ipia_hrc_v2`.
- Motor V1 legado (`custo_importacao_rs_t`, `custo_importacao_historico_mensal`,
  `calcular_ipia_mensal`) **deliberadamente não alterado** — continua
  reproduzindo a fórmula pré-1.5 (Offer com margem 3%) para
  `--selftest`/PDF legado, mesmo critério já usado na ADR 0014.

## Why Cost is core

Ver `docs/validation/ipia_hrc_import_parity_scope.md` para a investigação
completa. Resumo da evidência que motivou a decisão do usuário:

1. o Reporting em produção já rotulava o PPI como "Custo de paridade de
   importação", nunca como preço ofertado — a série oficial, até esta
   migração, calculava Offer mas se apresentava como Cost;
2. a âncora doméstica (V1 Usiminas/CSN, V2 PIA-Produto) é um preço de
   produtor/mill, não de revenda — incluir margem de trading só do lado
   importado é uma comparação assimétrica;
3. nenhum benchmark público de markup de trading de aço plano foi
   encontrado (nem neste sprint nem no anterior,
   `docs/validation/ipia_hrc_cost_parameter_calibration.md`);
4. práticas institucionais de import parity price amplamente citadas
   (FEWS NET/USAID, glossários de commodities/energia) definem paridade
   como landed cost, sem margem comercial;
5. a própria pesquisa original já registrava a ambiguidade ("zere se
   quiser medir custo puro em vez de preço ofertado"), nunca resolvida
   até esta decisão.

## Offer analytical layer

`PPI_OFFER`/`calcular_ppi_offer` continuam disponíveis para:

- reproduzir o comportamento pré-1.5 (`margem=0.03`, dentro de tolerância
  numérica — ver `tests/unit/test_ipia_hrc_cost_offer_split.py::test_ppi_offer_com_margem_3pct_reproduz_legado_pre_1_5`);
- cenários de sensitivity/market intelligence com margem parametrizável;
- decomposição futura (Driver Decomposition, não implementada nesta
  etapa) — `scripts/validar_ipia_hrc_v2_final.py::decompor_mes` já expõe
  `ppi_cost_reconstruido`/`ppi_offer_reconstruido`/`margem_rs_t`
  separadamente.

Nunca usado para calcular `ipia_hrc_v2` nem qualquer coluna oficial.

## Version impact

`VERSAO_METODOLOGIA`: `"1.4" → "1.5"`. Critério de bump conforme
`docs/METODOLOGIA.md` §24 (mudança metodológica com efeito econômico
mensurável em valores publicados).

## Historical impact

Execução real de `scripts/migrar_ipia_hrc_cost_offer.py`, 2026-08-29
(vintage anterior `20260829T022116Z`, metodologia 1.4 → nova vintage
`20260829T174456Z`, metodologia 1.5):

| Métrica | Valor |
|---|---:|
| Meses comparáveis | 78 de 78 |
| Mean ΔPPI (Cost novo vs. Offer antigo) | **-2,9126%** (constante — margem é um multiplicador fixo, não varia por mês) |
| Max \|ΔPPI\| | 2,9126% |
| Mean ΔIPIA (pontos) | **+3,1955** |
| Min ΔIPIA (pontos) | +2,0288 |
| Max ΔIPIA (pontos) | +4,7125 |
| `publication_status` mudou | **0 meses** (esperado — a arquitetura Cost/Offer não altera cobertura/incerteza de política comercial) |

O ΔIPIA varia mês a mês (ao contrário do ΔPPI, constante) porque o IPIA é
`preço_doméstico/PPI×100` — a mesma redução percentual de PPI produz um
ganho de pontos de IPIA proporcional ao nível do IPIA em cada mês
(`IPIA_novo - IPIA_antigo = IPIA_antigo × (1/(1-0,0291) - 1) ≈ IPIA_antigo × 3,00%`).

## Threshold crossings

**3 de 78 meses** cruzam o threshold 100 (todos de `<=100` para `>100`,
nunca o sentido oposto — consistente com PPI_COST sempre menor que
PPI_OFFER antigo, logo IPIA novo sempre maior):

| Mês | PPI_OFFER antigo | PPI_COST novo | IPIA antigo | IPIA novo | Status (antigo→novo) |
|---|---:|---:|---:|---:|---|
| 2020-12 | R$ 3.681,21/t | R$ 3.574,00/t | 98,68 | 101,64 | EXPERIMENTAL → EXPERIMENTAL |
| 2022-05 | R$ 6.140,96/t | R$ 5.962,10/t | 97,76 | 100,70 | PUBLICATION_GRADE → PUBLICATION_GRADE |
| 2022-11 | R$ 5.072,82/t | R$ 4.925,07/t | 97,67 | 100,60 | PUBLICATION_GRADE → PUBLICATION_GRADE |

Nenhum dos três muda `publication_status` — a mudança de lado do
threshold é puramente econômica (o produtor doméstico passa a aparecer
sob pressão competitiva nesses 3 meses, quando antes não aparecia),
nunca um artefato de cobertura/qualidade de dado.

## MoM reversals

**0 reversões de direção mês a mês** (de 77 comparações válidas) — o
deslocamento é uma translação aproximadamente uniforme (~+3% em todos os
meses), então a direção de qualquer movimento mês a mês do IPIA (subiu ou
desceu em relação ao mês anterior) é preservada entre a série antiga e a
nova.

## Current-period impact

Mês de referência mais recente calculável: **2026-06**.

| | Valor |
|---|---:|
| PPI_COST (oficial, 1.5+) | R$ 3.671,37/t |
| PPI_OFFER (analítico, margem 3%, para comparação) | R$ 3.781,51/t |
| Preço doméstico (PIA-based) | R$ 4.709,76/t |
| **IPIA-HRC oficial (usa PPI_COST)** | **128,28** |
| IPIA equivalente se a série ainda usasse PPI_OFFER | 124,55 |

Diferença de +3,73 pontos no mês mais recente — o produtor doméstico
aparece com uma pressão competitiva de importação ligeiramente maior sob
a nova definição (Cost), consistente com a remoção de uma margem
comercial que artificialmente encarecia o lado importado.

## Vintage migration

- **Vintage anterior**: `20260829T022116Z` (metodologia 1.4) — permanece
  intacta e byte-identical em
  `data/processed/vintages/ipia_hrc_v2/20260829T022116Z/`. OFFICIAL: 48
  meses (2019-02 a 2023-12); PROVISIONAL: 30 meses.
- **Vintage nova**: `20260829T174456Z` (metodologia 1.5),
  `previous_vintage_id=20260829T022116Z`. OFFICIAL: 48 meses (idênticos em
  cobertura, valores revisados); PROVISIONAL: 30 meses.
- **Sanity check executado**: `preco_domestico_rs_t` idêntico entre as
  duas vintages em todos os meses comuns — toda a diferença de PPI/IPIA
  vem exclusivamente da remoção da margem do core, nenhuma revisão de
  fonte doméstica contaminou o comparativo.
- `data/processed/ipia_hrc_v2_official.csv`/`ipia_hrc_v2_provisional.csv`
  (LATEST) atualizados a partir da vintage `20260829T174456Z`.
- Nenhum congelamento (`congelado_df=None`) aplicado nesta execução —
  exceção deliberada e autorizada (Seção 12 da decisão aprovada), mesmo
  padrão já usado nas migrações de FX convention (ADR 0014) e correção de
  política de importação.

## Reproducibility

- Vintage anterior permanece intacta e byte-identical em
  `data/processed/vintages/ipia_hrc_v2/<vintage_id_antiga>/` (nunca
  sobrescrita — mecanismo append-only, ADR 0012).
- Nova vintage persistida com `previous_vintage_id` apontando para a
  anterior — cadeia de proveniência preservada.
- `data/processed/ipia_hrc_v2_official.csv`/`ipia_hrc_v2_provisional.csv`
  (LATEST) atualizados só a partir da vintage recém-persistida, nunca do
  objeto em memória (mesma garantia de ordem já documentada em
  `executar_pipeline_ipia_hrc`).
- Comparativo completo old-vs-new salvo em
  `data/processed/validation/ipia_hrc_cost_offer_migration/cost_offer_migration_old_vs_new.csv`
  (gitignored, reproduzível rodando o script novamente).

## Tests

- `tests/unit/test_ipia_hrc_cost_offer_split.py` (novo) — PPI_COST ignora
  margem; `calcular_ppi_offer` = `PPI_COST × (1+margem)`; margem zero ==
  Cost; margem 3% reproduz o legado pré-1.5; isolamento (margem não altera
  componentes físicos/regulatórios); `ipia_hrc_v2` usa Cost, não Offer;
  `ppi_offer_rs_t` fica `NaN` junto de `ppi_rs_t` quando `UNKNOWN`.
- `tests/unit/test_ipia_hrc_multi_ncm.py`,
  `tests/unit/test_validar_ipia_hrc_v2_decompor_mes.py` — atualizados
  explicitamente (coluna `ppi_brl_t`→`ppi_cost_brl_t` no agregador
  bottom-up; reconstrução de componentes sem `×(1+margem)`; comparação
  contra o motor V1 legado dividida por `(1+margem)` quando necessário)
  para refletir a mudança de escopo deliberada, nunca forçados a
  reproduzir o valor antigo.
- `tests/unit/test_ipia_hrc_v2_pia_integrado.py`,
  `test_ipia_hrc_v2_integrado.py`, `test_ipia_hrc_v2_vintages.py`,
  `test_ipia_hrc_publication_contract.py`, `test_ipia_hrc_cli_pipeline.py` —
  fixtures atualizadas com a nova coluna `ppi_offer_rs_t` (schema
  ampliado, nenhuma asserção de negócio alterada).
- Suíte completa: ver relatório de entrega para a contagem observada.
