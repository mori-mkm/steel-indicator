# IPP-242 × PIA-HRC Validation — sinal do indicador usado no Denton

**Status: VALIDATION ONLY — não implementa nenhuma mudança.** Denton,
preço doméstico oficial, vintages, fórmula do IPIA, `VERSAO_METODOLOGIA`
e reporting permanecem exatamente como estavam antes desta etapa.

Reproduzir: `docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/validar_ipp242_pia_hrc.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`).

## Question

> O IPP 242-Siderurgia contém sinal suficiente sobre a direção e a
> dinâmica de preços da siderurgia para ser usado como indicador de alta
> frequência entre os benchmarks anuais da PIA-HRC no Proportional
> Denton?

Explicitamente **não** é a pergunta "o IPP prevê perfeitamente o preço
HRC" — o Denton força o nível anual a bater com a PIA por construção; o
risco está na **forma intra-ano**, não no nível anual final (ver §Denton
vs baselines).

## Data

Confirmado direto no código e no dado ao vivo, não só na documentação:

| Série | Fonte | Código | Frequência | Unidade | Cobertura | Papel metodológico |
|---|---|---|---|---|---|---|
| PIA-HRC (preço implícito) | IBGE/SIDRA | tabela 7752, categoria 54849 (Prodlist 2422.2020 "Bobinas a quente de aços ao carbono, não revestidos") | Anual | R$/t nominal (receita líquida de vendas ÷ quantidade vendida, mesmo código Prodlist nos dois) | 2014–2023 (10 anos) | Âncora de nível (benchmark anual do Denton) |
| IPP 242-Siderurgia | IBGE/SIDRA | tabela 6723, classificação 844[47259] | Mensal | Número-índice (dez/2018=100, nominal) | 2018-12 a 2026-07; **7 anos com 12 meses completos (2019–2025)** | Indicador de movimento intra-ano (Proportional Denton) |

PIA-HRC (R$/t, nominal) por ano: 2014=1.757,6 · 2015=1.475,0 ·
2016=1.560,7 · 2017=1.896,3 · 2018=2.234,1 · 2019=2.406,9 ·
2020=2.840,7 · 2021=5.644,7 (pico do supercycle) · 2022=5.393,3 ·
2023=4.844,3.

Nenhuma das duas séries é deflacionada — a comparação é nominal-nominal,
consistente dos dois lados (deflacionar só um lado introduziria uma
inconsistência nova, não corrigiria nada).

**IPP-242 é um agregado de toda a siderurgia brasileira** (não existe
tabela IPP do SIDRA que quebre por produto ou por CNAE de 4+ dígitos) —
limitação já reconhecida na metodologia como `PRODUCT_AGGREGATION`, objeto
central desta validação.

## Transformations

PIA é anual; IPP é mensal. Correlacionar **níveis** diretamente seria
espúrio (duas séries com tendência de alta ao longo do período). O foco é
**variação anual**, com uma transformação principal e duas de robustez:

- **A — Principal**: crescimento da média aritmética anual do índice
  (`mean(IPP dentro do ano)`), só para anos com os 12 meses presentes.
  Escolhida como principal por ser a agregação mais direta e menos
  sensível a outlier de um único mês, e por corresponder ao mesmo
  conceito de "nível médio do ano" que a PIA representa (receita/volume
  do ano inteiro).
- **B — Robustez**: média das variações YoY mês a mês dentro do ano
  (pondera igualmente cada mês, em vez de deixar a média anual absorver a
  forma).
- **C — Robustez**: dezembro contra dezembro (captura só o nível de
  fechamento do ano, ganha um ano a mais de N porque não exige os 12
  meses completos do ano anterior, só o mês de dezembro).

Nenhuma foi escolhida por maximizar a correlação — A foi fixada como
principal antes de rodar C e B.

## Annual comparison

**N = 4** (2020–2023) para os métodos A e B — o menor denominador comum
entre PIA (2014–2023) e IPP-242 completo (2019–2025, primeiro ano cheio
2019, então a primeira variação calculável é 2019→2020). **N = 5**
(2019–2023) para o método C (dezembro), que não exige o ano anterior
inteiro.

