# IPIA Brasil

**Inteligência setorial para medir a competitividade do aço importado no mercado brasileiro.**

O **IPIA Brasil** é um projeto de research quantitativo que transforma dados públicos de comércio exterior, câmbio, preços industriais e informações divulgadas por siderúrgicas em indicadores sobre o mercado brasileiro de aço.

O principal indicador desenvolvido é o **IPIA — Índice de Paridade de Importação do Aço**, atualmente aplicado à **bobina laminada a quente (HRC — Hot-Rolled Coil)**.

A pergunta central é simples:

> **Quanto custa trazer aço importado para o Brasil e como esse custo se compara ao preço praticado no mercado doméstico?**

O projeto implementa o pipeline completo:

**fontes públicas → tratamento e validação → cálculo econômico → indicadores → relatório setorial em PDF**

---

## O que é o IPIA

O IPIA compara o preço doméstico do aço com o custo econômico estimado de importar o mesmo produto e colocá-lo no mercado brasileiro.

A fórmula principal é:

```text
IPIA = (Preço doméstico em R$/t / Custo de importação posto no cliente em R$/t) × 100
```

Interpretação:

| IPIA | Leitura |
|---|---|
| **> 100** | O preço doméstico está acima da paridade de importação. A importação tende a ficar mais competitiva. |
| **= 100** | Preço doméstico e custo de importação estão em paridade. |
| **< 100** | O preço doméstico está abaixo da paridade. O produtor local possui maior proteção frente ao produto importado. |

O objetivo não é apenas acompanhar preços, mas decompor **quais fatores estão alterando a competitividade relativa do aço importado**, como câmbio, preço internacional, frete, impostos e custos de internação.

---

## O que o projeto entrega

Atualmente o repositório implementa de ponta a ponta:

### IPIA — Paridade de Importação

Série mensal comparando:

- preço doméstico do aço;
- preço FOB de importação;
- frete internacional;
- seguro;
- câmbio;
- Imposto de Importação;
- AFRMM;
- despesas portuárias;
- frete interno;
- margem do importador;
- custo total de importação posto no cliente.

### Pressão das importações

O projeto também acompanha indicadores complementares, como:

- taxa de penetração das importações;
- evolução histórica da paridade;
- composição do custo de importação;
- origem geográfica das importações;
- participação dos principais países fornecedores;
- câmbio;
- evolução do preço doméstico e do custo importado.

Esses indicadores ajudam a distinguir, por exemplo, se o aumento da pressão competitiva decorre de:

- queda do preço internacional;
- valorização do real;
- redução do frete;
- mudança na origem das importações;
- crescimento da participação do aço estrangeiro;
- ou aumento do preço doméstico.

---

## Relatório setorial

O projeto possui uma camada própria de geração de relatórios em PDF:

```text
src/reporting/
├── theme.py
├── components.py
├── pages.py
└── report_builder.py
```

O comando:

```bash
python src/indices_setoriais.py --pdf-ipia
```

gera:

```text
data/processed/ipia_relatorio.pdf
```

O relatório possui quatro páginas:

1. **Visão executiva**
   - nível atual do IPIA;
   - leitura do cenário;
   - principais movimentos do período;
   - informações metodológicas.

2. **Decomposição do custo de importação**
   - preço internacional;
   - câmbio;
   - impostos;
   - logística;
   - custo final posto no cliente;
   - spread frente ao preço doméstico.

3. **Séries temporais**
   - evolução do IPIA;
   - penetração das importações;
   - câmbio;
   - principais KPIs.

4. **Indicadores e origem das importações**
   - países fornecedores;
   - participação relativa;
   - indicadores recentes;
   - tabela de acompanhamento.

O design utiliza uma identidade visual própria e uma estrutura editorial voltada para relatórios de research econômico e setorial.

---

## Fontes de dados

O IPIA procura utilizar prioritariamente dados públicos e reproduzíveis.

| Informação | Fonte |
|---|---|
| Importações brasileiras de aço | Comex Stat / MDIC |
| Preço FOB, frete e seguro | Comex Stat |
| Câmbio | Banco Central do Brasil — SGS |
| IPP de Metalurgia | IBGE / SIDRA |
| Preço doméstico | Releases públicos de siderúrgicas |
| Volume doméstico | Releases públicos de siderúrgicas |
| Penetração das importações | Instituto Aço Brasil |

O escopo atual de HRC utiliza **13 NCMs de bobina laminada a quente não ligada, com largura ≥ 600 mm**, definidos a partir do escopo utilizado na investigação brasileira de defesa comercial para laminados a quente.

---

## Preço doméstico

Uma das principais dificuldades metodológicas é que não existe uma API pública com preço mensal de HRC no mercado brasileiro.

Além disso, as siderúrgicas brasileiras analisadas não divulgam separadamente preço e volume específicos de bobina laminada a quente em seus releases trimestrais.

Por isso, o projeto utiliza atualmente dados públicos de **Usiminas e CSN** como uma proxy do mercado doméstico.

O processo é:

