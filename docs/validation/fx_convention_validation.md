# FX Convention Validation — IPIA-HRC PPI

**Status: VALIDATION / NON-PUBLISHED — Level 3 decision support, not a decision.**

> **Atualização de implementação:** a recomendação **B (monthly mean)**
> deste documento foi **aprovada e implementada** — ver ADR 0014
> (`docs/adr/0014-ppi-fx-convention-media-mensal.md`) e
> `docs/validation/fx_convention_migration.md` (execução da migração,
> vintages envolvidas, comparativo antigo-vs-novo). Este documento
> permanece **inalterado** como registro histórico da investigação que
> levou à decisão — não reflete mais o estado atual do código para o
> motor V2 (`agregar_ipia_hrc_multi_ncm_mensal`), mas continua correto
> como descrição do motor legado V1 (`calcular_ipia_mensal`), que não foi
> alterado.

Nenhum vintage oficial, série publicada, CSV de produção ou PDF foi
alterado por este documento ou pelo script que o produziu
(`scripts/validar_fx_convention.py`) **no momento em que foi escrito**. A
convenção cambial de produção permanece exatamente a que já existia
antes desta análise **— ver a atualização acima para o que mudou depois**.

Reproduzir: `docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/validar_fx_convention.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`).

---

## 1. Pergunta

> Para um índice mensal de paridade de importação de HRC baseado em
> comércio exterior agregado mensal, qual convenção cambial melhor
> representa o custo cambial enfrentado durante aquele mês?

Contexto: a pesquisa metodológica original (`references/manual_metodologico_indices_setoriais.md`
§5.2) presumia "câmbio PTAX médio do mês"; a auditoria da etapa anterior
suspeitou que o código usa "a última cotação disponível do mês"; nenhuma
das duas descrições, como se verá abaixo, está exatamente certa.

## 2. O que o código faz hoje — confirmado diretamente no código, não na documentação anterior

### 2.1 Série BCB/SGS usada

- Código SGS: **1**.
- Nome oficial (Portal de Dados Abertos do BCB): "Taxa de câmbio - Livre
  - Dólar americano (venda) - diário".
- Confirmado ao vivo nesta etapa contra o endpoint oficial de PTAX
  (Olinda `CotacaoDolarDia`): em 27/08/2026, SGS-1 = 5.1642, e o boletim
  de fechamento oficial da mesma data traz `cotacaoVenda=5.16420,
  cotacaoCompra=5.16370`. **SGS-1 = PTAX venda do boletim de FECHAMENTO
  diário** (não abertura, não boletim intermediário, não médio
  intradiário simples — o próprio boletim de fechamento já é, por
  metodologia do BCB, a média aritmética dos 4 boletins do dia desde a
  Resolução BCB nº 45/2020 — ver §14).
- Unidade: BRL por USD, taxa de venda.
- Frequência da fonte: diária (dias úteis; sem cotação em fins de
  semana/feriados bancários).
- O comentário no código (`SGS = {"cambio_venda": 1, ...}  # a confirmar:
  PTAX. Cheque a ordem de grandeza`) nunca havia sido formalmente
  confirmado dentro do projeto — **confirmado agora** (drift documental
  fechado; código não foi alterado, só a confirmação foi feita e
  registrada aqui).

### 2.2 Transformação aplicada — e uma correção importante à auditoria anterior

Todos os 5 pontos de chamada em `src/indices_setoriais.py` (linhas 1038,
1140, 1323, 2632, e o pipeline G5 em `_pipeline_import_side_hrc`) seguem
o mesmo padrão:

```python
cambio = sgs(SGS["cambio_venda"], inicio=...).reindex(<índice mensal>, method="ffill")
```

