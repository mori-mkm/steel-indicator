# IPIA Brasil — Índices Setoriais

## Objetivo
Este projeto implementa um motor de cálculo de índices setoriais brasileiros
sobre dado público — começando pelo IPIA (Índice de Paridade de Importação do
Aço, bobina laminada a quente), com vergalhão e cesta multi-produto planejados
em seguida. A referência metodológica (janela de padronização congelada,
escala 0–100 ancorada em 50, pesos teóricos fixos, cobertura mínima) segue o
manual de índices setoriais do projeto — ver "Contexto e documentos de
referência" abaixo.

## Stack principal
- Python
- pandas, numpy
- requests (chamadas a APIs públicas: BCB/SGS, Comex Stat)
- argparse (CLI em `src/indices_setoriais.py`)
- Testes: autoteste embutido via `--selftest` (função `check()` dentro do
  próprio script) — **não é pytest**. Se migrar para pytest no futuro, isso é
  uma decisão de arquitetura e entra na regra de "trade-off de arquitetura"
  abaixo, não uma troca silenciosa.

## Princípios de desenvolvimento
- Prefira mudanças pequenas, testáveis e reversíveis — um teste novo por
  comportamento novo, sempre no mesmo commit da mudança que ele testa.
- Não altere a arquitetura do motor (estrutura de `ParamsIPIA`, `SETORES`,
  formato de saída dos DataFrames) sem justificar a decisão.
- Preserve compatibilidade com o comportamento existente quando possível —
  todo parâmetro novo entra com default que reproduz o cálculo antigo (é o
  padrão já usado em `antidumping_usd_t=0.0`).
- Toda constante de calibração (câmbio, alíquotas, antidumping, volume
  mínimo, janela de referência) é parâmetro nomeado e documentado — nunca um
  número solto no meio do cálculo.
- Não introduza dependências sem necessidade clara.
- Não invente resultados de execução, valores de API ou status regulatório
  (ex.: se antidumping foi ou não aplicado). Se não for possível confirmar
  rodando ou buscando de verdade, declare explicitamente que está
  desconhecido/não verificado — não preencha com estimativa disfarçada de
  fato.
- Nenhum dado deve ser fabricado ou estimado silenciosamente onde a fonte
  real não existir ou não puder ser checada. Interpolação, suavização e
  proxies são aceitáveis, mas sempre marcados em coluna/flag explícita (ex.:
  `interpolado`, `suavizado`, `peso_confiabilidade`) — nunca indistinguíveis
  do dado bruto.

## Workflow obrigatório
Ao receber uma tarefa:
1. Inspecione o código relevante antes de propor alterações.
2. Para mudanças relevantes, apresente primeiro um plano.
3. Depois da aprovação, implemente a solução.
4. Execute `--selftest` (e `--check-sources` quando a mudança tocar chamada
   de rede real).
5. Leia a saída real dos testes — nunca presuma que passou.
6. Se houver falha ou erro de API (403, schema diferente, coluna trocada),
   diagnostique a partir do erro real antes de tentar de novo. Erro de rede
   real (ex.: API mudou de GET para POST) é diferente de bloqueio de
   ambiente — não trate um pelo outro sem checar.
7. Corrija e execute novamente.
8. Não declare a tarefa concluída enquanto `--selftest` não tiver rodado e
   passado de verdade.
9. Ao terminar, informe:
   - arquivos modificados;
   - decisões tomadas;
   - testes executados;
   - resultado dos testes;
   - riscos ou pendências (ex.: dado ainda não confirmado, status
     regulatório em aberto, granularidade de fonte não verificada).

## Autonomia
Claude deve executar diretamente os comandos necessários quando possuir
acesso às ferramentas — incluindo `--check-sources` e chamadas reais às APIs
públicas (BCB, Comex Stat), já que rodando localmente no ambiente do usuário
Claude tem acesso à rede real, diferente de um ambiente sandboxed sem saída.
Não peça ao usuário para executar manualmente comandos que Claude possa
executar.

O usuário deve ser envolvido quando houver:
- decisão de escopo (ex.: qual produto/NCM entra no índice, qual empresa é
  âncora de preço doméstico);
- trade-off de arquitetura (ex.: migrar de autoteste embutido para pytest);
- mudança relevante de comportamento do cálculo (ex.: trocar critério de
  peso de confiabilidade, mudar janela de referência);
- remoção de dado;
- alteração destrutiva;
- escolha de negócio sem resposta técnica objetiva (ex.: como tratar meses
  de peso reduzido, threshold de volume mínimo, o que publicar vs. o que
  fica só como diagnóstico interno).

## Git
- Pode consultar `git status`, `git diff` e `git log`.
- Não executar `git push` sem autorização explícita.
- Não alterar histórico Git sem autorização explícita.
- Não executar comandos destrutivos como `reset --hard` sem autorização
  explícita.
- Repositório é público — nunca commitar dado sensível, chave de API, ou
  qualquer material de cliente (ver Segurança).

## Segurança
- Nunca acessar, exibir ou modificar arquivos `.env`.
- Nunca imprimir credenciais ou tokens.
- Nunca armazenar segredos no código.
- Nunca adicionar a este repositório (mesmo que temporariamente, mesmo fora
  do commit) qualquer material preparado para o Jonas Siqueira (relatório de
  casa de research, modelo financeiro, ou qualquer documento com estratégia
  comercial de terceiro) — esse conteúdo é de outro engajamento e fica fora
  deste repo por decisão já tomada.

## Contexto e documentos de referência
- `src/indices_setoriais.py`: motor de cálculo (ICCS, IPIA), com
  `NCM_BOBINA_QUENTE`, `ParamsIPIA`, `serie_mensal_preco_bobina` e o
  autoteste.
- A metodologia completa (fórmulas do ICCS/IPIA, regras de governança,
  matriz de licenciamento de fonte) vive num manual metodológico que **não
  está neste repositório** — foi preparado para outro engajamento e contém
  informação de terceiro. Se uma sessão futura precisar da metodologia
  completa e não tiver esse contexto, é melhor perguntar do que assumir.
  Considerar criar um `docs/METODOLOGIA.md` só com as regras de cálculo
  (sem o conteúdo de negócio/estratégia) para não depender de memória de
  conversa.
- Pendências conhecidas no momento em que este arquivo foi criado: (1)
  âncora de preço doméstico via ITR/release de Usiminas/CSN ainda não
  confirmada quanto à granularidade por produto; (2) status definitivo do
  antidumping de laminado a quente da China (esperado para julho/2026,
  ainda não confirmado) — afeta `antidumping_usd_t`.