```text
Releases trimestrais
        ↓
Preço médio por empresa
        ↓
Média ponderada pelo volume vendido
        ↓
Âncora trimestral de preço doméstico
        ↓
Encadeamento mensal via IPP / IBGE
        ↓
Série mensal utilizada pelo IPIA
```

Essa limitação não é escondida.

Cada observação carrega metadados indicando se o valor é observado, calculado, estimado ou baseado em proxy.

---

## Governança e proveniência dos dados

Uma preocupação central do projeto é separar claramente **dado observado de transformação analítica**.

Os números utilizados no relatório são classificados segundo sua proveniência:

```text
OBSERVADO
CALCULADO
ESTIMADO
```

Além disso, um indicador pode receber a marcação adicional:

```text
PROXY
```

Por exemplo, o preço doméstico atual pode ser:

```text
CALCULADO · PROXY
```

porque combina dados observados das empresas, agregação ponderada e uma aproximação do mercado de HRC por meio de informações do segmento de siderurgia.

Cada indicador também possui seu próprio:

```text
reference_period
```

evitando tratar como contemporâneos dados que possuem diferentes defasagens de publicação.

---

## Tratamento de baixa liquidez

Meses com pouco volume importado podem produzir preços médios pouco representativos.

O projeto utiliza:

```text
VOLUME_MINIMO_T = 5.000 toneladas/mês
```

para construir um peso de confiabilidade:

```text
peso_confiabilidade =
min(volume_do_mes / volume_minimo, 1)
```

Meses com volume suficiente permanecem inalterados.

Meses com volume reduzido podem receber suavização seletiva por média móvel de três meses.

O preço bruto continua armazenado separadamente.

O objetivo é evitar que operações pequenas e pouco representativas produzam movimentos artificiais no índice sem eliminar eventos reais de mercado com grande volume.

---

## Dados faltantes

O projeto diferencia três situações.

### Importação sem observação no mês

Pode receber interpolação linear e é explicitamente marcada:

```text
interpolado = True
peso_confiabilidade = 0
```

### Importação com volume baixo

Pode receber suavização seletiva:

```text
suavizado = True
```

### Preço doméstico entre releases

É encadeado utilizando a evolução do IPP de Metalurgia do IBGE:

```text
metodo = encadeado_ipp
```

Caso o IPP mais recente ainda não esteja disponível:

```text
metodo = hold_flat_fallback
```

Nenhuma dessas transformações é apresentada como se fosse observação original.

---

## Arquitetura

```text
ipia-brasil/
│
├── src/
│   ├── indices_setoriais.py
│   │
│   └── reporting/
│       ├── __init__.py
│       ├── components.py
│       ├── pages.py
│       ├── report_builder.py
│       └── theme.py
│
├── data/
│   ├── curated/
│   │   └── preco_domestico_aco.csv
│   ├── raw/
│   └── processed/
│
├── docs/
│   ├── METODOLOGIA.md
│   ├── report_design_system.md
│   └── adr/
│
├── CLAUDE.md
├── requirements.txt
└── README.md
```

### `src/indices_setoriais.py`

Motor principal do projeto.

Responsável por:

- coletores;
- transformações;
- cálculo de paridade;
- motor genérico de índices;
- indicadores auxiliares;
- proveniência;
- validações;
- CLI;
- autotestes.

### `src/reporting/`

Camada de apresentação.

O cálculo nunca é duplicado dentro do relatório: as páginas consomem os resultados produzidos pelo motor principal.

### `docs/METODOLOGIA.md`

Documentação detalhada da metodologia atual:

- fórmulas;
- parâmetros;
- fontes;
- tratamentos;
- proxies;
- limitações;
- classificação dos dados.

### `docs/adr/`

Registro das principais decisões metodológicas e arquiteturais do projeto.

---

## Instalação

Clone o repositório:

```bash
git clone https://github.com/mori-mkm/ipia-brasil.git
cd ipia-brasil
```

Crie e ative um ambiente virtual:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Principais bibliotecas:

- pandas
- NumPy
- Requests
- Matplotlib
- pdfplumber
- xlrd

---

## Como executar

### Validar o motor sem acessar a internet

```bash
python src/indices_setoriais.py --selftest
```

O projeto possui uma suíte de autotestes embutida no próprio motor, cobrindo regras de cálculo, proveniência, suavização, reconciliação entre séries e componentes utilizados no relatório.

---

### Validar as fontes públicas

```bash
python src/indices_setoriais.py --check-sources
```

Consulta as APIs utilizadas pelo projeto e exibe observações recentes para validação.

---

### Consultar preço de importação de HRC

```bash
python src/indices_setoriais.py --preview-bobina
```

Gera:

```text
data/processed/serie_bobina_quente.csv
```

---

### Consultar a série doméstica

```bash
python src/indices_setoriais.py --preview-domestico
```

Gera:

```text
data/processed/serie_domestico_aco.csv
```

---

### Publicar o IPIA-HRC

```bash
python src/indices_setoriais.py --ipia
```

Busca as fontes, calcula o IPIA-HRC (PIA-based), separa OFFICIAL/PROVISIONAL,
persiste uma nova vintage imutável em `data/processed/vintages/ipia_hrc_v2/`
e atualiza:

```text
data/processed/ipia_hrc_v2_official.csv
data/processed/ipia_hrc_v2_provisional.csv
```

`--ano-ini`/`--ano-fim` não se aplicam a este comando — a janela de fetch e
a janela de publicação já são fixadas pelo pipeline aprovado (ver
`docs/adr/0013-ipia-hrc-publication-contract.md`).

Para ver a última publicação já existente sem consultar as fontes de novo
(sem rede, sem criar vintage nova):

```bash
python src/indices_setoriais.py --ipia-latest
```

---

### Gerar o relatório

```bash
python src/indices_setoriais.py --pdf-ipia
```

Gera:

```text
data/processed/ipia_relatorio.pdf
```

---

## Motor genérico de índices

Além do IPIA, o projeto possui uma infraestrutura genérica para construção de índices compostos.

Ela implementa conceitos como:

- pilares;
- variáveis;
- orientação positiva ou negativa;
- pesos teóricos fixos;
- janela histórica de referência;
- z-score;
- winsorização;
- cobertura mínima;
- redistribuição de pesos para dados faltantes;
- validação exploratória com PCA.

A janela histórica utilizada como referência é congelada:

```text
2013-01-01 → 2019-12-31
```

Isso evita que a entrada de uma observação nova altere retroativamente toda a escala histórica de um índice.

---

## ICCS

O repositório também contém a especificação do:

**ICCS — Índice de Condições de Crédito Setorial**

Os pilares, variáveis, pesos e fontes já estão definidos no motor.

A especificação pode ser consultada com:

```bash
python src/indices_setoriais.py --spec
```

Os coletores necessários para produzir o ICCS completo ainda não foram implementados.

---

## Metodologia e decisões de arquitetura

A metodologia detalhada está em:

[`docs/METODOLOGIA.md`](docs/METODOLOGIA.md)

As principais decisões técnicas são documentadas como **Architecture Decision Records — ADRs**:

- [`ADR 0001`](docs/adr/0001-ancora-preco-domestico-usiminas-csn-ponderado.md) — âncora do preço doméstico;
- [`ADR 0002`](docs/adr/0002-encadeamento-trimestre-mes-via-ipp.md) — transformação trimestral → mensal;
- [`ADR 0003`](docs/adr/0003-dado-especifico-vs-proxy-e-versionamento-data-curated.md) — proxy de preço e dados curados;
- [`ADR 0004`](docs/adr/0004-matplotlib-para-relatorio-pdf-ipia.md) — geração do relatório;
- [`ADR 0005`](docs/adr/0005-suavizacao-seletiva-preco-importacao.md) — tratamento de baixo volume;
- [`ADR 0006`](docs/adr/0006-remocao-icms-credito-campo-morto.md) — tratamento do ICMS;
- [`ADR 0007`](docs/adr/0007-taxa-penetracao-importacao-acobrasil.md) — penetração das importações;
- [`ADR 0008`](docs/adr/0008-taxonomia-observado-calculado-estimado-proxy-e-vintage.md) — proveniência e vintage dos dados.

---

## Limitações atuais

O IPIA deve ser interpretado considerando algumas limitações metodológicas importantes:

- o preço doméstico ainda é uma **proxy do segmento siderúrgico**, e não um preço observado exclusivamente de HRC;
- a cobertura histórica dos releases domésticos ainda está sendo ampliada;
- alguns parâmetros de internação são hipóteses calibráveis;
- ICMS de importação não é atualmente incorporado ao custo econômico;
- a taxa de penetração disponível é agregada para produtos planos, não específica para HRC;
- decisões de defesa comercial, incluindo antidumping, precisam ser verificadas periodicamente;
- a lista de NCMs utilizada deve continuar sendo auditada conforme mudanças regulatórias.

Essas limitações são documentadas de forma explícita porque o princípio central do projeto é:

> **uma aproximação identificada é preferível a uma precisão artificial.**

---

## Roadmap

Próximas extensões possíveis do projeto:

- ampliar a cobertura histórica do preço doméstico;
- incorporar novas fontes de preços;
- acompanhar automaticamente mudanças de defesa comercial;
- adicionar outras siderúrgicas quando houver dados comparáveis;
- aumentar a granularidade dos indicadores de demanda e importação;
- expandir o motor para outros produtos siderúrgicos;
- implementar o ICCS;
- estudar índices para vergalhão e outros produtos;
- evoluir de um índice isolado para uma plataforma de inteligência setorial do aço.

---

## Status

**IPIA / HRC:** implementado de ponta a ponta  
**Coleta de dados públicos:** implementada  
**Governança de proveniência:** implementada  
**Relatório PDF:** implementado  
**ICCS:** especificação definida, coletores pendentes  
**Outros produtos siderúrgicos:** roadmap

---

## Autor

**Matheus Mori**

Estatística, Data Science, Machine Learning e desenvolvimento de produtos analíticos orientados a decisão.

GitHub: [github.com/mori-mkm](https://github.com/mori-mkm)