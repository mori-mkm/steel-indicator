# Guia Operacional de Coleta

## Quais séries coletar, de onde e em que ordem

**134 séries catalogadas, com identificador verificado, defasagem medida e prioridade de execução**

Preparado para Jonas Siqueira · 19 de agosto de 2026

### Acompanha

- `catalogo_series_coleta.xlsx` — a lista mestra, filtrável por índice, pilar e prioridade.
- `coletor.py` — a esteira de coleta, com 19 testes automatizados.

Fecha a etapa de pesquisa dos quatro índices: **ICCS, IPIA, IIDB e ICS**.

Cada identificador traz o status da verificação — não há código adivinhado.

---

# 1. O que esta pesquisa mudou

Sete achados invalidam suposições que estavam de pé nos documentos anteriores. Três deles mudam o desenho de um índice, e um deles trocaria o sinal do ICCS se passasse batido.

| Achado | Consequência |
|---|---|
| **Os rótulos de inadimplência do SGS não são o que se supõe** | A série `21083` é inadimplência de **pessoa jurídica TOTAL** e a `21084` é **pessoa física TOTAL** — não recursos direcionados e livres, como a numeração sugere. As de recursos livres são `21086` (PJ) e `21112` (PF). Provado por identidade de composição: a média ponderada de `21083` e `21084` pelos saldos reproduz exatamente o **4,68% de junho**. |
| **Não existe inadimplência setorial fina** | O SGS tem saldo de crédito em **30 setores finos** — inclusive metalurgia e siderurgia, papel e celulose, petróleo e gás, informação e comunicação. Mas **não tem inadimplência por atividade**. Isso só existe no SCR.data, e lá o CNAE abre apenas por seção. Redesenha o ICCS (seção 3). |
| **O endpoint `ultimos/N` do SGS mente** | Ele serve cache por URL e devolve janelas terminais diferentes conforme o N pedido — divergências de até três meses observadas na mesma série no mesmo dia, e um caso de valor inconsistente. **Nunca use em ingestão.** |
| **A CCEE não tem CNAE** | Confirmado lendo o CSV: só existe `RAMO_ATIVIDADE` com 15 valores macro. **Data center não tem ramo próprio** — cai em SERVIÇOS ou TELECOMUNICAÇÕES. Fecha, negativamente, a pergunta que ficou aberta no parecer anterior. |
| **O Instituto Aço Brasil publica Excel** | Série mensal em `.xls`, com URL previsível e download livre sem cadastro. Contraria a suposição de que a entidade só publica PDF. É a fonte mais fácil do IPIA. |
| **A página de portarias do MME de 2026 está fora do ar** | O índice cobre 2006 a 2025; `/2026` retorna 404. O fluxo provavelmente migrou sob o Decreto 12.772/2025. Em 2025, **9 das 19 portarias eram de data center** — é a melhor série de pipeline físico do país e você precisa confirmar para onde ela foi. |
| **O `/tables/ncm` do Comex Stat devolve códigos extintos** | Sem campo de vigência. O SH 8542 devolve seis códigos extintos junto com os quatro vigentes; o 8471 devolve 59 códigos do regime antigo. **Somar tudo duplica a série.** |

> **A correção que mais dói se passar batido**  
> Se você montar o pilar de qualidade da carteira com a série `21083` achando que é “recursos direcionados”, vai estar medindo pessoa jurídica total — uma variável com nível, volatilidade e ciclo diferentes. O índice funcionaria, publicaria e estaria errado. Nada no dado avisaria.

---

# 2. O mapa da coleta

- **134** séries catalogadas, com identificador, defasagem e prioridade.
- **67** séries do SGS já executáveis no coletor, com faixa de validação.
- **6 dias** de defasagem do Comex Stat — a fonte mais rápida do Brasil.
- **5 fontes** resolvem cerca de 80% de tudo que os quatro índices precisam.

## 2.1 As cinco fontes que resolvem quase tudo