onde `<índice mensal>` é uma série de timestamps de **início de mês**
(`YYYY-MM-01`, construída via `pd.to_datetime(year + "-" + month + "-01")`
ou `pd.date_range(..., freq="MS")").

**Verificado empiricamente nesta etapa** (não apenas inferido): dado
`.reindex(alvo, method="ffill")` sobre uma série diária, o valor atribuído
ao slot `YYYY-MM-01` é a última observação diária **na ou antes** dessa
data exata — nunca uma observação posterior. Teste direto com dado real
do BCB:

```
2024-03-20  5.0120
...
2024-03-28  4.9962
2024-04-01  5.0532   <- 1º de abril é dia útil, tem cotação própria
2024-04-02  5.0476
...
reindex(['2024-03-01','2024-04-01','2024-05-01'], ffill):
2024-03-01       NaN   (sem observação anterior disponível na amostra)
2024-04-01    5.0532   <- exatamente a cotação do PRÓPRIO dia 1º/abril
2024-05-01    5.0520   <- (nesta amostra truncada; em produção seria a
                            última cotação de abril, pois 1º/maio é feriado)
```

**Formalização exata da convenção atual:**

```
FX_current(t) = τ(d*),  d* = max{ d ∈ D : d ≤ primeiro_dia_calendario(t) }
```

onde `D` é o conjunto de dias úteis com cotação PTAX venda de fechamento
e `τ(d)` a cotação do dia `d`.

**Isto NÃO é "a última cotação disponível até o fim do mês"** (como a
auditoria da etapa anterior descreveu em `docs/METODOLOGIA.md` §9.6 — essa
descrição está imprecisa e será corrigida junto com a decisão desta
etapa, não agora, para não misturar documentação com metodologia antes da
decisão). É, na prática, **a cotação de fechamento do último dia útil
IMEDIATAMENTE ANTES do início do mês** (ou do próprio dia 1º, nos casos
raros em que ele é dia útil). Ou seja: o câmbio aplicado ao custo de
importação do mês `t` reflete as condições cambiais do **fim do mês
`t-1`**, não de nenhum instante dentro do próprio mês `t` (exceto,
trivialmente, o primeiro instante dele).

Nenhum comentário no código indica que este comportamento é
intencional — não há nenhuma menção a "contratação antecipada de câmbio"
ou "timing de compra a termo" nos comentários de `sgs()`/`cambio_venda`.
A leitura mais provável (INFERÊNCIA, não fato documentado) é que se trata
de um efeito colateral não examinado de combinar `freq="MS"` (índice de
início de mês) com `method="ffill"`, não uma escolha metodológica
deliberada.

### 2.3 Tratamento de ausência

Forward-fill puro: nenhuma interpolação, nenhuma extrapolação. Se não
houver nenhuma cotação anterior na amostra buscada, o resultado é `NaN`
explícito (nunca fabricado) — comportamento correto e já coberto por
teste (`tests/unit/test_ppi_parametros_e_cambio.py::test_cambio_mensal_usa_ultima_cotacao_disponivel_do_mes_ffill`,
que precisa ser revisado após a decisão desta etapa se a convenção mudar).

## 3. Semântica temporal do Comex Stat — o que define "o mês" de uma importação

Pesquisado ao vivo nesta etapa (FAQ oficial do MDIC,
`gov.br/mdic/.../perguntas-frequentes-faq`, acesso 28/08/2026):

> "as operações de **importação** são contabilizadas nas estatísticas
> brasileiras no momento em que a mercadoria é **desembaraçada** na
> entrada no país."

Ou seja: o "mês" de uma linha de importação no Comex Stat é o mês do
**desembaraço aduaneiro** — o evento em que a carga é liberada pela
Receita Federal, tipicamente também o momento em que II/AFRMM são
apurados/recolhidos. (Para exportação, o critério mudou ao longo do
tempo — antes de 1997: data de emissão da guia; 1997–2017: desembaraço;
pós-2018: data de carga completamente exportada — mas essa mudança **não
se aplica ao lado de importação**, que usa desembaraço em toda a série.)

**Implicação para a pergunta de FX:** o evento economicamente relevante
que o Comex Stat usa para "carimbar" o mês de uma importação
(desembaraço) acontece **dentro** do próprio mês `t`, distribuído ao
longo dele. Isso não prova que o câmbio "correto" seja uma média do mês
— o importador pode ter contratado câmbio antes (hedge, forward,
adiantamento de contrato de câmbio — ver §15) — mas **enfraquece
diretamente a convenção atual**, que usa uma cotação de **antes do início**
do mês de desembaraço, ou seja, sistematicamente **anterior** ao evento
que o próprio Comex Stat usa para definir o período. Uma cotação média
(ou de fechamento) do mês de desembaraço está, no mínimo, temporalmente
mais alinhada ao evento que o dado mensal representa do que uma cotação
fixada antes de esse mês começar.

## 4. Convenções candidatas

| | Definição formal | Fonte dos dados diários |
|---|---|---|
| **A — CURRENT** | `FX_current(t) = τ(max{d ≤ 1º dia de t})` — exatamente o que produção faz hoje | mesma série SGS-1, mesmo fetch |
| **B — MONTHLY MEAN** | `FX_mean(t) = média aritmética de τ(d)` para todo `d` com mês-calendário `= t` | idem |
| **C — END OF MONTH** | `FX_eom(t) = τ(max{d ≤ último dia de t})` — cotação de fechamento do último dia útil **dentro** do mês `t` | idem |

C foi adicionada com justificativa forte: a descoberta do §2.2 mostra que
A não é "fim de mês" nem "média" — é um instantâneo de **início** de mês
(efetivamente o fim do mês anterior). C isola exatamente essa dúvida
("o problema é o ponto no tempo errado, ou é usar um ponto em vez de uma
média?") sem introduzir nenhum peso ou dado novo — não há justificativa
para uma quarta convenção (ex. ponderada por fluxo de comércio): o
próprio Comex Stat só expõe agregados mensais, não datas de desembaraço
por transação, então não há como construir um peso intramensal
defensável sem inventar dado que a fonte não fornece.

## 5. Painel de dados usado

Reaproveitado (sem novo fetch do Comex Stat): `data/processed/validation/ipia_hrc_v2_import_decomposition_panel.csv`
(produzido por `scripts/validar_ipia_hrc_v2_final.py`, Stage G3, com dado
real do Comex Stat/BCB) — contém `cif_usd_t`, `frete_usd_t`,
`aliquota_ii`, `aliquota_afrmm`, `antidumping_usd_t` e `cambio_mes`
(= FX_current) por mês, já FX-independentes exceto a última coluna.

Câmbio diário: busca ao vivo nesta etapa via
`indices_setoriais._pipeline_cambio_historico_seguro(2012, 2026)` (mesmo
coletor chunked de produção, nunca `/ultimos/N`) — 3.682 observações
diárias, 2012-01-02 a 2026-08-28.

Preço doméstico oficial: `data/processed/ipia_hrc_v2_official.csv` +
`ipia_hrc_v2_provisional.csv` (série publicada, usada apenas para leitura,
nunca modificada).

**Janelas de comparação (tratamento explícito da quebra de dados, como
pedido):**

- **FX e PPI**: 2012-02 a 2026-06, **131 meses** calculáveis (dos ~172
  meses-calendário do intervalo; os demais são `UNKNOWN` sob a política de
  publicação bottom-up do ADR 0009 — cobertura de política comercial
  insuficiente naquele mês — exclusão correta e preexistente, não uma
  lacuna introduzida por esta análise).
- **IPIA** (precisa de preço doméstico, disponível só a partir de
  2019-02): **78 meses**, 2019-02 a 2026-06. Dentro desses, **48 meses**
  já são `OFFICIAL` (status `EXPERIMENTAL` ou `PUBLICATION_GRADE`,
  congelados); os demais 30 são `PROVISIONAL` (ainda revisáveis por
  natureza, independente desta análise).

**Sanity check de fidelidade:** a fórmula usada para recomputar PPI é a
mesma de produção (`indices_setoriais._ppi_brl_t`, importada, nunca
reimplementada). Reconstruir `PPI_current` a partir do painel bate com
`ipia_hrc_v2` oficial com erro **zero** para IPIA (`max diff = 0.00000000`,
verificado). Para PPI em nível absoluto há um resíduo pequeno (**máx.
3,09 R$/t**, ~0,05–0,1% do PPI típico) — ver §17 (Limitações) para a causa
exata e por que ele não contamina a comparação entre convenções.

## 6. Comparação FX: CURRENT vs MEAN (n=131 meses, 2012-02–2026-06)

| Métrica | Valor |
|---|---|
| Média da diferença (current − mean) | −0,0079 |
| Mediana da diferença | −0,0066 |
| MAE | 0,0712 |
| RMSE | 0,0938 |
| Diferença % média | −0,249% |
| MAPE | 1,708% |
| Máximo \|diff\| | 0,2874 |
| P5 / P25 / P50 / P75 / P95 | −0,1573 / −0,0631 / −0,0066 / 0,0417 / 0,1448 |
| Correlação | 0,99746 |

**Viés sistemático:** `mean(FX_current − FX_mean) = −0,0079` — current
**subestima** levemente o câmbio médio do mês, em média, mas o efeito é
pequeno (~0,25%) e a correlação é altíssima (0,997). A divergência real
está na **dispersão mês a mês** (MAPE 1,7%, P95 de 0,14 sobre uma base de
~4-5), não num viés de nível constante.

CURRENT vs END-OF-MONTH (isola o efeito de timing puro, sem misturar com
"ponto vs média"): MAE 0,1187, RMSE 0,1562, MAPE 2,863% — **quase o dobro
do MAE contra a média**. Isto é evidência direta de que a maior parte da
divergência de CURRENT vem de **estar no ponto errado do calendário**
(início vs fim de mês), não apenas de ser um ponto em vez de uma média.

## 7. Impacto sobre o PPI (n=131 meses)

| Métrica | Valor (R$/t) |
|---|---|
| Diferença média (current − mean) | −8,62 |
| Diferença mediana | −4,11 |
| MAE | 51,98 |
| RMSE | 71,90 |
| Diferença % média | −0,224% |
| MAPE | 1,497% |
| Máximo \|diff\| | 367,17 |
| P5/P25/P50/P75/P95 | −122,36 / −44,84 / −4,11 / 27,34 / 107,50 |
| Correlação | 0,99861 |

## 8. Meses extremos — maior \|PPI_current − PPI_mean\|

| Mês | PPI_current | PPI_mean | Δ (R$/t) | Δ% |
|---|---:|---:|---:|---:|
| 2022-06 | 6.791,55 | 7.158,72 | −367,17 | −5,13% |
| 2022-10 | 6.798,42 | 6.611,02 | +187,40 | +2,84% |
| 2015-03 | 2.283,69 | 2.457,87 | −174,17 | −7,09% |
| 2021-10 | 6.005,74 | 6.159,97 | −154,22 | −2,50% |
| 2023-06 | 4.344,33 | 4.198,52 | +145,82 | +3,47% |
| 2018-08 | 3.218,57 | 3.357,07 | −138,50 | −4,13% |
| 2020-05 | 3.756,96 | 3.892,42 | −135,46 | −3,48% |
| 2021-11 | 7.063,46 | 6.929,35 | +134,12 | +1,94% |
| 2024-10 | 4.427,33 | 4.558,70 | −131,37 | −2,88% |
| 2021-07 | 4.686,38 | 4.816,51 | −130,12 | −2,70% |

## 9. Impacto sobre o IPIA-HRC (n=78 meses, 2019-02–2026-06)

Esta é a comparação mais relevante para a decisão.

| Métrica | Valor (pontos de IPIA) |
|---|---:|
| Diferença média (current − mean) | +0,120 |
| Diferença mediana | +0,110 |
| MAE | 1,576 |
| RMSE | 1,904 |
| Diferença % média | +0,177% |
| MAPE | 1,493% |
| Máximo \|diff\| | 4,483 |
| P5/P25/P50/P75/P95 | −2,963 / −1,196 / 0,110 / 1,337 / 3,039 |
| Correlação | 0,99447 |

- **Direção mensal (MoM):** 73 de 77 meses (94,8%) têm a mesma direção
  (ambas convenções sobem ou ambas caem no mesmo mês); **4 meses** (5,2%)
  divergem de direção.
- **Cruzamento do threshold 100 (mudança de interpretação de paridade):**
  **0 meses** — em nenhum mês da janela comparável uma convenção indica
  "importar compensa" (IPIA>100) enquanto a outra indica o oposto. Este é
  o achado mais tranquilizador da análise: a narrativa qualitativa do
  índice (paridade favorável/desfavorável) **nunca muda** entre as duas
  convenções, no histórico inteiro observável.
- **YoY:** 66 meses comparáveis; diferença média \|YoY_current −
  YoY_mean\| = 2,20 pontos.

### Meses extremos — maior \|IPIA_current − IPIA_mean\|

| Mês | IPIA_current | IPIA_mean | Δ (pts) | Status |
|---|---:|---:|---:|---|
| 2022-06 | 87,40 | 82,92 | +4,48 | PUBLICATION_GRADE |
| 2023-06 | 117,32 | 121,39 | −4,07 | PUBLICATION_GRADE |
| 2019-08 | 93,82 | 89,92 | +3,91 | EXPERIMENTAL |
| 2021-07 | 132,81 | 129,22 | +3,59 | EXPERIMENTAL |
| 2024-10 | 109,31 | 106,16 | +3,15 | PROVISIONAL |
| 2026-01 | 111,57 | 114,68 | −3,11 | PROVISIONAL |
| 2021-06 | 127,77 | 130,88 | −3,11 | EXPERIMENTAL |
| 2021-08 | 131,34 | 128,32 | +3,02 | EXPERIMENTAL |
| 2025-06 | 113,98 | 117,00 | −3,02 | PROVISIONAL |
| 2021-05 | 154,13 | 157,08 | −2,95 | EXPERIMENTAL |

## 10. Timing bias — top 10 meses por volatilidade cambial intramensal

Critério **quantitativo** (não escolhido a dedo): `(máx − mín) / média`
das cotações diárias dentro do mês, ranking decrescente.

| Mês | FX início (1º dia útil do mês) | FX médio | FX fim (últ. dia útil do mês) | FX_current (produção) | Vol. intramensal | Δ(current−mean) | ΔPPI | ΔIPIA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015-03 | 2,8655 | 3,1395 | 3,2080 | 2,8782 | 12,83% | −0,2613 | −174,17 | n/d¹ |
| 2018-08 | 3,7491 | 3,9298 | 4,1353 | 3,7491 | 11,94% | −0,1807 | −138,50 | n/d¹ |
| 2016-06 | 3,6126 | 3,4245 | 3,2098 | 3,6126 | 11,76% | +0,1881 | +65,83 | n/d¹ |
| 2016-03 | 3,9913 | 3,7039 | 3,5589 | 3,9913 | 11,67% | +0,2874 | +119,64 | n/d¹ |
| 2020-05 | 5,5816 | 5,6434 | 5,4263 | 5,4270 | 11,31% | −0,2164 | −135,46 | +2,44 |
| 2014-09 | 2,2364 | 2,3329 | 2,4510 | 2,2364 | 9,44% | −0,0965 | −67,90 | n/d¹ |
| 2022-06 | 4,7765 | 5,0492 | 5,2380 | 4,7765 | 9,14% | −0,2727 | −367,17 | +4,48 |
| 2017-05 | 3,1724 | 3,2095 | 3,2437 | 3,1984 | 8,98% | −0,0111 | −7,22 | n/d¹ |
| 2022-05 | 5,0266 | 4,9550 | 4,7289 | 4,9191 | 8,61% | −0,0359 | −42,38 | +0,68 |
| 2015-04 | 3,1556 | 3,0432 | 2,9936 | 3,1556 | 8,59% | +0,1124 | +70,72 | n/d¹ |

¹ n/d = fora da janela com preço doméstico publicado (antes de 2019-02) —
gap de dado tratado explicitamente, não omitido.

**Conclusão quantitativa:** nos 3 meses de maior volatilidade intramensal
que também caem dentro da janela IPIA comparável (2020-05, 2022-06,
2022-05), o `ΔIPIA` chega a **+4,48 pontos** (2022-06, o maior de toda a
série) — confirma que o timing bias é real e concentrado exatamente nos
meses de câmbio mais volátil, como esperado teoricamente, e não é um
artefato aleatório.

## 11. Decomposição da volatilidade (MoM, nível-a-nível)

| Série | std(Δcurrent) | std(Δmean) | Current é mais volátil? |
|---|---:|---:|---|
| FX | 0,21938 | 0,19866 | +10,4% |
| PPI (R$/t) | 447,43 | 437,56 | +2,3% |
| IPIA (pts) | 11,6646 | 11,3285 | +3,0% |

A convenção atual adiciona volatilidade mês a mês, mas o efeito é modesto
(2–10%, não uma diferença de ordem de grandeza). Isto é **diagnóstico**,
não um argumento por si só — uma série mais suave não é automaticamente
"melhor" (uma média mensal suaviza mecanicamente qualquer coisa); o dado
relevante para a decisão é o restante desta análise (viés, direção,
threshold-100), não a volatilidade isolada.

## 12. Impacto sobre o histórico já publicado (vintages OFFICIAL)

**Limiares desta análise, criados especificamente para este relatório —
NÃO são uma política institucional já adotada pelo projeto** (declarado
explicitamente, como pedido):

| Classe | \|ΔIPIA\| (pontos) |
|---|---|
| IMMATERIAL | < 0,5 |
| LOW | 0,5 – 2,0 |
| MODERATE | 2,0 – 5,0 |
| HIGH | > 5,0 |

Aplicado aos **48 meses já `OFFICIAL`** (EXPERIMENTAL ou
PUBLICATION_GRADE, portanto já congelados e publicados):

| Classe | N meses | % |
|---|---:|---:|
| IMMATERIAL | 10 | 20,8% |
| LOW | 20 | 41,7% |
| MODERATE | 18 | 37,5% |
| HIGH | 0 | 0% |

Nenhum mês já publicado teria mudança classificada como `HIGH` sob estes
limiares, mas **37,5%** teriam mudança `MODERATE` (2–5 pontos) — não é um
efeito irrelevante, mas também não é dramático: o teto observado em toda
a série (48 meses oficiais + 30 provisórios) é 4,48 pontos, e nenhum mês
muda de lado do threshold 100.

## 13. Pesquisa institucional

Prioridade seguida: BCB → MDIC/Comex Stat → IMF → demais.

- **Banco Central do Brasil** — PTAX: desde a Resolução BCB nº 45/2020, a
  PTAX é a média aritmética das taxas de 4 consultas diárias aos dealers
  de câmbio; o boletim de fechamento é a média dos boletins do dia
  (confirmado no Portal de Dados Abertos do BCB e cruzado ao vivo contra
  o endpoint oficial de cotação, §2.1).
  [Taxa de câmbio - Livre - Dólar americano (venda) - diário](https://dadosabertos.bcb.gov.br/dataset/1-taxa-de-cambio---livre---dolar-americano-venda---diario) ·
  [A taxa de câmbio de referência Ptax (BCB, Relatório de Inflação)](https://www.bcb.gov.br/conteudo/relatorioinflacao/EstudosEspeciais/EE042_A_taxa_de_cambio_de_referencia_Ptax.pdf)
- **MDIC / Comex Stat** — critério de mês para importação = data de
  desembaraço aduaneiro (§3).
  [Perguntas Frequentes — FAQ, MDIC](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/perguntas-frequentes-faq)
- **IMF/ILO/OECD/Eurostat/UN/World Bank, Export and Import Price Index
  Manual (2009)** — segue o SNA 2008: a conversão cambial deve, em
  princípio, usar a taxa vigente na **data da transação**; quando isso não
  é possível, uma **média para o menor período possível** é a alternativa
  recomendada. Exemplo citado no próprio manual: o BLS dos EUA, cujo
  período de referência de preço é o dia 1º do mês, usa a **taxa média do
  mês anterior** como aproximação prática — um precedente institucional
  real de usar uma **média**, não um ponto, quando a taxa exata da
  transação não está disponível. O manual também nota que, havendo taxas
  de compra e venda distintas, o ponto médio entre elas evita embutir o
  spread cambial — o projeto usa a taxa de **venda** pura (não o ponto
  médio compra/venda), uma simplificação preexistente não investigada
  nesta etapa (ver §15).
  [Export and Import Price Index Manual — IMF eLibrary](https://www.elibrary.imf.org/downloadpdf/display/book/9781589067806/9781589067806.pdf) ·
  [mesmo manual — OECD](https://www.oecd.org/content/dam/oecd/en/publications/reports/2009/12/export-and-import-price-index-manual-theory-and-practice_g1ghcc55/9789264085411-en.pdf)

**Leitura da evidência institucional:** nenhuma fonte prescreve
literalmente "use a última cotação disponível antes do início do mês"
(convenção A, como hoje implementada). A referência mais próxima e mais
citada (SNA 2008/IMF) recomenda a taxa da transação ou, na ausência
dela, uma média — o que favorece a convenção B, ainda que com a ressalva
de que "menor período possível" pode, em teoria, favorecer algo mais
granular do que uma média mensal se dado diário de transação existisse
(não existe, no Comex Stat agregado).

## 14. Câmbio observado vs. câmbio efetivo da empresa (limitação, não resolvida aqui)

Nenhuma convenção baseada em PTAX/SGS reproduz necessariamente a taxa
efetivamente contratada por um importador individual — empresas usam
hedge, contrato de câmbio a termo, ou fechamento antecipado por outras
razões de tesouraria. O IPIA-HRC estima uma **paridade de mercado
reprodutível** a partir de uma fonte pública e auditável, não a
tesouraria de nenhuma empresa específica. Isso vale **igualmente** para
as três convenções candidatas (A, B e C) — nenhuma delas resolve essa
limitação, que é estrutural ao uso de PTAX como proxy. Recomendação:
esta distinção deveria ser adicionada à metodologia (`docs/METODOLOGIA.md`
§9.6) como limitação explícita, independentemente de qual convenção for
escolhida — não é uma razão para preferir A, B ou C entre si.

## 15. Matriz de decisão

Escala: 1 (fraco) a 5 (forte), na direção "atende bem ao critério".

| Critério | A — Current | B — Monthly Mean | C — End of Month |
|---|---:|---:|---:|
| Representatividade mensal (reflete condições **dentro** do mês de desembaraço) | 1 — reflete o mês **anterior** | 5 — média de todo o mês | 3 — só o último dia do mês |
| Timing bias (ausência de) | 1 — maior MAE vs. mean/eom (§6) | 5 — é a própria referência | 3 — ainda um ponto, mas ao menos dentro do mês certo |
| Volatilidade adicionada | 2 — +2 a +10% vs. mean (§11) | 5 — referência (mais suave por construção) | 2–3 — provavelmente similar a A (não medido diretamente, só A vs. mean e A vs. eom) |
| Coerência com definição do Comex (desembaraço, §3) | 1 — cotação de **antes** do desembaraço começar | 5 — cobre o mês inteiro do desembaraço | 4 — pelo menos dentro do mês do desembaraço |
| Reprodutibilidade | 5 — já implementado, testado | 5 — mesma fonte, groupby simples | 5 — mesma fonte, groupby simples |
| Transparência/simplicidade de explicar | 2 — hoje mal compreendida até pelo próprio código (comentário "a confirmar") | 5 — "câmbio médio do mês" é imediato de explicar a qualquer leitor | 4 — "câmbio de fechamento do mês" também é simples de explicar |
| Evidência institucional (§13) | 1 — nenhuma fonte descreve isso | 4 — alinhado ao precedente SNA2008/BLS | 2 — nenhuma fonte específica prioriza fim-de-mês para dado mensal agregado |
| Impacto no histórico (§12) — favorece MANTER se o impacto de mudar for alto | 5 — zero impacto (é o status quo) | 3 — MAE 1,58 pts, 37,5% dos meses oficiais em `MODERATE`, mas 0 reversão de threshold 100 | não medido diretamente nesta etapa (só A vs. mean e A vs. eom foram comparados a fundo; C vs. mean não) |
| Complexidade de implementação | 5 — nenhuma mudança | 4 — troca `reindex(...,ffill)` por `groupby(mês).mean()` | 4 — troca `ffill` por `last()` dentro do mês |

## 16. Recomendação

### B — MIGRATE TO MONTHLY MEAN

**CONFIDENCE = MEDIUM**

Razões a favor:
- É a convenção mais alinhada à evidência institucional disponível
  (SNA 2008/IMF, precedente BLS) entre as testadas.
- Corrige um problema que a própria auditoria revelou não ser "ponto vs
  média", mas primariamente **timing**: a convenção atual usa uma
  cotação de antes do mês começar, o que nenhuma fonte institucional
  recomenda e nenhum comentário no código declara ser intencional.
- Empiricamente, o custo de migrar é limitado: correlação altíssima com
  o atual (0,994 no IPIA), **zero** reversões de threshold 100 em 78
  meses, 94,8% de concordância de direção mês a mês.
- Reduz timing bias mensurável nos meses de maior volatilidade cambial
  (exatamente onde o problema mais importa).

Razões para não ter confiança alta (por isso MEDIUM, não HIGH):
- O resíduo de reconstrução do painel agregado (§17) não foi eliminado
  com uma reconstrução granular por NCM — o limite teórico derivado
  (<1 R$/t de contaminação na diferença entre convenções) é uma
  INFERÊNCIA, não uma verificação direta.
- 37,5% dos meses oficiais teriam mudança `MODERATE` (2–5 pontos) — não é
  um efeito desprezível, e qualquer mudança de convenção reabre a
  discussão de revisão de histórico publicado (§18).
- É fundamentalmente um julgamento de valor sobre "o que o câmbio do mês
  deveria significar" — instituições diferentes fazem escolhas
  diferentes (o próprio IMF manual permite mais de uma prática aceitável),
  e não há uma fonte que dite exatamente esta escolha para uma paridade
  de importação brasileira de aço.

**C (end-of-month)** não é recomendada como escolha principal — ela
resolveria parte do timing bias mas sem o respaldo institucional de B, e
seu impacto vs. mean/current não foi medido diretamente nesta etapa
(seria preciso rodar uma terceira rodada completa de comparação
`current vs eom` e `mean vs eom` no IPIA, não só no FX). Se o usuário
preferir uma mudança mínima que ainda corrija o timing, C é a alternativa
natural a pedir como segunda análise.

## 17. Limitações

1. **Resíduo de reconstrução por agregação (quantificado, não eliminado
   totalmente).** O painel reaproveitado (`ipia_hrc_v2_import_decomposition_panel.csv`)
   traz uma única `aliquota_ii`/`aliquota_afrmm` por mês (média ponderada
   por KG entre os grupos NCM×país), não os grupos granulares. Como o PPI
   verdadeiro é uma média ponderada por KG do PPI de cada grupo — e cada
   grupo tem sua própria alíquota — recompor o PPI agregado a partir da
   alíquota já média introduz um pequeno erro de reconstrução (**máx.
   3,09 R$/t observado**, ~0,05–0,1% do PPI típico) por não capturar a
   covariância entre CIF e alíquota entre grupos. **Argumento de por que
   isso não invalida a comparação** (INFERÊNCIA matemática, testada via
   `tests/unit/test_fx_convention_analysis.py::test_recompute_ppi_e_afim_em_fx`):
   PPI é uma função **afim** do câmbio para componentes fixos — isso vale
   tanto no nível do grupo quanto, por linearidade, no nível agregado — o
   erro de reconstrução (que vem da alíquota, não do câmbio) escala
   proporcionalmente ao câmbio usado; como `FX_current` e `FX_mean` diferem
   em média por só ~0,25%, a contaminação estimada na DIFERENÇA
   `PPI_current − PPI_mean` é inferior a ~1 R$/t — duas ordens de
   grandeza abaixo do efeito medido (MAE 52 R$/t). Não eliminado com uma
   reconstrução granular por (mês, NCM, país) nesta etapa por
   proporcionalidade de esforço; fica como item de reforço futuro se a
   decisão for adotar B ou C.
2. **PTAX venda, não o ponto médio compra/venda** — o próprio IMF Export
   and Import Price Index Manual recomenda o ponto médio entre compra e
   venda para excluir o spread cambial; o projeto usa só a venda, uma
   simplificação preexistente, não investigada nem alterada aqui.
3. **Câmbio observado ≠ câmbio efetivo da empresa** — ver §14.
4. **Janela de comparação do IPIA é 2019-02–2026-06** (78 meses) — mais
   curta que a janela FX/PPI (2012-02–2026-06, 131 meses) porque o preço
   doméstico oficial só existe a partir de 2019-02; qualquer decisão
   sobre o histórico pré-2019 no lado importado (`historical
   experimental`, ADR 0009) não tem contraparte de IPIA para validar
   contra threshold-100/direção — só FX e PPI foram comparados nesse
   trecho mais antigo.
5. **C (end-of-month) só foi comparada contra A**, não contra B — uma
   comparação C vs. B ficaria para uma etapa de aprofundamento se o
   usuário preferir C como opção final.

## 18. Versionamento, caso a convenção seja alterada (decisão NÃO tomada aqui)

Classificação recomendada: **methodological/parameter revision**, não
"bug fix silencioso" — apesar de a convenção atual divergir do que a
pesquisa original pretendia (o que teria cheiro de bug fix), ela já é a
base de **48 meses publicados como OFFICIAL** (`EXPERIMENTAL`/
`PUBLICATION_GRADE`, portanto congelados sob a política de vintages do
ADR 0012). Mudar isso agora alteraria valores já publicados — o próprio
`CLAUDE.md` e a política de vintages do projeto proíbem reescrever
histórico publicado silenciosamente. Portanto, se aprovada, a mudança
deveria:

- ser registrada como decisão explícita (ADR, ver §19);
- **não sobrescrever** as vintages já congeladas — precisaria de uma
  nova vintage/versão (ex.: `V2.1` ou equivalente, seguindo o esquema de
  versionamento que o projeto já adotar — não invento um número aqui);
- avaliar bump de `VERSAO_METODOLOGIA` (hoje `"1.2"`) por `docs/METODOLOGIA.md`
  §24 — a mudança altera o cálculo econômico publicado, logo qualifica
  como mudança que exige avaliação de bump, ao contrário do que ocorreu
  na ADR 0013 (que não mudava número nenhum);
- documentar explicitamente "antes → depois → motivo" para os 48 meses
  OFFICIAL, exatamente como pedido pelo `CLAUDE.md` para qualquer
  correção potencial de série histórica.

## 19. Proposta de conteúdo de ADR (DRAFT — status PROPOSED, decisão do usuário pendente)

> Este conteúdo é um rascunho para eventual `docs/adr/0014-*.md` — **não
> foi criado como arquivo em `docs/adr/`** nesta etapa, porque esse
> diretório é documentado (`CLAUDE.md`) como contendo apenas ADRs já
> aceitos; colocá-lo lá antes da decisão do usuário poderia ser
> confundido com uma decisão já tomada. Fica registrado aqui até a
> decisão.

---

**# 0014 (proposta) - IPIA-HRC: convenção cambial do PPI**

**Status: PROPOSED — aguardando decisão explícita do usuário. NÃO
implementado.**

**Contexto:** `docs/validation/fx_convention_validation.md` investigou a
divergência entre a convenção cambial implementada (`FX_current`, um
instantâneo do início do mês, efetivamente o fechamento do mês anterior)
e a intenção original da pesquisa metodológica (câmbio médio mensal).
Evidência institucional (SNA 2008/IMF, precedente BLS) e a semântica do
próprio Comex Stat (mês definido pelo desembaraço aduaneiro, evento que
ocorre dentro do mês) favorecem uma convenção de média mensal. O impacto
empírico é mensurável mas não disruptivo: MAE de 1,58 pontos de IPIA,
37,5% dos 48 meses oficiais em impacto `MODERATE` (2-5 pontos, limiar
bespoke desta análise), zero reversões de threshold 100, 94,8% de
concordância de direção mês a mês.

**Decisão:** *(em aberto — depende da escolha do usuário entre A/B/C/D,
ver relatório)*

**Consequências, se B (monthly mean) for adotada:** requer nova
vintage/versão publicada (não sobrescreve as 48 vintages OFFICIAL já
congeladas), avaliação de bump de `VERSAO_METODOLOGIA`, atualização de
`docs/METODOLOGIA.md` §9.6 com a fórmula corrigida, atualização/adição de
testes de `tests/unit/test_ppi_parametros_e_cambio.py`, documentação
explícita "antes → depois → motivo" para os 48 meses afetados.

---

## 20. Artefatos produzidos

Todos sob `data/processed/validation/fx_convention/` (gitignored, como o
resto de `data/processed/`), rotulados `VALIDATION_NON_PUBLISHED_COUNTERFACTUAL`
na própria coluna do CSV principal — nunca sob `data/curated/` nem sob
`data/processed/vintages/`:

- `fx_convention_counterfactual_panel.csv` — série completa mês a mês
  com as 3 convenções de FX e o PPI/IPIA resultante de cada uma.
- `fx_convention_timing_bias.csv` — tabela da §10.
- `fx_convention_extreme_months_ppi.csv` / `..._ipia.csv` — tabelas das
  §8/§9.

## 21. Referências

- [IMF/ILO/OECD/Eurostat/UN/World Bank — Export and Import Price Index Manual, 2009](https://www.elibrary.imf.org/downloadpdf/display/book/9781589067806/9781589067806.pdf)
- [BCB — A taxa de câmbio de referência Ptax](https://www.bcb.gov.br/conteudo/relatorioinflacao/EstudosEspeciais/EE042_A_taxa_de_cambio_de_referencia_Ptax.pdf)
- [BCB — Portal de Dados Abertos, série 1 (câmbio venda diário)](https://dadosabertos.bcb.gov.br/dataset/1-taxa-de-cambio---livre---dolar-americano-venda---diario)
- [MDIC — Perguntas Frequentes (FAQ), critério de data de importação](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/perguntas-frequentes-faq)
- `references/manual_metodologico_indices_setoriais.md` §5.2 (pesquisa original, "câmbio médio do mês")
- `docs/adr/0009-*.md` (janela publication-grade, agregação bottom-up)
- `docs/validation/ipia_hrc_v2_final_validation.md` §11 (sensibilidade de FX/FOB/D_porto/D_interno/margem, etapa anterior)
