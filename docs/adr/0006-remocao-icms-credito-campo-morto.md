# 0006 - Remoção de `icms_credito` (campo morto) e decisão de não modelar ICMS por enquanto

## Contexto

`ParamsIPIA` tinha um campo `icms_credito: bool = True` com o comentário
"se o comprador credita ICMS". Investigação (23/08/2026) confirmou que
esse campo **nunca foi lido em lugar nenhum do código**:
`custo_importacao_rs_t()` monta o custo de importação a partir de CIF,
II, AFRMM, antidumping, despesas de porto, frete interno e margem — sem
nenhum termo de ICMS, embutido ou explícito. Busca por "icms" em todo o
repositório não encontrou nenhum ADR ou nota em
`docs/METODOLOGIA.md` (antes desta tarefa) registrando isso como decisão
deliberada — só a própria declaração do campo. Ou seja: **código morto**,
não a implementação de uma premissa pensada, mesmo que o nome do campo
sugerisse o contrário.

## Decisão

1. **Remover** `icms_credito` de `ParamsIPIA` (`src/indices_setoriais.py`).
   Confirmado antes da remoção que nenhuma outra parte do código
   referenciava o campo (busca em todo o repositório, só 3 ocorrências:
   a declaração e duas notas em `docs/METODOLOGIA.md` já escritas numa
   tarefa anterior descrevendo o próprio problema).
2. **Não implementar ICMS agora.** Documentar em
   `docs/METODOLOGIA.md` (seção de limitações), como decisão nova e
   datada (23/08/2026) — não como premissa retroativa que "sempre
   existiu" —, a razão econômica: o público-alvo típico do IPIA
   (importador que revende) normalmente credita o ICMS pago na
   importação, então o efeito é majoritariamente de caixa (timing), não
   custo econômico líquido, para esse perfil.
3. **Condição de revisão explícita**: se o índice precisar servir um
   perfil de comprador que não credita ICMS (consumidor final, empresa
   em regime que não credita), essa decisão precisa ser revisitada —
   nesse perfil ICMS é custo real e a paridade calculada hoje subestima
   o custo de importação.

## Alternativas consideradas

- **Opção A - manter fora do cálculo, só documentar a premissa**: mesmo
  efeito técnico de resultado que a Opção C (nenhuma mudança no `ppi_brl_t`
  calculado), mas mantém no código um campo (`icms_credito`) que sugere
  uma opção configurável funcional quando na verdade não é — o booleano
  existiria sem nunca ser lido, o que é mais enganoso do que não ter o
  campo. Descartada por esse motivo, mesmo concordando com a razão
  econômica de A (que foi incorporada na decisão final, só que como nota
  de limitação, não como campo morto no código).
- **Opção B - implementar de verdade**: adicionar um componente real de
  ICMS ao custo quando o comprador não credita. Rejeitada por ora porque
  exige (i) levantar a alíquota de ICMS-importação correta — varia por
  estado de desembaraço e por regime (ex.: a Resolução do Senado 13/2012
  prevê 4% para importados com conteúdo de importação >40% sujeitos à
  lista CAMEX — não confirmado se bobina a quente se enquadra; isso é
  pendência de dado nova, não algo já levantado no projeto) — e (ii)
  resolver o cálculo "por dentro" do ICMS (o imposto compõe a própria
  base de cálculo, gross-up), estruturalmente diferente de AFRMM/II
  aqui, que são sobretaxas simples aplicadas uma vez sobre uma base já
  fechada. Sem necessidade real hoje de modelar o perfil "não credita",
  o custo de implementar corretamente não se justifica ainda.
- **Opção C (escolhida) - remover o campo, documentar como limitação
  conhecida, reintroduzir quando houver necessidade real.**

## Consequências

- `ParamsIPIA` fica com um parâmetro a menos; nenhuma mudança de
  resultado do índice (o campo nunca teve efeito).
- `docs/METODOLOGIA.md` passa a descrever "índice não modela ICMS" como
  limitação conhecida com razão econômica explícita, em vez de "campo
  declarado mas não usado" — mais honesto sobre o estado real do código.
- Se o campo for reintroduzido no futuro (Opção B), será como
  implementação nova de verdade, não reativação de código morto — a
  alíquota e o cálculo "por dentro" precisam ser resolvidos do zero.