| Fonte | Defasagem | Acesso | O que entrega |
|---|---:|---|---|
| **BCB SGS** | 0 a 30 d | API livre | Macro completo, crédito agregado, custo do crédito, e o bloco de 30 setores de saldo de crédito por atividade. Sem chave, sem limite. Resolve o ICCS quase inteiro. |
| **Comex Stat** | 6 d | API livre | Importação e exportação por NCM desde 1997, com frete e seguro na importação. Alimenta IPIA e IIDB ao mesmo tempo. |
| **IBGE SIDRA** | 31 a 43 d | API, não testada | PIM-PF (produção física), IPP (preço ao produtor) e PMS (serviços) por divisão CNAE. É o substituto público do IPA setorial da FGV. |
| **BCB SCR.data** | 30 d | ZIP, ODbL | A única fonte de inadimplência e ativo problemático por atividade. Limitada à seção CNAE. |
| **Aço Brasil** | 30 d | Excel livre | Produção, vendas, importação, exportação e consumo aparente de aço, em série mensal. |

## 2.2 O achado mais subaproveitado: 30 setores de crédito no SGS

O bloco de séries `22027` a `22044` e `27722` a `27748` traz o saldo de crédito por atividade econômica em cerca de trinta recortes. Quatro deles caem exatamente sobre os seus setores-alvo:

| Código | Série | Setor-alvo |
|---:|---|---|
| `27748` | Indústria de metalurgia e siderurgia | Siderurgia — o módulo do IPIA |
| `27747` | Indústria de petróleo, gás e álcool | Petróleo e gás |
| `27739` | Serviços de informação e comunicação | Tecnologia |
| `27746` | Indústria de papel e celulose | Commodities |
| `27725` | Indústria de obras de infraestrutura | Pilar de execução do IIDB |
| `22027` | Agropecuária | Agro — o crédito rural das cooperativas |

**Ressalva importante:** a soma do bloco setorial em junho de 2026 dá **R$ 3,59 trilhões**, que não fecha nem com o saldo de pessoa jurídica (**R$ 2,75 tri**) nem com o do sistema (**R$ 7,36 tri**). O universo estatístico é diferente do bloco `20539`. Não misture os dois num mesmo índice sem antes ler a metodologia — é o tipo de inconsistência que um analista do lado do cliente encontra em cinco minutos.

---

# 3. A restrição que redesenha o ICCS

> **O problema, em uma frase**  
> O volume de crédito existe em 30 setores finos. A inadimplência existe apenas por seção CNAE. O pilar de maior peso do ICCS — qualidade da carteira, 30% — só pode ser resolvido no nível grosso, enquanto os outros pilares podem ir ao nível fino.

Uma seção CNAE é larga demais para o propósito: a seção C junta toda a indústria de transformação, e a seção J junta editoras, telecomunicações e serviços de TI num bloco só. Se você resolver o índice todo por seção, o ICCS de “siderurgia” será, na prática, o ICCS de “indústria de transformação” — e o cliente vai perceber.

## As três saídas, e qual recomendo

| # | Saída | Avaliação |
|---|---|---|
| **A** | Construir o ICCS inteiro no nível de seção | **Consistente, mas fraco.** Oito a dez índices grossos, sem resolução no setor que o cliente compra. Perde o diferencial. |
| **B** | Duas camadas explícitas | **Recomendada.** Inadimplência da seção compartilhada entre os subsetores dela, somada a volume, atividade e preço no nível fino. Documente a imputação na metodologia, em vez de escondê-la. O índice fica setorial de verdade, e a limitação fica pública. |
| **C** | Derivar um proxy de inadimplência da desaceleração do crédito fino | **Não.** É inferência sobre inferência. Não sobreviveria à pergunta de um auditor no produto da 4.966. |

Com a saída B, ajuste os pesos para refletir onde está a informação específica do setor: reduza o pilar de qualidade de **30% para cerca de 22%** e redistribua para acesso e capacidade, que são resolvidos no nível fino. E publique, junto ao índice, a nota de que a inadimplência é de seção. **Declarar a limitação é o que separa metodologia de marketing.**

---

# 4. Três armadilhas técnicas

## 4.1 O cache do SGS

O endpoint `/dados/ultimos/{N}` devolve janelas terminais diferentes conforme o N. Na mesma série, no mesmo dia: `ultimos/3` parou em abril e `ultimos/6` chegou a junho — com o valor de abril revisado entre as duas chamadas. Em um caso, o mesmo mês veio com valores incompatíveis por caminhos diferentes.

```text
# errado — cache por URL, janela imprevisível
https://api.bcb.gov.br/dados/serie/bcdata.sgs.20631/dados/ultimos/3?formato=json

# certo — janela explícita, com reprocessamento móvel de 6 meses
https://api.bcb.gov.br/dados/serie/bcdata.sgs.20631/dados?formato=json
  &dataInicial=01/01/2010&dataFinal=19/08/2026
```

