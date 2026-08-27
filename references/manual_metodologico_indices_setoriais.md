# Manual Metodológico — Documento Técnico

## Como construir os três índices setoriais

**Especificação completa do ICCS, do IPIA e do ICS — com uma arquitetura que dispensa painel próprio no primeiro ano**

Preparado para Jonas Siqueira  
Agosto de 2026

Complementa o relatório **Uma casa de research setorial para o Brasil**.

Acompanha o motor de cálculo `indices_setoriais.py`, com **17 testes automatizados**.

Todas as fontes de dados citadas foram testadas ao vivo durante a preparação deste documento. O que não pôde ser verificado está marcado como tal.

---

# Neste documento

1. **A pergunta sobre a FGV, respondida direto** — O que as sondagens cobrem, e por que não podem ser o núcleo.
2. **A inversão que resolve o problema** — Existem dois tipos de fosso, e o barato não precisa de painel.
3. **Princípios comuns aos três índices** — As sete regras que separam um índice de uma média ponderada qualquer.
4. **ICCS — especificação completa** — O primeiro índice a construir. Cem por cento dado público.
5. **IPIA — especificação completa** — Paridade de importação sem licenciar cotação de agência de preços.
6. **ICS — como fazer o survey sem dinheiro** — Quatro caminhos, em ordem de custo.
7. **Governança e protocolo de publicação**.
8. **Matriz de licenciamento das fontes**.
9. **Nomenclatura e conformidade**.
10. **Roteiro de 12 semanas**.
11. **O código que acompanha este manual**.
12. **Fontes e limitações**.

---

# 1. A pergunta sobre a FGV, respondida direto

A ideia faz sentido como insumo de contexto e **não faz sentido como núcleo**. Há quatro razões, e a quarta é a que mais importa.

## 1.1 O que as sondagens da FGV IBRE de fato cobrem

Verificado no portal do IBRE durante a preparação deste documento:

| Sondagem ativa | Periodicidade | Setor coberto |
|---|---|---|
| Sondagem da Indústria de Transformação | Mensal | Indústria de transformação (agregado) |
| Sondagem de Expectativas do Consumidor | Mensal | Consumidor |
| Sondagem do Setor de Serviços | Mensal | Serviços |
| Sondagem do Comércio | Mensal | Comércio |
| Sondagem da Construção | Mensal | Construção |
| Sondagem Econômica da América Latina | Trimestral | Economia regional |
| Indicador Antecedente de Emprego (IAEmp) | Mensal | Mercado de trabalho |

Descontinuadas: **Sondagem de Investimentos** (encerrada em janeiro de 2019) e **Indicador Coincidente de Desemprego** (encerrado em maio de 2021).

Fonte: FGV IBRE, página de sondagens e índices de confiança, consultada em agosto de 2026.

## 1.2 Os quatro problemas

| Problema | Detalhe |
|---|---|
| **1. Cobertura** | Das sete sondagens ativas, nenhuma cobre bancos, petróleo e gás, siderurgia isoladamente ou tecnologia. São quatro dos seus cinco setores-alvo. A siderurgia existe apenas como uma linha dentro da indústria de transformação, e o desmembramento por CNAE não é publicado abertamente. |
| **2. Licenciamento** | As manchetes (ICI, ICC, ICOM, ICST, IAEmp) circulam em release gratuito, mas séries detalhadas e microdados são produto comercial do FGV Dados. Construir um índice vendido sobre dado licenciado exige autorização expressa de uso derivado. Não consegui verificar os termos comerciais da FGV nesta pesquisa — as páginas do FGV Dados bloquearam o acesso automatizado. Peça as condições por escrito antes de decidir qualquer coisa. |
| **3. Frequência do controle** | Você fica exposto a decisões que não controla: mudança de metodologia, de amostra, de calendário, ou descontinuação — como já aconteceu duas vezes, com a Sondagem de Investimentos e o ICD. Um índice comercial que morre porque o fornecedor descontinuou o insumo é um passivo, não um ativo. |
| **4. Estratégico — o decisivo** | Se o seu índice é uma transformação do índice da FGV, o fosso é da FGV. Você vira camada de interpretação sobre benchmark alheio — exatamente a posição de 34% de margem que o relatório anterior recomendou evitar. Reprocessar uma sondagem pública não cria informação nova; e informação nova é a única coisa que um assinante paga para ter. |

## 1.3 Onde a FGV faz sentido — e a alternativa gratuita

Duas funções legítimas, ambas periféricas:

- **Variável de contexto** dentro de um índice cuja identidade vem de outro lugar, com peso pequeno e atribuição clara.
- **Série de validação no backtest.** Seu índice deve correlacionar razoavelmente com o ICI no período comum — se não correlacionar nada, provavelmente está errado; se correlacionar 0,95, é redundante e não tem por que existir. O ponto ideal fica entre **0,5 e 0,75**: você mede a mesma economia, com informação adicional.

> **A alternativa gratuita que quase ninguém usa**  
> A Sondagem Industrial da CNI é mensal, gratuita, e publicada com desagregação por atividade industrial — inclusive metalurgia. A CNI também publica o ICEI, os Indicadores Industriais e as Sondagens Especiais, todos sem custo. Para o componente industrial, ela entrega quase o mesmo que a FGV e não cria dependência comercial. Confirme os termos de uso para fim comercial diretamente com a CNI.

