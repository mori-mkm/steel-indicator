# Metodologia de cálculo — IPIA

Este documento descreve **como** o motor calcula o IPIA hoje, derivado
diretamente de `src/indices_setoriais.py` e dos ADRs em `docs/adr/`. Não
duplica o "porquê" já registrado nos ADRs — linka para eles. Não contém
nada de estratégia de negócio, precificação de produto ou material de
terceiro; é só a metodologia de cálculo em si.

Escopo: cobre o **IPIA** (Índice de Paridade de Importação do Aço,
bobina laminada a quente), que é o único índice com coleta e cálculo
ponta a ponta implementados hoje. O **ICCS** (Índice de Condições de
Crédito Setorial) existe só como especificação de pilares/pesos/fontes
(`ICCS` em `src/indices_setoriais.py`) — sem nenhum coletor implementado
ainda, então não há "como calcular" real para documentar além da
especificação em si (rodável via `--spec`).

## 1. Fórmula do IPIA

```
IPIA = (preço_doméstico_R$/t / custo_de_importação_posto_no_cliente_R$/t) × 100
```

Implementada em `ipia(preco_domestico_rs_t, ppi_rs_t)`.

- **IPIA > 100**: preço doméstico acima da paridade de importação —
  importar compensaria mais que comprar do produtor local.
- **IPIA < 100**: preço doméstico abaixo da paridade — o produtor local
  está protegido pela distância até o custo de importar.
- **IPIA = 100**: preço doméstico exatamente igual ao custo de importação
  posto no cliente.

Os dois insumos vêm de caminhos de cálculo independentes (seções 2 e 6
abaixo) e são combinados por `calcular_ipia_mensal(ano_ini, ano_fim)`,
que é a função central usada tanto pelo CLI `--ipia` (saída CSV) quanto
pelo relatório `--pdf-ipia` — as duas saídas nunca divergem porque
chamam a mesma função.

## 2. Custo de importação posto no cliente (paridade)

Implementado em `custo_importacao_rs_t(preco_fob_usd_t, frete_usd_t, seguro_usd_t, cambio, p: ParamsIPIA)`.

Entrada: FOB, frete e seguro em US$/t (do Comex Stat, ver seção 3) e
câmbio (BCB/SGS, série `cambio_venda`, PTAX). O FOB usado é
`preco_usd_t_publicado` — a série **já com suavização seletiva aplicada**
(ver seção 5.2) — não o `preco_usd_t` bruto; frete e seguro não são
suavizados, entram brutos. Ver [ADR 0005](adr/0005-suavizacao-seletiva-preco-importacao.md)
para o porquê dessa escolha. Sequência de cálculo:

| Etapa | Fórmula | Coluna de saída |
|---|---|---|
| CIF em US$/t | `FOB + frete + seguro` | `cif_usd_t` |
| CIF em R$/t | `CIF_usd × câmbio` | `cif_brl_t` |
| Imposto de Importação | `CIF_brl × aliquota_ii` | `ii_brl_t` |
| AFRMM | `(frete_usd × câmbio) × afrmm` | `afrmm_brl_t` |
| Antidumping | `antidumping_usd_t × câmbio` | `antidumping_brl_t` |
| Base | `CIF_brl + II + AFRMM + antidumping + despesas_porto_rs_t + frete_interno_rs_t` | — |
| Total (paridade) | `Base × (1 + margem_importador)` | `ppi_brl_t` |

Todos os parâmetros de internação vêm da dataclass `ParamsIPIA` — o
único bloco explicitamente marcado no código como subjetivo/calibrável,
com os defaults atuais:

| Parâmetro | Default | Significado |
|---|---|---|
| `aliquota_ii` | 0.108 | Imposto de Importação da NCM (TEC) |
| `afrmm` | 0.08 | Adicional de Frete para Renovação da Marinha Mercante, 8% sobre o frete marítimo |
| `despesas_porto_rs_t` | R$ 210,00/t | Capatazia, armazenagem, despacho |
| `frete_interno_rs_t` | R$ 140,00/t | Porto → cliente |
| `margem_importador` | 0.03 | Margem da trading/importador |
| `icms_credito` | `True` | **Declarado mas não usado** em `custo_importacao_rs_t` hoje — nenhum efeito no cálculo atual. Ver seção 8 (limitações). |
| `antidumping_usd_t` | 0.0 | Direito específico em US$/t. Zerado por padrão — status para bobina a quente da China não confirmado como definitivo na última checagem (ver seção 8). |

## 3. NCMs de bobina a quente (`NCM_BOBINA_QUENTE`)

13 códigos NCM de 8 dígitos, agrupados em três categorias:

- `com_relevo`: `72081000`
- `decapada`: `72082500`, `72082610`, `72082690`, `72082710`, `72082790`
- `nao_decapada`: `72083610`, `72083690`, `72083700`, `72083810`, `72083890`, `72083910`, `72083990`

Escopo: bobina laminada a quente **não ligada**, largura **≥ 600mm**,
filtrando só as posições "em rolos". Fonte da delimitação: Circular
SECEX 39/2025 (abertura da investigação antidumping de laminados a
quente da China). Ficaram **fora** do escopo original da circular (e
portanto fora de `NCM_BOBINA_QUENTE`):

- `7208.40/53/54/90` — chapa, não enrolado (produto diferente de bobina).
- `7211.xx` — largura < 600mm.
- `7225`/`7226` — aço ligado (liga diferente).

O comentário no código marca explicitamente: "confirme no Siscomex antes
do primeiro cálculo" — a lista não teve confirmação adicional além da
leitura da circular.

## 4. Peso de confiabilidade por volume (não por número de registros)

`VOLUME_MINIMO_T = 5000.0` (toneladas/mês). Em
`serie_mensal_preco_bobina`, cada mês recebe:

```
peso_confiabilidade = min(toneladas_do_mes / VOLUME_MINIMO_T, 1.0)
```

caindo linearmente a partir de 1.0 abaixo do limiar, chegando a 0 para
volumes muito pequenos. **Não** usa `n_registros` (quantidade de
combinações NCM×país no mês) como critério.

Racional (comentário no código, seção `VOLUME_MINIMO_T`): um mês com
poucos parceiros comerciais mas volume grande é sinal de preço real —
ex. set/2021, pico de um supercycle: 27 mil t em só 6 registros, porque
o mercado global estava concentrado na escassez. Um mês com volume
pequeno (ex. jun/2020: 55 t em 3 registros) é ruído de fato. Usar
`n_registros` penalizaria exatamente os meses de maior conteúdo
informativo do índice. Testado em `--selftest` (seção 8c): dois meses
com o mesmo `n_registros` mas volumes muito diferentes recebem pesos
diferentes. Esse mesmo peso também decide quais meses são suavizados
(seção 5.2 abaixo) — um pico de supercycle de peso pleno nunca é
suavizado, mesmo com poucos registros.

## 5. Tratamento de meses faltantes e de baixo volume

Três tratamentos distintos, cada um resolvendo um problema diferente,
nunca aplicados ao mesmo dado:

### 5.1 Lado da importação — interpolação linear de meses faltantes (`serie_mensal_preco_bobina`)
Quando um mês não tem nenhum registro no Comex Stat, `preco_usd_t`,
`frete_usd_t`, `seguro_usd_t` e `toneladas` são preenchidos por
interpolação linear entre os meses vizinhos (`pandas.interpolate(method="linear")`).
Marcado explicitamente na coluna `interpolado` (booleana), e
`peso_confiabilidade` é forçado a `0.0` nesses meses — um mês
interpolado nunca é tratado como dado real, mesmo que o volume
interpolado por acaso caia acima do limiar. Documentado no código como
"provisório — o ideal é investigar por que o mês ficou sem dado antes de
publicar de verdade".

### 5.2 Lado da importação — suavização seletiva de meses de baixo volume (`suavizar_preco_importacao`)
Diferente da interpolação (que preenche meses **sem nenhum dado**), a
suavização seletiva reduz o ruído de meses que **têm** dado mas com
volume abaixo do mínimo (`peso_confiabilidade < 1.0`, ver seção 4):

```
preco_usd_t_publicado = media_movel_centrada_3_meses(preco_usd_t)   se peso_confiabilidade < 1.0
preco_usd_t_publicado = preco_usd_t                                 se peso_confiabilidade == 1.0 (nunca suaviza)
```

`rolling(window=3, center=True, min_periods=1)` sobre `preco_usd_t`. O
bruto (`preco_usd_t`) **nunca é sobrescrito** — fica sempre disponível
para auditoria — e a coluna booleana `suavizado` marca em quais meses o
publicado difere do bruto. Frete e seguro não são suavizados (só o
preço). É `preco_usd_t_publicado`, não o bruto, que alimenta
`custo_importacao_rs_t` dentro de `calcular_ipia_mensal` — ver
[ADR 0005](adr/0005-suavizacao-seletiva-preco-importacao.md) para essa
escolha e o porquê de não deixar as duas colunas coexistindo sem uma
sendo efetivamente usada no cálculo publicado. Testado em `--selftest`
(seção 8d): um mês de peso pleno (mesmo com poucos registros) mantém o
publicado idêntico ao bruto; um mês de peso reduzido recebe a média
móvel.

