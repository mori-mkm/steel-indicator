# 0009 - Janela publication-grade/experimental do IPIA-HRC e Historical Import Policy Model

## Contexto

`docs/research/hrc_import_policy_history.md` (Stage E4/E4b) investigou os parâmetros
históricos de política de importação (II/TEC, AFRMM, antidumping, cota) necessários
para calcular o custo de importação do IPIA-HRC entre 2012-01 e o presente.

Resultado da investigação:

- **II/TEC**: confirmado individualmente para 4 dos 13 NCMs de `NCM_BOBINA_QUENTE`
  (`72083700`, `72083890`, `72083990` = 12%; `72083910` = 10%) entre 2012 e
  2022-03, com evidência SECONDARY_REPRODUCTION (Res. CAMEX 94/2011), depois
  10,8%/9% a partir de 2022-04-01 (Res. GECEX 272/2021, DOC). Para os outros 9
  NCMs, apenas uma faixa (10%-14%) é conhecida (FACT, Nota Técnica 1/2018) - o
  valor individual de cada um não foi comprovado.
- **AFRMM**: 25% (2012-01 a 2022-03-24) → 8% (2022-03-25 em diante, incluindo
  2023 inteiro, conforme STF Tema 1368/ARE 1.527.985) - fechado com FACT em
  toda a janela.
- **Antidumping**: fechado com FACT/DOC - valor efetivo sempre US$0/t para
  HRC (China/Rússia) em toda a janela 2012-presente (medida de 2018 sempre
  suspensa, extinta em 2020; investigação de 2025 sem direito provisório).
- **Cota 2026/27** (Res. GECEX 929/2026): mecanismo e alíquotas confirmados
  para 4 códigos; a alíquota efetiva depende de consumo de cota não rastreado.

A diferença entre 10%, 12% e 14% de II se propaga quase 1:1 para o custo de
importação (`ii = cif_brl * aliquota_ii`, somado direto na base do PPI antes
da margem) - uma variação de ~4 pontos percentuais no II corresponde a uma
variação de ~3,5-4% no PPI calculado e, por consequência, no IPIA publicado.
Não é uma diferença desprezível.

## Decisão

Adotar o modelo de **duas trilhas** (Option C, avaliada formalmente em
decisão Level 3):

1. **Publication-grade**: `2022-04-01 → presente`. Único período elegível
   para alimentar a série oficial do IPIA-HRC V2. Todos os parâmetros
   necessários (NCM - Stage E3 -, II/TEC, AFRMM, antidumping) têm evidência
   suficiente nessa janela.
2. **Historical experimental**: `2012-01-01 → 2022-03-31`. Mantido
   explicitamente separado, nunca concatenado silenciosamente à série
   oficial, porque o II individual de 9 dos 13 NCMs não está comprovado
   nesse período (apenas a faixa 10%-14% é conhecida).
3. `1997-2011` permanece fora de escopo (decisão já tomada na Stage E3, não
   revisitada aqui).

Esta escolha refina a decisão da Stage E3 (que já havia estabelecido
`2012-01 → presente` como janela aprovada para vigência de NCM): a série
agregada de 13 NCMs só é publication-grade a partir do ponto em que **todos**
os parâmetros necessários estão confirmados simultaneamente - hoje esse
ponto é definido pelo II/TEC, não pelo NCM.

Foi implementado um **Historical Import Policy Model** mínimo
(`steel_indicator/parameters/trade_policy.py`) que resolve, de forma
determinística e sem look-ahead, os parâmetros de II/TEC (por NCM/data),
AFRMM (por data) e antidumping (por origem/data/exportador) aplicáveis a
qualquer data entre 2012-01 e o presente, retornando um status explícito
(`PUBLICATION_GRADE` / `EXPERIMENTAL` / `UNKNOWN`) e nunca uma tarifa
inventada quando o valor não é conhecido. A cota de 2026/27 é representada
como fato/regra conhecida; quando a alíquota efetiva depender de consumo de
cota não rastreado, o modelo retorna `UNKNOWN` explícito em vez de escolher
silenciosamente dentro/fora da cota.

Este modelo **não está conectado** a `calcular_ipia_mensal`/`ParamsIPIA`
nesta decisão - o wiring é um próximo batch separado.

## Alternativas consideradas

- **Option A - janela oficial começa em 2022-04, sem trilha experimental**:
  máxima segurança metodológica, mas descarta o trabalho já validado
  (NCM, AFRMM, antidumping) para 2012-2022-03 sem deixar nenhum artefato
  para retomada futura.
- **Option B - usar tarifas históricas inferidas (ex.: 12% para os 9 NCMs
  não comprovados) marcadas como `A_CONFIRMAR`**: maximiza extensão
  histórica, mas arrisca publicar (mesmo com selo de baixa confiança) um
  número que pode divergir em até 4 pontos percentuais de II do valor real
  (a faixa conhecida vai até 14%, não só 12%) - risco de retrabalho e
  correção metodológica formal se a suposição se provar errada.
- Option C foi escolhida por preservar o rigor de A **e** reaproveitar o
  trabalho já investido no período experimental, seguindo o mesmo padrão de
  duas trilhas já usado no projeto (nowcast vs. oficial; NCM 1997-2011
  experimental vs. 2012-presente aprovado na Stage E3).

## Consequências

- Nenhum valor de II é atribuído por suposição aos 9 NCMs não comprovados
  entre 2012-01 e 2022-03-31 - o modelo retorna `UNKNOWN` explícito.
- O primeiro IPIA-HRC V2 publication-grade terá histórico oficial iniciando
  em 2022-04, mais curto que a janela de NCM aprovada na Stage E3
  (2012-presente) - esse descompasso é intencional e documentado, não um
  descuido.
- Uma extensão histórica experimental (2012-2022-03) pode ser calculada e
  exibida separadamente (fora da série oficial) assim que o wiring for
  implementado, sem exigir nova pesquisa de fonte para existir.
- Se os 9 valores de II forem confirmados no futuro, a promoção do período
  experimental a publication-grade é uma mudança metodológica formal
  (`CLAUDE.md` §"Governança de mudança metodológica" / `docs/METODOLOGIA.md`
  §24), não uma atualização silenciosa.
- `docs/METODOLOGIA.md` foi atualizado no ponto mínimo necessário para
  refletir esta janela (ver §9.5 e §26).
