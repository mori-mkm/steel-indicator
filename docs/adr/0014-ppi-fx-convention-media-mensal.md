# 0014 - IPIA-HRC: convenção cambial do PPI — média mensal

## Status

**Accepted.** Decisão econômica aprovada explicitamente pelo usuário no
prompt que abriu esta etapa de implementação (FX Convention Sprint →
implementação). `docs/validation/fx_convention_validation.md` é o
registro da investigação; este ADR é a decisão formal derivada dela —
mesmo padrão já usado pela ADR 0013 em relação ao Stage G3/G4.

## Contexto

A auditoria anterior (`docs/validation/fx_convention_validation.md`)
confirmou, direto no código (não por inferência), que a convenção cambial
usada pelo PPI do IPIA-HRC V2 era:

```
FX_current(t) = τ(max{d ∈ D : d ≤ primeiro_dia_calendario(t)})
```

implementada como `sgs(...).reindex(<índice mensal>, method="ffill")` em
`agregar_ipia_hrc_multi_ncm_mensal`. Na prática, isso faz o câmbio do mês
`t` corresponder ao fechamento do último dia útil **anterior** ao início
de `t` — geralmente o fechamento do **mês anterior** — não à última
cotação do próprio mês `t`, nem a uma média do mês `t`, como diferentes
leituras anteriores do projeto presumiam.

Esse comportamento nunca foi uma decisão metodológica deliberada: nenhum
comentário no código o justifica, o comentário original do parâmetro SGS
o marcava como "a confirmar", e a pesquisa metodológica original
(`references/manual_metodologico_indices_setoriais.md` §5.2) presumia
"câmbio PTAX médio do mês". É um efeito colateral de combinar
`freq="MS"` com `method="ffill"`.

Evidência levantada na investigação:
- **MDIC/Comex Stat**: o mês de uma importação é definido pela data de
  **desembaraço aduaneiro** — evento que ocorre dentro do próprio mês
  `t`, nunca antes dele.
- **IMF/ILO/OECD/Eurostat/UN/World Bank, Export and Import Price Index
  Manual (2009)**: segue o SNA 2008 — taxa da transação ou, na ausência
  dela, **média do menor período possível**; cita o precedente do BLS
  (EUA), que usa uma **taxa média** (do mês anterior, dado o timing da
  publicação) como aproximação prática.
- Empiricamente (78 meses, 2019-02 a 2026-06): MAE de 1,58 pontos de
  IPIA entre a convenção atual e uma média mensal, correlação 0,994,
  **zero** cruzamentos do threshold 100, 94,8% de concordância de
  direção mês a mês (MoM) — divergência mensurável, mas não disruptiva.

## Decisão

A convenção cambial oficial do PPI do IPIA-HRC (motor V2,
`agregar_ipia_hrc_multi_ncm_mensal`, que alimenta as séries `ipia_hrc_v2_official.csv`/
`ipia_hrc_v2_provisional.csv`) passa a ser:

```
FX_t = (1 / N_t) · Σ FX_d,  para todo dia útil d com cotação válida cujo mês-calendário é t
```

Implementada em uma única função reutilizável,
`indices_setoriais.calcular_fx_mensal(cambio_diario, meses_idx)`, chamada
pelo único ponto de produção que alimenta a série oficial/provisional.
Nunca faz forward-fill entre meses: um mês sem nenhuma observação diária
válida levanta `ValueError` explícito (fail-fast), nunca herda
silenciosamente o câmbio de outro mês.

**Escopo desta decisão — o que muda e o que não muda:**

| Função | Lineage | Mudou? |
|---|---|---|
| `agregar_ipia_hrc_multi_ncm_mensal` | V2 (série oficial/provisional) | **Sim** — usa `calcular_fx_mensal` |
| `calcular_ipia_mensal` | V1 legado (`--selftest`, PDF antigo) | Não — congelado deliberadamente |
| `custo_importacao_detalhado_mensal` | V1 legado (decomposição do PDF antigo) | Não — mesma linhagem V1 |
| `calcular_ipia_hrc_v2` (NCM único) | V2, desconectado, mantido como referência de limitação superada | Não — não alimenta nenhuma saída publicada; alterá-lo não teria efeito econômico e ampliaria o escopo do batch sem necessidade |

A linhagem V1 permanece congelada por ser referência histórica/
comparação de bug fixes, não a série publicada — alterar sua convenção de
câmbio misturaria uma correção metodológica nova com a preservação de
comportamento legado que os próprios testes de characterization existem
para proteger.

## Rationale

- **Coerência temporal com o Comex Stat**: o mês de desembaraço (evento
  que a própria fonte usa para definir `t`) acontece dentro do mês `t`; a
  convenção antiga usava uma cotação de antes desse evento sequer
  começar.
- **Evidência institucional**: SNA 2008/IMF recomenda a taxa da
  transação ou uma média do menor período possível; o precedente citado
  (BLS) usa explicitamente uma taxa média, não um ponto.
- **Redução de timing bias**: a comparação `current` vs. `end-of-month`
  (isolando o efeito de estar no ponto errado do calendário) mostrou MAE
  quase o dobro da comparação `current` vs. `mean` — a maior parte do
  problema é timing, não "ponto vs. média" em si, mas a média mensal
  resolve ambos ao mesmo tempo com uma regra simples e institucionalmente
  respaldada.