| Ano | Δ PIA-HRC | Δ IPP-242 (A) | Mesmo sinal? | Diferença (p.p.) |
|---|---:|---:|---|---:|
| 2020 | +18,02% | +13,12% | Sim | +4,90 |
| 2021 | +98,71% | +66,63% | Sim | +32,08 |
| 2022 | −4,45% | +1,04% | **Não** | −5,49 |
| 2023 | −10,18% | −12,72% | Sim | +2,54 |

## Correlation

| Método | N | Pearson | Spearman | Directional accuracy |
|---|---:|---:|---:|---:|
| A (principal) | 4 | **0,9930** | 1,0000 | 3/4 (75%) |
| B (robustez) | 4 | 0,9909 | — | 3/4 (75%) |
| C (robustez, dez/dez) | 5 | **0,8309** | — | 4/5 (80%) |

**Interpretação, sem superinterpretar:** com N=4–5, um único coeficiente
de correlação não é uma prova estatística robusta — é uma descrição de 4
a 5 pontos. Ainda assim, o SINAL é consistente e economicamente
coerente nos três métodos (nunca próximo de zero, nunca negativo). A
queda de Pearson de 0,99 (A) para 0,83 (C) ao trocar só a forma de
agregar o IPP mostra que **a magnitude da correlação depende da escolha
metodológica** — não deve ser citada como um número único "validado".
`beta = 1,438` (regressão diagnóstica g_PIA ~ g_IPP, método A): a PIA-HRC
se move ~1,4× mais que o IPP-242 por unidade de movimento do IPP — o IPP
**subestima a amplitude** dos ciclos específicos de HRC (esperado: um
agregado de toda a siderurgia diluiu o supercycle específico de bobina a
quente de 2021). Beta não foi usado para recalibrar nada.

## Directional accuracy

**3 de 4 anos (75%) com o mesmo sinal** no método principal; **4 de 5
(80%)** no método dez/dez. O ano de sinal divergente **muda conforme o
método** (2022 no método A/B; 2019 no método C) — sinal de fragilidade
dado o N pequeno, não de um único ano "ruim" identificável de forma
estável.

## Leave-one-out

| Ano removido | N | Pearson | Spearman | Directional accuracy |
|---|---:|---:|---:|---:|
| 2020 | 3 | 0,9933 | 1,0000 | 66,7% |
| 2021 | 3 | 0,9331 | 1,0000 | 66,7% |
| 2022 | 3 | 0,9974 | 1,0000 | **100,0%** |
| 2023 | 3 | 0,9994 | 1,0000 | 66,7% |

Pearson permanece alto (0,93–0,999) em todos os subconjuntos de N=3 —
inclusive removendo 2021 (o ano do supercycle, o ponto de maior
magnitude), a correlação cai só para 0,933, não colapsa. **Spearman = 1,0
em toda remoção não é evidência forte por si só**: com apenas 3 pontos
restantes, o número de ordenações possíveis é pequeno e uma correlação de
postos perfeita é mecanicamente fácil de obter por acaso — reportado por
completude, não como prova de robustez. A directional accuracy sobe para
100% só quando o próprio ano divergente (2022) é removido — como
esperado, não é uma confirmação independente.

**Conclusão do leave-one-out:** a correlação de Pearson não depende de um
único ponto (não colapsa ao remover 2021, o mais extremo); a conclusão de
"3 de 4 direções corretas" é a que resta minimamente sensível — remover
qualquer ano exceto 2022 ainda deixa 2/3 corretos.

## Corporate validation

**Duas checagens, de qualidade epistemológica diferente:**

### 5. Comparação mensal existente (contaminada — não independente)

Confirmado ao vivo: **N=16 meses** (2025-04 a 2026-07 — uma janela mais
longa que os "15 meses (2025-04 a 2026-06)" citados no Stage G3 anterior,
porque um mês adicional de IPP (2026-07) já está disponível agora).
`delta_pct` médio **−11,56%** (citação anterior: −11,66%/15 meses — a
pequena diferença vem exatamente desse mês extra, não de nenhuma
inconsistência), mediana −11,11%, desvio-padrão 1,49pp, min −14,49%, max
−9,25%, correlação de níveis 0,8485, tendência do gap −0,041pp/mês
(praticamente plana).

