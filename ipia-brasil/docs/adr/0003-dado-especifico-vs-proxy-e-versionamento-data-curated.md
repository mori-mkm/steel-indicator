# 0003 - Dado específico vs. proxy no preço doméstico, e versionamento em `data/curated/`

## Contexto

Não existe API pública para preço doméstico de bobina a quente. A única
fonte é o release trimestral de resultados de Usiminas/CSN. Antes de
implementar qualquer cálculo, era preciso confirmar se esses releases
detalham volume/receita especificamente por "laminados a quente" ou só o
agregado do segmento "Siderurgia"/"Aço" inteiro (mistura chapas grossas,
laminados a quente, laminados a frio e revestidos).

## Investigação (não suposição — leitura real dos documentos)

Nesta sessão, os releases completos e as apresentações de resultados mais
recentes disponíveis foram baixados e o texto extraído de verdade (via
`pdfplumber`, não estimado por resumo de imprensa):

- **Usiminas, Release de Resultados 1T26** (`ri.usiminas.com`, 26 páginas):
  seção "Unidade de Negócio — Siderurgia" tem Produção de Aço Bruto,
  Produção Total de Laminados (agregado) e Volume de Vendas total, split
  só por Mercado Interno/Exportações. A quebra que existe é por mercado de
  destino (Automotivo, Grande Rede, Indústria), não por tipo de produto.
- **Usiminas, Apresentação de Resultados 1T26** (38 páginas, slides): tem
  um gráfico de capacidade instalada por linha de produto (Chapas Grossas,
  Laminados a Quente, Laminados a Frio, Galvanizados) — mas é
  **capacidade**, não volume vendido nem receita nem preço. O gráfico
  "Evolução das Vendas de Aço" só quebra por Mercado Interno/Exportações
  e por mercado de destino, sem produto.
- **CSN, Resultado Trimestral 2T26** (`ri.csn.com.br`, 45 páginas):
  produção reportada como "aços laminados planos" (agregado) vs. "aços
  longos". Publica um "Preço Médio no mercado doméstico" (R$/ton) — mas é
  do segmento Siderurgia inteiro, não de um produto específico.

Conclusão da leitura real: **nenhuma das duas empresas publica, no release
trimestral nem na apresentação de resultados, volume/receita/preço
específico de laminados a quente separado dos demais produtos planos**.
A granularidade real disponível hoje é nível de segmento ("Siderurgia"),
não nível de produto. Isso confirma, com evidência direta, a pendência já
registrada em `CLAUDE.md` antes desta tarefa.

## Decisão

1. **Tipo de dado**: todo registro carregado hoje em
   `data/curated/preco_domestico_aco.csv` tem
   `tipo="proxy_segmento_aco"` — nunca `"especifico_laminado_quente"`,
   porque isso seria inventar uma granularidade que a fonte não tem. Se um
   dia uma fonte específica de bobina a quente for confirmada (ex.: um
   detalhamento novo em release futuro, ou outra fonte), ela entra na
   mesma tabela com o tipo correto — o motor (`preco_domestico_ponderado`)
   já sabe propagar isso e marcar como `"misto"` um trimestre onde as duas
   empresas discordam de tipo.
2. **Versionamento**: o CSV curado fica em `data/curated/`, **commitado no
   Git** — ao contrário de `data/raw/` (PDFs de origem, grandes, material
   de terceiro) e `data/processed/` (séries 100% reproduzíveis via API),
   que continuam gitignored. Motivo: é um dado pequeno, extraído de fonte
   pública, e essencial para o índice rodar — sem ele, quem clona o
   repositório não tem nenhum insumo para calcular o IPIA. É tratado como
   parte do código-fonte, no mesmo espírito de `NCM_BOBINA_QUENTE` já
   versionado dentro do `.py`.

## Alternativas consideradas

- **Assumir proxy sem ler os documentos de verdade**: mais rápido, mas
  vai contra a regra do projeto de nunca declarar status de dado sem
  confirmar rodando/buscando de verdade.
- **Esperar confirmação manual antes de implementar qualquer coisa**:
  mais conservador, mas trava a tarefa inteira numa pendência que, uma vez
  investigada de verdade, tem resposta clara (não existe, hoje, dado
  específico público nesses releases).
- **Deixar o CSV curado fora do Git (mesmo padrão de `data/raw`)**: mais
  consistente com o resto de `data/`, mas quebra a reprodutibilidade do
  repositório para quem clona do zero.

## Consequências

- O IPIA calculado hoje (`--ipia`) é, formalmente, um índice de paridade
  para o **segmento de aço inteiro** das duas empresas, usado como proxy
  para bobina a quente — não um IPIA de bobina a quente puro. Isso está
  marcado na coluna `tipo_dado_domestico` de toda saída, nunca escondido.
- Os dois trimestres hoje carregados (`2026Q1` Usiminas, `2026Q2` CSN) não
  são a mesma janela temporal para as duas empresas — outra limitação de
  dado disponível no momento, também não escondida (ver ADR 0001).
- Se uma fonte específica de bobina a quente aparecer no futuro, a
  migração é só adicionar linhas novas ao CSV com `tipo=
  "especifico_laminado_quente"` — nenhuma mudança de arquitetura
  necessária.
