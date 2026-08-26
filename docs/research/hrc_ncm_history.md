# IPIA-HRC — Histórico de vigência da cesta NCM (Stage E3)

**Data da investigação:** 2026-08-26
**Tipo:** investigação de fonte/metodologia. **Não** implementa IPIA-HRC V2. **Não** altera `NCM_BOBINA_QUENTE`.
**Depende de:** `docs/research/comex_live_validation.md` (Stage E2).
**Script reprodutor (parcial):** `scripts/research_hrc_ncm_history.py` (consultas Comex Stat; os documentos oficiais externos citados abaixo precisam ser buscados manualmente, ver seção 7).

## Status do documento

Fecha parcialmente o bloqueante `docs/METODOLOGIA.md` §15.3 ("NCMs vigentes por período") para a cesta atual de HRC (`NCM_BOBINA_QUENTE`, 13 códigos). **Não resolve vergalhão nem qualquer outra família.** Não autoriza mudança de `NCM_BOBINA_QUENTE`.

## Legenda de evidência

- **FACT** — observado diretamente numa fonte primária (API ou documento oficial) nesta sessão.
- **DOC** — informado por `references/` ou por um documento oficial não verificado ao vivo nesta sessão.
- **INFERENCE** — conclusão derivada dos fatos acima, não uma confirmação direta.

## Escopo investigado

Os 13 códigos atuais de `NCM_BOBINA_QUENTE` (`src/indices_setoriais.py`), usados **somente como amostra** — esta investigação não valida nem invalida a constante, apenas reúne evidência sobre ela:

```text
72081000
72082500 72082610 72082690 72082710 72082790
72083610 72083690 72083700 72083810 72083890 72083910 72083990
```

---

## 1. Fontes consultadas

Em ordem de prioridade, conforme solicitado:

1. **Comex Stat `/tables/ncm?search=7208`** (API oficial, ao vivo) — registro histórico de códigos sob a posição 7208.
2. **Comex Stat `/general`** (API oficial, ao vivo) — presença de registros de comércio por código/ano, 1997–2024.
3. **MDIC/Camex — Tabela de Correlação NCM 2017↔2022** (documento oficial, PDF, baixado e lido nesta sessão):
   `https://www.gov.br/mdic/pt-br/assuntos/camex/estrategia-comercial/arquivos-listas/Tabela_de_Correlacao_NCM_2017_2022_Atualizada.pdf`
4. **MDIC/Camex — Tabela de Correlação NCM 2012↔2017** (documento oficial, .doc, baixado e lido nesta sessão via `antiword`):
   `https://www.gov.br/mdic/pt-br/assuntos/camex/estrategia-comercial/tarifas/arquivos-e-imagens/correl_ncm_sh2012-ncm_sh2017.doc`
5. **Rastreador NCM** (`https://rastreadorncm.mdic.gov.br/`) — ferramenta oficial de rastreio de mudanças de NCM. **Tentativa de acesso bloqueada por Cloudflare (challenge anti-bot, HTTP 403)** nesta sessão. Não contornado (não é objetivo desta etapa burlar proteção de acesso). Registrado como limitação.
6. Tentativas de localizar tabelas de correlação equivalentes para as fronteiras 2007↔2012 e 2002↔2007, usando o mesmo padrão de URL do MDIC — **não encontradas** (HTTP 404 em todas as variações tentadas). Não insistido além disso, para não "tentar endpoints aleatoriamente".
7. `references/guia_de_coleta_de_series.md` e `references/catalogo_series_coleta.xlsx` (aba "Catálogo", linha ID 91) — já lidos nas etapas anteriores; usados como DOC de apoio.
8. `src/indices_setoriais.py` — comentário de origem de `NCM_BOBINA_QUENTE` (Circular SECEX 39/2025).

## 2. Achado inicial: reconciliando "19 NCMs" do catálogo com os "13" do código

**FACT**: `references/catalogo_series_coleta.xlsx`, aba Catálogo, linha ID 91, registra "19 NCMs verificadas" para "Comex Stat — importação SH 7208 (laminados a quente)", início 1997-01.

**FACT**: consultando `/tables/ncm?search=7208` ao vivo, a posição 7208 tem **exatamente 19 códigos** registrados no total:

```text
72081000 72082500 72082610 72082690 72082710 72082790
72083610 72083690 72083700 72083810 72083890 72083910 72083990   (= os 13 de NCM_BOBINA_QUENTE)
72084000 72085100 72085200 72085300 72085400 72089000            (= 6 códigos adicionais)
```

