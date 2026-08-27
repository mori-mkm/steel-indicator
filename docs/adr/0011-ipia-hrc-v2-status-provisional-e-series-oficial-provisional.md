# 0011 - IPIA-HRC V2 PIA-based: status PROVISIONAL e séries oficial/provisional separadas

## Contexto

O ADR 0010 introduziu o Domestic Price V2 caminho PIA
(`preco_domestico_hrc_pia_v2()`): benchmark anual PIA-Produto + IPP
242-Siderurgia via Proportional Denton, cobrindo 2019-2023 como janela
BENCHMARKED e 2024+ como extensão PROVISIONAL (encadeada, nunca
promovida a publication-grade automaticamente). Esse ADR avaliou, mas
explicitamente não implementou, a integração real desse caminho com o
import side V2 (`agregar_ipia_hrc_multi_ncm_mensal`, ADR 0009) — deixou
isso para um batch futuro.

Faltavam, antes de fechar essa integração:

1. um vocabulário de `publication_status` que represente honestamente um
   mês cujo lado doméstico é provisório — sem forçá-lo a `UNKNOWN` (que
   descartaria informação real) nem a `PUBLICATION_GRADE`/`EXPERIMENTAL`
   com uma flag adicional (que misturaria dado provisório com dado
   publicado no mesmo contrato de estabilidade);
2. uma regra explícita para impedir que uma atualização normal do
   provisional (novo mês de IPP, ou uma nova PIA reprocessando o Denton
   conjunto) mude números já publicados como oficiais — sem construir
   toda a infraestrutura de vintage/persistência ainda fora de escopo.

## Decisão

1. **Quarto status, `PROVISIONAL`**, definido em `indices_setoriais.py`
   (não em `steel_indicator.parameters.trade_policy` — não é um status de
   política comercial; `status_efetivo()` nunca devolve `PROVISIONAL`).
   Vocabulário final de `publication_status` no nível composto:
   `PUBLICATION_GRADE`, `EXPERIMENTAL`, `PROVISIONAL`, `UNKNOWN`.
2. **Regra de status conjunta**, usando dinamicamente o último ano PIA
   benchmarked (`last_pia_year`, nunca hardcoded):
   - domestico ausente ou import `UNKNOWN` → `UNKNOWN`;
   - domestico BENCHMARKED + import `EXPERIMENTAL` → `EXPERIMENTAL`;
   - domestico BENCHMARKED + import `PUBLICATION_GRADE` →
     `PUBLICATION_GRADE`;
   - domestico PROVISIONAL + import calculável (`EXPERIMENTAL` ou
     `PUBLICATION_GRADE`) → `PROVISIONAL`, sempre.
   `domestic_is_proxy` continua ortogonal a `publication_status` nos
   quatro casos.
3. **Duas séries de saída explicitamente separadas**, nunca concatenadas
   automaticamente: OFFICIAL (só `EXPERIMENTAL`/`PUBLICATION_GRADE`) e
   PROVISIONAL (só `PROVISIONAL`, com `is_provisional`/`last_pia_year`
   adicionais). Meses `UNKNOWN` não entram em nenhum dos dois arquivos
   publicados. O cálculo econômico não muda — `IPIA = preço doméstico /
   PPI × 100`, o mesmo `ipia()` de sempre — a separação é contrato de
   estabilidade de publicação.
4. **Congelamento no fluxo normal via sobrescrita, não Denton
   condicionado**: `calcular_ipia_hrc_v2_pia(congelado_df=...)` aceita a
   saída OFFICIAL de uma execução anterior e sobrescreve, verbatim, todo
   mês nela presente, descartando o recálculo fresco para esses meses —
   qualquer que seja a causa da mudança upstream (revisão de IPP, ou a
   propriedade conhecida do Denton conjunto ao somar um novo ano de PIA,
   já documentada no ADR 0010). A decisão original permitia, mas não
   exigia, implementar um Denton condicionado ao último ponto congelado
   "se necessário" para promover meses provisórios a benchmarked com
   continuidade suave; optou-se por **não** implementar essa variante
   nesta stage — a sobrescrita já garante a invariante exigida (nenhum mês
   OFFICIAL publicado muda) com uma implementação mais simples e auditável
   que não toca `denton_proporcional()`. O tradeoff aceito: a transição
   entre o último mês congelado e o primeiro mês recém-promovido a
   benchmarked por uma nova PIA pode ter uma continuidade um pouco menos
   suave do que um Denton condicionado produziria — decisão explícita,
   revisitável se isso se mostrar material com dado real.