Some a isso que o BCB revisa retroativamente — as concessões de abril mudaram entre duas chamadas no mesmo dia. Por isso o coletor sempre recoleta os últimos seis meses e grava vintages.

## 4.2 Os códigos NCM extintos

O `/tables/ncm` devolve o registro histórico completo desde 1997, sem campo de vigência. Somar tudo duplica a série:

| Consulta | Devolve |
|---|---|
| `8542` | Extintos `85421300`, `85421400`, `85421900`, `85422100`, `85422900`, `85423000` junto com os vigentes `85423100`, `85423200`, `85423300`, `85423900` |
| `7210` | `72106900` (extinto) junto com os sucessores `72106911`, `72106919`, `72106990` |
| `8471` | Cerca de 59 códigos `8471.49.xx` do regime antigo junto com o `84714900` atual |

Cruze sempre com a **TEC vigente — Anexo I da Resolução GECEX 272/2021 consolidada** — antes de montar a cesta.

## 4.3 Os vintages do CAGED

O arquivo `CAGEDMOV` de cada mês é imutável, mas o saldo verdadeiro de uma competência muda por até doze meses, através dos arquivos `CAGEDFOR` (declarações fora do prazo) e `CAGEDEXC` (exclusões), com um ajuste maior em janeiro. A série que o PDET divulga como manchete é só o MOV do mês.

Consequência prática: guarde os três arquivos de cada divulgação. O vintage de uma competência é:

```text
MOV + Σ FOR − Σ EXC
```

acumulados até a data de observação, e só estabiliza cerca de treze meses depois.

---

# 5. Ordem de execução

| Janela | O que fazer | Por quê |
|---|---|---|
| **Semana 1** | As 40 séries P0 do SGS, histórico completo. `python coletor.py --coletar P0` | Uma chamada por série, sem autenticação. Em um dia você tem o pilar de crédito inteiro do ICCS e o macro dos quatro índices. |
| **Semana 1** | Comex Stat: aço, hardware e equipamento elétrico desde 1997 | Seis dias de defasagem e API aberta. Alimenta IPIA e IIDB ao mesmo tempo. |
| **Semana 1** | Raspar as portarias do MME de 2006 a 2025 | Prioridade absoluta. A página de 2026 já saiu do ar. Se o arquivo histórico sair também, você perde a única série longa de pipeline de data center do Brasil. Isso não espera. |
| **Semana 2** | Aço Brasil: toda a série de Performance Mensal | Download livre. Inspecione as abas do `.xls` e mapeie as colunas antes de automatizar. |
| **Semana 2** | SCR.data: ZIP anuais de 2012 a 2026 | Arquivos grandes. Só depois de baixar dá para confirmar se o CNAE de seção vem como letra ou como nome por extenso. |
| **Semana 3** | IBGE: PIM-PF, IPP e PMS das divisões-alvo | Valide os identificadores na primeira chamada — as APIs do IBGE não puderam ser testadas nesta pesquisa. |
| **Mês 1** | CVM (ITR e DFP), CAGED, ONS, ANEEL | Âncora de preço doméstico do aço, emprego setorial e pilar de execução do IIDB. |
| **Mês 2** | ANP: produção por poço desde 2005 | Scraping da listagem por ano — o padrão de nome do ZIP muda a cada ano. |
| **Mês 3** | CCEE, ANATEL, PMC, SINAPI, Contas Nacionais | Complementos. Nenhum é bloqueante para o primeiro índice. |
| **Depois** | CONAB e CEPEA | Um exige navegador headless; o outro exige negociação de licença. Deixe por último. |

---

# 6. As lacunas que você precisa fechar

Sete pontos não puderam ser verificados nesta pesquisa e bloqueiam a codificação de algum índice. Estão marcados em vermelho na aba **Lacunas** da planilha.