### 5.3 Lado doméstico — encadeamento via IPP, com hold-flat como fallback (`encadear_preco_domestico_mensal`)
Diferente da importação, aqui **não se usa interpolação linear** — o
motivo é look-ahead bias, explicado em detalhe no
[ADR 0002](adr/0002-encadeamento-trimestre-mes-via-ipp.md). Resumo
técnico do método:

1. Dentro do próprio trimestre já confirmado (release trimestral
   carregado), o nível é usado direto → `metodo="nivel_trimestral"`.
2. Depois do trimestre confirmado mais recente, até o próximo release
   sair, o nível é projetado mês a mês pela variação do IPP do IBGE
   (CNAE 24 – Metalurgia, tabela SIDRA 6903):
   ```
   preco(mes M) = nivel_trimestral_confirmado × (IPP[M] / IPP[último mês do trimestre confirmado])
   ```
   → `metodo="encadeado_ipp"`.
3. Se o IPP do mês `M` específico ainda não foi divulgado, repete o
   último nível calculado → `metodo="hold_flat_fallback"` (nunca vira
   `NaN`, nunca extrapola).

Cada mês da série de saída carrega o `metodo` usado, nunca escondido.

**Quando cada um se aplica, resumido**: interpolação linear é sempre
lado-importação e só para buracos pontuais (mês sem nenhum registro)
dentro de uma série mensal já disponível via API; suavização seletiva
também é lado-importação, mas para meses que **têm** dado, só reduz o
ruído de volume fino; encadeamento IPP/hold-flat é sempre lado-doméstico
e serve para *expandir* um nível trimestral (a granularidade real da
fonte) em pontos mensais, nunca para preencher buracos dentro do próprio
CSV curado.

## 6. Âncora de preço doméstico

Pipeline, em ordem:

1. `carregar_preco_domestico_trimestral()` lê `data/curated/preco_domestico_aco.csv`
   (curado manualmente, versionado no Git — ver
   [ADR 0003](adr/0003-dado-especifico-vs-proxy-e-versionamento-data-curated.md)).
   Calcula `preco_rs_t = receita_liquida_segmento_rs / volume_vendas_t`
   quando a coluna não vem pronta da fonte (é o caso da Usiminas; a CSN
   já publica "Preço Médio" explícito).
2. `preco_domestico_ponderado(df)` agrega por trimestre, empresa a
   empresa, com **média ponderada pelo volume de vendas de aço no
   trimestre** — não simples. Ver
   [ADR 0001](adr/0001-ancora-preco-domestico-usiminas-csn-ponderado.md)
   para o porquê de Usiminas+CSN ponderadas (vs. só uma das duas, vs.
   média simples). **Nota de escopo**: o ADR 0001 avalia como
   alternativas "só Usiminas", "só CSN" e "média simples" — a inclusão
   ou não de outras produtoras (ex. Gerdau) **não consta como
   alternativa avaliada** nessa decisão; se isso for relevante para o
   índice de bobina a quente especificamente, é uma extensão de escopo
   ainda em aberto, não decidida até aqui.
3. `encadear_preco_domestico_mensal(trimestral, ipp_mensal)` expande o
   trimestral em mensal (ver seção 5.2 acima e ADR 0002).

### `tipo_dado_domestico`: proxy vs. específico
Toda linha (empresa/trimestre) carrega um `tipo`:

- `"especifico_laminado_quente"`: dado específico de bobina a quente
  (hoje, **nenhuma linha carregada tem esse tipo** — ver seção 8).
- `"proxy_segmento_aco"`: agregado do segmento "Siderurgia"/"Aço" inteiro
  da empresa (chapas grossas + laminados a quente + laminados a frio +
  revestidos), usado como proxy. **É o tipo de todo dado carregado hoje.**
- `"misto"`: um trimestre agregado (`preco_domestico_ponderado`) onde as
  empresas que compõem o blend têm tipos diferentes entre si — o motor
  nunca finge que o blend inteiro é específico se só uma parte é. Regra
  implementada e testada em `--selftest` (seção 12).

Ver [ADR 0003](adr/0003-dado-especifico-vs-proxy-e-versionamento-data-curated.md)
para a investigação completa de por que a granularidade real disponível
hoje é "segmento", não "produto".

## 7. Fontes de dado e particularidades

