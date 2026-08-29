# IPIA-HRC — Import Policy Evidence Hardening

**Status: RESEARCH + VALIDATION ONLY — não implementa nenhuma mudança.**
`resolver_ii`, as policy tables de produção (`steel_indicator/parameters/
trade_policy.py`), vintages, publication status, PPI, IPIA e
`VERSAO_METODOLOGIA` permanecem exatamente como estavam antes desta etapa.

**⚠️ ACHADO QUE EXIGE ATENÇÃO — candidato a bug de produção, aguardando
decisão Level 3.** Ver Seção "Executive conclusion" e Seção 7. Nenhuma
correção foi aplicada em `src/`.

Reproduzir: `docker build -t steel-indicator-dev .` seguido de
`docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/validar_hrc_import_policy_evidence.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`). O script baixa a
mesma planilha oficial usada como evidência nesta etapa
(ver Seção 5 — Evidence hierarchy) e reproduz o contrafactual.

## Question

> Podemos determinar corretamente a alíquota de II/TEC aplicável a cada
> NCM HRC e período histórico sem usar aproximações? Podemos determinar
> de forma reproduzível a situação da cota/regra comercial recente que
> hoje impede classificação segura de alguns volumes?

## 1. Executive conclusion

- **13 de 13 NCMs da cesta oficial tiveram sua alíquota atual (2022-04+)
  verificada** contra evidência primária Tier 1 (planilha oficial
  consolidada gov.br/mdic/camex, "Anexos I a X da Resolução Gecex nº
  272/2021", atualizada até a Resolução Gecex nº 812/2025) — confirmada de
  forma independente em **duas** abas da mesma planilha (Anexo I - TEC e
  Anexo II - Diferentes da TEC).
- **Descoberta principal (produção): 4 dos 13 NCMs estão codificados com a
  alíquota errada no regime 2022-04+.** `steel_indicator/parameters/
  trade_policy.py` (`_ALIQUOTA_2022_TODOS_OS_13`) atribui 10,8% a
  `72082610`, `72082710`, `72083610`, `72083810` — a evidência oficial diz
  **9%** para os quatro (mesma exceção "limite mínimo de elasticidade
  275/355 MPa" já corretamente aplicada a `72083910`, mas não replicada
  aos outros 4 códigos na mesma posição estrutural `.10`).
- **Descoberta secundária (produção): 2 NCMs sujeitos a uma elevação
  tarifária não modelada.** `72082690` e `72082790` estão em 25% (não
  10,8%) desde 2026-02-26 até 2027-02-25 (Resolução Gecex nº 865/2026,
  Anexo IX-DCC) — um mecanismo **sem cota** (ao contrário dos 4 códigos já
  cobertos por `_NCMS_COM_COTA_929_2026`), que a produção não reconhece em
  nenhum lugar.
- **Cobertura temporal/em KG**: as duas correções cobrem **2022-04-01 em
  diante** (o regime atual, publication-grade), nunca o histórico
  2012–2022-03. Em volume: os 4 NCMs de alíquota corrigida somam **2,02%**
  do KG total importado desde 2022-04 (mas chegam a 33,8% do volume de um
  mês específico — dez/2024); os 2 NCMs da elevação DCC somam **35,3
  milhões de kg** só em mar/2026 (mês em que 72082690 sozinho respondeu
  por ~29,3M kg).
- **Redução de UNKNOWN: zero.** Nenhuma das duas correções fecha um mês
  antes `UNKNOWN`/`EXPERIMENTAL` — ambas corrigem o **valor** de meses já
  calculáveis, nunca a **cobertura**. `publication_status` contrafactual é
  idêntico ao atual em todos os 90 meses testados (51 PUBLICATION_GRADE +
  27 EXPERIMENTAL + 12 UNKNOWN, current e candidate).
- **Impacto quantificado no PPI**: 48 dos 78 meses calculáveis mudam de
  valor sob a policy candidata (nunca de status), variação de **-0,49% a
  +5,60%**. Dentro da janela **já publicada e congelada** OFFICIAL
  (2022-04 a 2023-12), **19 meses são afetados**, todos com impacto pequeno
  (máximo -0,49%, out/2023).
- **2012–2022-03 (9 NCMs não confirmados)**: nenhuma evidência primária
  nova foi obtida nesta etapa para o valor exato. Um padrão estrutural
  forte (a mesma divisão "posição `.10` = exceção MPa reduzida, `.90` =
  padrão") foi confirmado no regime atual e permite uma **hipótese
  INFERRED** razoável (4 dos 9 códigos provavelmente 10%→9%, 5
  provavelmente 12%→10,8%) — mas isso **não é promovido** a VERIFIED nem
  usado no contrafactual principal.
- **Cota GECEX 929/2026**: volumes exatos por sub-período agora
  disponíveis (Tier 1). Volume observado agregado em jul/2026 sozinho
  **já excede o teto do sub-período inteiro** para 3 dos 4 códigos (ex.:
  72083990: 39,98M kg importados em um mês vs. 16,44M kg de cota para os 4
  meses) — classificação: **B — PARTIALLY OBSERVABLE**.
- **2020-11**: reclassificado com evidência reprodutível como
  **TRUE_ZERO** (3 consultas independentes, 100% consistentes).
- **Evidence strength: MODERATE-STRONG** para o regime atual (2022-04+,
  Tier 1, duas fontes independentes convergentes); **WEAK/INFERRED** para
  2012-2022-03 (nenhuma mudança de status desta etapa).
- **Recommendation: B — PARTIAL IMPLEMENTATION** (ver Seção 13) — mas
  **NADA foi implementado nesta etapa**, conforme escopo.

## 2. NCM inventory

Extraído diretamente de `NCM_BOBINA_QUENTE` (`src/indices_setoriais.py`):

| NCM | Categoria (código) | Descrição (Anexo I oficial) |
|---|---|---|
| 72081000 | com_relevo | Em rolos, apresentando motivos em relevo |
| 72082500 | decapada | Decapada, espessura ≥4,75mm |
| 72082610 | decapada | Decapada, 3mm≤espessura<4,75mm, limite elástico ≥355 MPa |
| 72082690 | decapada | Decapada, 3mm≤espessura<4,75mm, "Outros" |
| 72082710 | decapada | Decapada, espessura<3mm, limite elástico ≥275 MPa |
| 72082790 | decapada | Decapada, espessura<3mm, "Outros" |
| 72083610 | nao_decapada | Não decapada, espessura>10mm, limite elástico ≥355 MPa |
| 72083690 | nao_decapada | Não decapada, espessura>10mm, "Outros" |
| 72083700 | nao_decapada | Não decapada, 4,75mm≤espessura≤10mm |
| 72083810 | nao_decapada | Não decapada, 3mm≤espessura<4,75mm, limite elástico ≥355 MPa |
| 72083890 | nao_decapada | Não decapada, 3mm≤espessura<4,75mm, "Outros" |
| 72083910 | nao_decapada | Não decapada, espessura<3mm, limite elástico ≥275 MPa |
| 72083990 | nao_decapada | Não decapada, espessura<3mm, "Outros" |

13 códigos confirmados — nenhuma mudança na cesta.

## 3. Historical NCM validity

**Não repesquisado nesta etapa** — já `CLOSED` para a janela de publicação
2019-02+ desde a Stage E3/ADR 0009 (`docs/METODOLOGIA.md` §15.3): tabelas
de correlação oficiais MDIC/Camex (2012↔2017, 2017↔2022) confirmam **zero
mudanças na posição 7208** desde 2012. A tabela oficial de correlação
NCM 2017↔2022 (`Tabela_de_Correlacao_NCM_2017_2022_Atualizada.pdf`,
gov.br/mdic) foi localizada nesta sessão como referência adicional, mas
não foi necessário reabrir a questão — decisão já fechada permanece
válida.

## 4. Historical II reconstruction

### 4.1 Regime atual (2022-04-01+) — VERIFIED nesta etapa

Fonte: planilha oficial "Anexo I - TEC" e "Anexo II - Diferentes da TEC"
(gov.br/mdic/camex, ver Seção 5). Tabela completa por NCM:

| NCM | Alíquota oficial (Anexo I/II) | Alíquota em produção | Status |
|---|---:|---:|---|
| 72081000 | 10,8% | 10,8% | ✓ correto |
| 72082500 | 10,8% | 10,8% | ✓ correto |
| **72082610** | **9%** | 10,8% | **✗ CORRIGIR** |
| 72082690 | 10,8% (base) — **25% desde 2026-02-26** | 10,8% (sempre) | ✓ base correta / **✗ elevação DCC não modelada** |
| **72082710** | **9%** | 10,8% | **✗ CORRIGIR** |
| 72082790 | 10,8% (base) — **25% desde 2026-02-26** | 10,8% (sempre) | ✓ base correta / **✗ elevação DCC não modelada** |
| **72083610** | **9%** | 10,8% | **✗ CORRIGIR** |
| 72083690 | 10,8% | 10,8% | ✓ correto |
| 72083700 | 10,8% (base) — cota 929/2026 | 10,8% + UNKNOWN em cota | ✓ correto |
| **72083810** | **9%** | 10,8% | **✗ CORRIGIR** |
| 72083890 | 10,8% (base) — cota 929/2026 | 10,8% + UNKNOWN em cota | ✓ correto |
| 72083910 | 9% (base) — cota 929/2026 | 9% + UNKNOWN em cota | ✓ correto |
| 72083990 | 10,8% (base) — cota 929/2026 | 10,8% + UNKNOWN em cota | ✓ correto |

### 4.2 Regime histórico (2012-01 a 2022-03-31) — sem evidência nova

Não localizada evidência primária adicional nesta etapa (mesmo esforço de
busca do Stage E4b, sem sucesso adicional em novas tentativas — Anexo I
da Resolução CAMEX 94/2011 continua não reproduzido de fonte primária).
Permanece exatamente como já registrado em
`docs/research/hrc_import_policy_history.md`:

| NCM | valid_from | valid_to | II | Evidence quality |
|---|---|---|---:|---|
| 72083700, 72083890, 72083990 | 2012-01-01 | 2022-03-31 | 12% | SECONDARY_REPRODUCTION |
| 72083910 | 2012-01-01 | 2022-03-31 | 10% | SECONDARY_REPRODUCTION |
| demais 9 códigos | 2012-01-01 | 2022-03-31 | **UNKNOWN** (faixa 10%-14%) | FACT (só a faixa) |

**Hipótese estrutural nova (INFERRED, não VERIFIED)**: a descoberta do
padrão `.10`=exceção/`.90`=padrão no regime atual, combinada com o fato de
que a mesma exceção já existia em 2012 para `72083910` (10% vs. 12% dos
códigos "padrão"), sugere que os outros 4 códigos `.10` da cesta
(`72082610`, `72082710`, `72083610`, `72083810`) **provavelmente**
também eram 10% (não 12%) em 2012-2022-03, e os 5 restantes (`72081000`,
`72082500`, `72082690`, `72082790`, `72083690`) **provavelmente** eram
12%. Suporte adicional: `12%×0,9=10,8%` e `10%×0,9=9%` batem exatamente
com o corte linear de 10% da TEC (Res. GECEX 272/2021) já documentado.
**Esta hipótese não foi promovida nem usada no contrafactual principal**
— é INFERRED (correlação estrutural, não confirmação direta para o
período histórico específico), registrada aqui só para pesquisa futura.

## 5. Evidence hierarchy

| Fonte | Tier | Formato | Status |
|---|---|---|---|
| Planilha oficial consolidada, gov.br/mdic/camex ("Anexos I a X da Resolução Gecex nº 272/2021", atualizada até Res. Gecex nº 812/2025 e nº 941/2026) | **Tier 1** | .xlsx estruturado | **VERIFIED** — baixada e parseada ao vivo nesta sessão |
| Tabela de correlação NCM 2017↔2022 (gov.br/mdic) | Tier 1 | PDF/.xlsx | localizada, não precisou ser reaberta (Seção 3) |
| Resolução CAMEX nº 94/2011, Anexo I (2012) | Tier 1 (não acessado) | tentado, não obtido | continua SECONDARY_REPRODUCTION |
| Nota Técnica nº 1/2018/COPOL (faixa 10%-14%) | Tier 1/2 | citação | inalterado desta etapa |
| LegisWeb, Normasbrasil, Infoconsult (texto de resoluções) | Tier 2-3 | HTML | só para localizar/confirmar contexto, nunca como valor final de alíquota |
| Portal Único Siscomex — Consulta histórica NCM (`portalunico.siscomex.gov.br/classif`) | Tier 1 (SPA, API não documentada publicamente) | tentado (404/401 em endpoints testados) | não acessado nesta sessão — ver Seção 12 |

**Nenhuma fonte Tier 3 foi usada como evidência final de alíquota** — só
para localizar/contextualizar documentos, conforme exigido.

## 6. Remaining unknown tariffs

- **9 NCMs, 2012-01 a 2022-03-31**: valor exato de II continua UNKNOWN
  (só a faixa 10%-14% é FACT). Hipótese INFERRED registrada na Seção 4.2,
  não promovida.
- **Data exata (dia) da transição 2021-11→2022-04 por código**: continua
  não determinada com precisão de dia (já registrado no research doc
  original).
- **Alocação operacional da cota 929/2026** (quem recebe a preferência
  dentro do sub-período): delegada à SECEX em regulamento complementar,
  não localizada nesta sessão (ver Seção 10).

## 7. Current vs candidate coverage

| Métrica | Current | Candidate |
|---|---:|---:|
| UNKNOWN | 12 | 12 |
| EXPERIMENTAL | 27 | 27 |
| PUBLICATION_GRADE | 51 | 51 |
| **Total meses testados** | **90** | **90** |

**Zero mudança de cobertura.** As correções encontradas nesta etapa não
fecham nenhum mês `UNKNOWN`/`EXPERIMENTAL` — elas corrigem o **valor**
calculado em meses que já eram calculáveis. Isso é uma resposta direta e
honesta à pergunta principal do sprint: a evidência nova encontrada
**não** resolve a lacuna histórica de 2012-2022-03 (o gargalo real
continua lá); ela corrige um erro de codificação no regime que já era
tratado como "resolvido".

## 8. Current vs candidate publication status

Nenhum mês muda de `publication_status` (Seção 7). O que muda é
`ppi_rs_t` em 48 dos 78 meses calculáveis — ver tabela completa em
`data/processed/validation/hrc_import_policy_evidence/contrafactual_comparacao.csv`.
Maiores desvios:

| Mês | `publication_status` | Δ PPI (candidate vs. current) | total_kg do mês |
|---|---|---:|---:|
| 2026-03 | PUBLICATION_GRADE (import); PROVISIONAL (composto) | **+5,60%** | 72.197.254 |
| 2023-04 | PUBLICATION_GRADE (**OFFICIAL, já publicado**) | -0,49% | 27.674.422 |
| 2024-12 | PUBLICATION_GRADE (PROVISIONAL, composto) | -0,47% | 9.714.513 |
| 2022-06 | PUBLICATION_GRADE (**OFFICIAL, já publicado**) | -0,39% | 3.213.025 |
| 2026-05 | PUBLICATION_GRADE (PROVISIONAL, composto) | -0,23% | 44.843.420 |

## 9. Months potentially recovered

**Zero meses recuperados de UNKNOWN/EXPERIMENTAL para um status melhor.**
Isso contraria a expectativa inicial do sprint (§13 esperava alguma
redução de UNKNOWN) — a evidência nova encontrada resolveu um problema
diferente do que se buscava: não uma lacuna de cobertura, e sim um erro
de valor num regime já coberto. Reportado com transparência, não
maquiado como sucesso parcial de cobertura.

## 10. 2026 quota investigation

**Instrumento legal**: Resolução Gecex nº 929, de 25/06/2026 (altera
Anexo IX da Res. Gecex nº 272/2021).

**NCMs afetadas**: `72083700`, `72083890`, `72083910`, `72083990` (já
modelados em produção) — **mais** `72082690` e `72082790`, afetados por
um instrumento **diferente e anterior** (Resolução Gecex nº 865/2026,
24/02/2026), sem mecanismo de cota (elevação simples e incondicional).

**Vigência**: 929/2026 — 26/06/2026 a 25/06/2027, em 3 sub-períodos
quadrimestrais. 865/2026 — 26/02/2026 a 25/02/2027, vigência única, sem
sub-períodos.

**Quantidade da cota (929/2026)** — agora VERIFIED, extraída diretamente
da fonte oficial (tabela completa em `cota_929_2026_volumes.csv`):

| NCM | Sub-período 1 (26/06–25/10/2026) | Sub-período 2 (26/10/2026–25/02/2027) | Sub-período 3 (26/02–25/06/2027) |
|---|---:|---:|---:|
| 72083700 | 899.250 kg | 899.250 kg | 899.249 kg |
| 72083890 | 2.177.597 kg | 2.177.596 kg | 2.177.596 kg |
| 72083910 | 6.663.744 kg | 6.663.744 kg | 6.663.744 kg |
| 72083990 | 16.442.803 kg | 16.442.803 kg | 16.442.803 kg |

**Tarifa intra-cota**: alíquota padrão de cada código (10,8% ou 9% —
inalterada). **Tarifa extra-cota**: 25% para os quatro. **865/2026** (72082690/72082790): 25% incondicional, sem componente intra-cota.

**Mecanismo de consumo**: não rastreado publicamente por este pipeline —
sem acesso a licença/declaração individual.

**Forma oficial de acompanhamento / frequência**: não localizada nesta
sessão (mesma lacuna já registrada — "delegada à SECEX, não pesquisada").

**Acesso público ao saldo consumido/restante**: não localizado.

## 11. Questão central da cota (§16)

> É possível determinar, para cada mês, qual parcela do volume entrou
> dentro da cota e qual parcela entrou fora dela?

**Não, não com precisão mensal/por-fluxo — mas agora podemos dizer algo
quantitativo que antes não podíamos.** Comparando o volume agregado real
(Comex Stat, todas as origens) do único mês inteiro disponível dentro do
1º sub-período (jul/2026) contra o teto oficial do sub-período inteiro (4
meses):

| NCM | Volume agregado, jul/2026 (1 mês) | Cota do sub-período (4 meses) | Jul/2026 sozinho já excede? |
|---|---:|---:|---|
| 72083700 | 2.119.692 kg | 899.250 kg | **Sim, 2,36×** |
| 72083890 | 10.159.720 kg | 2.177.597 kg | **Sim, 4,67×** |
| 72083910 | 0 kg | 6.663.744 kg | Não |
| 72083990 | 39.980.837 kg | 16.442.803 kg | **Sim, 2,43×** |

Para 3 dos 4 códigos, o volume observado **num único mês** já ultrapassa
o teto de **todo o sub-período de 4 meses**. Isso não prova a divisão
exata dentro/fora de cota (não temos data de desembaraço por declaração,
nem o critério de alocação da SECEX), mas é evidência forte de que uma
fração substancial do volume desses códigos está, estruturalmente,
entrando fora da cota (25%) — **não é razoável assumir que a maior parte
do volume observado está pagando a alíquota preferencial**. Sem a fonte
de alocação da SECEX, **não podemos ir além disso**.

**Nunca assumimos `first imports = quota` nem qualquer regra FIFO sem
fonte oficial** — o que está acima é uma comparação de totais agregados,
não uma alocação por embarque.

## 12. Classificação do gap 2026 (§18)

**B — PARTIALLY OBSERVABLE.**

O mecanismo, os NCMs, a vigência e agora os volumes exatos da cota são
públicos e VERIFIED (Seção 10). O que falta é **puramente a alocação
operacional** (qual declaração específica consome qual parcela da cota) —
isso está, pela própria resolução, delegado à SECEX em regulamento
complementar não localizado nesta sessão. Uma tentativa de sondar a API
não documentada do Portal Único Siscomex (`portalunico.siscomex.gov.br/
classif`) confirmou que existe infraestrutura real (respostas 401/404
estruturadas, não timeout/bloqueio), mas os endpoints corretos não foram
identificados sem documentação de API — não seguido além disso, conforme
"não torne o pipeline frágil" (Sec.24 do sprint).

## 13. 2020-11 technical missing investigation

Três consultas independentes ao Comex Stat (duas chamadas idênticas nesta
sessão + o cache de uma execução anterior desta mesma sessão, em janelas
de busca diferentes: 2020-2021, 2012-2026) **concordam: zero linhas para
2020-11 em todos os 13 NCMs e todos os países.**

**Classificação: TRUE_ZERO.** Reproduzível (não é instabilidade de API).
Corrobora com o padrão mais amplo de 2020: junho/2020 (55t), agosto/2020
(1.098t) e outubro/2020 (315t) já mostravam volume extremamente baixo
(documentado no sprint de liquidez/concentração como o ano de maior
instabilidade, choque COVID). Um mês inteiro sem nenhuma importação de
HRC de nenhuma origem é uma leitura econômica plausível dentro desse
contexto, não um indício isolado de falha de coleta.

**Correção ao Missing Data Audit anterior**: o documento
`docs/validation/ipia_hrc_missing_data_audit.md` registrou esta situação
como possível `A_TECHNICAL_MISSING` "pendente de reconfirmação", citando
uma consulta anterior que teria mostrado volume positivo. Essa citação
não foi, na verdade, verificada rigorosamente naquele momento — a
reinvestigação desta etapa não encontrou nenhuma evidência de volume
positivo para 2020-11 em nenhuma consulta, cacheada ou ao vivo. **Não se
recomenda mais reconfirmação — a classificação TRUE_ZERO é considerada
fechada.**

**Nenhuma imputação foi feita.** O mês permanece como está na fonte: sem
registro.

## 14. Conflicts / unresolved issues

| NCM | Período | Fonte A | Fonte B | Conflito |
|---|---|---|---|---|
| 72082610, 72082710, 72083610, 72083810 | 2022-04+ | `trade_policy.py` (produção): 10,8% | Anexo I/II oficial (gov.br/mdic): 9% | **Resolvido nesta etapa a favor da Fonte B** (Tier 1, mais específica, duas abas independentes concordam) — candidato registrado, produção **não alterada** |
| 72082690, 72082790 | 2026-02-26+ | `trade_policy.py`: 10,8% (sem registro de elevação) | Anexo IX-DCC oficial: 25% (Res. 865/2026) | **Resolvido a favor da Fonte B** — candidato registrado, produção **não alterada** |
| 9 NCMs restantes | 2012-2022-03 | Faixa 10%-14% (Nota Técnica 1/2018) | Hipótese estrutural INFERRED (10% ou 12%, Seção 4.2) | **Não resolvido** — INFERRED não promovida a VERIFIED |

Nenhum outro conflito identificado.

## 15. Recommendation

**B — PARTIAL IMPLEMENTATION.**

- A correção de alíquota 2022-04+ (4 NCMs) e a elevação DCC não modelada
  (2 NCMs) têm evidência **VERIFIED, Tier 1, dupla confirmação
  independente** — candidatas fortes a uma futura decisão Level 3 de
  atualização de `trade_policy.py`. Isto inclui, notavelmente, **19 meses
  já publicados na série OFFICIAL congelada** (2022-04–2023-12) que
  atualmente carregam um PPI levemente incorreto (até -0,49%).
- A lacuna histórica 2012-2022-03 (9 NCMs) **permanece sem evidência
  VERIFIED** — nenhuma promoção recomendada; a hipótese estrutural
  INFERRED é uma pista de pesquisa futura, não uma base de decisão.
- A cota 929/2026 permanece **PARTIALLY OBSERVABLE** — o mecanismo e os
  volumes agora são VERIFIED, mas a alocação operacional não é pública.

**Não implementado nesta etapa, por desenho** (Level 3, aguardando
aprovação explícita): nenhuma linha de `trade_policy.py` foi alterada.

## 16. Confidence

**MEDIUM-HIGH** para as duas correções do regime atual (evidência Tier 1,
confirmação cruzada independente na mesma fonte oficial, contrafactual
quantificado). **LOW** para a hipótese histórica 2012-2022-03 (INFERRED).
**MEDIUM** para a classificação da cota 2026 (mecanismo e volumes
VERIFIED; alocação operacional continua não observável publicamente).

## 17. Production impact

**No official series changed.** Nenhum arquivo em `src/` foi alterado.
`trade_policy.py`, vintages, publication status, PPI, IPIA e
`VERSAO_METODOLOGIA` permanecem idênticos ao início desta etapa.

## 18. Tests

collected 396, passed 396, failed 0, errors 0 (382 baseline + 14 novos).

## 19. Selftest

**PASS.**

## References

- `docs/research/hrc_import_policy_history.md` (Stage E4/E4b — evidência
  histórica original, base desta etapa).
- `docs/METODOLOGIA.md` §9.5, §9.5.1, §9.5.2, §15.3.
- ADR 0009 (janela publication-grade/experimental), ADR 0012 (vintages),
  ADR 0013 (contrato de publicação).
- Planilha oficial: gov.br/mdic/camex, "Anexos I a X da Resolução Gecex
  nº 272/2021" (atualizada até Res. Gecex nº 812/2025 e nº 941/2026) —
  <https://www.gov.br/mdic/pt-br/assuntos/camex/se-camex/strat/tarifas/vigentes>.
- Resolução Gecex nº 865/2026 (elevação DCC 72082690/72082790) e nº
  929/2026 (cota 72083700/72083890/72083910/72083990).