**INFERENCE**: os "19" do catálogo = os 13 códigos atuais de bobina em rolos + os 6 códigos de "chapa/não enrolado" da mesma posição 7208, que `NCM_BOBINA_QUENTE` já exclui deliberadamente por escopo de produto (bobina ≠ chapa). Isto **não é uma divergência de vigência** — é a mesma posição NCM completa, filtrada por subtipo de produto, exatamente como o comentário do código já descreve.

**Achado secundário (documentação, não vigência)**: o comentário em `src/indices_setoriais.py` linha 97–99 lista os códigos excluídos como "7208.40/53/54/90", mas a API mostra que **72085100 e 72085200** também são códigos de chapa/não enrolado da mesma posição, não mencionados no comentário. **FACT** (a API os retorna) mas **não corrigido nesta etapa** — é uma lacuna de documentação do comentário existente, não uma mudança de metodologia, e não estava no escopo autorizado desta investigação (proibido alterar `NCM_BOBINA_QUENTE` ou seu comentário). Registrado aqui para conhecimento.

## 3. Cross-check via presença de comércio (Comex Stat `/general`, 1997–2024)

**FACT** (dados brutos, agregados por NCM/ano; ver `scripts/research_hrc_ncm_history.py` para reproduzir):

| NCM | 1º ano com registro | último ano com registro | anos intermediários sem registro |
|---|---|---|---|
| 72081000 | 1997 | 2024 | 2000, 2006, 2018 |
| 72082500 | 1997 | 2024 | nenhum |
| 72082610 | 1997 | 2024 | 1999, 2004, 2007 |
| 72082690 | 1997 | 2024 | nenhum |
| 72082710 | 1997 | 2024 | 1999, 2003, 2004 |
| 72082790 | 1997 | 2024 | nenhum |
| 72083610 | 1998 | 2024 | 14 anos (código de liquidez muito baixa — ver Stage E2, 1 registro em todo 2024) |
| 72083690 | 1997 | 2024 | nenhum |
| 72083700 | 1998 | 2024 | nenhum |
| 72083810 | 1998 | 2024 | 2013, 2015–2018 |
| 72083890 | 1997 | 2024 | nenhum |
| 72083910 | 1998 | 2024 | nenhum |
| 72083990 | 1997 | 2024 | nenhum |

**INFERENCE**: nenhum dos 13 códigos exibe o padrão que indicaria introdução tardia (zero registros do início até um ano intermediário, depois passando a ter registros) nem extinção seguida de silêncio permanente (registros que param e nunca mais voltam). Todos aparecem já no primeiro ano testável (1997 ou 1998) e novamente em 2023/2024.

**Ressalva explícita, conforme instruído**: ausência de registro num ano **não prova** ausência de vigência (pode ser só ausência de comércio real). Presença de registro também **não prova** vigência formal contínua — apenas que houve uma transação classificada sob aquele código naquele momento, o que é compatível com vigência mas não a certifica sozinho. Este cross-check é **evidência de apoio (INFERENCE)**, não prova documental (`FACT` de vigência).

## 4. Cross-check via tabelas oficiais de correlação de nomenclatura

Esta é a evidência mais forte obtida nesta investigação, porque vem diretamente dos atos oficiais que documentam mudanças de código (item 3 da prioridade solicitada).

**FACT**: a Tabela de Correlação NCM 2017↔2022 (MDIC/Camex, PDF oficial, lida integralmente nesta sessão — 29 páginas, 2008 códigos correlacionados) **não contém nenhum código começando em "72"** (capítulo inteiro de ferro/aço ausente da lista de mudanças).

**FACT**: a Tabela de Correlação NCM 2012↔2017 (MDIC/Camex, documento oficial, lido integralmente nesta sessão — 1659 códigos correlacionados) **também não contém nenhum código começando em "72"**.

**INFERENCE**: como essas tabelas de correlação existem especificamente para listar códigos que **mudaram** (foram criados, desdobrados, fundidos ou renumerados) entre duas versões da NCM, a ausência total do capítulo 72 nas duas tabelas mais recentes é evidência de que **a posição 7208 (e portanto os 13 códigos investigados) não foi alterada nas revisões SH2017→NCM2017 nem SH2022→NCM2022** — ou seja, nenhuma mudança de nomenclatura afetou esses códigos desde pelo menos a vigência da NCM2012.

**UNKNOWN**: não foi possível localizar (nem por busca nem por variação do padrão de URL oficial já confirmado) as tabelas de correlação equivalentes para as fronteiras **2007→2012** (implementação da SH2012) e **2002→2007** (implementação da SH2007). Sem elas, não há confirmação documental direta de que os 13 códigos também não mudaram entre 1997 e 2012 — apenas a evidência inferencial de presença de comércio da seção 3.

## 5. metricCIF e vigência — nota de escopo

