# IPIA Brasil — Índices Setoriais

Motor de cálculo de índices setoriais brasileiros sobre dado público.
Hoje implementa o **IPIA** (Índice de Paridade de Importação do Aço,
bobina laminada a quente) de ponta a ponta — coleta, cálculo, teste e
relatório em PDF —, e a especificação do **ICCS** (Índice de Condições
de Crédito Setorial — pesos e fontes definidos, coleta ainda não
implementada). Vergalhão e cesta multi-produto são próximos passos
planejados.

Todo o motor vive em `src/indices_setoriais.py`. A metodologia de
cálculo completa (fórmulas, tratamento de dado faltante, fontes e
particularidades de cada uma, limitações conhecidas) está em
[`docs/METODOLOGIA.md`](docs/METODOLOGIA.md) — este README é só a porta
de entrada.

## Instalação

```
pip install -r requirements.txt
```

## O que o IPIA calcula

IPIA = preço doméstico / custo de importação posto no cliente × 100.

- **> 100**: preço doméstico acima da paridade de importação (importar compensa).
- **< 100**: preço doméstico abaixo da paridade (produtor local protegido).

### Lado da importação
Preço de importação (USD/t) vem do **Comex Stat** (13 NCMs de 8 dígitos
de bobina laminada a quente não ligada, ≥600mm — `NCM_BOBINA_QUENTE`),
convertido para custo posto no cliente em R$/t via `custo_importacao_rs_t`:
CIF (câmbio PTAX do BCB/SGS) + II + AFRMM + antidumping (parâmetro,
zerado por padrão — status pendente, verificado periodicamente) +
despesas de porto + frete interno + margem do importador. Meses de
volume abaixo do mínimo passam por suavização seletiva (média móvel de
3 meses) antes de entrar no cálculo — meses de peso pleno nunca são
suavizados, mesmo com poucos parceiros comerciais (ver ADR 0005).

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
`hold_flat_fallback`), e a série de importação marca `interpolado`,
`peso_confiabilidade` (por volume, não por número de registros) e
`suavizado` em colunas explícitas.

## Uso

```
python src/indices_setoriais.py --selftest          # valida a matemática, sem rede
python src/indices_setoriais.py --check-sources      # testa as APIs públicas (BCB, Comex Stat, IBGE)
python src/indices_setoriais.py --preview-bobina      # série mensal de preço de importação (Comex Stat)
python src/indices_setoriais.py --preview-domestico   # série mensal de preço doméstico (curado + IPP)
python src/indices_setoriais.py --ipia                # calcula o IPIA completo -> data/processed/ipia_mensal.csv
python src/indices_setoriais.py --pdf-ipia             # relatório PDF de 1 página -> data/processed/ipia_relatorio.pdf
python src/indices_setoriais.py --spec                # imprime a especificação do ICCS (pilares/pesos/fontes)
```

Não há suíte pytest — o teste é `--selftest`, uma função `check()`
embutida no próprio script (ver `CLAUDE.md`).

## Estrutura de dados

| Pasta | Conteúdo | Versionado? |
|---|---|---|
| `data/curated/` | Preço doméstico trimestral por empresa, extraído de release — pequeno e essencial para o índice rodar | Sim (Git) |
| `data/raw/` | PDFs de origem dos releases (grandes, material de terceiro) | Não |
| `data/processed/` | Séries derivadas, 100% reproduzíveis via API/CSV curado | Não |

## Decisões de arquitetura (ADR)

- [`docs/adr/0001`](docs/adr/0001-ancora-preco-domestico-usiminas-csn-ponderado.md) — âncora de preço doméstico: média Usiminas+CSN ponderada por volume (com atualização de ago/2026 sobre a expansão de cobertura e validação cruzada entre as duas fontes).
- [`docs/adr/0002`](docs/adr/0002-encadeamento-trimestre-mes-via-ipp.md) — encadeamento do nível trimestral em série mensal via IPP.
- [`docs/adr/0003`](docs/adr/0003-dado-especifico-vs-proxy-e-versionamento-data-curated.md) — por que o dado hoje é proxy de segmento (não específico de bobina a quente) e por que `data/curated/` é versionado.
- [`docs/adr/0004`](docs/adr/0004-matplotlib-para-relatorio-pdf-ipia.md) — matplotlib como dependência para o relatório PDF de 1 página.
- [`docs/adr/0005`](docs/adr/0005-suavizacao-seletiva-preco-importacao.md) — suavização seletiva do preço de importação (média móvel só em meses de peso reduzido).
- [`docs/adr/0006`](docs/adr/0006-remocao-icms-credito-campo-morto.md) — remoção de campo morto (`icms_credito`) e decisão de não modelar ICMS por enquanto.

## Pendências conhecidas

- **Âncora de preço doméstico**: proxy do segmento "Siderurgia" inteiro,
  não específico de bobina a quente — nenhuma das duas empresas publica
  essa quebra. Cobertura histórica: 4 trimestres com Usiminas e CSN
  simultâneas (2025Q2–2025Q4, 2026Q2); 2026Q1 segue só com Usiminas (CSN
  1T26 não localizado); 2023Q1–2025Q1 seguem pendentes de curadoria.
- **Antidumping**: status para laminado a quente da China checado e
  confirmado como **pendente** em 23/08/2026 (não é fato permanente,
  precisa ser rechecado a cada publicação) — `antidumping_usd_t=0.0`
  até confirmação.
- **ICMS não modelado**: decisão de 23/08/2026, não premissa implícita
  — ver ADR 0006 para a razão econômica e a condição de revisão.
- **ICCS**: especificação completa (pilares, pesos, fontes) já definida
  no motor, mas sem coletores implementados ainda.

Detalhes de workflow, princípios de desenvolvimento e regras de
autonomia estão em `CLAUDE.md`. Metodologia de cálculo completa em
`docs/METODOLOGIA.md`.