| Lacuna | Bloqueia | Como fechar |
|---|---|---|
| O POST `/general` do Comex Stat não foi executado ao vivo | IPIA | Rodar `coletor.py --validate`, que já traz o payload pronto |
| Ano inicial de `metricFreight`, `metricInsurance` e `metricCIF` | IPIA | Chamar com `period.from = "1997-01"` e ver quando param de vir nulos |
| Lista de NCMs vigentes, para descartar os extintos | IPIA | Anexo I da Resolução GECEX 272/2021 consolidada |
| Conteúdo das abas do Excel do Aço Brasil | IPIA | Baixar e inspecionar. É livre |
| Para onde foi o fluxo de portarias de acesso em 2026 | IIDB | Verificar `sntep/despachos-decisorios/2026` e o rito do Decreto 12.772/2025 |
| Como o CNAE de seção aparece no CSV do SCR.data | ICCS | Baixar um ZIP e ler o cabeçalho — a metodologia não enumera os valores |
| As APIs do IBGE não puderam ser testadas | ICCS | `coletor.py --validate` testa a chamada do SIDRA |

Outras seis lacunas — **cotas siderúrgicas, CKAN de ONS e ANEEL, CONAB, CEPEA, ANATEL, encoding do CAGED** — não bloqueiam nenhum índice e estão listadas na planilha.

---

# 7. Disciplina de vintages

Toda coleta é gravada com carimbo da data em que foi coletada, não só da data de referência, e registrada num manifesto com hash. Isso responde a uma pergunta que sempre chega, geralmente de um auditor no produto da 4.966: **qual era o número quando você publicou?**

Sem vintages, a resposta é uma reconstrução — e reconstrução não passa em auditoria. Com vintages, é um arquivo.

```text
# estrutura gravada pelo coletor
dados/
  manifesto.csv          # coletado_em, id, n_obs, primeira, ultima, sha256
  sgs/
    inad_pj_total/
      2026-08-19.csv     # o que a API devolveu naquele dia
      2026-09-12.csv     # nova coleta: revisões ficam visíveis
```

---

# 8. Licenciamento — as duas restrições que importam

| Fonte | Licença | O que muda no produto |
|---|---|---|
| **BCB SCR.data e ANEEL** | ODbL | A cláusula de compartilhamento incide sobre bases derivadas. Venda o índice e a análise; não redistribua a base tratada. Se o cliente pedir o dado processado, entregue por API com resultado calculado. Valide com advogado antes do primeiro release. |
| **CEPEA / ESALQ** | Restrita | Não use sem licença. Uso comercial e redistribuição são restritos, e alguns indicadores são referência de contratos da B3. Bloqueia fetcher automatizado com HTTP 403 — o que é, em si, um recado. |
| **Instituto Aço Brasil** | Não declarada | Download livre e sem cadastro, mas a política de uso comercial não está publicada. Peça por escrito antes de embutir no produto. |
| **SGS, Comex Stat, IBGE, CVM, CAGED, ONS, CCEE, ANP** | Abertas | Uso comercial permitido com atribuição. Microdados individualizados do IBGE têm sigilo estatístico — use apenas agregados. |

---

# 9. Como usar os arquivos

```bash
# valida a lógica do coletor, sem tocar na rede (19 testes)
python coletor.py --selftest

# testa as fontes ao vivo e imprime o último valor de cada série
# é aqui que você fecha as lacunas de IBGE e Comex Stat
python coletor.py --validate

# imprime o catálogo embutido, por prioridade
python coletor.py --catalogo

# coleta as séries P0 do SGS, com validação e vintage
python coletor.py --coletar P0
```

Na planilha, comece pela aba **Prioridades** para o plano de execução, use a aba **Catálogo** com o filtro na coluna **Prioridade** para saber o que coletar, consulte **Endpoints** antes de escrever qualquer requisição, e leia **Lacunas** antes de considerar qualquer índice pronto para publicar.

> **Se você só tiver uma semana**  
> Rode `--coletar P0`, monte as cestas de NCM do Comex Stat e raspe as portarias do MME. Isso já entrega o pilar de crédito completo do ICCS, o preço de importação do IPIA e a série histórica de pipeline do IIDB. É a fatia da coleta com maior retorno por hora de trabalho — e a das portarias é a única que corre risco de desaparecer.

## Sobre o status de verificação

Todo identificador no catálogo traz um status.

- **Verificado** significa que a API foi chamada e o valor retornado foi conferido — é o caso de todos os códigos do SGS e das NCMs do Comex Stat.
- **Documentado** significa confirmado em documentação oficial ou em código de produção de terceiros, mas não executado — é o caso do IBGE, da CVM e do CAGED, cujos hosts estiveram inacessíveis nesta sessão.
- **A confirmar** significa que não foi possível verificar.

Nenhum código foi adivinhado; onde não houve verificação, isso está escrito.