Fora do escopo desta etapa (isso pertence à Stage E2, já fechada como PARTIALLY CLOSED). Não revisitado aqui.

## 6. Tabela por código (Fase 1 solicitada)

| ncm | descrição (resumo) | valid_from | valid_to | status | predecessor | successor | evidence | confidence |
|---|---|---|---|---|---|---|---|---|
| 72081000 | bobina a quente, com motivos em relevo | 1997 (INFERENCE) / confirmado sem mudança desde 2012 (FACT) | presente | ATIVO | nenhum identificado | N/A | FACT (correlação 2012-2024) + INFERENCE (1997-2012) | ALTA (2012–hoje) / MÉDIA (1997–2012) |
| 72082500 | bobina a quente, decapada, espessura ≥4,75mm | idem | presente | ATIVO | nenhum identificado | N/A | idem | idem |
| 72082610 | bobina a quente, decapada, 3mm≤esp.<4,75mm, limite elasticidade ≥355MPa | idem | presente | ATIVO | nenhum identificado | N/A | idem | idem |
| 72082690 | bobina a quente, decapada, 3mm≤esp.<4,75mm, outros | idem | presente | ATIVO | nenhum identificado | N/A | idem | idem |
| 72082710 | bobina a quente, decapada, esp.<3mm, limite elasticidade ≥275MPa | idem | presente | ATIVO | nenhum identificado | N/A | idem | idem |
| 72082790 | bobina a quente, decapada, esp.<3mm, outros | idem | presente | ATIVO | nenhum identificado | N/A | idem | idem |
| 72083610 | bobina a quente, não decapada, esp.>10mm, limite elasticidade ≥355MPa | 1998 (INFERENCE — primeiro registro observado) | presente | ATIVO, **liquidez muito baixa** (ver seção 3) | nenhum identificado | N/A | idem | MÉDIA (liquidez baixa reduz confiança da evidência de presença, mas não muda o status de vigência) |
| 72083690 | bobina a quente, não decapada, esp.>10mm, outros | 1997 (INFERENCE) | presente | ATIVO | nenhum identificado | N/A | idem | ALTA/MÉDIA |
| 72083700 | bobina a quente, não decapada, 4,75mm≤esp.≤10mm | 1998 (INFERENCE) | presente | ATIVO | nenhum identificado | N/A | idem | ALTA/MÉDIA |
| 72083810 | bobina a quente, não decapada, 3mm≤esp.<4,75mm, limite elasticidade ≥275MPa | 1998 (INFERENCE) | presente | ATIVO | nenhum identificado | N/A | idem | ALTA/MÉDIA |
| 72083890 | bobina a quente, não decapada, 3mm≤esp.<4,75mm, outros | 1997 (INFERENCE) | presente | ATIVO | nenhum identificado | N/A | idem | ALTA/MÉDIA |
| 72083910 | bobina a quente, não decapada, esp.<3mm, limite elasticidade ≥275MPa | 1998 (INFERENCE) | presente | ATIVO | nenhum identificado | N/A | idem | ALTA/MÉDIA |
| 72083990 | bobina a quente, não decapada, esp.<3mm, outros | 1997 (INFERENCE) | presente | ATIVO | nenhum identificado | N/A | idem | ALTA/MÉDIA |

**Nenhum predecessor foi identificado para nenhum dos 13 códigos** — não porque a busca tenha concluído que eles nasceram exatamente em 1997/1998 sem histórico anterior (isso seria uma afirmação forte que a evidência disponível não sustenta), mas porque:

(a) não há indício de descontinuidade nas fontes consultadas que motivasse procurar um predecessor, e
(b) o Comex Stat `/general` não tem dado anterior a 1997 para verificar (ver `docs/research/comex_live_validation.md`), e as tabelas de correlação oficiais disponíveis só cobrem 2012 em diante.

Isso é registrado como **UNKNOWN quanto ao período pré-1997**, não como "sem predecessor confirmado".

## 7. Cesta versionada — proposta conceitual (Fase 4, NÃO implementada em código)

Com a evidência reunida, a proposta conceitual **defensável hoje** é uma cesta **única e estável**, sem quebras conhecidas:

```text
1997-01 → presente
  72081000, 72082500, 72082610, 72082690, 72082710, 72082790,
  72083610, 72083690, 72083700, 72083810, 72083890, 72083910, 72083990

  inclusion_reason: nenhuma mudança de nomenclatura encontrada (FACT, 2012-presente;
                    INFERENCE por ausência de sinal de quebra, 1997-2012)
  equivalence_status: FULL (2012-presente, por FACT documental)
                       PARTIAL/INFERENCE (1997-2012, por ausência de tabela de
                       correlação oficial localizada para essa janela)
  evidence: docs/research/hrc_ncm_history.md, seções 3 e 4
```

