# 0001 - Âncora de preço doméstico do IPIA: média ponderada por volume (Usiminas + CSN)

## Contexto

O IPIA precisa de um preço doméstico de referência para comparar contra o
custo de importação (paridade). Usiminas e CSN são as duas grandes
produtoras de aços laminados planos do Brasil, ambas com resultado
trimestral público. Nenhuma das duas isoladamente é obviamente "o" preço
doméstico de bobina a quente do país.

## Decisão

A âncora de preço doméstico é a **média ponderada por volume de vendas de
aço no trimestre** entre Usiminas e CSN (`preco_domestico_ponderado()` em
`src/indices_setoriais.py`). Quando só uma das duas tem dado disponível
para um trimestre, o preço fica sendo o daquela empresa isolada (não é
tratado como erro nem como "menos confiável" por si só — mas o `tipo`
daquele trimestre reflete a granularidade real do dado, não a cobertura de
empresas).

## Alternativas consideradas

- **Só Usiminas**: maior player em aços planos, mas ignora completamente a
  CSN, que também é relevante nesse mercado.
- **Só CSN**: mesmo problema no sentido inverso; além disso o mix de
  receita da CSN é mais diversificado (mineração, cimento, embalagens), o
  que dilui a leitura setorial se fosse usada isolada como proxy do
  "segmento aço".
- **Média simples (não ponderada)**: mais simples de implementar, mas trata
  igualmente uma empresa que vendeu 2x mais aço no trimestre que a outra —
  distorce o preço médio de mercado na direção da empresa menor.

## Consequências

- O preço doméstico de um trimestre onde só uma empresa tem dado carregado
  não é, tecnicamente, "Usiminas+CSN" — é só aquela empresa. Isso é visível
  na coluna `empresas` do resultado de `preco_domestico_ponderado()`.
- Conforme mais trimestres forem curados no CSV (idealmente com as duas
  empresas no mesmo trimestre), o blend passa a refletir de fato uma média
  ponderada das duas.

## Atualização (ago/2026): cobertura expandida para 4 trimestres com blend real