---

# 2. A inversão que resolve o problema

Você está tentando replicar o fosso do PMI, que é caro. Mas a S&P Global tem dois tipos de fosso, e o outro custa quase nada.

| Tipo | Exemplo | De onde vem a defesa | Custo de construir |
|---|---|---|---|
| **Painel** | PMI | Do acesso: milhares de respondentes recrutados e retidos ao longo de anos. Ninguém replica sem repetir o esforço. | Alto |
| **Cálculo** | Platts, índices S&P Dow Jones | Da adoção: uma regra pública e fixa, aplicada com pontualidade absoluta, que o mercado passa a citar. O insumo é observável; o ativo é ser a referência. | Baixo |

O S&P 500 não tem painel nenhum. É uma regra de seleção e ponderação aplicada a preços públicos, publicada sem falhar desde 1957. Ele vale US$ 1,85 bilhão de receita ao ano com 71% de margem porque virou a referência — não porque os dados sejam secretos. O Platts é a mesma coisa em outro mercado: uma metodologia documentada, aplicada numa janela fixa, todo dia, até que os contratos passassem a citá-la.

> **A inversão**  
> Construa primeiro os índices de cálculo — que não precisam de survey algum, rodam sobre dado público e podem estrear em oito semanas. O índice de painel vem depois, no ano 2, quando você já tiver assinantes cujos executivos são o painel. Aí ele custa o tempo de enviar um formulário.  
>  
> **Nova ordem:** ICCS (mês 2) → IPIA (mês 4) → ICS com painel (mês 14+).

Há um ganho adicional, e é grande: um índice de cálculo é **reprodutível por terceiros**. Qualquer pessoa pode conferir sua conta. Isso soa como fraqueza — é exatamente o oposto. Reprodutibilidade é o que faz um auditor aceitar o número num processo de 4.966, e é o que faz um jornalista citá-lo sem medo. Um índice de survey com n pequeno tem o problema inverso: ninguém consegue verificar, então ninguém confia enquanto você não tiver marca.

---

# 3. Princípios comuns aos três índices

Sete regras. Elas são o que separa um índice de uma média ponderada qualquer, e cada uma existe porque a violação dela já quebrou o índice de alguém.

## 3.1 A janela de padronização é congelada

Todo componente é padronizado por média e desvio-padrão calculados numa janela histórica fixa — a sugestão aqui é **janeiro de 2013 a dezembro de 2019**, que é o maior trecho comum entre as fontes e exclui a distorção da pandemia.

$$
z_{i,t} = \frac{x_{i,t} - \mu_i^{ref}}{\sigma_i^{ref}}
$$

recortado em **[-3, +3]**.

`μ` e `σ` vêm da janela de referência congelada, nunca da amostra corrente.

> **Este é o erro que mais destrói índice novo**  
> Se você recalcula média e desvio com a amostra cheia a cada mês, o passado do seu índice muda toda vez que chega um dado novo. O cliente que citou “ICCS de 42 em março” abre a série em junho e encontra 45. A credibilidade acaba ali, e não tem conserto — a série inteira vira suspeita.

O motor que acompanha este manual testa exatamente isso: o autoteste acrescenta doze meses de valores extremos e verifica que nenhuma observação passada se moveu (**desvio máximo de 0,00**), e em seguida demonstra a contraprova — padronizando pela amostra cheia, o passado se desloca em até **3,08 desvios**.

## 3.2 A escala é 0 a 100, ancorada em 50

$$
Índice_t = 50 + 10 \times z_t^{composto}
$$

truncado em **[0, 100]**.

- **50** = média da janela de referência.
- **60** = um desvio-padrão acima.
- **40** = um desvio-padrão abaixo.

Isso dá três propriedades boas de uma vez: é imediatamente interpretável (“acima de 50 é melhor que a média histórica”), é familiar para quem já lê PMI, e — ponto não trivial — **não é escala de rating**, o que mantém o produto fora do alcance da Resolução CVM 9/2020.

## 3.3 Pesos são teóricos e fixos; o PCA só valida

Defina os pesos por raciocínio econômico, documente o raciocínio e congele. Use análise de componentes principais apenas como checagem: se o primeiro componente explicar menos de **45% da variância conjunta**, seus pilares estão medindo coisas diferentes demais e a composição precisa ser revista.

Nunca deixe o PCA definir os pesos. Pesos estimados mudam a cada reestimação, e um índice cujos pesos mudam não tem série histórica — tem uma sequência de índices diferentes com o mesmo nome.

## 3.4 Dado faltante redistribui peso, e a cobertura é publicada

Quando um componente falta, o peso dele é redistribuído proporcionalmente entre os disponíveis dentro do mesmo pilar, e a taxa de cobertura do mês é publicada junto com o número. **Abaixo de 60% de cobertura, o setor simplesmente não é publicado naquele mês.** Publicar um número frágil sem avisar é pior do que não publicar.

