# Comex Stat — Validação ao vivo (Stage E2)

**Data da investigação:** 2026-08-26
**Executor:** investigação de fonte (Spec 0003, Stage E2), não refatoração.
**Script reprodutor:** `scripts/research_comex_live.py` (opt-in, faz rede real, fora da suíte pytest).
**Adapter usado:** `steel_indicator.sources.comex` (produção, Stage E1, sem alteração nesta etapa).

## Status do documento

Fecha, com evidência reproduzível, os itens 1–10 do objetivo da Stage E2 sobre o Comex Stat.
**Não** resolve a vigência histórica da cesta de NCM (investigação separada, explicitamente fora de escopo aqui — ver seção "Limitações").
**Não** autoriza mudança de metodologia, fórmula ou parâmetro.

## Legenda de evidência

- **FACT** — observado diretamente na API nesta sessão.
- **DOC** — vem de `references/guia_de_coleta_de_series.md` ou `references/catalogo_series_coleta.xlsx`.
- **INFERENCE** — conclusão derivada dos fatos, não observada diretamente.

## Amostra usada

Todas as consultas usaram os 13 NCMs atualmente definidos em `NCM_BOBINA_QUENTE`
(`src/indices_setoriais.py`), **apenas como amostra de teste da API**:

```text
72081000 72082500 72082610 72082690 72082710 72082790
72083610 72083690 72083700 72083810 72083890 72083910 72083990
```

Isto **não** valida a cesta histórica de HRC — ver "Limitações".

---

## 1. POST /general

**FACT** — validado. Endpoint, payload mínimo e resposta real:

- Endpoint: `https://api-comexstat.mdic.gov.br/general`
- Payload (probe mínimo, 1 NCM, 2024):

```json
{
  "flow": "import",
  "monthDetail": true,
  "period": {"from": "2024-01", "to": "2024-12"},
  "filters": [{"filter": "ncm", "values": ["72083610"]}],
  "details": ["ncm", "country"],
  "metrics": ["metricFOB", "metricKG", "metricFreight", "metricInsurance"]
}
```

- Resposta: HTTP 200, corpo JSON com chaves top-level `data`, `success`, `message`, `processo_info`, `language`. `success: true`, `message: null`.
- `data.list` é a lista de registros (mesmo caminho que `comex_importacao_ncm` já usa em produção — confirmado consistente).

## 2. Schema real observado

**FACT** — um registro real (payload acima):

```json
{
  "coNcm": "72083610",
  "year": "2024",
  "monthNumber": "10",
  "ncm": "Produtos laminados planos, de ferro ou aço não ligado, ... laminados a quente ...",
  "country": "França",
  "metricFOB": "296",
  "metricFreight": "1",
  "metricInsurance": "0",
  "metricKG": "112"
}
```

Achados de schema:

- **FACT**: todos os valores numéricos vêm como **string** (`"296"`, não `296`). Já compatível com o código de produção existente, que já aplica `pd.to_numeric(..., errors="coerce")` em todas as colunas de métrica antes de usá-las (`serie_mensal_preco_bobina`) — nenhuma divergência de comportamento encontrada.
- **FACT**: o código do NCM vem em `coNcm` (não em `ncm` — esse campo é a descrição textual completa do produto). Já é o campo usado pela produção (`check_sources()`, `df["coNcm"].value_counts()`) — consistente.
- **FACT**: `country` vem como nome completo em texto (ex. "França", "China", "Coreia do Sul"), não código — consistente com o uso já feito em `origem_importacao_bobina_por_pais`.
- **FACT**: nenhum campo inesperado relevante apareceu; nenhuma quebra de schema frente ao que o adapter já assume.

## 3. Cobertura das métricas (tabela consolidada)

Consultas: janelas 1998–2004, 2005–2009, 2010–2014, 2015–2019, 2020–2024 (13 NCMs da amostra), mais os anos isolados 1995, 1996, 1997. Total de registros analisados nas janelas 1998–2024: **4090**.

