# IPIA-HRC — Histórico de parâmetros de política de importação (Stage E4)

**Data da investigação original:** 2026-08-26
**Data da 1ª revisão:** 2026-08-26 (mesma sessão, correção AFRMM/antidumping após auditoria externa)
**Data da 2ª revisão (E4b):** 2026-08-26 (mesma sessão, fechamento dirigido do histórico de II/TEC 2012–2022)
**Tipo:** investigação metodológica. **Não** implementa cálculo, **não** altera `ParamsIPIA`, **não** cria estrutura de dados nova.
**Janela investigada:** 2012-01 → presente (decisão Stage E3).
**Escopo de produto:** os 13 NCMs de `NCM_BOBINA_QUENTE` (amostra/referência; esta investigação não altera a constante).

## Legenda de evidência

- **FACT** — lido diretamente numa fonte primária nesta sessão (texto de lei/decreto/decisão no Planalto/STF, ou página oficial gov.br).
- **DOC** — fonte secundária confiável (escritórios de advocacia, LegisWeb, notícias especializadas), sem leitura direta do ato primário nesta sessão.
- **INFERENCE** — conclusão derivada dos fatos acima.
- **UNKNOWN** — não determinado; registrado explicitamente.

---

## Correções após revisão

Esta seção existe para não esconder o histórico da correção, conforme solicitado.

### O que estava errado na versão original

1. **AFRMM 2023 foi classificado como CONTESTADO/UNKNOWN.** Isso refletia corretamente a controvérsia jurídica *tal como ela existia em 2023*, mas a versão original não buscou o desfecho posterior. **O STF julgou o Tema 1368 (ARE 1.527.985) em 03/02/2025** (acórdão publicado 12/02/2025), com tese fixada de que a aplicação das alíquotas integrais do AFRMM a partir da revogação do Decreto 11.321/2022 pelo Decreto 11.374/2023 **não está sujeita à anterioridade tributária**. Fundamento: o Decreto 11.321/2022 foi revogado no mesmo dia em que começaria a produzir efeitos, o que impediu a consolidação de qualquer direito adquirido. **Conclusão corrigida: a alíquota de 8% (não 4%) é a regra válida para o ano de 2023 inteiro**, sem a exceção que a versão original deixou em aberto. Isso está detalhado na seção 2 revisada abaixo.

2. **Antidumping 2018–2023 foi deixado como "não sabemos se a suspensão foi levantada".** Isso estava incompleto: a sequência oficial documentada é **suspensão imediata (2018) → prorrogação da suspensão (2018) → extinção definitiva da medida em janeiro/2020** (Resolução Gecex nº 5/2020), não uma indefinição até 2023. **A versão original também usava a data de vigência nominal de 5 anos (19/01/2023) como se fosse a data real de encerramento, quando a medida já havia sido extinta antes disso, em 2020.** Corrigido na seção 3 abaixo, com a distinção explícita entre direito formalmente calculado e direito efetivamente exigível.

3. **A investigação de 2025 não tinha sido atualizada com o desenvolvimento mais recente.** Incorporada a determinação preliminar positiva de dumping (Parecer nº 1800/2025/MDIC, 23/12/2025) e a prorrogação do prazo da investigação (Circular SECEX nº 100/2025, 24/12/2025) — **sem recomendação de direito provisório**, ou seja, mesmo com a determinação preliminar positiva, nenhum direito estava sendo cobrado até o fim desta investigação.

4. **A seção de cota 2026/2027 tinha detalhes imprecisos** (assumia 9% uniforme dentro da cota e periodicidade "trimestral"). Corrigido com leitura mais precisa do texto da Resolução Gecex 929/2026 (seção 4 abaixo): a alíquota dentro da cota **não é uniforme** — é a alíquota-padrão de cada código (10,8% para três códigos, 9% para 7208.39.10), e o que a cota realmente controla é a alíquota **fora** da cota (25% para todos os quatro). Periodicidade correta: **quadrimestral** (3 sub-períodos de 4 meses no ano de vigência), não trimestral.

A versão original desta seção terminava aqui, concluindo que "II pré-2022 continua sendo o UNKNOWN mais material". **Essa conclusão também precisou de correção** — ver item 5.

5. **(E4b) A suposição implícita de que 10,8%/9% poderiam ter valido desde 2012 estava ERRADA.** A versão anterior registrou isso como INFERENCE fraca ("provável que 10,8%/9% já valessem desde 2012"), mas evidência nova mostra que as alíquotas efetivamente vigentes em 2012 (e ainda em dezembro/2018) eram **diferentes e mais altas**: um patamar de **12%** (com exceção pontual em 10% para 7208.39.10), não 10,8%/9%. **A mudança para 10,8%/9% é resultado de um corte geral e documentado de 10% na Tarifa Externa Comum do Mercosul**, aplicado a partir de novembro/2021 (Resolução GECEX 272/2021) e efetivo por código a partir de 2022-04-01 — não uma continuidade retroativa dos valores atuais. Ver seção 1 revisada, que substitui integralmente a análise anterior.