## 3.5 Ajuste sazonal só onde faz sentido

Séries de fluxo (produção, concessões de crédito, importações) precisam de ajuste sazonal — **X-13ARIMA-SEATS**, disponível no `statsmodels`. Séries de estoque e razões (inadimplência, saldo/valor adicionado, taxa de juros) não precisam e não devem receber. Aplicar ajuste sazonal onde não há sazonalidade só adiciona ruído de estimação.

## 3.6 A defasagem define o calendário, e o calendário é sagrado

| Fonte | Defasagem típica | Consequência |
|---|---:|---|
| BCB SCR.data | ~30 dias | Dado de junho disponível no fim de julho |
| IBGE PIM-PF e IPP | ~35 a 40 dias | Amarra o calendário do pilar de capacidade |
| Comex Stat | ~10 a 15 dias | A fonte mais rápida do conjunto |
| CVM ITR | 45 dias após o trimestre | Componente trimestral, interpolado |

Logo: o ICCS de referência do mês **M** sai em **M+2**. Escolha um dia fixo — por exemplo, a segunda quinta-feira de cada mês, às 8h — publique o calendário anual em dezembro e nunca atrase. Pontualidade não é detalhe operacional: é metade do ativo. O que faz um jornalista pautar seu índice todo mês é saber exatamente quando ele sai.

## 3.7 Revisão e vintages

O índice é revisado apenas quando a fonte primária revisa. Toda publicação gera um vintage arquivado: o que foi publicado, quando, com quais dados. Mudança metodológica só em janeiro, anunciada com três meses de antecedência, com a série inteira recalculada e as duas versões publicadas em paralelo por seis meses.

---

# 4. ICCS — Índice de Condições de Crédito Setorial

## 4.1 Por que este é o primeiro

Ele alinha com o ponto de entrada comercial (bancos e cooperativas, pela porta da Resolução CMN 4.966), roda cem por cento sobre dado público, é mensal, tem histórico desde 2012 e — o mais importante — é insumo direto do produto que você vai vender. O índice não é um exercício de marketing separado: é o motor do pacote de cenários.

Note a inversão de perspectiva: o ICCS **não mede o setor bancário**. Ele mede as condições de crédito dos setores tomadores, que é precisamente o que um banco precisa para provisionar.

## 4.2 O achado que torna isso possível

> **SCR.data — Sistema de Informações de Créditos, dados abertos do Banco Central**  
> Verificado durante a preparação deste manual: publicação mensal, série desde junho de 2012, com desagregação por CNAE para clientes pessoa jurídica, além de UF, modalidade de crédito, porte do cliente, origem dos recursos, indexador e segmento da instituição. Métricas: carteira ativa, ativo problemático, inadimplência e medidas agregadas das operações. Licença ODbL.

Isto é, na prática, um retrato mensal e gratuito da saúde creditícia de cada setor da economia brasileira — o insumo exato de que a 4.966 precisa, publicado pelo próprio regulador que fiscaliza a norma. É o ativo público mais subaproveitado do país para o seu negócio.

Endereço: `dadosabertos.bcb.gov.br/dataset/scr_data` · arquivos ZIP mensais, com tutorial e documento de metodologia.

## 4.3 Universo setorial

Comece com oito setores, mapeados para divisões da CNAE — o que garante que o dado de crédito (BCB), o de produção e preços (IBGE) e o de comércio exterior (Comex Stat, via correlação NCM–CNAE) conversem entre si.

| Setor | CNAE | Fonte de atividade específica |
|---|---|---|
| Siderurgia e metalurgia | 24 | Instituto Aço Brasil (estatística mensal, Excel aberto) + IBGE PIM-PF |
| Petróleo e gás | 06, 19 | ANP (produção por campo e por poço, dados abertos) |
| Mineração | 07 | IBGE PIM-PF extrativa + Comex Stat |
| Tecnologia | 62, 63 | IBGE PMS (serviços de informação e comunicação) |
| Agro e alimentos | 01, 10 | CONAB (safra) + IBGE PIM-PF alimentos |
| Papel e celulose | 17 | IBGE PIM-PF + Comex Stat |
| Química | 20 | IBGE PIM-PF + Comex Stat |
| Construção | 41–43 | IBGE PIM-PF insumos + BCB mercado imobiliário |

## 4.4 Os cinco pilares e as catorze variáveis