| Fonte | Uso | Particularidade a saber |
|---|---|---|
| **Comex Stat** (`api-comexstat.mdic.gov.br/general`) | FOB, frete, seguro, peso por NCM/país/mês (importação) | O endpoint `/general` **exige POST** com JSON no corpo (`_post_json`). Uma chamada GET com filtro na querystring recebe **403 do WAF**, não é falta de acesso — erro já diagnosticado em sessão anterior, documentado no código para não ser re-investigado do zero. |
| **BCB/SGS** (`api.bcb.gov.br/dados/serie/...`) | Câmbio (PTAX, série `cambio_venda`, código 1) | Série diária: a API **rejeita (406)** janela de consulta acima de 10 anos para séries diárias — por isso `calcular_ipia_mensal` amarra o início da consulta a `ano_ini` em vez de usar o default de `sgs()` (2010), que sozinho já estoura o limite a partir de 2020. Códigos SGS têm status de confirmação heterogêneo (ver tabela abaixo). |
| **IBGE/SIDRA** (tabela 6903) | IPP mensal, CNAE 24 – Metalurgia, para encadeamento trimestre→mês | Variável 10008 (número-índice, dez/2018=100), classificação `842[46641]` = "24 METALURGIA". **Confirmada ao vivo** via `.../agregados/6903/metadados`. A tabela **5796** (que aparece em buscas antigas por "IPP CNAE") está **encerrada desde jan/2019** — não usar. |
| **Releases trimestrais Usiminas/CSN** | Preço doméstico (âncora) | Sem API — ingestão semi-manual via CSV curado (`data/curated/`). Ver seção 6 e ADR 0003. |

### Status dos códigos SGS (`SGS` dict)

| Código | Nome | Status |
|---|---|---|
| 21082 | `inad_total` | **Verificado ao vivo** (bateu com valor divulgado, jun/2026) |
| 21086 | `inad_pj_total` | **Verificado ao vivo** (idem) |
| 21084 | `inad_livres_total` | Valor plausível, rótulo **a confirmar** |
| 21083 | `inad_direc_total` | Valor plausível, rótulo **a confirmar** |
| 1 | `cambio_venda` | **A confirmar** (PTAX — checar ordem de grandeza) |
| 432 | `selic_meta` | **A confirmar** |
| 433 | `ipca_mes` | **A confirmar** |

`--check-sources` imprime os últimos valores de cada série para conferência antes de publicar.

## 8. Limitações conhecidas hoje

- **Proxy de segmento, não produto específico**: o preço doméstico usado
  hoje é sempre `tipo_dado_domestico="proxy_segmento_aco"` — o segmento
  "Siderurgia" inteiro de Usiminas/CSN, não bobina a quente isolada.
  Nenhuma das duas empresas publica essa quebra nos releases
  investigados (ver ADR 0003). O IPIA calculado hoje é, formalmente, um
  índice de paridade para o segmento de aço das duas empresas usado como
  proxy — não um IPIA de bobina a quente puro.
- **Cobertura histórica curta do dado doméstico**: só dois trimestres
  carregados no CSV curado (2026Q1 Usiminas, 2026Q2 CSN) — e não são a
  mesma janela temporal para as duas empresas (ver ADR 0001). Todo o
  histórico anterior a 2026Q1 depende de curadoria futura.
- **Antidumping confirmado como pendente em 23/08/2026**:
  `antidumping_usd_t=0.0` por padrão. Checagem feita via pesquisa (não
  suposição) nessa data: cold-rolled (Resolução Gecex 854) e revestido
  (856) foram decididos em 12/02/2026, mas laminado a quente da China
  **não aparece em nenhuma resolução Gecex** até a de número 947
  (04/08/2026, última verificada). Duas datas de expectativa já passaram
  sem decisão (fev-mar/2026 segundo imprensa, jul/2026 segundo a própria
  Usiminas no release do 1T26). Isso **não é um fato permanente** — é o
  status numa data específica, que precisa ser rechecado periodicamente
  (não só confirmado uma vez) em gov.br/mdic/.../defesa-comercial antes
  de cada publicação.
- **`icms_credito` declarado mas não usado**: campo existe em
  `ParamsIPIA` mas `custo_importacao_rs_t` não o referencia em nenhum
  lugar — hoje não tem efeito no cálculo, é só um campo informativo à
  espera de ser incorporado.
- **NCMs não reconfirmados no Siscomex**: a lista em `NCM_BOBINA_QUENTE`
  vem da leitura da Circular SECEX 39/2025; o próprio comentário no
  código pede confirmação adicional no Siscomex antes do primeiro
  cálculo publicado — isso não foi feito além da leitura da circular.
- **`--pdf-ipia` mostra "penetração de importação" como não disponível**:
  não há coletor implementado para essa métrica — só existe como entrada
  de spec do ICCS (`penetracao_importados`, pilar `externo`), sem dado
  real por trás ainda.