---

## 1. Imposto de Importação / TEC (Fase 1) — reescrita completa (E4b)

A análise abaixo **substitui integralmente** a versão anterior desta seção, que presumia (incorretamente, por ausência de evidência de mudança) que 10,8%/9% poderiam valer desde 2012. Evidência nova, obtida nesta investigação dirigida, mostra que isso é falso.

### 1.1 Snapshot 2012 (Resolução CAMEX nº 94/2011, vigente desde 2012-01-01)

**SECONDARY_REPRODUCTION** (valores fornecidos por você, atribuídos ao Anexo I da Resolução CAMEX nº 94/2011; **não reproduzidos de forma independente por mim a partir do texto primário nesta sessão** — ver tentativas na subseção 1.1.1):

| ncm | aliquota_2012 | evidence |
|---|---|---|
| 72083700 | 12% | SECONDARY_REPRODUCTION (fornecido) |
| 72083890 | 12% | SECONDARY_REPRODUCTION (fornecido) |
| 72083910 | 10% | SECONDARY_REPRODUCTION (fornecido) — já era exceção |
| 72083990 | 12% | SECONDARY_REPRODUCTION (fornecido) |
| demais 9 códigos | UNKNOWN (valor exato não obtido) | ver 1.1.2 |

#### 1.1.1 Tentativas de obter o Anexo I como fonte primária/PRIMARY

Registro de esforço, para não repetir buscas já esgotadas:

1. Busquei e baixei o HTML de uma reprodução do "Anexo I" (infoconsult.com.br) — arquivo de 5,7MB. **Não continha** linhas tarifárias de 8 dígitos para 7208; continha apenas uma tabela de correlação de 6 dígitos (não utilizável para alíquota).
2. Tentei `taxpratico.com.br/ncm/<código>` (site que indexa alíquota por NCM) — todas as URLs testadas (inclusive uma citada diretamente pelo Google) retornaram HTTP 404 no momento da consulta.
3. Tentei `buscadorncm.com.br` para dois códigos — mostra **apenas a alíquota atual** (9%/10,8%), sem histórico anterior a 2022.
4. Busquei o valor exato ("7208.39.10" + "10%"/"12%" + 2012/2013) diretamente — sem resultado com a granularidade necessária.

**Não seguido além disso**, conforme instruído ("não faça pesquisa jurídica aberta"). **Os valores de 2012 permanecem SECONDARY_REPRODUCTION, não elevados a PRIMARY/FACT nesta sessão.**

#### 1.1.2 Os outros 9 códigos em 2012 — ainda UNKNOWN, com faixa conhecida

Não obtive o valor específico de 2012 para: `72081000, 72082500, 72082610, 72082690, 72082710, 72082790, 72083610, 72083690, 72083810`.

**FACT** (lido diretamente do texto da Resolução CAMEX nº 97/2018, Nota Técnica nº 1/2018, Seção II.2, via reprodução em LegisWeb — citação textual): *"as alíquotas do imposto de importação aplicadas pelo Brasil aos produtos de que trata esse caso variam de 10% a 14%, níveis bastante superiores à alíquota média mundial, que é de 4,7%"*. Esta frase refere-se ao conjunto de NCMs cobertos pela medida antidumping de 2018 (7208.10.00 a 7225.40.90, ou seja, os 13 códigos de bobina + os 4 de chapa + os 2 de aço ligado da posição 7225).

**INFERENCE**: a existência de um **teto de 14%** nessa citação (mais alto que os 12% conhecidos para os 4 códigos confirmados) significa que **não posso presumir que os 9 códigos restantes também estavam em 12%** — alguns poderiam estar em 14%, ou em outro valor dentro da faixa. A própria citação, ao dar uma *faixa* em vez de um número único, é evidência de que a família NÃO era uniforme. **Isto é exatamente o tipo de suposição que a instrução pediu para não fazer silenciosamente.**

**Confirmação negativa útil**: **FACT** — em dezembro/2018, a faixa ainda incluía valores de dois dígitos claramente acima de 10,8% (a saber, até 14%), o que confirma independentemente que **o patamar de 10,8%/9% ainda não existia em 2018** — reforçando que a mudança para 10,8%/9% é posterior, não uma continuidade desde 2012.

### 1.2 Snapshot 2017 (Resolução CAMEX nº 125/2016 / NCM 2017)

**UNKNOWN.** Não foi encontrada, nesta busca dirigida, uma citação com o valor específico de II para os 13 códigos em 2017. Como a citação de dezembro/2018 (acima) já mostra a faixa "10% a 14%" ainda vigente, e nenhuma resolução de alteração de alíquota do II para 7208 (bobina) foi localizada entre 2012 e 2018 em nenhuma das buscas desta ou da revisão anterior, a **INFERENCE razoável é que o regime de 2017 é o mesmo de 2012** (12%/10% para os 4 códigos confirmados; 10–14% não especificado para os demais) — mas isto é INFERENCE por ausência de mudança encontrada, não uma confirmação direta para 2017 especificamente.

