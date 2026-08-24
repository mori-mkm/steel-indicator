# 0007 - Taxa de penetração de importação: fonte híbrida PDF+Excel do Instituto Aço Brasil

## Contexto

`gerar_pdf_ipia()` mostrava a linha fixa "Penetração de importação: não
disponível (sem coletor implementado)" — a métrica só existia como
entrada de spec do ICCS (`penetracao_importados`), sem coletor real.

## Investigação

O **Instituto Aço Brasil** publica mensalmente, em
`https://www.acobrasil.org.br/site/estatistica-mensal/`, dois arquivos —
a página sempre expõe só o **mês mais recente**, sem arquivo de meses
passados, e a URL de cada arquivo não é previsível (testado: adivinhar a
pasta de upload para um mês anterior funcionou para junho/2026 mas deu
404 para maio/2026 — não dá para confiar em URL adivinhada sem
verificar):

- **PDF** ("Estatística Mensal", ~26 páginas): seção **"9.1. Taxa de
  Penetração das Importações Brasileiras de Produtos de Aço - Mensal"**
  — tabela com Planos/Longos/Total, cada um com Consumo Aparente (A),
  Importação (B, já excluindo importações diretas pelas usinas) e a taxa
  B/A%. É o número **oficial** do Instituto, mas cada edição só mostra o
  mês corrente + o mesmo mês do ano anterior — não uma série histórica.
  Existe também a seção "9.2 ... Acumulado no Ano" (YTD), com os mesmos
  rótulos de produto mas números diferentes — fácil de confundir se não
  se isolar a seção certa antes de extrair (o parser corta o texto entre
  "9.1." e "9.2." antes de qualquer regex, exatamente por isso).
- **Excel `.xls`** ("Performance Mensal"): série histórica mensal
  completa desde **2013**, com os componentes brutos (Importações e
  Consumo Aparente, já separados Planos/Longos) — mas **sem** a taxa
  pronta.

**Granularidade confirmada**: só Planos vs. Longos (agregado) — nunca
bobina a quente isolada. `tipo_dado_penetracao` nunca é
"específico_laminado_quente"; a categoria usada pelo IPIA é sempre
"planos".

**Achado central — calcular a taxa a partir do Excel não reproduz o
número oficial do PDF**: testado para julho/2026, Planos — Excel
(Importação/Consumo Aparente brutos) dá 16,66%; PDF oficial dá 17,9%.
Diferença real de ~1,2 p.p., não arredondamento. A nota do PDF explica
parcialmente: a tabela oficial exclui "importações diretas pelas
usinas"; o Excel aparentemente não aplica a mesma exclusão nos seus
componentes brutos.

## Reverificação manual (pedida antes de aprovar a implementação)

Depois da investigação inicial, uma notícia (euqueroinvestir.com,
19/08/2026) citou penetração de Planos em 16% (vs. 21% um ano antes) e
Longos em 11% (vs. 13%) — divergindo dos números extraídos da tabela
9.1 (17,9%/24,1% Planos; 14,6%/15,5% Longos). Isso motivou reverificação
completa antes de prosseguir:

1. **Re-baixei o PDF** (MD5 idêntico ao download original — o arquivo
   não mudou desde a extração inicial).
2. **Confirmei linha/mês corretos**: seção "9.1 ... Mensal", colunas
   Jul/2025 e Jul/2026 — não a "9.2 ... Acumulado no Ano".