| Peso do pilar | Pilar / variável | Peso interno | Sinal | Fonte |
|---:|---|---:|:---:|---|
| **30%** | **QUALIDADE DA CARTEIRA** |  |  |  |
|  | Inadimplência do setor | 45% | − | BCB SCR.data por CNAE |
|  | Ativo problemático / carteira ativa | 35% | − | BCB SCR.data por CNAE |
|  | Variação 12 meses da inadimplência | 20% | − | BCB SCR.data por CNAE |
| **25%** | **ACESSO E VOLUME** |  |  |  |
|  | Saldo de crédito real, variação 12m | 50% | + | BCB SCR.data + IPCA |
|  | Concessões reais, variação 12m | 30% | + | BCB SCR.data + IPCA |
|  | Crédito sobre valor adicionado do setor | 20% | + | BCB + IBGE Contas Nacionais |
| **15%** | **CUSTO DO CRÉDITO** |  |  |  |
|  | Indicador de Custo do Crédito — PJ | 50% | − | BCB ICC |
|  | Spread bancário PJ | 30% | − | BCB SGS |
|  | Juro real ex-ante | 20% | − | BCB SGS + expectativas Focus |
| **20%** | **CAPACIDADE DE PAGAMENTO** |  |  |  |
|  | Produção física do setor, variação 12m | 40% | + | IBGE PIM-PF ou fonte setorial |
|  | Proxy de margem: IPP do setor menos custo de insumo | 35% | + | IBGE IPP por CNAE |
|  | Cobertura de juros das listadas do setor | 25% | + | CVM ITR/DFP, dados abertos |
| **10%** | **PRESSÃO EXTERNA** |  |  |  |
|  | Penetração de importados no consumo aparente | 60% | − | Comex Stat + produção doméstica |
|  | Termos de troca do setor, variação 12m | 40% | + | Comex Stat (valor unitário exportação / importação) |

**Sinal:** (+) maior é melhor; (−) maior é pior, e a variável entra invertida. Especificação implementada e validada em `indices_setoriais.py --spec`.

> **Nota sobre o IPP.** O Índice de Preços ao Produtor do IBGE é gratuito e desagregado por CNAE — é o substituto público direto do IPA-DI da FGV para a proxy de margem. Usá-lo elimina a única dependência de dado licenciado que restaria no pilar de capacidade.

## 4.5 O pipeline de cálculo, passo a passo

### 1. Coleta e alinhamento

Baixe o SCR.data mensal, filtre por CNAE e agregue por setor. Traga as séries do SGS, do Comex Stat, do IBGE e da CVM. Reindexe tudo em frequência mensal, com data no primeiro dia do mês. Interpole linearmente as séries trimestrais (CVM), marcando quais pontos são interpolados.

### 2. Transformação

Aplique `var12m`, `var12m_real` (deflacionando pelo IPCA) ou nível, conforme a especificação de cada variável. Só então aplique ajuste sazonal, e apenas às séries de fluxo.

### 3. Padronização

z-score contra a janela congelada de 2013 a 2019, recortado em ±3 desvios. Se algum setor tiver menos de 12 observações na janela, ele ainda não pode ser publicado — é honestidade, não limitação técnica.

### 4. Orientação

Multiplique por −1 as variáveis em que “maior” significa “pior” (inadimplência, custo, penetração de importados). Depois disso, para toda variável, maior é melhor.

### 5. Agregação em dois níveis

Média ponderada dentro de cada pilar, depois entre pilares. Em ambos os níveis, o peso do que falta é redistribuído proporcionalmente, e a cobertura é acumulada.

### 6. Escala e corte

`Índice = 50 + 10 × z composto`, truncado em `[0, 100]`. Setores com cobertura abaixo de 60% saem como indisponíveis, e não como um número.

### 7. Diagnóstico antes de publicar

Rode a validação por PCA e o teste de antecedência. Arquive o vintage. Só então publique.

## 4.6 Critérios de aceitação — o índice tem que provar que serve

Um índice que não antecipa nada é um gráfico bonito. Antes do primeiro release, exija que ele passe em quatro testes:

| Teste | Critério de aprovação |
|---|---|
| **Antecedência — o teste que importa** | A correlação entre o ICCS em *t* e a variação da inadimplência do setor em *t+6* deve ser materialmente maior, em valor absoluto, que a correlação contemporânea. Se não for, o índice é redundante em relação ao próprio dado de inadimplência e não deve existir. |
| **Coerência interna (PCA)** | O primeiro componente principal explica pelo menos **45% da variância conjunta**, com loadings de sinal compatível com as orientações teóricas. |
| **Estabilidade de revisão** | A revisão média absoluta ao acrescentar um mês fica abaixo de **1,5 ponto**. Acima disso, o índice é volátil demais para ser citado. |
| **Correlação externa** | Entre **0,5 e 0,75** com o ICI da FGV, nos setores industriais e no período comum. Abaixo de 0,5, provavelmente há erro; acima de 0,8, você está apenas reproduzindo o ICI. |

## 4.7 O que é grátis e o que é pago

| Camada | Conteúdo |
|---|---|
| **Grátis — release mensal** | O número principal dos oito setores, a variação no mês, um gráfico e uma nota analítica de 400 palavras. Data e hora fixas, calendário anual publicado. |
| **Pago — assinatura** | Os cinco subíndices por setor, a série completa desde 2013, cortes por porte de empresa e por UF, entrega em planilha e API, e o comentário analítico completo. |
| **Pago — produto 4.966** | A tradução do índice em projeção de inadimplência por setor sob três cenários ponderados por probabilidade, com memória de cálculo, documento de metodologia e carta de responsabilidade. É este o entregável que o cliente leva para o auditor — e é ele que justifica o preço. |

---

# 5. IPIA — Índice de Paridade de Importação do Aço

## 5.1 O problema e a solução