### 1.3 Snapshot 2022 e a explicação do "quando e como" (achado principal do E4b)

**FACT** (múltiplas fontes de notícia consistentes, incluindo Agência Brasil/gov.br): o governo brasileiro, em conjunto com o Mercosul, **tornou definitivo um corte geral de 10% na Tarifa Externa Comum**, com cortes tarifários em vigor **desde novembro de 2021** — coincidindo exatamente com a data da **Resolução GECEX nº 272/2021** (19/11/2021).

**INFERENCE, mas com forte suporte aritmético**: este corte geral de 10% explica exatamente a transição observada:

```text
12%  × (1 − 10%) = 10,8%   ✓ bate com o valor atual confirmado
10%  × (1 − 10%) =  9,0%   ✓ bate com a exceção atual confirmada (7208.39.10)
```

**Esta é a resposta a "quando e como"**: as alíquotas não foram "sempre 10,8%/9%" — elas eram **12%/10%** até a Resolução GECEX 272/2021 aplicar um corte linear de 10% sobre a TEC, resultando nos valores atuais. A data de corte é **novembro/2021** (decisão) com efetivação por código em **2022-04-01** (rollout da NCM2022, per `buscadorncm.com.br`) — um intervalo de ~4,5 meses entre decisão e vigência por código que não foi resolvido com precisão de dia nesta sessão (**UNKNOWN residual pequeno**: se algum código já refletia o corte antes de 2022-04-01, ou se todos migraram exatamente nessa data).

**Se o mesmo corte de 10% se aplicou uniformemente a TODOS os 13 códigos** (não só aos 4 confirmados), isso teria efeitos previsíveis também sobre os 9 códigos ainda não confirmados — mas **isto não foi verificado individualmente para eles**, e a existência do teto de 14% em 2018 (seção 1.1.2) mostra que nem todos os códigos da família estavam exatamente em 12% antes do corte, então o valor pós-corte de qualquer código acima de 12% não seria necessariamente 10,8%.

### 1.4 Alterações intermediárias pesquisadas (2012–2022)

Nenhuma alteração de alíquota do II especificamente para os códigos de bobina (7208.10/25/26/27/36/37/38/39) foi localizada entre 2012 e a Resolução GECEX 272/2021, além do corte geral de 10% já descrito. As únicas alterações tarifárias temporárias encontradas na posição 7208 nesse intervalo (Resoluções CAMEX 87/2013 e 21/2014, redução para 2% com cota) miram **7208.51.00/7208.52.00 (chapa, fora da cesta)**, confirmado na Stage E3/seção 3.4 e não revisitado em profundidade nesta execução (instrução: não misturar antidumping/NCM history novamente).

### 1.5 Cota tarifária 2026/2027 (Resolução GECEX 929/2026) — preservado, confirmação oficial mais precisa

**DOC** (LegisWeb, texto da resolução obtido via fonte secundária nesta revisão — mais preciso que a versão original):

| ncm afetado | alíquota dentro da cota | alíquota fora da cota |
|---|---|---|
| 7208.37.00 | 10,8% (alíquota padrão do código, inalterada) | 25% |
| 7208.38.90 | 10,8% (alíquota padrão do código, inalterada) | 25% |
| 7208.39.10 | 9% (alíquota padrão do código, inalterada) | 25% |
| 7208.39.90 | 10,8% (alíquota padrão do código, inalterada) | 25% |

- **Estrutura**: 3 sub-períodos **quadrimestrais** (4 meses cada) dentro do ano de vigência: 26/06/2026–25/10/2026; 26/10/2026–25/02/2027; 26/02/2027–25/06/2027.
- **Vigência total**: 26/06/2026 a 25/06/2027.
- **Volume**: definido por código, igual em cada sub-período (valor exato por código não extraído nesta sessão — apenas a estrutura).
- **Sem acúmulo**: saldo não utilizado num sub-período **não** transporta para o próximo.
- **Critério de alocação**: a ser definido pela SECEX em regulamento complementar — **UNKNOWN** o critério operacional exato (ordem de chegada, licenciamento, etc.).

**Implicação metodológica explícita (não implementada aqui)**: como a cota controla apenas o acesso à alíquota BASE (dentro da cota = alíquota normal do código; fora = 25%), a alíquota **efetiva** de importação para esses 4 códigos, nesse ano específico, **depende de quanto da cota já foi consumido no sub-período** — não é uma constante mensal simples. Modelar isso exigiria saber, mês a mês, o volume acumulado importado sob cada código dentro do sub-período vigente, comparado ao limite da cota — uma dependência de estado (quanto já foi importado), não um parâmetro puramente temporal. **Isso é uma hipótese metodológica adicional que a Fase 5 pediu para não implementar ainda, e que de fato não deveria ser resolvida silenciosamente.**

### 1.6 Tabela final — II (corrigida, substitui a versão anterior)

Períodos consecutivos com a mesma regra consolidados, conforme pedido. Nenhuma linha mensal.

