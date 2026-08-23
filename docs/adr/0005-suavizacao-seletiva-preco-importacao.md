# 0005 - Suavização seletiva do preço de importação, e uso de `preco_usd_t_publicado` no cálculo do IPIA

## Contexto

`serie_mensal_preco_bobina()` já marcava meses de volume abaixo do
mínimo com `peso_confiabilidade < 1.0` (ver seção 4 de
`docs/METODOLOGIA.md`), mas não fazia nada com essa marcação além de
publicá-la — o `preco_usd_t` bruto desses meses entrava no cálculo do
IPIA do mesmo jeito que um mês de peso pleno. Este recurso (suavização
seletiva) tinha sido decidido e testado numa sessão de chat anterior,
fora deste repositório, mas nunca foi commitado aqui — confirmado por
investigação no histórico Git (nenhum commit, branch, tag ou objeto
órfão continha esse código; `git log --all -S` para os termos
relevantes não encontrou nada). Tratado como implementação nova, não
como recuperação de arquivo perdido.

## Decisão

1. **Suavização seletiva** (`suavizar_preco_importacao`, chamada dentro
   de `serie_mensal_preco_bobina`): meses com `peso_confiabilidade < 1.0`
   recebem, na nova coluna `preco_usd_t_publicado`, a média móvel
   centrada de 3 meses do `preco_usd_t` bruto
   (`rolling(window=3, center=True, min_periods=1)`). Meses de peso pleno
   (`peso_confiabilidade == 1.0`) nunca são suavizados — o publicado fica
   idêntico ao bruto, mesmo que o mês tenha poucos registros (ex.: pico
   de supercycle). O bruto nunca é sobrescrito; a nova coluna booleana
   `suavizado` marca onde publicado e bruto divergem.

2. **`calcular_ipia_mensal()` passa a usar `preco_usd_t_publicado`**, não
   o bruto, como entrada de `custo_importacao_rs_t` (o FOB da paridade).
   Frete e seguro continuam brutos — a suavização se aplica só ao preço,
   que foi o único componente com o argumento de ruído (volume fino
   distorce o preço unitário; frete e seguro têm dinâmica própria, fora
   do escopo desta decisão).

3. **`gerar_pdf_ipia()` não precisou de nenhuma alteração direta.** Ela
   nunca acessa `preco_usd_t`/`preco_usd_t_publicado` — consome só a
   saída já calculada por `calcular_ipia_mensal` (`ipia`,
   `preco_domestico_rs_t`, `ppi_rs_t`, ...), que passa a refletir a
   suavização automaticamente por transitividade.

## Alternativas consideradas

- **Deixar as duas colunas coexistindo sem uma sendo usada no cálculo**:
  rejeitada explicitamente — publicar `preco_usd_t_publicado` sem ele
  alimentar o IPIA de fato deixaria ambíguo qual coluna é "a oficial",
  e o índice continuaria exposto ao ruído que a suavização foi pedida
  para resolver.
- **Suavizar também frete e seguro**: rejeitada por escopo — a
  especificação e o racional de ruído dados foram especificamente sobre
  o preço unitário (exemplo do pico de supercycle), não sobre frete/seguro.
  Pode ser revisitado como decisão separada se houver evidência de que
  frete/seguro sofrem o mesmo problema.
- **Suavizar incondicionalmente (todos os meses, não só os de peso
  reduzido)**: rejeitada pela especificação — suavizar um mês de peso
  pleno destruiria sinal real (ex.: o próprio pico de supercycle citado
  como motivação original do peso por volume, seção 4 de
  `docs/METODOLOGIA.md`).

## Consequências

- Meses históricos com `peso_confiabilidade < 1.0` (existentes ou
  futuros na janela `--ano-ini`/`--ano-fim`) passam a ter um IPIA
  calculado sobre o preço suavizado, não mais sobre o bruto puro — uma
  mudança real de valor publicado para esses meses especificamente
  (nenhuma mudança para meses de peso pleno, como confirmado rodando
  `--ipia` de verdade para jan-jun/2026, janela onde todo mês tem peso
  1.0 — os números saíram bit-a-bit idênticos aos de antes desta
  mudança).
- `preco_usd_t` bruto continua em todas as saídas (`--preview-bobina`,
  CSV intermediário) para auditoria — nada foi removido, só passou a
  existir uma coluna adicional e uma escolha explícita de qual delas
  alimenta o índice publicado.