Paridade de importação exige um preço de referência do produto importado. A rota óbvia — cotação FOB China de bobina laminada a quente — é dado de agência de preços (Platts, Argus, Fastmarkets), licenciado e proibido de redistribuir. Publicar um índice construído sobre isso não é viável.

> **A saída: o valor unitário de importação do Comex Stat**  
> O Comex Stat publica, por NCM, por país de origem e por mês, o valor FOB, a quantidade e o peso líquido. A razão entre valor e peso é o preço unitário que o importador brasileiro efetivamente pagou.

Para efeito de paridade, isso não é um substituto pior da cotação de agência — é um referencial melhor. A cotação FOB de origem é um preço teórico de mercado; o valor unitário aduaneiro é o **preço realizado na fronteira brasileira**, já incorporando mix de produto, origem e condições negociadas. E é dado oficial, gratuito e redistribuível com atribuição.

Melhor ainda: a API expõe as métricas `metricFreight` e `metricInsurance`, e a base bruta traz `VL_FRETE` e `VL_SEGURO` por NCM. Ou seja, frete e seguro também vêm da fonte, em vez de serem estimados — o que elimina o parâmetro mais discutível da conta. A API foi testada e responde com dados de **1997 a 2026**; confirme a disponibilidade das métricas de frete e seguro para as suas NCMs específicas na primeira execução.

## 5.2 A fórmula

### CIF em US$/t

$$
CIF_t^{US\$/t} = P_t^{FOB} + Frete_t + Seguro_t
$$

### PPI em R$/t

$$
PPI_t^{R\$/t} = [CIF_t \cdot E_t + II + AFRMM + D_{porto} + D_{interno}] \cdot (1 + m)
$$

Onde:

- `E_t` = câmbio PTAX médio do mês.
- `II` = `CIF_t × E_t × alíquota do Imposto de Importação da NCM`.
- `AFRMM` = 8% sobre o frete marítimo em reais.
- `D` = despesas de internação e frete interno.
- `m` = margem do importador.

### IPIA

$$
IPIA_t = \left(\frac{Preço\ doméstico_t}{PPI_t}\right) \times 100
$$

- **Acima de 100** → o preço doméstico está acima da paridade: importar compensa, e o produtor local está sob pressão.
- **Abaixo de 100** → o preço doméstico está abaixo da paridade: o produtor local está protegido pelo custo de importar.

Repare que este índice tem uma leitura de negócio imediata e diária. É a conta que a área comercial de toda siderúrgica e de todo distribuidor de aço refaz o tempo todo — e ninguém publica no Brasil. É o candidato mais forte a virar dependência operacional, que é o mecanismo do Platts.

## 5.3 O outro problema: o preço doméstico

Não existe preço doméstico público de bobina a quente no Brasil. Quatro opções, e a recomendação é combinar duas:

| # | Fonte | Avaliação |
|---|---|---|
| **a** | IPP do IBGE, divisão 24 | **Parcial.** Gratuito, mensal e por CNAE, mas é índice, não nível. Serve para a variação, não para ancorar o valor em reais por tonelada. |
| **b** | Valor unitário de exportação, Comex Stat | **Parcial.** Gratuito e no mesmo dado, mas preço de exportação difere sistematicamente do preço no mercado interno. |
| **c** | Receita líquida ÷ volume vendido no mercado interno, nos ITR da CVM | **Melhor âncora de nível.** Gerdau, CSN e Usiminas publicam receita e volume por segmento em demonstrações auditadas e abertas. Dá um preço médio realizado em R$/t, trimestral e verificável. |
| **d** | Coleta própria com distribuidores | **Opcional.** Cinco a oito distribuidores, uma pergunta por semana. É o embrião barato do painel — e aqui o survey rende, porque preço é a informação que ninguém publica. |

**Recomendação:** ancore o nível em **(c)**, trimestralmente, e interpole os meses intermediários pela variação de **(a)**. Documente a regra de encadeamento. O resultado é integralmente público, reprodutível e auditável — e ninguém mais publica.

## 5.4 Frequência: o oficial mensal e o nowcast semanal

O Comex Stat é mensal, com cerca de 10 a 15 dias de defasagem. Publique dois produtos com rótulos claramente distintos, e jamais os misture:

| Produto | Frequência | Composição |
|---|---|---|
| **IPIA (oficial)** | Mensal | Todos os componentes com dado fechado. É o número de referência, o que vai no gráfico e o que se cita. |
| **IPIA-Nowcast** | Semanal | Mantém o preço FOB, o frete e o seguro do último mês fechado, e atualiza apenas o câmbio (diário, do BCB) e eventuais mudanças de alíquota ou cota. Publicado sempre com a etiqueta de estimativa e a data do último dado duro. |

## 5.5 Os parâmetros de internação

É o único bloco subjetivo do índice, e por isso deve ser o mais transparente. Publique os valores junto com o índice e revise uma vez por ano, em janeiro, com aviso prévio.