| ncm | valid_from | valid_to | aliquota_ii | legal_basis | evidence_type | confidence |
|---|---|---|---|---|---|---|
| 72083700 | 2012-01-01 | ~2021-11/2022-03 (corte geral, data exata de efetivação por código não confirmada) | 12% | Res. CAMEX 94/2011, Anexo I | SECONDARY_REPRODUCTION | MÉDIA (valor fornecido, não re-derivado do texto primário; consistente com Nota Técnica 1/2018) |
| 72083890 | 2012-01-01 | idem | 12% | Res. CAMEX 94/2011, Anexo I | SECONDARY_REPRODUCTION | MÉDIA |
| 72083990 | 2012-01-01 | idem | 12% | Res. CAMEX 94/2011, Anexo I | SECONDARY_REPRODUCTION | MÉDIA |
| 72083910 | 2012-01-01 | idem | 10% (já era exceção) | Res. CAMEX 94/2011, Anexo I | SECONDARY_REPRODUCTION | MÉDIA |
| 72081000, 72082500, 72082610, 72082690, 72082710, 72082790, 72083610, 72083690, 72083810 | 2012-01-01 | 2022-03-31 | **UNKNOWN** — algo dentro de "10% a 14%" (faixa confirmada em 2018), valor exato por código não determinado | Res. CAMEX 97/2018 / Nota Técnica 1/2018 (só confirma a faixa, não o valor individual) | FACT (da faixa) / UNKNOWN (do valor exato) | BAIXA |
| 72083700, 72083890, 72083990 | 2022-04-01 | presente (exceto sub-períodos fora de cota, ver 1.5) | 10,8% | Res. GECEX 272/2021, Anexo I (após corte geral de 10% na TEC, Res. GECEX 272/2021, decisão nov/2021) | DOC | MÉDIA-ALTA |
| 72083910 | 2022-04-01 | presente (exceto sub-períodos fora de cota, ver 1.5) | 9% | idem | DOC | MÉDIA-ALTA |
| demais 9 códigos | 2022-04-01 | presente | **provavelmente 10,8%** (assumido pela fonte de catálogo original, não reverificado código a código nesta ou na revisão anterior) | Res. GECEX 272/2021, Anexo I | DOC | BAIXA-MÉDIA |
| 72083700, 72083890, 72083910, 72083990 | sub-períodos fora de cota entre 2026-06-26 e 2027-06-25 | — | 25% | Res. GECEX 929/2026 | DOC | MÉDIA (mecanismo confirmado; consumo real da cota não rastreado) |

**Nota sobre a linha "demais 9 códigos, 2012–2022": esta é a lacuna real que permanece.** Não é possível, com a evidência obtida nesta sessão, afirmar um valor único e defensável de II para esses 9 códigos em nenhum mês entre 2012-01 e 2022-03 — apenas que estava em algum ponto entre 10% e 14%.

---

## 2. AFRMM (Fase 2) — corrigido

### 2.1 Regra base (2004–2022-03-24): 25% — inalterado

**FACT** (Planalto, Art. 6º, Lei 10.893/2004, redação original): 25% na navegação de longo curso. Cobre 2012-01 até a alteração de 2022.

### 2.2 Lei nº 14.301/2022 → 8% (a partir de 2022-03-25) — inalterado

**FACT** (Planalto, redação vigente com anotação "Redação dada pela Lei nº 14.301, de 2022") + **DOC** (data exata de vigência, 25/03/2022, após derrubada de veto).

### 2.3 Episódio do desconto de 50% e sua resolução definitiva pelo STF — CORRIGIDO

**FACT** (Planalto): Decreto 11.321/2022 concedia desconto de 50%, vigência a partir de 2023-01-01. **FACT** (Planalto): Decreto 11.374/2023 revogou o anterior, publicado 2023-01-02.

**FACT** (STF, Tema 1368 de Repercussão Geral, leading case ARE 1.527.985): julgamento de mérito em **03/02/2025**, acórdão publicado **12/02/2025**, Relator Min. Luís Roberto Barroso. **Tese fixada**: a aplicação das alíquotas integrais do AFRMM, a partir da revogação do Decreto 11.321/2022 pelo Decreto 11.374/2023, **não está submetida ao princípio da anterioridade tributária** (nem anual, nem nonagesimal). Fundamento citado: o Decreto 11.321/2022 foi revogado no mesmo dia em que produziria efeitos, o que impede a consolidação de direito adquirido pelos contribuintes.

**Conclusão corrigida**: **a alíquota de 8% é a regra juridicamente válida e exigível para o ano-calendário de 2023 inteiro** (não 4%, e não uma mistura ambígua). O desconto de 50% do Decreto 11.321/2022 é tratado, após o Tema 1368, como **nunca tendo produzido efeitos válidos e definitivos** para fins de exigibilidade geral.