5. **Duas exceções futuras ao congelamento, não implementadas**: (a)
   correção/revisão oficial da fonte IBGE; (b) mudança metodológica
   deliberada. A decisão aprovada exige apenas que a arquitetura não as
   torne impossíveis — `congelado_df` é um parâmetro simples, substituível
   por um mecanismo de vintage completo no futuro sem quebrar a assinatura
   pública de `calcular_ipia_hrc_v2_pia()`.
6. **Nenhuma infraestrutura de persistência/vintage nova**: `congelado_df`
   é responsabilidade do chamador (orquestração externa, ex. um script que
   lê o CSV OFFICIAL anterior). O valor corrente do IPIA é sempre exibido
   como PROVISIONAL, nunca como definitivo.
7. **Ancora corporativa nunca entra neste caminho**: `calcular_ipia_hrc_v2_pia()`
   usa exclusivamente `preco_domestico_hrc_pia_v2()` como fonte doméstica
   (parâmetro `pia_domestico_df`) — `preco_domestico_hrc_mensal_v2()`
   (Usiminas+CSN) continua existindo, testado, como benchmark
   independente (ADR 0010 item 2), mas não é lido nem chamado por este
   caminho.

## Alternativas consideradas

- **Denton condicionado ao último ponto congelado** (explicitamente
  permitido pela decisão aprovada, "se necessário"): rejeitado nesta
  stage por não ser necessário para satisfazer a invariante de
  congelamento exigida — a sobrescrita verbatim já garante isso de forma
  mais simples. Permanece como opção documentada caso a continuidade na
  fronteira benchmarked/provisional se mostre material o suficiente para
  justificar a complexidade adicional (resolver um KKT restrito a partir
  de um ponto fixo).
- **Reabrir/tratar `PROVISIONAL` como `PUBLICATION_GRADE`/`EXPERIMENTAL`
  com uma flag `is_provisional=True`**: rejeitado — a decisão aprovada
  proíbe explicitamente esse padrão; misturaria dado provisório com o
  contrato de estabilidade da série oficial.
- **Descartar meses provisórios (tratar como `UNKNOWN`)**: rejeitado —
  jogaria fora informação real (o valor corrente calculável) sem
  necessidade; o objetivo é mostrar o valor corrente explicitamente
  rotulado como sujeito a revisão, não escondê-lo.

## Consequências

- O IPIA-HRC V2 PIA-based passa a ter cobertura publication-relevante
  bem maior que o caminho corporate antigo: OFFICIAL cobre 2019-02 a
  2023-12 (48 meses calculáveis — 27 `EXPERIMENTAL`, 21
  `PUBLICATION_GRADE`), mais 30 meses PROVISIONAL (2024-01 a 2026-06, na
  data desta execução) mostrando o valor corrente explicitamente sujeito
  a revisão.
- Comparado ao IPIA-HRC V2 corporate antigo nos 15 meses sobrepostos
  (2025-04 a 2026-06): o novo IPIA fica sistematicamente abaixo, delta
  médio -11,66%, desvio-padrão 1,49pp — mesma magnitude/estabilidade já
  medida no nível de preço doméstico isolado (ADR 0010), agora propagada
  para o índice completo. Confirma que a correção de product-mix do lado
  doméstico é a explicação estrutural dominante do gap.
- `docs/METODOLOGIA.md` §12.11 registra a decisão completa.
- Ainda **não conectado** a `--selftest`/CLI/relatório oficial — mesmo
  status dos demais caminhos V2 (peça de cálculo interna, testada,
  validada com dado real via `scripts/gerar_ipia_hrc_v2_pia.py`).
- Publicar este caminho como definitivo continua bloqueado pelos mesmos
  itens já registrados em `docs/METODOLOGIA.md` §15 (bloqueantes do IPIA
  V2) e pela ausência de um mecanismo de vintage/revisão real para a
  janela provisional — este ADR só resolve a semântica de status e a
  separação de saída, não a publicação.