| Parâmetro | Valor inicial | Observação |
|---|---:|---|
| Alíquota do Imposto de Importação | conforme TEC da NCM | Atenção às cotas e majorações temporárias em vigor para o aço |
| AFRMM | 8% do frete marítimo | Confirme a alíquota vigente e as hipóteses de isenção |
| Despesas portuárias | R$ 210 / t | Capatazia, armazenagem e despacho — calibre com dois despachantes |
| Frete interno porto–cliente | R$ 140 / t | Publique a rota de referência assumida |
| Margem do importador | 3% | Zere se quiser medir custo puro em vez de preço ofertado |

Os valores acima são pontos de partida plausíveis para calibração, não medições. Ajuste-os com dois ou três despachantes antes do primeiro release, e registre a fonte da calibração no documento de metodologia.

---

# 6. ICS — como fazer o survey sem dinheiro

Quando chegar a hora do índice de painel, há quatro caminhos. Em ordem crescente de custo — e o primeiro custa zero.

## 6.1 Caminho 1 — ICS sintético, sem survey nenhum

Exatamente a arquitetura do ICCS, aplicada a variáveis de atividade em vez de crédito: produção física, utilização de capacidade, comércio exterior, preços, emprego formal (CAGED, mensal e por CNAE), energia consumida (ONS, horário). Custo marginal zero, porque a esteira de dados já existe.

**Cuidado de nomenclatura:** só chame de “índice de difusão” se de fato usar difusão de respostas. Um índice construído sobre variáveis contínuas é um **índice sintético de condições**. Chamar uma coisa pelo nome da outra é o tipo de imprecisão que um economista sênior do lado do cliente percebe na primeira leitura, e que custa caro em credibilidade.

## 6.2 Caminho 2 — micropainel de 12 a 20 respondentes

> **O argumento que muda o cálculo: concentração**  
> O PMI precisa de 400 empresas por painel porque cobre a indústria de transformação inteira, que é pulverizada. Seus setores não são. A siderurgia brasileira tem **31 usinas operadas por 11 grupos**. Um painel de 8 desses 11 não é uma amostra pequena — é quase um censo, cobrindo a esmagadora maioria da capacidade instalada do país.

O mesmo vale, com folga menor, para petróleo e gás, papel e celulose e mineração. Em setor concentrado, quinze respondentes certos valem mais que quatrocentos aleatórios — e isso é um argumento metodológico legítimo, não uma desculpa.

Regras mínimas para operar com n pequeno sem se expor:

- Publique o **n** e a cobertura estimada de capacidade ou de faturamento do setor. Sempre, em toda publicação.
- Painel fixo, não amostra rotativa. O mesmo respondente todo mês reduz drasticamente a variância, porque elimina o ruído de composição — que é a maior fonte de erro em amostra pequena.
- Use apenas o **saldo de respostas** (percentual de “melhor” menos percentual de “pior”). Não tente estimar médias ou intervalos de confiança com n de 15.
- Divulgue só a **média móvel de três meses** no primeiro ano, até acumular histórico suficiente para calibrar a volatilidade.
- Perguntas ternárias e factuais, sobre o mês corrente contra o anterior. Nunca peça opinião sobre o futuro no mesmo bloco das perguntas factuais.

## 6.3 Caminho 3 — o painel se paga em produto

É o mecanismo que a S&P Global usa no PMI: quem responde ao painel recebe acesso gratuito ao índice completo. O insumo é pago em produto, não em dinheiro, e o custo marginal é zero. Melhor ainda, converte respondente em usuário e usuário em candidato a assinante — o painel vira canal comercial.

## 6.4 Caminho 4 — a parceria com associação setorial

Instituto Aço Brasil, IBP, Brasscom, ABIMAQ ou o sistema OCB já têm o canal, a lista e a legitimidade que levariam anos para você construir. A proposta é simples e equilibrada: eles emprestam o canal e coassinam; você faz a metodologia, o cálculo, a publicação e a defesa técnica do número.

Há precedente direto e citável: todo PMI nacional é coassinado por um patrocinador — J.P.Morgan no índice global, HCOB na zona do euro, au Jibun Bank no Japão. O Instituto Aço Brasil já publica estatística mensal do setor; um índice de condições coassinado é uma extensão natural do que ele faz, não uma concorrência.

## 6.5 Quando

Mês 14 em diante, depois que o ICCS e o IPIA já estiverem publicando com regularidade e você tiver assinantes. Aí o convite para o painel deixa de ser um pedido de favor a desconhecidos e passa a ser o convite para participar de um índice que a pessoa já lê.

---

# 7. Governança e protocolo de publicação

| Item | Regra |
|---|---|
| **Calendário** | Publicado em dezembro para todo o ano seguinte, com data e hora exatas de cada divulgação. Nunca atrase — a pontualidade é metade do ativo. |
| **Embargo** | Mesma hora para todos, sem exceção. Nenhum cliente, patrocinador ou jornalista recebe antes. Registre a lista de distribuição de cada release. |
| **Documento de metodologia** | Público, versionado e datado. Toda alteração gera nova versão, com as anteriores mantidas acessíveis. |
| **Vintages** | Arquive o que foi publicado, quando e com quais dados de entrada. É o que permite responder a “por que o número mudou” com um arquivo em vez de uma explicação. |
| **Comitê de índice** | Duas ou três pessoas, com ata. Aprova qualquer mudança metodológica e qualquer decisão sobre dado anômalo. Em casa pequena isso parece burocracia — é o que faz o índice sobreviver à saída de qualquer pessoa. |
| **Regra de mudança** | Só em janeiro, anunciada com três meses de antecedência, com série recalculada e as duas versões publicadas em paralelo por seis meses. |
| **Marca** | Registro no INPI, classes NCL 35 e 42, antes do primeiro release. É a proteção mais eficaz que existe aqui — a metodologia não é protegida por direito autoral, mas o nome é. |
| **Dado anômalo** | Política escrita e prévia sobre o que fazer quando a fonte publica um valor absurdo: manter, excluir ou marcar. Decidir isso depois de ver o número é como se perde a independência. |