**Particularidade a registrar separadamente, sem contaminar o ano inteiro** (conforme pedido): entre **2023-01-01 e 2023-01-02** (os dois dias em que o Decreto 11.321/2022 esteve nominalmente em vigor antes de ser revogado), pode ter havido contribuintes que recolheram AFRMM à alíquota de 4% de boa-fé, e a jurisprudência de casos individuais sobre reembolso desse período específico **não foi pesquisada** (é uma questão de direito tributário processual individual, não uma regra de alíquota geral). Para fins de um índice macro como o IPIA, **isto não deve gerar uma exceção de dois dias na série mensal** — a granularidade mensal do IPIA já absorve esse detalhe.

### 2.4 Situação atual (2024–presente): 8% — inalterado

Sem nova alteração localizada.

### 2.5 Tabela final — AFRMM

| valid_from | valid_to | aliquota | base | legal_basis | confidence | note |
|---|---|---|---|---|---|---|
| 2012-01-01 | 2022-03-24 | 25% | remuneração do transporte aquaviário (longo curso) | Lei 10.893/2004, Art. 6º, redação original | ALTA | — |
| 2022-03-25 | 2022-12-31 | 8% | idem | Lei 14.301/2022 | ALTA | — |
| 2023-01-01 | 2023-01-02 | tecnicamente 4% por 2 dias (decreto depois revogado) | idem | Decreto 11.321/2022 | BAIXA (irrelevante para granularidade mensal) | não modelar como exceção mensal |
| 2023-01-01 | 2023-12-31 | 8% (regra válida e exigível, conforme STF) | idem | Lei 14.301/2022 + Decreto 11.374/2023 + STF Tema 1368 (ARE 1.527.985, j. 03/02/2025) | ALTA | superou a controvérsia registrada na versão original deste documento |
| 2024-01-01 | presente | 8% | idem | Lei 14.301/2022 (sem alteração posterior localizada) | MÉDIA-ALTA | — |

**Nota de sobreposição das duas linhas de 2023**: a linha "4% por 2 dias" e a linha "8% o ano inteiro" não são contraditórias — a primeira registra o que estava *nominalmente escrito* num decreto que durou 48 horas; a segunda registra o que o STF determinou como *efetivamente exigível*. Para o modelo do IPIA, **usar apenas a segunda linha (8%, ano inteiro)**.

---

## 3. Antidumping (Fase 3) — corrigido

### 3.1 Sequência oficial completa 2018–2020

**FACT** (página oficial MDIC, "Medidas em vigor — Laminados a quente") + **DOC** (LegisWeb, Resolução Gecex 5/2020):

| data | ato | efeito |
|---|---|---|
| 2018-01-19 | Resolução CAMEX nº 2/2018 | Aplica direito antidumping definitivo (China e Rússia, valores por produtor/exportador em US$/t) **e suspende sua aplicação imediatamente**, por interesse público |
| 2018-12-10 | Resolução CAMEX nº 97/2018 | Prorroga a suspensão |
| 2019-10-23 | Circular SECEX nº 59/2019 | Registra pedido de reaplicação (retomada da cobrança) |
| 2020-01-15/17 | **Resolução GECEX nº 5/2020** | **Encerra a avaliação de interesse público com a EXTINÇÃO definitiva das medidas antidumping** aplicadas pela Resolução CAMEX 2/2018 |

**Conclusão corrigida**: a medida **nunca chegou a ser efetivamente cobrada** em nenhum momento entre 2018-01-19 e sua extinção em 2020-01. Foi aplicada e suspensa no mesmo ato (2018), a suspensão foi prorrogada (2018), um pedido de reaplicação foi registrado (2019) mas **não foi acolhido** — em vez disso, a medida foi **extinta** (2020).

### 3.2 Direito formalmente calculado vs. efetivamente exigível

| período | direito formalmente calculado | direito efetivamente exigível (relevante para o IPIA) |
|---|---|---|
| 2012-01 → 2018-01-18 | nenhum | **US$ 0/t** |
| 2018-01-19 → 2020-01-17 | SIM — valores específicos por produtor (China: US$44,08 a US$226,58/t; Rússia: US$118,50 e US$207,43/t) | **US$ 0/t (suspenso o tempo todo)** |
| 2020-01-18 → 2025-06-02 | nenhum (extinto) | **US$ 0/t** |
| 2025-06-03 → presente (investigação em curso) | determinação preliminar positiva de dumping (Parecer 1800/2025/MDIC, 23/12/2025), **sem recomendação de direito provisório** | **US$ 0/t** (nenhum direito, provisório ou definitivo, aplicado até a data desta investigação) |

**Para o IPIA, o valor efetivo de antidumping para HRC (China/Rússia) é US$ 0/t em toda a janela 2012–presente até prova em contrário** — isto é agora uma conclusão bem fundamentada (FACT + DOC), não mais uma lacuna de "não sabemos".

### 3.3 Investigação 2025 — situação atual (corrigida)

**DOC** (múltiplas fontes consistentes: LegisWeb, Nasser Advogados):

