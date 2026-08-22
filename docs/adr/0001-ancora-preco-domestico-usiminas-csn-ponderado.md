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
  na coluna `empresas` do resultado de `preco_domestico_ponderado()` (ver
  `data/curated/preco_domestico_aco.csv`, que hoje tem só Usiminas no 1T26
  e só CSN no 2T26 — trimestres desencontrados, não a mesma janela para as
  duas empresas ainda).
- Conforme mais trimestres forem curados no CSV (idealmente com as duas
  empresas no mesmo trimestre), o blend passa a refletir de fato uma média
  ponderada das duas.