**Isto não é uma tabela `period_start/period_end/ncm/...` implementada** — é a conclusão textual de que, com a evidência disponível, **não há razão documental para propor mais de um período**. Se uma tabela de correlação para 2002→2007 ou 2007→2012 for localizada depois e revelar uma mudança, esta seção precisa ser revisada antes de qualquer implementação.

## 8. Comparabilidade (Fase 5)

Não force o resultado A, conforme instruído. Avaliação honesta, diferenciando por sub-período:

- **2012–presente**: evidência de nível **FACT** (duas tabelas de correlação oficiais, sem nenhuma mudança na posição 7208) → sustentaria **A. FULLY COMPARABLE** isoladamente para esta janela.
- **1997–2012**: evidência apenas de nível **INFERENCE** (presença de comércio, sem sinal de quebra) → não atinge o padrão de confirmação documental usado para 2012–presente.

**Classificação global do período 1997–presente: C. PARTIALLY COMPARABLE.**

Não por haver diferença de escopo econômico conhecida entre sub-períodos (nenhuma foi encontrada), mas porque o **nível de confiança da evidência não é uniforme**: forte e documental de 2012 em diante, apenas inferencial e não documental de 1997 a 2012. Tratar o período inteiro como A (FULLY COMPARABLE) exigiria a tabela de correlação 2002↔2007 e 2007↔2012 (ou equivalente), que não foi localizada.

## 9. Contradições encontradas

Nenhuma contradição material. O único ponto de atenção foi a aparente divergência "19 vs. 13" do catálogo de pesquisa, que se resolveu como diferença de escopo de produto (bobina vs. chapa da mesma posição), não como indício de código faltante ou extinto.

## 10. Evidências que confirmam a documentação existente

- `docs/data-sources.md` já classificava Comex Stat como "VERIFIED with remaining field-level checks" e pedia validação da cesta NCM por período — esta investigação avança exatamente essa validação, sem ainda fechá-la por completo.
- O guia (`references/guia_de_coleta_de_series.md`) alerta que `/tables/ncm` retorna códigos extintos sem campo de vigência, usando 8542/7210/2704 como exemplos. **Nenhum código extinto foi encontrado dentro da própria posição 7208** nesta investigação — os 6 códigos "extras" encontrados (72084000/51/52/53/54/90) são vigentes e legitimamente fora de escopo (chapa, não bobina), não códigos extintos.

## 11. UNKNOWNs (lista consolidada)

- Vigência/nomenclatura dos 13 códigos entre 1997 e 2012 — sem confirmação documental direta (tabelas de correlação SH2002/SH2007 não localizadas).
- Se os 13 códigos existiam sob a mesma numeração antes de 1997 (o Comex Stat não cobre período anterior; nenhuma fonte histórica pré-1997 foi consultada).
- Se a *descrição*/escopo textual de cada código mudou de sentido ao longo do tempo mesmo mantendo o mesmo número de 8 dígitos (as tabelas de correlação confirmam ausência de *renumeração*, não necessariamente ausência de *redefinição textual* dentro do mesmo código — isso exigiria comparar o texto da TEC vigente em cada época, não feito aqui).
- Cobertura do Rastreador NCM oficial — acesso bloqueado por proteção anti-bot (Cloudflare) nesta sessão; não contornado.
- Anexo I da Resolução Gecex 272/2021 consolidada (TEC vigente) — citado como referência em `docs/METODOLOGIA.md`/`docs/data-sources.md`, mas não obtido/lido diretamente nesta sessão.
- Se a lacuna do comentário em `NCM_BOBINA_QUENTE` (72085100/72085200 não mencionados como excluídos) tem alguma implicação prática — provavelmente não (são códigos de chapa, já fora do escopo por definição de produto), mas não verificado a fundo.

## 12. Status do bloqueante "NCMs vigentes por período" (`docs/METODOLOGIA.md` §15.3)

**PARTIALLY CLOSED**, especificamente para a família HRC (`NCM_BOBINA_QUENTE`):

- Fechado com evidência documental forte (FACT) para 2012–presente.
- Fechado apenas com evidência inferencial (INFERENCE, não FACT) para 1997–2012.
- **Continua OPEN** para: qualquer outra família de produto (vergalhão, explicitamente fora de escopo aqui); confirmação textual de escopo por período (não só numeração); e cobertura do Rastreador NCM oficial.

---

**Reprodutibilidade parcial:** `scripts/research_hrc_ncm_history.py` reproduz as consultas ao Comex Stat (seções 2 e 3). Os documentos oficiais das seções 4 precisam ser buscados manualmente nas URLs citadas (não incluídos no script para não versionar cópias de documentos de terceiros no repositório).