Partindo do estado inicial (só Usiminas no 1T26, só CSN no 2T26 —
trimestres desencontrados), foram curados mais 7 registros trimestrais em
`data/curated/preco_domestico_aco.csv`, cobrindo **4 trimestres com
Usiminas E CSN simultaneamente**: 2025Q2, 2025Q3, 2025Q4 e 2026Q2 (2026Q1
segue só com Usiminas — o release da CSN para 1T26 não foi localizado,
ver nota de pendência abaixo). Essa cobertura é validada em
`--selftest` (checagem "CSV curado tem pelo menos 4 trimestres com
Usiminas E CSN simultaneamente").

**Metodologia de extração e verificação usada (para uma sessão futura
repetir o processo com o mesmo rigor):**

- Documentos localizados via busca + link direto do CDN Mziq (Usiminas e
  CSN publicam no mesmo CDN compartilhado por dezenas de empresas da B3).
  **Descoberta por busca textual não é confiável isoladamente**: um
  candidato encontrado para "CSN 1T26" era, na verdade, o release de uma
  empresa de celulose/papel (confirmado abrindo o PDF e lendo a p.2, que
  citava "Celulose Fluff" e "Papéis Containerboard" — nada a ver com
  siderurgia); outro candidato pertencia à CSN Mineração (CMIN3), uma
  companhia listada separada da CSN (CSNA3). Nenhum número desses dois
  falsos positivos entrou no CSV.
- **O resumo automático do WebFetch não é confiável para esses PDFs**
  (stream comprimido) — em mais de uma ocasião ele "chutou" o tipo de
  documento errado (ex.: classificou releases reais de "Release de
  Resultados" como "apresentação em PowerPoint"). Todo número que entrou
  no CSV foi extraído com `pdfplumber` rodando localmente sobre o PDF
  baixado, nunca do resumo do WebFetch.
- **Reconciliação por soma de segmentos** (Usiminas): a tabela
  "Desempenho Operacional das Unidades de Negócios" tem colunas
  Mineração + Siderurgia + Ajustes = Consolidado. Toda linha nova de
  Usiminas no CSV foi conferida somando as três parcelas e comparando
  com o consolidado publicado (bateu exato ou com diferença de
  arredondamento de R$1mi em todos os casos) — isso também serviu para
  destravar um caso em que a extração em texto corrido do PDF (4T25)
  tinha embaralhado as colunas 4T25/3T25 de uma tabela; a reextração
  como tabela estruturada (`pdfplumber.extract_tables()`) resolveu.
- **Confirmação de segmento** (CSN): os números de volume de venda vêm
  sempre de uma subseção explicitamente rotulada "Volume de Vendas
  (Kton) – Siderurgia" no release — verificado que essa seção é distinta
  das seções "Volume de Vendas – Mineração" e "Volume de Vendas –
  Cimento" que aparecem no mesmo documento, para nunca confundir volume
  da CSN inteira com volume do segmento de aço.
- **Dado repetido em documentos independentes como sinal de qualidade**:
  o release do 4T25 da Usiminas mostra também a coluna comparativa do
  3T25; o release do 3T25 mostra a coluna do 2T25. Em todo caso onde o
  mesmo trimestre apareceu em dois documentos diferentes (3T25 Usiminas:
  visto no doc do 3T25 e na coluna comparativa do doc do 4T25; 1T26
  Usiminas: já no CSV e recuperado como coluna comparativa no doc do
  2T26), os valores bateram exatamente — inclusive o preço doméstico
  R$4.890/t e o volume 938 mil t do 2026Q1 já carregado, confirmados de
  forma independente pelo release do 2T26.

**Validação cruzada entre fontes independentes (achado real, não
esperado no desenho original do ADR)**: como CSN publica "Preço Médio"
diretamente e Usiminas exige calcular receita/volume, dá para comparar
os dois preços implícitos do mesmo trimestre como checagem de
plausibilidade — Usiminas e CSN são concorrentes no mesmo mercado
brasileiro de aços planos, então preços muito discrepantes no mesmo
trimestre seriam um sinal de alerta (erro de extração, ou de fato um mix
de produto muito diferente):

| Trimestre | CSN (direto) | Usiminas (implícito) | Diferença |
|---|---|---|---|
| 2025Q2 | R$5.300/t | R$5.437,82/t | +2,6% |
| 2025Q3 | R$4.899/t | R$5.279,52/t | +7,8% |
| 2025Q4 | R$4.893/t | R$4.997,91/t | +2,1% |
| 2026Q2 | R$4.996/t | R$5.448,39/t | +9,1% |

As diferenças ficam na faixa de 2-9%, plausível para duas empresas
concorrentes com mix de produto e estratégia comercial próprios (a CSN
descreve explicitamente, no seu próprio release do 3T25, uma mudança de
estratégia comercial para "voltar a ser competitiva" em preço naquele
trimestre — coerente com a maior diferença observada, 7,8%, justamente
nesse trimestre). Nenhuma das diferenças é grande o bastante para
sugerir erro de extração ou de trimestre errado.

**Pendência explícita**: CSN 2026Q1 (1T26) não foi localizado. O único
candidato encontrado (mesma pasta Mziq confirmada das demais releases da
CSN, nome de arquivo exato "RESULTADO TRIMESTRAL 1T26") retorna 404 real
do servidor Mziq — o arquivo parece ter sido removido/substituído desde
que foi indexado por buscadores. Sem snapshot no Wayback Machine, sem
link alternativo encontrado via busca do texto do release, do site de
notícias da CSN ou de agregadores financeiros. 2026Q1 continua com
cobertura só de Usiminas até esse documento ser localizado (ou até a CSN
republicar/disponibilizar de outra forma). 2023Q1–2025Q1 (9 trimestres)
seguem como pendência maior, não tentados nesta sessão pelo mesmo motivo
de custo de verificação por trimestre.