- Início: Circular SECEX nº 39/2025, publicada 2025-06-03, a pedido de ArcelorMittal Brasil, Gerdau Açominas e Usiminas (petição de 2024-10-30).
- Determinação preliminar positiva de dumping: Parecer/Despacho nº 1800/2025/MDIC, de 2025-12-23.
- **Sem direito provisório recomendado/aplicado** nessa determinação preliminar.
- Circular SECEX nº 100/2025 (2025-12-24): prorroga o prazo de conclusão da investigação por 18 meses a partir do início.
- Em fevereiro de 2026, o Gecex aplicou direito antidumping definitivo para **laminados a frio** (Res. 854/2026) e **laminados revestidos** (Res. 856/2026) da China — **produtos diferentes de HRC**, confirmando que essas decisões não se referem ao nosso escopo.
- Nenhuma resolução definitiva para laminados **a quente** da China foi localizada até a data desta investigação (agosto/2026) — a investigação segue em andamento.

**Não se assume direito definitivo enquanto não houver ato aplicando-o**, conforme instruído.

### 3.4 Medida confirmada fora de escopo (mantido da versão original)

Resolução CAMEX 77/2013 — chapas grossas, NCM 7208.51.00/7208.52.00, África do Sul/Coreia do Sul/China/Ucrânia. Fora de `NCM_BOBINA_QUENTE`.

### 3.5 Tabela final — Antidumping

| origin | exporter | valid_from | valid_to | nominal_value | suspended | effective_value_for_ipia | legal_basis | confidence |
|---|---|---|---|---|---|---|---|---|
| China | Maanshan Iron & Steel Co. Ltd. | 2018-01-19 | 2020-01-17 | US$154,68/t | SIM (o tempo todo) | US$0/t | Res. CAMEX 2/2018; Res. CAMEX 97/2018; Res. GECEX 5/2020 | ALTA |
| China | Bengang Steel Plates Co. Ltd | 2018-01-19 | 2020-01-17 | US$44,08/t | SIM | US$0/t | idem | ALTA |
| China | Baoshan Iron & Steel Co., Ltd | 2018-01-19 | 2020-01-17 | US$77,72/t | SIM | US$0/t | idem | ALTA |
| China | Demais (residual) | 2018-01-19 | 2020-01-17 | US$226,58/t | SIM | US$0/t | idem | ALTA |
| Rússia | JSC Severstal | 2018-01-19 | 2020-01-17 | US$118,50/t | SIM | US$0/t | idem | ALTA |
| Rússia | Demais (residual) | 2018-01-19 | 2020-01-17 | US$207,43/t | SIM | US$0/t | idem | ALTA |
| China | (todas) | 2020-01-18 | 2025-06-02 | nenhuma medida | n/a | US$0/t | Res. GECEX 5/2020 (extinção) | ALTA |
| China | (investigação, ainda sem produtor/exportador específico definido) | 2025-06-03 | presente | determinação preliminar positiva, sem direito provisório | n/a (nenhum direito aplicado) | US$0/t | Circular SECEX 39/2025; Parecer 1800/2025/MDIC; Circular SECEX 100/2025 | MÉDIA-ALTA |

Não foram criadas linhas para períodos sem qualquer medida (2012–2018), conforme instruído.

---

## 4. Modelo temporal mínimo recomendado (Fase 5 — não implementado)

Mantida a recomendação da versão original: **três estruturas simples e específicas** (II por NCM/período; AFRMM por período sem NCM; antidumping por origem/exportador/período com campo `suspended`), não uma tabela genérica única. A correção desta revisão reforça essa recomendação: o campo `suspended` (ou equivalente `effective_value` separado de `nominal_value`) provou ser **indispensável**, não opcional — sem ele, o modelo teria atribuído US$44–226/t de antidumping para 2018–2020, quando o valor efetivo sempre foi zero.

Novo ponto que a correção revelou: para a cota GECEX 929/2026, um modelo puramente temporal (`valid_from`/`valid_to`/`value`) **não é suficiente** — seria necessário um componente de estado (consumo acumulado da cota no sub-período). Isso é uma dimensão adicional de complexidade que a Fase 5 original não previa e que fica registrada aqui como algo a decidir antes de qualquer implementação que cubra 2026 em diante para os 4 códigos afetados.

---

## 5. Limitações remanescentes

- **II/TEC 2012–2022-03 para 4 códigos (72083700, 72083890, 72083910, 72083990)**: valor conhecido (12%/10%) apenas como **SECONDARY_REPRODUCTION** — não re-derivado do texto primário da Res. CAMEX 94/2011 por mim nesta sessão, apesar de tentativas genuínas (seção 1.1.1). Corroborado indiretamente por a Nota Técnica 1/2018 confirmar que a família ainda estava fora do patamar 10,8%/9% em dezembro/2018.
- **II/TEC 2012–2022-03 para os outros 9 códigos**: **UNKNOWN quanto ao valor exato** — apenas uma faixa (10% a 14%) é conhecida (FACT), não o valor específico de cada código. Esta é a lacuna real remanescente, não uma simples ausência de confirmação de estabilidade como a versão anterior sugeria.
- Data exata (dia) da transição de 12%/10% para 10,8%/9% por código: não determinada com precisão — sabe-se que a decisão do corte geral é de novembro/2021 e que ao menos um código já refletia o novo valor em 2022-04-01, mas não se todos migraram no mesmo dia.
- Alocação operacional da cota GECEX 929/2026: delegada à SECEX, não pesquisada.
- Reembolsos/litígios individuais dos 2 dias de vigência do Decreto 11.321/2022: não pesquisado (irrelevante para modelagem mensal).