---

# 8. Matriz de licenciamento das fontes

| Fonte | Uso comercial | Condição e cuidado |
|---|:---:|---|
| **BCB — SCR.data** | Sim | Licença ODbL. Atribuição obrigatória. Ver o alerta abaixo — é a única fonte do conjunto com cláusula de compartilhamento. |
| **BCB — SGS e Olinda** | Sim | Dados abertos, com citação da fonte. API testada e funcionando. |
| **MDIC — Comex Stat** | Sim | Dados abertos, com citação. API testada, com dados de 1997 a 2026. |
| **IBGE — PIM-PF, IPP, PMS, PMC, Contas Nacionais** | Sim | Agregados de uso livre com citação obrigatória. Microdados individualizados têm sigilo estatístico pela Lei 5.534/1968 — não use. |
| **CVM — ITR e DFP** | Sim | Dados abertos em CSV estruturado. |
| **ANP, ONS, ANEEL, CONAB** | Sim | Dados abertos com citação. Confirme os termos de uso de cada portal. |
| **Instituto Aço Brasil** | Confirmar | Estatística mensal em Excel de download livre, mas verifique a política de uso comercial antes de embutir no produto. |
| **CNI — Sondagem Industrial** | Confirmar | Publicação gratuita. Peça confirmação por escrito para uso comercial derivado. |
| **FGV IBRE** | Não sem licença | Produto comercial. Não use séries detalhadas sem contrato de uso derivado. |
| **Platts, Argus, Fastmarkets** | Não | Redistribuição proibida por contrato. Não construa índice publicado sobre esses dados. |

> **Alerta específico sobre a licença ODbL do SCR.data**  
> A ODbL exige atribuição e traz uma cláusula de compartilhamento que incide sobre bases de dados derivadas. Publicar uma obra produzida a partir dela — o índice, um gráfico, um relatório — normalmente demanda apenas a nota de atribuição; já redistribuir a base derivada tende a atrair a obrigação de oferecê-la sob a mesma licença.  
>  
> Consequência prática, e ela molda o desenho do produto: **venda o índice e a análise, não a base tratada.** Se um cliente pedir o dado bruto processado, entregue por API com resultado calculado em vez de exportar a base. Esta é a leitura apresentada no manual e não substitui parecer jurídico — valide com um advogado de propriedade intelectual antes do primeiro release, porque a decisão afeta o que você pode vender.

---

# 9. Nomenclatura e conformidade

O índice setorial é seguro em relação à Resolução CVM 9/2020 desde que não individualize emissores, não use escala de crédito e não vire sinal de compra ou venda. O conteúdo pode ser quase o mesmo; o léxico é o que decide.

| Use | Nunca use |
|---|---|
| “Índice de Condições de Crédito Setorial” | “Rating setorial de crédito” |
| Escala 0 a 100 ancorada em 50 | AAA, BBB, BB+, escala de letras |
| “as condições de crédito do setor deterioraram” | “o risco de crédito da Empresa X aumentou” |
| “indicador sintético de condições setoriais” | “nota”, “grau”, “classificação de risco” |
| “o índice recuou para 43, abaixo da média histórica” | “rebaixamos o setor para BB com viés negativo” |

### Nota metodológica a incluir em todo release, logo abaixo do número

> “O [nome do índice] é um indicador sintético de condições agregadas do setor, construído sobre dados públicos segundo metodologia documentada e disponível publicamente. Não constitui avaliação da qualidade creditícia de qualquer empresa, emissor ou operação, nem classificação de risco de crédito na acepção da Resolução CVM nº 9/2020, nem relatório de análise na acepção da Resolução CVM nº 20/2021.”

---

# 10. Roteiro de 12 semanas até o primeiro release

