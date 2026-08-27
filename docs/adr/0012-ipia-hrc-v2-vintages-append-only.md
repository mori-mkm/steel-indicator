# 0012 - IPIA-HRC V2: persistência append-only de vintages de publicação

## Contexto

O ADR 0011 (Stage E11) introduziu a separação OFFICIAL/PROVISIONAL do
IPIA-HRC V2 PIA-based e o congelamento de meses OFFICIAL via `congelado_df`
— mas `congelado_df` era injetado manualmente pelo chamador a cada
execução, sem nenhum armazenamento automatizado de execuções anteriores.
Não havia forma de:

1. recuperar, depois do fato, "o que o IPIA calculou/publicou" numa data
   específica;
2. saber se um mês foi revisado entre duas execuções, e em quê;
3. reproduzir o cálculo econômico de uma execução passada sem repetir as
   chamadas de rede (Comex Stat, BCB/SGS, IBGE/SIDRA).

Faltava uma camada mínima de persistência que resolvesse isso sem exigir
banco de dados, cloud, API ou infraestrutura completa de reconstrução
retroativa do estado das fontes externas — decisão explicitamente fora de
escopo desta stage.

## Decisão

1. **Vintage = bundle imutável de arquivos + manifest**, identificado por
   `vintage_id` no formato `YYYYMMDDTHHMMSSZ` (UTC, ordenável
   lexicograficamente, sem `:`). Layout:
   `data/processed/vintages/<produto>/<vintage_id>/{manifest.json,
   official.csv, provisional.csv, import_side.csv, domestic_price.csv}` +
   `data/processed/vintages/<produto>/index.csv` (catálogo append-only).
   Só filesystem local — sem SQLite/Postgres/cloud/API.
2. **Imutabilidade real**: `criar_vintage()` nunca sobrescreve — colisão
   de `vintage_id` levanta `FileExistsError`. Escrita atômica via
   diretório temporário + `os.rename` para o destino final; o
   `index.csv` só é atualizado depois do rename bem-sucedido, então uma
   falha a qualquer momento antes disso nunca deixa uma vintage parcial
   visível ou catalogada.
3. **`reference_period` ≠ `data_vintage`**: o primeiro é o mês econômico
   descrito, o segundo é quando aquela versão do resultado foi produzida.
   Uma observação do mesmo `reference_period` pode existir em vintages
   diferentes com valores/status diferentes — ambas permanecem
   recuperáveis, nenhuma sobrescreve a outra.
4. **Manifest mínimo por vintage**: `vintage_id`, `created_at_utc`
   (derivado do próprio `vintage_id`), `previous_vintage_id`,
   `methodology_version` (reaproveita `VERSAO_METODOLOGIA` — nenhum
   segundo sistema de versionamento criado; este batch não muda a
   fórmula do IPIA, então nenhum bump acontece só por adicionar
   persistência), cobertura/contagens por `publication_status`,
   timestamps de consulta de fonte (`*_fetch_at_utc` — "quando esta
   execução consultou a fonte", nunca uma data de publicação da fonte
   inventada), lista de arquivos e hash SHA256 de cada um.
5. **`revised`**: comparação contra a vintage IMEDIATAMENTE anterior
   (`preco_domestico_rs_t`/`ppi_rs_t`/`ipia_hrc_v2` com tolerância
   numérica + `publication_status` exato), contra a UNIÃO
   official+provisional da vintage anterior (nunca só o mesmo arquivo —
   necessário para capturar promoção provisional→oficial corretamente).
   Mês novo → `False`. Mudar só `data_vintage`/`source_vintage_id` nunca
   conta como revisão.
6. **Official freeze no fluxo normal via `congelado_df` automático**: o
   script de orquestração (não uma função econômica de baixo nível)
   detecta a última vintage, carrega seu `official.csv` e passa como
   `congelado_df` — mesmo princípio já estabelecido no ADR 0011, agora
   automatizado. Primeira vintage: sem `previous_vintage_id`, sem
   `congelado_df`.
7. **Provisional permanece revisável** entre vintages — pode mudar de
   valor, ganhar novos meses, ou ser promovido a oficial quando uma nova
   PIA cobrir o ano correspondente. A vintage anterior nunca muda quando
   isso acontece (testado byte a byte).