**Achado metodológico não solicitado explicitamente, mas relevante:**
`preco_domestico_hrc_mensal_v2` (âncora corporativa) e
`preco_domestico_hrc_pia_v2` (série PIA) usam o **mesmo** `ibge_sidra_ipp_siderurgia()`
para encadear mês a mês (confirmado direto no código,
`preco_domestico_hrc_mensal_v2` linha ~1513). **Esta comparação não é um
teste independente do sinal do IPP** — parte da correlação observada
(0,85) é mecânica, porque as duas séries compartilham o mesmo modulador
mensal aplicado sobre âncoras de nível diferentes (trimestral corporativa
vs. anual PIA). O gap estável (§ADR 0011) continua sendo uma evidência
válida de que a **relação de nível** entre as duas âncoras é estável —
mas não prova que o IPP capture a forma mensal real do HRC.

### 5b. Checagem independente (âncora trimestral bruta, pré-IPP)

Construída nesta etapa especificamente para contornar a contaminação
acima: a âncora trimestral **bruta** (soma receita/soma volume,
Usiminas+CSN, `ancora_domestica_ponderada_v2`) nunca usa IPP-242 — seu
movimento trimestre a trimestre é evidência genuinamente independente.

| Trimestre | Corporate bruto (R$/t) | PIA+IPP242 (R$/t, média do trim.) | Δ corporate | Δ PIA+IPP | Mesmo sinal? |
|---|---:|---:|---:|---:|---|
| 2025Q2 | 5.377,83 | 4.793,50 | — | — | — |
| 2025Q3 | 5.111,93 | 4.508,41 | −4,94% | −5,95% | Sim |
| 2025Q4 | 4.951,63 | 4.420,67 | −3,14% | −1,95% | Sim |
| 2026Q1 | 5.213,22 | 4.500,60 | +5,28% | +1,81% | Sim |
| 2026Q2 | 5.235,73 | 4.647,73 | +0,43% | +3,27% | Sim |

**N = 4 trimestres comparáveis, 4/4 (100%) mesmo sinal, correlação QoQ =
0,8025.** N pequeno, mas é o dado independente mais limpo disponível no
projeto hoje — e o resultado é positivo.

**Value added, testado diretamente:** comparado contra uma baseline
"flat" (sem indicador algum — repete o último nível benchmarked por todo
o período), que por construção tem crescimento trimestral sempre igual a
zero: **4/4 acertos de direção com IPP-242, contra 0/4 (por construção)
sem nenhum indicador.** Esta é a evidência mais direta e menos ambígua
desta validação de que o IPP-242 agrega informação direcional real na
extensão provisional — mesmo com N=4.

## Denton vs baselines

Comparação analítica (nunca publicada) na janela benchmarked real
(2019–2023, 60 meses): Denton+IPP-242 atual vs. interpolação linear entre
níveis anuais (ancorada em 1º de julho de cada ano — convenção padrão
para não deslocar de fase uma média anual) vs. degrau/carry-forward anual.

| Método | std(variação % mensal) | MAD(variação % mensal) |
|---|---:|---:|
| Denton + IPP-242 (atual) | **4,255** | **3,322** |
| Linear | 2,569 | 1,740 |
| Step (degrau anual) | 13,141 | 2,226 |

**Interpretação:** Linear é mecanicamente a mais suave (por construção,
sem nenhum sinal real). Step tem o maior desvio-padrão pontual (todo o
ajuste do ano acontece de uma vez, em janeiro) mas MAD moderado (a
maioria dos meses tem variação zero). **Denton+IPP-242 tem o maior MAD** —
carrega genuinamente mais movimento mês a mês que ambas as baselines
triviais, herdado do IPP real. Isso não prova que esse movimento extra
seja "correto", mas prova que **o IPP não é redundante** com uma
interpolação ingênua — produz uma forma qualitativamente diferente.