- **Resultado empírico do validation sprint**: divergência mensurável mas
  não disruptiva (ver Consequences) — custo de migrar é baixo frente ao
  ganho de coerência metodológica.
- **Centralização**: antes desta decisão, a mesma lógica de agregação
  cambial existia implicitamente em cada ponto de chamada; agora há uma
  única função (`calcular_fx_mensal`) que representa a regra oficial —
  qualquer futuro consumidor do FX mensal do motor V2 reusa a mesma
  implementação.

## Consequences

- Mudança pequena em média (+0,12 pt de IPIA), mas não desprezível em
  meses individuais: máximo observado de 4,48 pts (jun/2022, dentro da
  janela oficial).
- **Zero** mudanças de regime (nenhum mês cruza o threshold 100 entre a
  convenção antiga e a nova).
- 4 reversões de direção mês a mês (MoM) identificadas na análise
  contrafactual, de 77 meses comparáveis.
- Dos 48 meses já `OFFICIAL` (`EXPERIMENTAL`/`PUBLICATION_GRADE`)
  existentes na vintage anterior, uma fração fica com impacto `MODERATE`
  (2–5 pontos, limiar bespoke da análise) — não `HIGH` em nenhum mês.
- **Bump de `VERSAO_METODOLOGIA`**: `"1.2" → "1.3"` — muda valores
  publicados (não apenas documentação/disclosure, ao contrário da ADR
  0013), portanto qualifica como bump segundo `docs/METODOLOGIA.md` §24.
- **Nova vintage, vintage anterior preservada**: a série revisada foi
  persistida como uma NOVA vintage append-only
  (`indices_setoriais.salvar_vintage_ipia_hrc_v2`) — a vintage anterior
  permanece intacta, imutável e totalmente reproduzível em
  `data/processed/vintages/ipia_hrc_v2/<vintage_id_antiga>/`. Ver
  `docs/validation/fx_convention_migration.md` para o comparativo
  completo antigo-vs-novo e os IDs de vintage envolvidos.
- **Gap arquitetural identificado, não resolvido por este ADR**: o
  mecanismo de congelamento (`congelado_df`, `calcular_ipia_hrc_v2_pia`)
  não distingue "revisão rotineira de fonte upstream" (que deve
  permanecer congelada) de "revisão metodológica aprovada" (que deve
  substituir os meses congelados) — o próprio código já documentava essa
  lacuna como decisão explícita de não implementar ainda. Esta migração
  contornou o gap orquestrando as funções de baixo nível diretamente
  (`scripts/migrar_fx_convention_media_mensal.py`), sem modificar
  `executar_pipeline_ipia_hrc` nem o mecanismo de congelamento em si — a
  proteção contra revisão rotineira continua válida para execuções
  futuras normais (`--ipia`), agora com a vintage desta migração como
  base. Se correções metodológicas aprovadas deste tipo se tornarem
  recorrentes, uma flag explícita (ex.: `--forcar-revisao-metodologica`)
  no orquestrador seria a evolução natural — não implementada aqui por
  estar fora do escopo desta decisão (cambial).
- `docs/METODOLOGIA.md` §9.6 e §9.8 (tabela de auditoria do PPI) foram
  corrigidos para descrever a nova convenção; a descrição anterior
  (imprecisa mesmo em relação ao comportamento antigo — dizia "última
  cotação até o mês" quando na prática era "última cotação antes do
  início do mês") não precisa mais ser mantida como válida para o motor
  V2.

## Alternatives considered

- **A — manter a convenção atual** (`current`/start-of-month snapshot):
  rejeitada — não tem justificativa metodológica deliberada, diverge do
  próprio comentário do código ("a confirmar"), e nenhuma fonte
  institucional a recomenda.
- **C — end-of-month** (cotação de fechamento do último dia útil dentro
  do mês): considerada como alternativa de menor mudança de
  implementação; não adotada como escolha principal porque tem menos
  respaldo institucional direto que a média mensal (nenhuma fonte prioriza
  especificamente "fim de mês" para dado mensal agregado) e seu impacto
  não foi comparado diretamente contra a média mensal na validação (só
  contra a convenção atual) — permanece como opção de aprofundamento
  futuro caso a média mensal se mostre insatisfatória.
- **Ponderação por fluxo de comércio dentro do mês**: descartada — o
  Comex Stat não expõe data de desembaraço por transação individual, só
  o agregado mensal; não há como construir esse peso sem inventar dado
  que a fonte não fornece.

## Documentos relacionados

- `docs/validation/fx_convention_validation.md` — investigação completa,
  evidência, matriz de decisão.
- `docs/validation/fx_convention_migration.md` — execução da migração,
  IDs de vintage, comparativo antigo-vs-novo.
- `docs/METODOLOGIA.md` §9.6, §9.8 — descrição metodológica atualizada.
- ADR 0009 (janela publication-grade), ADR 0012 (vintages append-only),
  ADR 0013 (publication contract) — mecanismos reutilizados sem alteração
  por esta decisão.
