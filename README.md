# IPIA Brasil — Índices Setoriais

Motor de cálculo de índices setoriais brasileiros sobre dado público.
Hoje implementa o **IPIA** (Índice de Paridade de Importação do Aço,
bobina laminada a quente) de ponta a ponta, e a especificação do
**ICCS** (Índice de Condições de Crédito Setorial — pesos e fontes
definidos, coleta ainda não implementada). Vergalhão e cesta
multi-produto são próximos passos planejados.

Todo o motor vive em `src/indices_setoriais.py`.

## O que o IPIA calcula

IPIA = preço doméstico / custo de importação posto no cliente × 100.

- **> 100**: preço doméstico acima da paridade de importação (importar compensa).
- **< 100**: preço doméstico abaixo da paridade (produtor local protegido).

### Lado da importação
Preço de importação (USD/t) vem do **Comex Stat** (13 NCMs de 8 dígitos
de bobina laminada a quente não ligada, ≥600mm — `NCM_BOBINA_QUENTE`),
convertido para custo posto no cliente em R$/t via `custo_importacao_rs_t`:
CIF (câmbio PTAX do BCB/SGS) + II + AFRMM + antidumping (parâmetro,
zerado por padrão — status ainda não confirmado) + despesas de porto +
frete interno + margem do importador.

### Lado doméstico
Não existe API pública para preço doméstico de bobina a quente — a
única fonte é o release trimestral de Usiminas/CSN, e nenhuma das duas
publica esse produto separado do agregado "Siderurgia" (ver
`docs/adr/0003`). O motor:
1. Lê `data/curated/preco_domestico_aco.csv` (curado à mão, versionado no Git).
2. Faz a média por trimestre ponderada por volume de vendas entre as
   empresas disponíveis (`preco_domestico_ponderado`, ver `docs/adr/0001`).
3. Encadeia o nível trimestral em série mensal usando a variação do IPP
   do IBGE/SIDRA (CNAE 24 — Metalurgia) até o próximo release confirmado
   (`encadear_preco_domestico_mensal`, ver `docs/adr/0002`).

Nenhum dado é fabricado silenciosamente: todo mês/trimestre carrega uma
coluna `tipo` (`proxy_segmento_aco` vs. `especifico_laminado_quente` vs.
`misto`) e um `metodo` (`nivel_trimestral`, `encadeado_ipp`,
`hold_flat_fallback`), e a série de importação marca `interpolado` e
`peso_confiabilidade` (por volume, não por número de registros) em
colunas explícitas.

## Uso

```
python src/indices_setoriais.py --selftest          # valida a matemática, sem rede
python src/indices_setoriais.py --check-sources      # testa as APIs públicas (BCB, Comex Stat, IBGE)
python src/indices_setoriais.py --preview-bobina      # série mensal de preço de importação (Comex Stat)
python src/indices_setoriais.py --preview-domestico   # série mensal de preço doméstico (curado + IPP)
python src/indices_setoriais.py --ipia                # calcula o IPIA completo -> data/processed/ipia_mensal.csv
python src/indices_setoriais.py --spec                # imprime a especificação do ICCS (pilares/pesos/fontes)
```

Não há suíte pytest — o teste é `--selftest`, uma função `check()`
embutida no próprio script (ver `CLAUDE.md`).

## Estrutura de dados

| Pasta | Conteúdo | Versionado? |
|---|---|---|
| `data/curated/` | Preço doméstico trimestral por empresa, extraído de release — pequeno e essencial para o índice rodar | Sim (Git) |
| `data/raw/` | PDFs de origem dos releases (grandes, material de terceiro) | Não |
| `data/processed/` | Séries derivadas, 100% reproduzíveis via API | Não |

## Decisões de arquitetura (ADR)

- [`docs/adr/0001`](docs/adr/0001-ancora-preco-domestico-usiminas-csn-ponderado.md) — âncora de preço doméstico: média Usiminas+CSN ponderada por volume.
- [`docs/adr/0002`](docs/adr/0002-encadeamento-trimestre-mes-via-ipp.md) — encadeamento do nível trimestral em série mensal via IPP.
- [`docs/adr/0003`](docs/adr/0003-dado-especifico-vs-proxy-e-versionamento-data-curated.md) — por que o dado hoje é proxy de segmento (não específico de bobina a quente) e por que `data/curated/` é versionado.

## Pendências conhecidas

- **Âncora de preço doméstico**: hoje é proxy do segmento "Siderurgia"
  inteiro, não específico de bobina a quente — nenhuma das duas empresas
  publica essa quebra. Os dois trimestres carregados no CSV curado
  (2026Q1 Usiminas, 2026Q2 CSN) também não são a mesma janela para as
  duas empresas — falta mais dado curado para um blend real.
- **Antidumping**: status definitivo para laminado a quente da China
  (esperado jul/2026) ainda não confirmado — `antidumping_usd_t=0.0`
  até confirmação.
- **ICCS**: especificação completa (pilares, pesos, fontes) já definida
  no motor, mas sem coletores implementados ainda.

Detalhes de workflow, princípios de desenvolvimento e regras de
autonomia estão em `CLAUDE.md`.