8. **Input snapshots, não um data lake**: cada vintage persiste
   `import_side.csv` (resultado usado do agregador bottom-up multi-NCM)
   e `domestic_price.csv` (resultado usado de
   `preco_domestico_hrc_pia_v2()`) — os inputs PROCESSADOS suficientes
   para reproduzir o cálculo econômico sem nova chamada às APIs. Não
   persistidos: respostas brutas do Comex, PDFs, payloads HTTP
   completos, cache de API.
9. **Duas exceções futuras ao congelamento, não implementadas**:
   correção/revisão oficial da fonte IBGE, e mudança metodológica
   deliberada. A arquitetura não as torna impossíveis (qualquer uma
   geraria uma NOVA vintage, nunca alteraria uma antiga) — só não foram
   construídas nesta stage.
10. **Separação de responsabilidade**: mecânica genérica (gerar ID,
    escrever atomicamente, hashear, indexar, carregar, listar) em
    `steel_indicator/storage/vintage_store.py`, parametrizada por
    `produto` — reutilizável por IPIA-Vergalhão/ICCS/ICS sem duplicação,
    mas deliberadamente não uma abstração para "qualquer índice do
    mundo" (só cobre o que os produtos do repositório precisam).
    Integração econômica específica do IPIA-HRC V2 (`calcular_revised`,
    manifest content, orquestração de save/load) permanece em
    `src/indices_setoriais.py`, ao lado das demais funções V2.

## Alternativas consideradas

- **Banco de dados local (SQLite)**: rejeitado — decisão explícita de
  manter a mecânica no nível de filesystem nesta stage; SQLite adiciona
  uma dependência de schema/migração desproporcional ao volume de dados
  (uma vintage a cada execução manual, dezenas de linhas por arquivo).
- **`--force` para sobrescrever uma vintage**: rejeitado — vintage é
  imutável por definição; um reprocessamento sempre gera uma NOVA
  vintage, nunca substitui uma antiga. Nenhuma flag de força foi
  implementada.
- **Denton condicionado como parte do congelamento** (mencionado como
  opção no ADR 0011): permanece fora de escopo aqui também — o
  congelamento por sobrescrita via `congelado_df` já garante a
  invariante exigida (nenhum mês OFFICIAL muda) independentemente do
  mecanismo de vintage.
- **Reconstruir o estado histórico das APIs externas**: rejeitado
  explicitamente como objetivo — este batch reproduz "o que o IPIA
  calculou/publicou naquela vintage" a partir dos inputs processados
  persistidos, não "o que a API tinha naquele instante" caso ela revise
  seus próprios dados depois.

## Consequências

- Primeira vintage local criada e validada: `20260827T150423Z`,
  `previous_vintage_id=None`, `methodology_version=1.2`,
  `last_pia_year=2023`. OFFICIAL (2019-02→2023-12, 48 meses) e
  PROVISIONAL (2024-01→2026-06, 30 meses) idênticos aos números já
  registrados no ADR 0011 — mesma execução, agora também persistida.
  Hashes SHA256 do manifest conferidos contra os arquivos reais no
  disco; recarregar a vintage e recalcular usando só os inputs
  processados persistidos reproduz `official.csv`+`provisional.csv`
  numericamente.
- `docs/METODOLOGIA.md` §12.12 registra a decisão completa.
- Vintages nunca entram no Git (`data/processed/vintages/` cai sob o
  padrão já existente `data/processed/*` do `.gitignore`).
- Ainda **não conectado** a `--selftest`/CLI/relatório oficial — mesmo
  status dos demais caminhos V2 (peça de cálculo interna, testada,
  validada com dado real).
- Nenhuma migração para object storage/banco foi feita — o layout
  `<produto>/<vintage_id>/` + manifest não impede uma migração futura,
  mas ela não foi implementada agora.
- As duas exceções futuras ao congelamento (correção de fonte, mudança
  metodológica) continuam sem mecanismo de implementação — qualquer uma
  exigiria decisão explícita antes de gerar uma nova vintage fora do
  fluxo normal.
