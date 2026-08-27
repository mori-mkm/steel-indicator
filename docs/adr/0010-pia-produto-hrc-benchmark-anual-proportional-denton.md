# 0010 - PIA-Produto como benchmark anual do Domestic Price HRC V2, via Proportional Denton

## Contexto

A âncora doméstica corporativa do IPIA-HRC V2 (ADR 0001,
`preco_domestico_hrc_mensal_v2()`) usa `receita/volume` de Usiminas+CSN no
segmento "Siderurgia" inteiro — nunca especificamente bobina a quente
(HRC). A primeira validação econômica end-to-end do IPIA-HRC V2 (15 meses
calculáveis, 2025-04 a 2026-06) mostrou IPIA médio ≈133, e apontou essa
mistura de produto como a explicação estrutural mais provável do nível
elevado.

Duas investigações Level 3 (`docs/research/hrc_domestic_price_sources.md`,
completo e adendo) mapearam fontes alternativas e encontraram a IBGE
PIA-Produto (tabela SIDRA 7752, categoria Prodlist 2422.2020 "Bobinas a
quente de aços ao carbono, não revestidos") como fonte pública,
estruturada, verificada ao vivo, genuinamente específica de HRC — ao
contrário da âncora corporativa. A investigação também confirmou, contra
a nota técnica oficial do IBGE, que a PIA-Produto **não separa mercado
interno de exportação** a nível de produto, e mediu essa exposição
cruzando com o Comex Stat: exportação representa 12%-43% (mediana 26,2%)
do volume vendido de HRC entre 2014-2023 — material, não desprezível.

## Decisão

1. **PIA-Produto 2422.2020 como benchmark ANUAL de nível**, não como
   âncora corporativa substituta. `preco_pia_hrc_y = receita_líquida_
   vendas_y / quantidade_vendida_y`. `provenance=CALCULADO`,
   `is_proxy=True`, `proxy_reason=DESTINATION_MIX` — nunca chamado de
   preço doméstico puro.
2. **Âncora corporativa (Usiminas+CSN) não faz splice/reancoragem da
   série PIA** — continua disponível só como benchmark independente de
   validação/sanity-check. Razão: mix de produto diferente entre as duas
   fontes e ausência de janela de sobreposição suficiente para calibrar
   uma transição (PIA cobre até 2023; a âncora corporativa curada hoje só
   cobre 2025Q2 em diante).
3. **IPP 242-Siderurgia como indicador mensal de movimento**
   (`ibge_sidra_ipp_siderurgia`, já existente, reaproveitado sem
   alteração) — `is_proxy=True`, `proxy_reason=PRODUCT_AGGREGATION`
   (mesmo motivo já registrado no §12.9/ADR anterior, agora nomeado
   explicitamente como razão de proxy separada da razão da PIA).
4. **Benchmarking temporal via Proportional Denton** (primeiras
   diferenças — IMF *Quarterly National Accounts Manual*, cap. 6):
   minimiza a soma dos quadrados das diferenças mês a mês da razão
   preço/indicador, sujeito a `mean(preço mensal do ano) == preço PIA
   daquele ano`. Implementado em `denton_proporcional()` como sistema
   linear KKT resolvido via `numpy.linalg.solve` — sem framework de
   otimização/disaggregation temporal, sem nova dependência. Nunca
   forward-fill anual, interpolação linear simples, pro-rata por ano ou
   reancoragem abrupta em janeiro.
5. **Constraint rotulada `TEMPORAL_ALLOCATION_PROXY`**: a restrição usa
   média mensal simples (não ponderada por quantidade doméstica mensal
   de HRC, que não existe hoje) como aproximação explícita do *unit
   value* real da PIA. Não foi inventado nenhum peso mensal para
   substituir essa lacuna.
6. **Cobertura real confirmada programaticamente**: IPP 242-Siderurgia
   começa em dez/2018 (tabela SIDRA 6723); a janela onde PIA anual + IPP
   mensal completo coexistem é 2019-2023 (60 meses). Anos de PIA sem os
   12 meses do IPP (2014-2018) não geram série mensal artificial — ficam
   só como benchmark anual isolado.
7. **Extensão provisional pós-última-PIA** (2024 em diante, hoje): preço
   encadeado a partir da última relação preço-benchmarked/IPP observada
   (mesma fórmula de `encadear_preco_domestico_mensal`).
   `provenance=ESTIMADO`, `is_proxy=True`, `is_provisional=True`. Nunca
   promovida a publication-grade automaticamente; nunca misturada
   silenciosamente com a janela benchmarked. `pia_reference_year`
   preservado em toda linha (campo mínimo necessário para reprocessar os
   meses provisórios quando uma nova PIA sair — mecanismo de revisão em
   si **não** implementado nesta stage).
8. **Publication status do IPIA** (só avaliado, integração real é batch
   futuro): domestic proxy é ortogonal a `publication_status` — um mês
   com domestic_is_proxy=True pode ainda ser PUBLICATION_GRADE se o lado
   de importação for PUBLICATION_GRADE (mesma regra já usada pela âncora
   corporativa, §12.9). A janela provisional (2024+) não deve ser
   promovida a publication-grade automaticamente ao integrar — decisão
   de quem fizer essa integração, fora desta stage.
9. **Novo caminho explícito**: `preco_domestico_hrc_pia_v2()` — não
   substitui nem remove `preco_domestico_hrc_mensal_v2()` (corporativo).
   Não conectado a `--selftest`/CLI/relatório nesta stage.

## Propriedade conhecida (documentada, não escondida)

O Denton é resolvido em conjunto para toda a janela benchmarked (para
suavizar a fronteira entre anos — é o próprio motivo de usar Denton em
vez de pro-rata). Isso significa que, ao reprocessar a série com um novo
ano de PIA, meses de anos mais antigos perto da nova fronteira podem
mudar levemente — prática padrão de temporal benchmarking (IMF QNA
Manual), não uma falha de look-ahead. A média anual de cada ano continua
batendo exatamente o alvo PIA em qualquer reprocessamento (garantia que
não muda). A extensão provisional nunca olha para frente: depende só do
IPP até o próprio mês (verificado em teste dedicado,
`tests/unit/test_preco_domestico_hrc_pia_v2.py`).

## Alternativas consideradas

Avaliadas formalmente na investigação Level 3 anterior
(`docs/research/hrc_domestic_price_sources.md`):

- **Option A (PIA sem qualificação de proxy)** — rejeitada: exposição a
  exportação medida (12%-43%) é material demais para tratar como preço
  doméstico puro sem selo.
- **Option C (PIA só como benchmark, nunca âncora)** — mais conservadora,
  também defensável; rejeitada em favor de Option B porque a PIA já seria
  usada como referência de validação de qualquer forma (§10 desta ADR),
  e negá-la como âncore desperdiçaria a cobertura histórica real
  (2019-2023) que ela sustenta com boa qualidade (fonte oficial,
  produto-específica, verificada).
- **Option D (ajuste de exportação)** — rejeitada por falta de evidência
  suficiente: a fração de exportação varia sem tendência limpa (12%-43%)
  e o preço de exportação, embora sistematicamente mais baixo que o preço
  combinado em todos os anos testados, não tem magnitude precisa o
  bastante (câmbio anual médio, não por embarque; sem confirmação
  linha-a-linha entre receita PIA e FOB Comex) para virar um ajuste
  oficial. Registrada como direção de pesquisa futura, não implementada.

## Consequências

- Domestic Price V2 passa a ter DOIS caminhos coexistindo, nunca
  combinados por reancoragem: corporativo (Usiminas+CSN, curadoria
  trimestral, 2025Q2+ hoje) e PIA-Produto (benchmark anual + IPP mensal,
  2019-2023 benchmarked + extensão provisional 2024+).
- Cobertura potencial do IPIA-HRC V2 aumenta materialmente: de 15 meses
  calculáveis hoje para até ~90 meses (2019-01 a 2026-06, na data desta
  execução), sujeito a decisão futura sobre publication_status da janela
  provisional e à integração real com o import side (não feita nesta
  stage).
- Nenhum mecanismo de revisão/vintage foi implementado — só os campos
  (`pia_reference_year`, `is_provisional`) que permitem construí-lo depois.
  Publicar a extensão provisional como se fosse definitiva, sem um plano
  de revisão quando a próxima PIA sair, seria uma lacuna de honestidade
  editorial — deve ser resolvida antes de qualquer publicação real dessa
  janela.
- `docs/METODOLOGIA.md` §12.10 registra a decisão completa.