3. **Confirmei a direção da exclusão de usinas**: achei, no mesmo PDF,
   uma tabela **independente** ("14.1 Importações Brasileiras de
   Produtos de Aço por Região de Origem", sem essa exclusão) mostrando
   `Total Jul/2026 = 383.167 t` — batendo exatamente com o resumo
   executivo do próprio PDF ("as importações de julho de 2026 foram de
   383 mil toneladas"). A tabela 9.1 (que exclui usinas) dá
   `Total B = 370.108 t` — menor, na direção correta (subconjunto menor
   que o total bruto).
4. **A notícia atribui explicitamente a conta ao BTG Pactual** ("dados
   do Aço Brasil, analisados pelo BTG"), não uma citação direta da
   tabela do Instituto. Não encontrei, em nenhuma tabela do PDF (9.1,
   9.2, vendas internas, produção), uma combinação que reproduza os
   números do BTG.

**Conclusão**: a tabela 9.1 é internamente consistente e bate com uma
tabela independente do mesmo documento e com o resumo executivo — é a
única fonte **do próprio Aço Brasil** para essa métrica. A divergência
com o número do BTG não é evidência de erro do lado do parser.

**Padrão geral a registrar** (não é specífico deste caso): "penetração
de importação" é um termo que diferentes participantes de mercado
(bancos, casas de research) costumam calcular com fórmulas próprias, não
públicas — o denominador pode ser "Consumo Aparente" (como o Aço Brasil
usa), "Vendas Internas + Importação", ou outra base. Divergência com um
número de terceiro **não é necessariamente erro do nosso lado**. A
evidência que sustenta uma fonte como confiável é **consistência
interna** — a tabela bate com outras tabelas independentes do mesmo
documento e com o texto narrativo — não concordância com todo número de
terceiro que aparecer por aí. Isso vale para qualquer fonte futura deste
projeto, não só esta.

## Decisão

**Fonte híbrida**: PDF (oficial) para o mês mais recente disponível;
Excel (aproximado, com o viés conhecido de ~1,2 p.p.) como fallback para
preencher o restante do histórico. Nunca mistura sem marcar qual é
qual — coluna `tipo_dado_penetracao`: `"oficial_mensal"` (PDF) vs.
`"aproximado_consumo_aparente"` (Excel). Quando o PDF cobre um mês que
o Excel também cobre, o oficial sempre vence (nunca sobrescrito pelo
aproximado) — implementado e testado em
`taxa_penetracao_importacao_planos_mensal()`.

Implementação em `src/indices_setoriais.py`:
- `_acobrasil_resolver_links_mes_atual()`: resolve os links ao vivo da
  página (nunca constrói URL adivinhando a pasta de upload).
- `_parse_tabela_penetracao_pdf(texto_pagina)` / `acobrasil_taxa_penetracao_pdf_mes_atual()`:
  extrai a tabela 9.1 do PDF (a lógica pura de parsing é separada da
  busca de rede, testável sem rede com o texto real capturado).
- `_calcular_penetracao_de_performance_mensal(df_bruto, categoria)` /
  `acobrasil_taxa_penetracao_xls_historico()`: calcula a taxa a partir
  dos componentes brutos do Excel, localizando as linhas por **texto**
  (nunca índice fixo, para não quebrar se o Instituto inserir/remover
  uma linha do template).
- `taxa_penetracao_importacao_planos_mensal()`: combina as duas,
  chamada por `calcular_ipia_mensal()`. Mês sem nenhuma das duas fontes
  fica `NaN` explícito (via `reindex` sem `ffill`), nunca fabricado.

## Alternativas consideradas

- **Só o PDF**: seria o número mais confiável, mas sem profundidade
  histórica automática — cada execução só teria o mês mais recente,
  exigindo curadoria manual de PDFs antigos (mesmo trabalho já feito
  para Usiminas/CSN) para qualquer histórico.
- **Só o Excel**: dá profundidade histórica de graça (2013+), mas
  publicaria um número que diverge do oficial do próprio Instituto sem
  nenhum aviso — contra o princípio do projeto de nunca disfarçar
  aproximação de dado bruto.
- **Híbrido (escolhida)**: mais código, mas o mês mais recente (o que
  mais importa para o relatório atual) usa o número oficial, e o
  histórico fica disponível mesmo que aproximado — com a diferença
  sempre marcada, nunca escondida.

## Limitação: cross-validação não implementada

Avaliado se dava para montar uma validação cruzada independente (mesmo
princípio que funcionou comparando preço CSN vs. Usiminas): **não dá**.
O projeto não tem consumo aparente doméstico próprio — só volume de
**importação** via Comex Stat, e com escopo mais estreito (13 NCMs
específicos de bobina a quente, não "Planos" inteiro). Sem o
denominador (consumo aparente) e com escopos diferentes, não há como
montar uma taxa própria comparável à do Aço Brasil. Registrado como
limitação, não implementado nesta tarefa.

## Consequências

- Nova dependência: `xlrd` (necessária para `pandas.read_excel` ler o
  `.xls` legado — `openpyxl` só cobre `.xlsx`). Adicionada a
  `requirements.txt` com o mesmo tratamento que `matplotlib` recebeu.
- `gerar_pdf_ipia()` mostra o número real quando disponível, com o
  rótulo "oficial" ou "aproximado" explícito; mantém "não disponível"
  só quando nenhuma das duas fontes cobre o mês — nunca um número
  inventado.
- Se o Instituto Aço Brasil um dia publicar uma quebra específica de
  bobina a quente (hoje só Planos agregado), o motor precisa de um novo
  `tipo_dado_penetracao` — mesmo padrão já usado para o preço doméstico
  (`especifico_laminado_quente` vs. `proxy_segmento_aco`).