| Semana | Entrega |
|---:|---|
| **1** | Registro das marcas no INPI. Baixar os 12 primeiros meses do SCR.data e entender a estrutura dos arquivos e o dicionário de dados. |
| **2–3** | Esteira de coleta: SCR.data, SGS, Comex Stat, IBGE, CVM. Rodar `--check-sources` e confirmar o rótulo de cada série do SGS no portal do Banco Central antes de seguir. |
| **4** | Mapa CNAE por setor e agregação do SCR.data. Primeira série de inadimplência e carteira por setor, desde 2013. |
| **5–6** | Montar os cinco pilares completos. Rodar o cálculo do ICCS pela primeira vez para os oito setores. |
| **7** | Os quatro testes de aceitação. Se falhar o teste de antecedência, revise a composição antes de seguir — não publique um índice que não antecipa nada. |
| **8** | Documento de metodologia, versão 1.0, escrito para ser lido por um auditor. Submeter à leitura crítica de dois economistas externos. |
| **9** | Calendário anual de divulgação. Política de revisão, de dado anômalo e de embargo. Constituição do comitê de índice. |
| **10** | IPIA: coleta das NCMs de aço, calibração dos parâmetros de internação com dois despachantes, âncora de preço doméstico pelos ITR. |
| **11** | Página pública do índice, com a metodologia, a série para download e o calendário. Assessoria de imprensa contratada e briefada. |
| **12** | Primeiro release do ICCS, em data e hora anunciadas com antecedência. A partir daqui, nunca mais atrase. |

---

# 11. O código que acompanha este manual

O arquivo `indices_setoriais.py` implementa o motor descrito aqui. Ele não é pseudocódigo: roda, e traz **17 testes automatizados** que validam a matemática sem depender de rede.

```bash
# valida a matemática — roda offline, em segundos
python indices_setoriais.py --selftest

# testa as APIs públicas e imprime os últimos valores de cada série,
# para você conferir o rótulo antes de publicar qualquer coisa
python indices_setoriais.py --check-sources

# imprime a especificação completa do ICCS: pilares, pesos, sinais e fontes
python indices_setoriais.py --spec
```

O que os testes cobrem:

- a janela de referência congelada não reescreve o passado;
- a contraprova de que a amostra cheia reescreve, em até 3,08 desvios;
- a winsorização respeita o corte;
- a média da janela de referência cai exatamente em 50;
- a orientação negativa espelha o índice;
- dado faltante redistribui peso corretamente e a cobertura reflete a perda;
- setor abaixo da cobertura mínima não é publicado;
- especificação com pesos inconsistentes é rejeitada;
- a aritmética completa da paridade de importação confere com o cálculo manual;
- o diagnóstico de antecedência detecta sinal antecedente plantado sem gerar falso positivo em ruído branco.

### Sobre os códigos de série do Banco Central

Duas séries foram verificadas ao vivo e batem com o divulgado para junho de 2026: `21082` (**inadimplência total, 4,68%**) e `21086` (**inadimplência de pessoa jurídica, 4,00%**). As demais estão no código marcadas como **a confirmar**, com os valores observados anotados. Confira cada rótulo no portal do SGS antes do primeiro release — um índice publicado sobre a série errada é um erro que não dá para desfazer.

---

# 12. Fontes e limitações

## Verificado ao vivo durante a preparação deste manual

- **API do SGS do Banco Central** — `api.bcb.gov.br/dados/serie/bcdata.sgs.{código}/dados`. Testada; séries `21082` e `21086` conferidas contra os valores divulgados de junho de 2026.
- **SCR.data** — `dadosabertos.bcb.gov.br/dataset/scr_data`. Mensal, desde junho de 2012, com CNAE para pessoa jurídica, carteira ativa, ativo problemático e inadimplência, por UF, modalidade, porte, origem e indexador. Licença ODbL.
- **API do Comex Stat** — `api-comexstat.mdic.gov.br/general`. Testada; responde com dados de 1997 a 2026.
- **Sondagens da FGV IBRE** — `portalibre.fgv.br`. Lista de sondagens ativas e descontinuadas conforme a tabela da seção 1.1.

## Não verificável nesta sessão

- APIs do IBGE (`servicodados.ibge.gov.br` e `apisidra.ibge.gov.br`) — o acesso automatizado foi bloqueado. Os endpoints e tabelas citados são de uso corrente e estáveis, mas valide-os na primeira execução antes de depender deles.
- Condições comerciais do FGV Dados — páginas inacessíveis. Peça os termos por escrito.
- Disponibilidade de frete e seguro no Comex Stat para NCMs específicas de aço — a API expõe as métricas; confirme o preenchimento efetivo para as suas NCMs.
- Termos de uso comercial do Instituto Aço Brasil e da CNI.

## Referências conceituais

- **Metodologia do S&P Global PMI:** índice de difusão sobre painel estratificado, com pesos de 30% para novos pedidos, 25% produção, 20% emprego, 15% prazos de entrega e 10% estoques; painel global de cerca de 13.500 empresas; respondentes recebem acesso gratuito aos dados.
- **Metodologia de assessment da Platts:** janela fixa de apuração, julgamento editorial documentado, conformidade com os princípios da IOSCO para agências de preços.
- **Resultados de 2025 da S&P Global:** Índices com 71% de margem ajustada e Ratings com 65%, contra 34% de Market Intelligence — a evidência quantitativa de que o benchmark vale mais que a análise sobre o benchmark.

---

Este manual descreve uma arquitetura metodológica e **não substitui parecer jurídico ou contábil**. Três decisões devem passar por profissional habilitado antes do primeiro release:

1. o enquadramento do produto frente às Resoluções CVM 9/2020 e 20/2021;
2. o alcance da cláusula de compartilhamento da licença ODbL sobre o produto comercial;
3. os termos de uso comercial das fontes marcadas como “confirmar” na seção 8.