| metric | exists | first_period_returned | first_period_populated | first_period_usable | last_period_usable | coverage (1998–2024) | zero_rate | status | evidence |
|---|---|---|---|---|---|---|---|---|---|
| `metricFOB` | FACT: sim | 1997-01 | 1997-01 | 1997-01 | 2024-12 | 100% preenchido | 0.0% | **USABLE** | FACT |
| `metricKG` | FACT: sim | 1997-01 | 1997-01 | 1997-01 | 2024-12 | 100% preenchido | 1.4% | **USABLE** | FACT |
| `metricFreight` | FACT: sim | 1997-01 | 1997-01 | 1997-01 | 2024-12 | 100% preenchido | 0.9% | **USABLE** | FACT |
| `metricInsurance` | FACT: sim | 1997-01 | 1997-01 | 1997-01 (com zero_rate mais alto no início) | 2024-12 | 100% preenchido | 29.5% (1998–2024); 60% em 1997 | **USABLE** (com ressalva) | FACT |
| `metricCIF` | FACT: sim, aceito como metric name | 2024 (único ano testado) | 2024 | 2024 | 2024 (não testado fora de 2024) | não testado fora de 2024 | não testado | **EXISTS, NÃO EXPLORADO EM PROFUNDIDADE** | FACT (ponto único) |

Definições aplicadas (item 2 do seu pedido):

- **FIELD EXISTS**: a API aceita o nome da métrica e devolve a coluna. Confirmado para as 5 métricas.
- **FIELD POPULATED**: valores não nulos, coercíveis a numérico, em (quase) 100% dos registros retornados. Confirmado para as 4 métricas centrais em toda janela 1997–2024 testada.
- **FIELD USABLE**: populado **e** carrega variação econômica real (não é 100% zero). Confirmado para as 4 — nenhuma delas apareceu com zero_rate = 100% em nenhuma janela testada. `metricInsurance` tem zero_rate legitimamente mais alto (envios sem seguro discriminado), não indício de dado ausente — mesmo padrão se repete em décadas distintas (1997: 60%; 1998–2024: 29.5%), então **INFERENCE**: é uma característica real do dado (parte dos embarques não tem seguro individualizado/declarado), não uma lacuna de preenchimento.

## 4. Fronteira histórica

**FACT** (evidência direta, ano isolado, mesma amostra de 13 NCMs):

| Ano | n_registros | metricFOB | metricKG | metricFreight | metricInsurance |
|---|---|---|---|---|---|
| 1995 | 0 | — | — | — | — |
| 1996 | 0 | — | — | — | — |
| **1997** | **30** | 30/30 preenchido, 30/30 > 0 | 30/30 preenchido, 30/30 > 0 | 30/30 preenchido, 30/30 > 0 | 30/30 preenchido, 12/30 > 0 |
| 1998–2004 (parte da janela combinada) | 588 | 100% preenchido | 100% preenchido | 100% preenchido | 100% preenchido |

**Fronteira histórica encontrada: 1997-01**, para as quatro métricas simultaneamente, nesta amostra de NCM. 1997 tem meses sem registro para esta amostra específica (jan/fev têm dado; março não aparece na amostra; abril em diante tem dado) — isto é **FACT** mas é esperado num recorte de 13 códigos de baixíssimo volume individual (ver Stage E1 / `docs/adr`), não evidência de lacuna sistêmica da fonte.

Não foi necessário recuar além de 1995 — dois anos consecutivos com 0 registros (1995, 1996) seguidos por 1997 com dado íntegro nas 4 métricas formam uma fronteira nítida, consistente com o que o guia já documentava.

## 5. metricCIF

**FACT**: `metricCIF` existe como nome de métrica aceito pela API. Testado com o mesmo registro do probe mínimo:

```text
metricFOB=296, metricFreight=1, metricInsurance=0  →  metricCIF=297
```

**FACT**: `297 = 296 + 1 + 0` — o campo bate exatamente com a soma `FOB + Freight + Insurance`, a mesma fórmula que `docs/METODOLOGIA.md` §9.3 já define e que o código de produção já calcula manualmente (`custo_importacao_rs_t`). **INFERENCE**: `metricCIF` é provavelmente apenas a soma server-side dos outros três campos, não uma fonte independente — mas isso foi confirmado num único registro; não foi testado em volume nem em anos anteriores a 2024.

## 6. NCMs da amostra — comportamento observado

**FACT**: nos anos testados (1997, 1998–2024 em 5 janelas, e isoladamente 2024), **todos os 13 códigos atuais de `NCM_BOBINA_QUENTE` retornaram pelo menos 1 registro** em pelo menos uma das janelas consultadas. Nenhum retornou zero em todas as janelas.