---

## 6. Status final por parâmetro

1. **AFRMM 2012–presente: PARTIALLY CLOSED.** Fechado com FACT para 2012–2022 (25%) e 2022–presente incluindo 2023 (8%, após STF Tema 1368). Resta apenas o detalhe irrelevante-para-mensal dos 2 dias de janeiro/2023.
2. **II 2012–presente: PARTIALLY CLOSED — reavaliado, mais preciso que a versão anterior.** Fechado (DOC/MÉDIA-ALTA) para 2022-04–presente para 4 dos 13 códigos (10,8%/9%, mais a cota 2026/27); fechado (DOC/BAIXA-MÉDIA, não reverificado individualmente) para os outros 9 no mesmo período. Para 2012–2022-03: fechado com SECONDARY_REPRODUCTION/MÉDIA para os 4 códigos confirmados (12%/10%, **não** 10,8%/9% como a versão anterior chegou a admitir como hipótese); **OPEN** para os outros 9 códigos (UNKNOWN o valor exato, apenas a faixa 10–14% é FACT).
3. **Antidumping 2012–presente: CLOSED** no sentido prático que interessa ao IPIA. Inalterado desta revisão (não repesquisado, conforme instruído).
4. **Cota 2026/27: CLOSED quanto ao mecanismo e às alíquotas**; **OPEN quanto à modelagem**. Inalterado.
5. **Meses/códigos ainda com parâmetro UNKNOWN**: todos os meses de 2012-01 a 2022-03, **apenas para os 9 códigos não confirmados** (`72081000, 72082500, 72082610, 72082690, 72082710, 72082790, 72083610, 72083690, 72083810`) — valor exato de II desconhecido, só a faixa 10–14%. Para os outros 4 códigos nesse mesmo período, o valor é conhecido por SECONDARY_REPRODUCTION (12%/10%), não mais UNKNOWN, mas também não é FACT/PRIMARY. Nenhum mês tem AFRMM ou antidumping como UNKNOWN.
6. **É possível implementar um primeiro Historical Import Policy Model 2012-presente sem usar parâmetros atuais retroativamente?** **Sim para AFRMM e antidumping.** **Para II, sim para 4 dos 13 códigos** (usando 12%/10% pré-2021-11 e 10,8%/9% depois — precisamente o que a correção deste documento existe para garantir que NÃO seja invertido). **Para os outros 9 códigos, não com confiança alta** — qualquer valor usado para 2012–2022-03 seria uma suposição dentro de uma faixa conhecida (10–14%), não um valor confirmado.
7. **Simplificação metodológica que ainda exige decisão sua**: (a) para os 4 códigos confirmados, aceitar SECONDARY_REPRODUCTION (12%/10%) como base documentada mesmo sem verificação PRIMARY direta, ou insistir em obter o Anexo I completo antes de publicar; (b) para os 9 códigos não confirmados, escolher entre assumir 12% por semelhança de padrão (risco: podem estar em até 14%), marcar `A_CONFIRMAR` sem valor (bloqueia publicação 2012-2022 para esses códigos), ou limitar a janela publication-grade de II a 2022-04–presente mesmo tendo a cesta NCM aprovada desde 2012 (Stage E3) — um descompasso entre os dois blockers que também é uma decisão sua; (c) se/como modelar o consumo de cota da Res. GECEX 929/2026.

---

**Arquivos modificados nesta revisão (E4b):** apenas este documento (`docs/research/hrc_import_policy_history.md`) — seção "Correções após revisão" ampliada com o item 5, e seção 1 (II/TEC) reescrita por completo. Nenhum script novo criado. Nenhum arquivo de produção tocado. AFRMM, antidumping e a estrutura da cota 2026/27 não foram repesquisados, conforme instruído.

---

## 7. Decisão aprovada — janela publication-grade / experimental (Option C)

**Decisão registrada nesta sessão, após avaliação Level 3 formal.** Ver `docs/adr/0009-ipia-hrc-janela-publication-grade-historical-import-policy.md` para o registro completo (contexto, alternativas, consequências).

