# 0002 - Encadeamento trimestre→mês do preço doméstico via IPP/IBGE

## Contexto

O preço doméstico de aço só é conhecido por trimestre (release de
resultados de Usiminas/CSN), mas o IPIA e o custo de importação
(`custo_importacao_rs_t`) são mensais. É preciso expandir um nível
trimestral em 3 pontos mensais sem inventar dado.

## Decisão

`encadear_preco_domestico_mensal()` usa o **IPP do IBGE (SIDRA, tabela
6903, CNAE 24 - Metalurgia)** para projetar o nível trimestral mês a mês
depois que o trimestre confirmado termina, até o próximo release sair:

```
preco(mes M) = nivel_trimestral_confirmado * (IPP[M] / IPP[ultimo mes do trimestre confirmado])
```

Dentro dos 3 meses do próprio trimestre já confirmado, o nível é usado
direto (`metodo="nivel_trimestral"`) — não há o que encadear, é o dado
real daquele trimestre. Quando o IPP de um mês específico ainda não foi
divulgado, cai em `hold_flat_fallback` (repete o último nível calculado)
em vez de deixar `NaN` ou extrapolar.

Tabela SIDRA confirmada ao vivo nesta sessão via
`servicodados.ibge.gov.br/api/v3/agregados/6903/metadados`: variável
10008 (número-índice, dez/2018=100), classificação 842, categoria 46641 =
"24 METALURGIA". A tabela 5796 (que aparece em buscas antigas por "IPP
CNAE") está **encerrada desde jan/2019** — não usar.

## Alternativas consideradas

- **Interpolação linear entre trimestres** (o método já usado no lado da
  importação para buracos pontuais no Comex Stat): aqui teria um problema
  diferente — para preencher os 2 primeiros meses de um trimestre ainda
  em andamento, precisaria do valor do trimestre SEGUINTE, que só é
  conhecido depois que ele termina e o release sai. Isso é look-ahead bias:
  usar dado futuro (ainda não publicado no momento em questão) para
  preencher o passado. Inadequado para um índice pensado para uso em tempo
  real/nowcast.
- **Hold flat puro** (repetir o valor do último trimestre confirmado até o
  próximo, sem nenhum ajuste): evita look-ahead, mas joga fora informação
  mensal real e disponível (o IPP já sinaliza, mês a mês, para que lado o
  preço de metalurgia está indo). Vira só o *fallback* de
  `encadear_preco_domestico_mensal`, usado apenas quando o IPP do mês
  específico ainda não foi divulgado.

## Consequências

- O IPIA mensal, nos meses entre um release trimestral e o próximo,
  reflete uma projeção via IPP, não um dado direto de Usiminas/CSN —
  isso fica marcado explicitamente na coluna `metodo`
  (`"nivel_trimestral"` vs. `"encadeado_ipp"` vs. `"hold_flat_fallback"`),
  nunca escondido.
- Se o IPP e o preço real de bobina a quente divergirem de forma
  persistente (ex.: um choque específico do mercado de aço que não se
  reflita no IPP agregado da metalurgia), a projeção mensal erra até o
  próximo trimestre confirmar/corrigir o nível. É um risco conhecido,
  aceitável dado que a alternativa (hold flat ou interpolação com
  look-ahead) é pior nos dois casos.
