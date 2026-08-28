# FX Convention Migration — IPIA-HRC PPI

**Status: IMPLEMENTED.** Registro de auditoria da execução da decisão
aprovada em `docs/validation/fx_convention_validation.md` e formalizada
em `docs/adr/0014-ppi-fx-convention-media-mensal.md`.

Reproduzir a migração (rede real; grava uma nova vintage):
`docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/migrar_fx_convention_media_mensal.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`).

## Previous behavior

Motor V2 (`agregar_ipia_hrc_multi_ncm_mensal`, alimenta as séries
oficial/provisional): `sgs(...).reindex(<índice mensal>, method="ffill")`
— o câmbio do mês `t` era a última cotação PTAX venda observada **antes
do início** de `t`, na prática o fechamento do **mês anterior**. Nunca
uma decisão metodológica deliberada (ver ADR 0014 §Contexto).

## New behavior

`FX_t = (1/N_t) · Σ FX_d` para toda observação diária válida cujo
mês-calendário é `t`, implementada em `indices_setoriais.calcular_fx_mensal()`
— única função de agregação cambial do motor V2, fail-fast (`ValueError`)
para qualquer mês sem nenhuma observação válida. **Motor legado V1**
(`calcular_ipia_mensal`, `custo_importacao_detalhado_mensal`) permanece
deliberadamente na convenção antiga — não foi tocado.

## Reason for change

Ver ADR 0014 e `docs/validation/fx_convention_validation.md` — evidência
institucional (SNA 2008/IMF, precedente BLS), coerência com a semântica
de "mês" do Comex Stat (desembaraço aduaneiro, evento dentro do mês) e
resultado empírico não disruptivo (correlação 0,994, zero cruzamentos de
threshold 100, custo de migração baixo frente ao ganho de coerência
metodológica).

## Version impact

| | Antes | Depois |
|---|---|---|
| `VERSAO_METODOLOGIA` | `"1.2"` | `"1.3"` |
| Vintage IPIA-HRC V2 | `20260827T213900Z` | `20260828T213446Z` (nova, `previous_vintage_id=20260827T213900Z`) |

Justificativa do bump: a mudança altera valores publicados (não apenas
disclosure/documentação, ao contrário da ADR 0013), qualificando como
bump segundo `docs/METODOLOGIA.md` §24. Esquema de versionamento
reaproveitado sem alteração — nenhum esquema novo foi inventado.

## Historical impact

Recálculo completo e real (não contrafactual/aproximado) via
`scripts/migrar_fx_convention_media_mensal.py`, comparando a vintage
nova contra a vintage anterior, **78 de 78 meses comparáveis**
(2019-02 a 2026-06, oficiais + provisórios):

| Métrica | Valor |
|---|---:|
| Diferença média (new − old) | −0,1195 pts |
| Diferença mediana | −0,1145 pts |
| Máximo \|diferença\| | 4,4829 pts |
| Mês do máximo | 2022-06 |
| Meses com `revised=True` (dos 48 já OFFICIAL) | 48 / 48 |
| Cruzamentos do threshold 100 | **0** |
| Mudança de `publication_status` | **0** meses |
| Reversões de direção MoM | **4** / 77 |

Estes números **batem, com precisão de 4 casas decimais**, com a análise
contrafactual aproximada do sprint anterior (que usava o painel agregado
com um resíduo de reconstrução conhecido de até 3,09 R$/t — ver
`docs/validation/fx_convention_validation.md` §17) — a análise anterior
já era confiável o suficiente para embasar a decisão, e o recálculo real
confirma isso.

**Nota (fora do escopo desta mudança, mas registrada por transparência):**
`preco_domestico_rs_t` mudou em **1 mês** (2026-06) por **0,0747 R$/t**
entre a vintage antiga e a nova — magnitude desprezível (~0,002% do valor
típico) e isolada a um único mês, consistente com uma revisão rotineira
de fonte upstream (IBGE/SIDRA) entre as duas execuções, **não causada
pela mudança de convenção cambial**. Confirmado programaticamente pelo
próprio script de migração (seção "3b" do log de execução) — nenhuma
outra diferença de preço doméstico foi encontrada nos 78 meses
comparáveis, então toda a diferença de IPIA reportada acima vem do
PPI/câmbio.

## Largest revisions

Top 10 por \|Δ\| (pontos de IPIA), dados reais da migração:

| Mês | IPIA old | IPIA new | Δ pts | Δ % | Status (old→new) | Threshold crossing? |
|---|---:|---:|---:|---:|---|---|
| 2022-06 | 87,4019 | 82,9190 | −4,4829 | −5,13% | PUBLICATION_GRADE → PUBLICATION_GRADE | Não |
| 2023-06 | 117,3184 | 121,3733 | +4,0549 | +3,46% | PUBLICATION_GRADE → PUBLICATION_GRADE | Não |
| 2019-08 | 93,8248 | 89,9864 | −3,8384 | −4,09% | EXPERIMENTAL → EXPERIMENTAL | Não |
| 2021-07 | 132,8078 | 129,2050 | −3,6027 | −2,71% | EXPERIMENTAL → EXPERIMENTAL | Não |
| 2026-01 | 111,5689 | 114,6859 | +3,1170 | +2,79% | PROVISIONAL → PROVISIONAL | Não |
| 2024-10 | 109,3141 | 106,2353 | −3,0787 | −2,82% | PROVISIONAL → PROVISIONAL | Não |
| 2021-06 | 127,7679 | 130,8462 | +3,0784 | +2,41% | EXPERIMENTAL → EXPERIMENTAL | Não |
| 2025-06 | 113,9822 | 117,0060 | +3,0238 | +2,65% | PROVISIONAL → PROVISIONAL | Não |
| 2021-08 | 131,3401 | 128,3213 | −3,0188 | −2,30% | EXPERIMENTAL → EXPERIMENTAL | Não |
| 2021-05 | 154,1288 | 157,0825 | +2,9537 | +1,92% | EXPERIMENTAL → EXPERIMENTAL | Não |

Nenhum mês nesta lista muda de `publication_status` — a revisão é
puramente de valor, nunca de classificação de qualidade/publicação.

## MoM reversals

4 de 77 movimentos mês a mês comparáveis mudaram de direção entre a
série antiga e a nova: **2021-07, 2023-11, 2024-11, 2026-03** — mesma
lista identificada na análise contrafactual do sprint anterior.

## Threshold crossings

**Zero.** Em nenhum dos 78 meses comparáveis um lado da comparação indica
`IPIA>100` (importar compensa) enquanto o outro indica `IPIA<100`
(produtor local protegido) — a narrativa qualitativa de paridade nunca
muda entre as duas convenções, em toda a série publicada.

## Reproducibility

- **Versão antiga:** totalmente reproduzível a partir da vintage imutável
  `data/processed/vintages/ipia_hrc_v2/20260827T213900Z/` (`manifest.json`,
  `official.csv`, `provisional.csv`, `import_side.csv`,
  `domestic_price.csv`, hashes SHA-256 de cada arquivo) — **não foi
  tocada** por esta migração.
- **Versão nova:** `data/processed/vintages/ipia_hrc_v2/20260828T213446Z/`,
  `previous_vintage_id=20260827T213900Z`, `methodology_version="1.3"`.
- **LATEST** (`data/processed/ipia_hrc_v2_official.csv`/`_provisional.csv`):
  atualizados a partir da vintage nova, recarregada do disco (nunca do
  objeto em memória) — mesma garantia byte-a-byte de
  `executar_pipeline_ipia_hrc`.
- **Comparativo completo** (todos os 78 meses, não só o top 10):
  `data/processed/validation/fx_convention/fx_convention_migration_old_vs_new.csv`,
  rotulado `OLD_VS_NEW_FX_MONTHLY_MEAN_MIGRATION` — artefato de validação,
  nunca confundido com `data/curated/` ou com uma vintage oficial.
- Ambas as vintages continuam listadas em
  `data/processed/vintages/ipia_hrc_v2/index.csv`, nunca removidas.

**Gap arquitetural usado conscientemente, documentado na ADR 0014:** esta
migração não passou pelo orquestrador rotineiro
(`executar_pipeline_ipia_hrc`), que sempre aplica `congelado_df` (e,
portanto, teria preservado os 48 meses antigos sem aplicar a nova
convenção). Em vez disso, chamou as mesmas funções de baixo nível que o
orquestrador usa, mas deliberadamente sem `congelado_df` — exatamente a
exceção que o próprio código já documentava como não implementada. Nada
no mecanismo de congelamento foi alterado; execuções futuras rotineiras
(`--ipia`) continuam protegidas contra revisão silenciosa, agora usando a
vintage `20260828T213446Z` como nova base.

## Tests

```
collected: 346
passed:    346
failed:    0
errors:    0
```

(338 da baseline pré-migração + 8 novos testes de `calcular_fx_mensal` —
ver `tests/unit/test_ppi_parametros_e_cambio.py`). `--selftest`: **PASS**
(inalterado — motor V1 não foi tocado).

12 testes de `tests/unit/test_ipia_hrc_multi_ncm.py` falharam
temporariamente durante a implementação (fixture `_stub_sgs` injetava uma
única cotação em 2000-01-01, dependente do forward-fill antigo para
"alcançar" qualquer mês testado) — causa confirmada como exclusivamente
de fixture de teste (nenhuma asserção desses testes é sobre câmbio em si;
são sobre agregação por NCM/política comercial). Corrigido trocando o
stub para uma série diária constante cobrindo 2010–2030 — nenhuma
asserção de teste foi alterada, só a forma de fornecer o câmbio
sintético.
