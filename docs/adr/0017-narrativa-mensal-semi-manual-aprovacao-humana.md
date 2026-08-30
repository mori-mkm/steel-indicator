# 0017 - Narrativa mensal semi-manual — aprovação humana explícita, busca não automatizada

## Status

**Accepted.** Decisão de infraestrutura/processo de publicação (não é
decisão econômica/metodológica — IPIA/PPI_COST/decomposição Shapley
permanecem exatamente como estavam; `VERSAO_METODOLOGIA` não muda).
Aprovada pelo usuário no prompt que abriu esta tarefa, incluindo os três
parâmetros: página 2 (com fallback para página 4), cobertura só em
pytest (não duplicada em `--selftest`) e N=3 ciclos como critério de
revisão desta ADR.

## Contexto

O Reporting V3 (ADR 0016) já explica *quantitativamente* por que o
IPIA-HRC mudou no mês (decomposição Shapley por driver). Falta o
contexto qualitativo que um leitor experiente espera — por que o câmbio
subiu, por que o FOB caiu — e isso exige pesquisa em fontes jornalísticas
externas, não um número já calculado no motor.

Duas decisões de design precisavam ser tomadas antes de qualquer
implementação:

1. **Quem escreve o texto e quem o aprova para publicação?**
2. **A busca pelas fontes jornalísticas roda automaticamente dentro do
   Claude Code, ou é feita por um humano fora dele?**

## Decisão

### 1. Narrativa é sempre semi-manual, nunca gerada/publicada automaticamente

Um arquivo `docs/research/AAAA-MM-narrativa.md` (frontmatter YAML +
corpo markdown, ver `src/reporting/narrativa_mensal.py`) guarda o
processo de pesquisa (drivers do Shapley já calculados, buscas
realizadas, achados citáveis ou lacunas registradas) e um rascunho de
texto. O relatório só inclui esse texto quando:

- `narrativa_status: aprovado` (nunca `rascunho`, nunca ausente, nunca
  qualquer outro valor);
- `revisado_por` e `data_revisao` preenchidos (aprovação sem atribuição
  explícita é tratada como malformada, não como aprovada);
- existe uma seção `## Narrativa` com conteúdo.

Qualquer desvio (arquivo ausente, rascunho, YAML quebrado, aprovado sem
revisor) devolve `None` silenciosamente — o relatório gera normalmente,
sem essa seção, nunca trava e nunca mostra rascunho como se fosse texto
final. Não existe caminho de código que publique uma narrativa sem esse
portão de aprovação humana explícita.

**Por quê**: texto qualitativo sobre causas econômicas externas (câmbio,
geopolítica, notícia de mercado) é exatamente o tipo de afirmação que
`reporting/narrative.py` foi desenhado para NUNCA fazer (vocabulário
fechado, só números já calculados — ver docstring daquele módulo). Abrir
essa porta exige um portão de revisão humana no mesmo nível de rigor,
não uma automação que insira causalidade não verificada num relatório
publicado.

### 2. A busca pelas fontes ainda não é automatizada dentro do Claude Code

Nesta etapa, o processo de busca (guiado pelos drivers do Shapley,
avaliação de quais achados sustentam ou não a direção do número) é feito
por um humano fora do Claude Code. Só a *infraestrutura* de
carregamento/aprovação/inclusão no relatório está implementada aqui.

**Por quê**: este projeto já documentou fricção real e repetida com
acesso automatizado a fontes financeiras/corporativas — ver ADR 0001
(§ "Metodologia de extração e verificação usada"): documentos no CDN
Mziq compartilhado por dezenas de empresas da B3, candidatos de busca
textual que resultam em falso-positivo (release de trimestre errado),
links que retornam 404 real mesmo já indexados por buscadores, sem
snapshot alternativo disponível. O primeiro ciclo real de narrativa
(Junho/2026, `docs/research/2026-06-narrativa.md`) reproduziu o mesmo
padrão: um driver (câmbio) teve achado jornalístico sólido e citável;
outro (preço FOB) não teve achado que sustentasse a direção do número, e
o processo manual registrou isso como lacuna em vez de forçar uma
explicação. Automatizar a busca antes de validar esse padrão de
julgamento (quando um achado sustenta a narrativa vs. quando vira lacuna
registrada) arriscaria automatizar exatamente o tipo de falso-positivo
já documentado em ADR 0001.

### 3. Critério de revisão

Revisitar a decisão de manter a busca manual **após 3 ciclos mensais
bem-sucedidos** (narrativa aprovada e publicada, achados citáveis e
lacunas registradas corretamente, sem incidente de causalidade
inventada). Se o padrão se mostrar estável e repetível, avaliar
automação assistida (busca sugerida, revisão humana ainda obrigatória) —
nunca publicação sem aprovação explícita, independentemente do que for
automatizado depois.

## Consequências

- Volume de publicação da narrativa é limitado pela disponibilidade de
  revisão humana — aceito, é o ponto da decisão.
- A seção "Narrativa do mês" só aparece na página 2 do Reporting V3 em
  meses com arquivo aprovado; todo mês sem aprovação gera o relatório
  exatamente como antes desta ADR (nenhuma mudança de layout ou de
  número).
- Texto de narrativa é entrada de tamanho livre (fronteira de confiança)
  — truncado no carregamento (`narrativa_mensal.MAX_CARACTERES_TEXTO`,
  ver `src/reporting/narrativa_mensal.py`) para nunca sobrepor o rodapé
  da página, com aviso logado e referência ao arquivo fonte completo.

## Alternativas consideradas

- **Gerar a narrativa via LLM dentro do pipeline**: rejeitada — é
  exatamente o padrão de causalidade não verificada que
  `reporting/narrative.py` já evita deliberadamente (ver docstring
  daquele módulo).
- **Aprovação implícita (qualquer arquivo presente é publicado)**:
  rejeitada — remove o único portão de revisão humana; um rascunho
  esquecido no diretório vazaria para o relatório publicado.
- **Automatizar a busca já nesta etapa**: rejeitada por ora — ADR 0001
  já demonstrou que acesso automatizado a fontes financeiras deste tipo
  produz falso-positivo sem verificação humana; melhor validar o
  julgamento manual (achado sólido vs. lacuna) por alguns ciclos antes
  de automatizar a parte mais frágil do processo.