**Coerência econômica qualitativa (2021, ano do supercycle):**
Denton+IPP-242 mostra ramp-up de R$3.927/t (jan) a um pico de R$6.424/t
(set) e correção para R$5.855/t (dez) — timing que bate com o pico e
correção conhecidos do supercycle global do aço em 2021. Linear, no
mesmo ano, produz uma trajetória monotônica suave sem pico intermediário;
Step fica achatado em R$5.644,7/t o ano inteiro. Nenhuma das duas
baselines triviais reproduz o formato de pico-e-correção real — só o
Denton+IPP-242 captura essa dinâmica, consistente com conhecimento
externo do mercado (não uma prova estatística, mas coerência econômica
qualitativa, exatamente o tipo de evidência que N pequeno demanda).

## Limitations

1. **N estruturalmente pequeno (4–5) para a comparação anual** — não é
   um problema de execução, é o tamanho real da amostra disponível
   (PIA-HRC é anual e recente-mente específica de HRC desde 2014; IPP-242
   só começa em dez/2018). Nenhuma técnica estatística sofisticada
   resolve isso — só mais anos de dado resolveriam.
2. **A comparação mensal com a âncora corporativa (§5) não é
   independente** — compartilha o mesmo IPP-242 dos dois lados. A
   checagem trimestral (§5b) é mais limpa, mas também pequena (N=4) e
   cobre só a extensão PROVISIONAL (2025Q2–2026Q2), nunca a janela
   Denton-benchmarked real (2019–2023) — não existe overlap temporal
   entre a cobertura corporativa curada e a janela PIA-benchmarked
   (achado já registrado em `docs/research/hrc_domestic_price_sources.md`).
3. **A comparação Denton vs. baselines (§Denton vs baselines) não tem
   ground truth mensal para a janela 2019–2023** — só compara
   propriedades estatísticas entre si (suavidade) e coerência qualitativa
   com conhecimento de mercado externo, nunca um erro medido contra um
   valor real.
4. **Correlação sensível à transformação escolhida** (0,99 em A, 0,83 em
   C) — nenhuma das duas é "a errada", mas a escolha metodológica muda o
   número o suficiente para que nenhum coeficiente único deva ser citado
   isoladamente como "a correlação do IPP com a PIA".
5. **IPP-242 é agregado (`PRODUCT_AGGREGATION`)** — beta=1,438 confirma
   quantitativamente que ele **subestima** a amplitude de ciclos
   específicos de HRC, consistente com ser um índice de toda a
   siderurgia.

## Decision matrix

Escala qualitativa (não um score único, para não esconder nuance):
Forte / Moderado / Fraco / Insuficiente.

| Critério | IPP-242 + Denton | Linear | Step |
|---|---|---|---|
| Consistência anual com a PIA | Moderado — direção certa em 75-80% dos anos, magnitude subestimada (beta=1,44) | N/A (não usa IPP) | N/A (não usa IPP) |
| Informação intra-ano | Forte (carrega o maior MAD de variação mensal; único que reproduz o pico de 2021) | Nenhuma (mecânico) | Nenhuma (degrau) |
| Relação com PIA-HRC (nível anual) | Forte — nível anual sempre bate exatamente por construção do Denton | Forte — mesmo alvo anual | Forte — mesmo alvo anual |
| Relação com corporate anchor (independente, §5b) | Moderado — 4/4 direção, N=4, só na extensão provisional | Não testável (sem cobertura no período) | 0/4 por construção (baseline "flat" testada) |
| Robustness (leave-one-out, métodos alternativos) | Moderado — Pearson estável, mas correlação e ano-divergente mudam conforme o método | Forte (não depende de indicador algum) | Forte (não depende de indicador algum) |
| Simplicidade | Moderado (Denton + indicador externo) | Forte (trivial) | Forte (trivial) |
| Reprodutibilidade | Forte — determinístico, testado, dado público | Forte | Forte |
| Fundamentação econômica | Moderado — proxy setorial reconhecido, mas evidência institucional (IMF/Eurostat) favorece indicadores mais específicos quando disponíveis | Fraco (nenhuma fundamentação econômica, só matemática) | Fraco |

