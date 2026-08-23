# 0004 - matplotlib como dependência para o relatório PDF do IPIA

## Contexto

O motor calcula o IPIA mensal completo (`--ipia`), mas a única saída até
agora era CSV e print no terminal. O primeiro passo de visualização
pedido foi uma página única em PDF com a série histórica, painel de
números recentes e ressalvas de metodologia. O projeto até então não
tinha nenhuma dependência de plotagem/geração de PDF — só
`pandas`, `numpy`, `requests` e `pdfplumber` (este último só para *ler*
PDF, na extração dos releases de Usiminas/CSN em `data/raw/`).

## Decisão

Adicionar `matplotlib` como dependência do projeto (instalado no
`.venv`), usado exclusivamente para gerar o relatório PDF de uma página
(`gerar_pdf_ipia` em `src/indices_setoriais.py`). O import é local à
função (mesmo padrão já usado para `requests` dentro de
`_get_json`/`_post_json`), com `matplotlib.use("Agg")` antes de importar
`pyplot`, para rodar sem display em qualquer ambiente (terminal, CI).

## Alternativas consideradas

- **Nenhuma dependência nova, só CSV**: mantém o projeto mais enxuto, mas
  não atende ao pedido explícito de uma primeira visualização em PDF —
  CSV não é uma peça visual.
- **reportlab / weasyprint (PDF a partir de HTML/CSS)**: dá mais controle
  de layout tipográfico para um sistema de relatório completo no estilo
  de casas de research (ver observação abaixo), mas é mais pesado e exige
  desenhar o gráfico em outra lib de qualquer forma (matplotlib, plotly,
  etc.) e depois compor — complexidade desnecessária para uma página
  única com um gráfico e três blocos de texto.
- **plotly**: melhor para relatório interativo/web, mas gera PDF estático
  via kaleido (dependência extra, motor de renderização externo) - mais
  peso do que o necessário para uma página exportada direto.

## Consequências

- `matplotlib` passa a ser dependência obrigatoria para `--pdf-ipia` e
  para a seção 15 do `--selftest` (que gera um PDF sintético num arquivo
  temporário para validar que a geração não quebra e produz arquivo não
  vazio - sem validar pixel a pixel).
- Este é só o primeiro passo visual (uma página, dado já calculado). Um
  sistema de relatório completo (múltiplas páginas, identidade visual
  estilo casa de research) é escopo separado e maior — se for adotado no
  futuro, entra como roadmap próprio (ex. um
  `docs/report_design_system_v2_roadmap.md`), não expande esta decisão
  retroativamente.