Contagem por NCM em 2024 (isolado):

```text
72081000: 14   72082500: 11   72082610: 16   72082690: 19   72082710: 10
72082790: 17   72083610: 1    72083690: 8    72083700: 15   72083810: 9
72083890: 16   72083910: 20   72083990: 20
```

**FACT**: `72083610` teve apenas **1 registro em todo o ano de 2024** — sinal de liquidez muito baixa para esse código específico, consistente com o tratamento de baixa liquidez já existente no motor (peso de confiabilidade por volume).

**Isto não confirma vigência histórica.** Não foi testado se esses códigos existiam sob a mesma numeração antes de 1997, nem se há descontinuidades/reclassificações no meio do período (ex.: o `/tables/ncm` documentado no guia como retornando códigos extintos sem campo de vigência não foi consultado nesta investigação — ver Limitações).

## 7. Evidências que confirmam o guia operacional

- **DOC → FACT confirmado**: guia afirma "Comex Stat: ... desde 1997". A fronteira real encontrada é exatamente 1997-01. Confirmado.
- **DOC → FACT confirmado**: guia afirma "6 dias de defasagem" e "API livre" — consistente com a resposta rápida e sem autenticação observada (não medimos defasagem exata nesta sessão, mas o acesso foi de fato livre, sem chave/token).
- **DOC → FACT confirmado**: guia afirma que o POST `/general` não havia sido executado ao vivo antes. Agora foi, com sucesso.

## 8. Evidências que contradizem ou refinam o guia

- **O guia lista "Ano inicial de metricFreight, metricInsurance e metricCIF" como lacuna (`A CONFIRMAR`)**. **FACT**: nesta investigação, as quatro métricas (incluindo Freight e Insurance) já vêm preenchidas desde o primeiro ano com qualquer dado (1997), para a amostra de 13 NCMs testada. Isto **fecha parcialmente** essa lacuna especificamente para HRC/bobina a quente — não generaliza automaticamente para outras famílias de produto (vergalhão, outros capítulos NCM), que não foram testadas.
- **metricCIF existe** — o guia não menciona explicitamente que a API já devolve CIF pronto; isso é uma informação nova, não uma contradição.

## 9. O que continua UNKNOWN

- Se a fronteira de 1997 vale igualmente para **todas** as famílias de produto do IPIA (ex. vergalhão) — só testamos a cesta HRC.
- Vigência histórica real de cada um dos 13 códigos NCM (o `/tables/ncm` — que o guia documenta como retornando códigos extintos sem campo de vigência — não foi consultado aqui).
- Cobertura de `metricCIF` fora de 2024 (testado num único ponto).
- Defasagem real (dias) entre publicação e disponibilidade via `/general` — não medida.
- Existência de paginação (`data.list` pode estar truncado para consultas muito maiores do que as usadas aqui — não testamos volume no limite).
- Comportamento do endpoint para NCMs de 6 dígitos ou família "vergalhão" (fora de escopo desta sessão).

## 10. Limitações explícitas

- Investigação restrita à amostra atual de HRC (`NCM_BOBINA_QUENTE`). **Não** conclui nada sobre a cesta de vergalhão nem sobre vigência histórica de códigos.
- Não foi feita consulta ao `/tables/ncm` (endpoint de vigência) nesta sessão — permanece como bloqueante metodológico separado (`docs/METODOLOGIA.md` §15.3).
- Amostras de anos específicos (1995, 1996, 1997, e blocos de 5 anos de 1998 a 2024) — não é o histórico mês a mês completo; um mês isolado sem dado dentro de uma janela testada não foi individualmente verificado.

## 11. Status do bloqueante frete/seguro (`docs/METODOLOGIA.md` §15.2)

**PARTIALLY CLOSED.**

Razão: a disponibilidade histórica de `metricFreight`/`metricInsurance` está confirmada com evidência real (FACT) desde 1997 **para a cesta atual de HRC**. Não fecha totalmente o bloqueante porque (a) não testamos a família vergalhão, (b) não testamos a vigência dos códigos NCM em si (bloqueante distinto, §15.3, continua `OPEN`), e (c) `metricCIF` foi confirmado em apenas um ponto amostral.

---

**Reprodutibilidade:** `python scripts/research_comex_live.py` reproduz todas as consultas acima (rede real, opt-in, não faz parte de `pytest tests/`).