## Recommendation

**B — KEEP WITH LIMITATION.**

Manter IPP-242 + Denton sem mudança nesta etapa, mas reforçar o
disclosure já existente (`PRODUCT_AGGREGATION`) com os achados
quantitativos desta validação, e registrar como item de pesquisa futura
buscar um indicador mais específico de HRC quando/se um existir.

**Justificativa (critério de materialidade, não elegância teórica):** a
evidência converge, por múltiplos ângulos independentes (correlação
anual consistentemente positiva nos 3 métodos, direção 75-80% nos anos
anuais, 4/4 no teste trimestral genuinamente independente, coerência
qualitativa no ano do supercycle, e a comparação direta "com IPP vs. sem
indicador algum" = 4/4 vs. 0/4), para "há sinal real, não é ruído" — mas
não o suficiente, dado N=4-5 e sensibilidade a escolha metodológica
(Pearson 0,99→0,83), para classificar como evidência **STRONG** sem
ressalva. Não há evidência de que o **método** (Denton) seja o problema —
pelo contrário, a literatura institucional (IMF WP/16/71) confirma que
Chow-Lin seria MENOS defensável com este N (coeficientes de regressão
instáveis, revisões maiores a cada novo ano de benchmark) — então **D
(review method)** não se justifica. **C (review indicator)** exigiria
evidência fraca o suficiente para questionar o status publication-grade
atual — não é o caso: nenhum teste produziu resultado próximo de zero ou
de sinal sistematicamente errado.

**Classificação da evidência: MODERATE.**

Critérios usados (analíticos desta validação, não uma escala já
institucionalizada no projeto):
- **STRONG** exigiria: direção consistente (>80-85%) E correlação estável
  entre métodos de construção alternativos E robustez leave-one-out sem
  ano-divergente móvel.
- **MODERATE** (classificação atual): direção majoritariamente correta
  (75-100% conforme o teste), correlação sempre positiva e
  economicamente coerente, mas instável em magnitude entre métodos, e ao
  menos uma checagem genuinamente independente positiva.
- **WEAK**: correlação próxima de zero ou o sinal frequentemente errado.
- **INCONCLUSIVE**: N insuficiente para qualquer leitura — não é o caso
  aqui porque, apesar do N pequeno, a convergência entre métodos
  diferentes (anual, trimestral independente, qualitativo) aponta na
  mesma direção.

## Confidence

**MEDIUM.** Não HIGH porque N é genuinamente pequeno e um dos três
métodos de robustez (C) reduz a correlação de 0,99 para 0,83. Não LOW
porque há convergência entre fontes de evidência independentes (anual,
trimestral bruto, qualitativo) apontando consistentemente para "há
sinal, direção majoritariamente correta, magnitude subestimada".

## References

- Eurostat, [ESS guidelines on temporal disaggregation, benchmarking and reconciliation (2018)](https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/KS-06-18-355) — Denton usa indicadores relacionados ("predictor variables") para aproximar o comportamento infra-anual da série-alvo; base institucional do desenho já adotado no projeto (ADR 0010).
- IMF, [Quarterly National Accounts Manual](https://www.imf.org/external/np/sta/qna/), cap. 6 — Proportional Denton (primeiras diferenças), já citado na ADR 0010/METODOLOGIA §12.9.
- IMF, [WP/16/71 — Nowcasting Annual National Accounts with Quarterly Indicators](https://www.imf.org/external/pubs/ft/wp/2016/wp1671.pdf) — Chow-Lin produz mais revisão a cada nova observação anual (coeficientes de regressão reestimados) — evidência institucional a favor de manter Denton (sem parâmetro estimado) em vez de Chow-Lin enquanto o N de benchmarks anuais for pequeno.
- `docs/adr/0010-pia-produto-hrc-benchmark-anual-proportional-denton.md`, `docs/research/hrc_domestic_price_sources.md`, `docs/validation/ipia_hrc_v2_final_validation.md` §4 (fonte original do gap corporate ≈-11,66%).