- **Publication-grade**: `2022-04-01 → presente`. Only this window is eligible to feed an official IPIA-HRC V2 series. Todos os parâmetros necessários (NCM — Stage E3 —, II/TEC, AFRMM, antidumping) estão confirmados com evidência suficiente nesta janela.
- **Historical experimental**: `2012-01-01 → 2022-03-31`. Permanece explicitamente separado da série oficial, **nunca concatenado silenciosamente**, porque o II individual de 9 dos 13 NCMs (`72081000, 72082500, 72082610, 72082690, 72082710, 72082790, 72083610, 72083690, 72083810`) não está comprovado nesse período — apenas uma faixa (10%–14%) é conhecida.
- `1997–2011` permanece fora de escopo desta e de qualquer implementação futura por ora (decisão já tomada na Stage E3, não revisitada aqui).
- Nenhum valor de II é atribuído silenciosamente aos 9 códigos não comprovados no período experimental — o modelo implementado (`steel_indicator/parameters/trade_policy.py`) retorna `UNKNOWN` explícito para esses casos, não uma tarifa inferida.
- Esta decisão **não é reaberta** nesta ou em tarefas subsequentes de implementação sem uma nova decisão Level 3 explícita.

---

## 8. Addendum (sprint "Import Policy Evidence Hardening", 2026-08-28)

**Tipo:** validação empírica com evidência primária nova. **Não** altera
`resolver_ii`, policy tables de produção, vintages, publication status,
PPI, IPIA ou `VERSAO_METODOLOGIA`. Registro completo, com tabelas e
contrafactual quantificado, em
`docs/validation/hrc_import_policy_evidence_hardening.md` — esta seção é
só o resumo que fecha o loop com a Seção 6 acima.

**Evidência primária Tier 1 nova obtida**: planilha oficial consolidada
gov.br/mdic/camex ("Anexos I a X da Resolução Gecex nº 272/2021",
atualizada até a Resolução Gecex nº 812/2025 e nº 941/2026), baixada e
parseada ao vivo. Duas descobertas verificadas (VERIFIED, confirmadas em
duas abas independentes da mesma planilha oficial):

1. **4 dos 13 NCMs têm alíquota errada em produção para o regime
   2022-04+**: `72082610`, `72082710`, `72083610`, `72083810` estão
   codificados em 10,8% (`_ALIQUOTA_2022_TODOS_OS_13`); a evidência
   oficial confirma **9%** — mesma exceção de "limite mínimo de
   elasticidade 275/355 MPa" já corretamente aplicada a `72083910`, mas
   não replicada a esses 4 códigos na mesma posição estrutural `.10`.
2. **2 NCMs sujeitos a uma elevação tarifária não modelada**: `72082690`
   e `72082790` estão em **25%** (não 10,8%) desde 2026-02-26 até
   2027-02-25 (Resolução Gecex nº 865/2026) — mecanismo diferente e mais
   simples que a cota 929/2026 já modelada (sem sub-períodos, sem
   componente intra-cota), completamente ausente de `trade_policy.py`.

**O que a Seção 1.1.2/1.6 acima continua sem resposta**: o valor exato de
II para os 9 códigos não confirmados em 2012-2022-03 **não foi
determinado** nesta nova investigação — o mesmo esforço de busca pelo
Anexo I da Resolução CAMEX 94/2011 (fonte primária de 2012) não teve
sucesso adicional. Uma hipótese estrutural nova (INFERRED, não VERIFIED)
foi registrada no documento de validação: a mesma divisão `.10`
(exceção)/`.90` (padrão) confirmada no regime atual, combinada com
`72083910` já ser a exceção conhecida em 2012 (10% vs. 12%), sugere que
os outros 4 códigos `.10` da cesta provavelmente também eram 10% em 2012
(não 12%) — mas isso não é promovido a evidência suficiente para
publicação.

**Cota GECEX 929/2026**: volumes exatos por sub-período (KG), antes
`UNKNOWN`, agora extraídos da mesma planilha oficial (Anexo IX-DCC) — ver
`docs/validation/hrc_import_policy_evidence_hardening.md` Seção 10. O
mecanismo de alocação operacional (SECEX) continua não localizado
publicamente.

**Contrafactual quantificado** (mesma função de produção
`agregar_ipia_hrc_multi_ncm_mensal`, rodada com a policy candidata via
monkeypatch temporário, nunca modificando `trade_policy.py`): as duas
correções **não fecham nenhum mês UNKNOWN/EXPERIMENTAL** — `publication_
status` contrafactual é idêntico ao atual nos 90 meses testados. O que
muda é o **valor** do PPI em 48 dos 78 meses calculáveis (-0,49% a
+5,60%), incluindo **19 meses já publicados na série OFFICIAL congelada**
(2022-04–2023-12, impacto máximo -0,49%).

**Status atualizado**: item 5 da Seção "Correções após revisão" original
(a suposição de que 10,8%/9% valeriam desde 2012 estava errada) permanece
válido e não é afetado por este addendum. O addendum é ortogonal: sobre a
precisão do valor **dentro** do regime 2022-04+ já identificado como
correto em data de transição, não sobre a data de transição em si.

**Recomendação registrada no documento de validação**: `B — PARTIAL
IMPLEMENTATION` — as duas correções do regime atual são candidatas fortes
a uma futura decisão Level 3; a lacuna 2012-2022-03 permanece sem
evidência suficiente para qualquer promoção.
