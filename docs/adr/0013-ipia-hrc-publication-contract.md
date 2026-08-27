# 0013 - IPIA-HRC: contrato de publicação (blockers, display, naming, disclosure)

## Contexto

O Stage G3 (`docs/validation/ipia_hrc_v2_final_validation.md`) validou a
economia do IPIA-HRC V2 PIA-based sem encontrar defeito de metodologia. O
Stage G4 (`docs/decisions/ipia_hrc_v2_publication_readiness.md`) levantou
evidência e opções para fechar os itens de publication-readiness ainda em
aberto. Este ADR registra as decisões Level 3 aprovadas a partir desse
memo — o memo permanece como o registro da análise; este ADR é só a
decisão. Não reabre nenhuma decisão econômica/metodológica já aprovada
nos ADRs 0009-0012.

## Decisão

1. **Bloqueantes §15, escopo IPIA-HRC**: `docs/METODOLOGIA.md` §15 foi
   reescrita como tabela de reconciliação (blocker/status original/
   evidência/escopo/status atual), preservando a redação original. 15.1
   (Comex POST) e 15.2/15.3 (frete-seguro / vigência de NCM, escopados a
   HRC e à janela de publicação 2019-02+) estão `CLOSED`. 15.4 (Aço
   Brasil) é `NOT APPLICABLE` ao core do IPIA-HRC — nunca foi dependência
   do cálculo, só do indicador auxiliar legado de penetração de
   importação. **Nenhum desses fechamentos se estende a IPIA-Vergalhão,
   a outros produtos, ou a qualquer janela fora de 2019-02+** — um
   produto/janela fora desse escopo mantém status original.
2. **Low-liquidity: DECISÃO FINAL (Stage G4C) — NO THRESHOLD / DISCLOSURE
   ONLY.** IPIA-HRC V2 não adota nenhum threshold binário de baixa
   liquidez. Nenhum `liquidity_status`, `low_liquidity` booleano,
   `threshold_t` ou limiar por percentil foi criado. `total_kg` continua
   publicado como informação observável, sem transformação.
   `ipia_hrc_v2`/`preco_domestico_rs_t`/`ppi_rs_t`/`publication_status`
   nunca dependem de volume. Nenhuma suavização, interpolação, exclusão
   ou UNKNOWN por volume é aplicada. Substitui a posição intermediária do
   Stage G4B ("threshold pendente de decisão futura") — a decisão foi
   fechada, não apenas adiada.

   Razão: o "limiar de baixo volume" citado no Stage G3 (percentil 10
   amostral de `total_kg`, `scripts/validar_ipia_hrc_v2_final.py`) foi
   uma ferramenta EXPLORATÓRIA válida (perguntou "os extremos de IPIA
   coincidem com baixa liquidez?"), mas nunca teve aprovação
   metodológica como regra de publicação, depende da amostra corrente
   (mesmo mês histórico poderia mudar de classificação conforme novos
   meses entrassem, sem seu `total_kg` mudar), e não tem relação com
   `VOLUME_MINIMO_T=5000` (constante legada de outra metodologia de
   suavização, nunca portada para V2). A resposta empírica à pergunta
   exploratória foi negativa o suficiente para não justificar ação:
   correlação volume×volatilidade fraca (≈-0,19), zero outliers
   classificados como economicamente indefensáveis (Stage G3, todos
   "A"/"B", nenhum "D - SUSPICIOUS"). Disclosure obrigatório (texto
   PT-BR/EN em `docs/METODOLOGIA.md` §11.1) substitui qualquer mecanismo
   de threshold. Uma futura regra quantitativa exigirá nova decisão
   Level 3 com evidência específica — nunca a reabertura silenciosa
   deste percentil nem do `VOLUME_MINIMO_T` legado.
3. **Domestic proxy**: PIA-Produto + IPP 242-Siderurgia + Proportional
   Denton continuam a metodologia oficial do domestic side do IPIA-HRC.
   Classificação `YELLOW` (duas camadas de proxy: destination/product mix
   da PIA, agregação setorial do IPP) — não bloqueia publicação, exige
   disclosure obrigatório (§10 abaixo). Âncora corporativa Usiminas+CSN
   permanece benchmark de validação independente — nunca usada para
   calibrar a série PIA-based.
4. **EXPERIMENTAL (2019-02–2022-03)**: permanece na série histórica
   publicada, `publication_status=EXPERIMENTAL`, visualmente distinto de
   `PUBLICATION_GRADE` — nunca escondido, nunca tratado como equivalente.
   Regra já aprovada (coverage≥60% AND uncertainty≤2%, ADR 0009)
   inalterada; Stage G3 confirmou 0 violações em 27 meses.
5. **PUBLICATION_GRADE (2022-04–2023-12)**: confirmado como núcleo
   histórico publication-grade — 21 meses, 100% policy coverage, 0
   violações, identidades exatas (Stage G3). Classificação inalterada.
6. **PROVISIONAL (2024-01–atual)**: publicável como "IPIA-HRC
   Provisional", exibido junto da trajetória histórica mas visualmente
   distinto — nunca concatenado silenciosamente como se tivesse o mesmo
   contrato de estabilidade do OFFICIAL. Permanece revisável; vintage
   anterior preserva os valores já publicados (mecanismo já implementado,
   Stage G2/ADR 0012).
7. **Wording do valor corrente** (não implementado como código — texto
   de referência, ver §10 do memo do Stage G4 para a versão completa):
   - PT-BR: *"IPIA-HRC Provisório — {mês/ano}: {valor}. Estimativa
     corrente sujeita a revisão quando o próximo benchmark anual da
     PIA-Produto for divulgado pelo IBGE. O valor não é definitivo para
     o período."*
   - EN: *"IPIA-HRC Provisional — {Mon/YYYY}: {value}. Current estimate
     subject to revision when the next annual IBGE PIA-Produto benchmark
     becomes available. The value is not final for the period."*
8. **Naming**: nome público do índice pós-migração é **IPIA-HRC** (sem
   sufixo "V2" em material público, uma vez que este caminho vire o único
   oficial). Série oficial: **IPIA-HRC Official**. Extensão corrente:
   **IPIA-HRC Provisional**. Caminho corporativo antigo: **IPIA-HRC
   Corporate Benchmark** — nunca apresentado como equivalente à série
   oficial. Identificadores Python `*_v2`/`calcular_serie_ipia_hrc_v2`
   **não foram renomeados** (quebraria compatibilidade sem necessidade;
   o sufixo é só uma marca de estágio interno, não branding público).
9. **Caminho corporativo legado**: `calcular_serie_ipia_hrc_v2` (âncora
   Usiminas+CSN) fica **interno/deprecated** — mantido, nunca removido
   (é o único cross-check independente do domestic side), nunca
   apresentado publicamente como opção equivalente ao IPIA-HRC oficial.
   Docstring atualizada para deixar esse status explícito.
10. **Disclosure obrigatório**: cobre PIA-Produto (benchmark anual),
    IPP 242 (indicador mensal), proxy doméstico, Proportional Denton,
    qualidade histórica da política comercial, EXPERIMENTAL,
    PUBLICATION_GRADE, PROVISIONAL, revisão/vintage, baixa liquidez
    (texto final PT-BR/EN em `docs/METODOLOGIA.md` §11.1 — substitui
    qualquer mecanismo de threshold, ver item 2 acima), disclaimer de
    benchmark independente. Texto completo (short/full, PT-BR/EN) no
    memo do Stage G4 §11 — não duplicado aqui.

## Alternativas consideradas

- **Fechar os 4 bloqueantes de §15 sem escopo (para "IPIA V2" em geral,
  incluindo vergalhão)**: rejeitada — a evidência (Stages E2/E3) só cobre
  a cesta HRC; estender ao vergalhão seria uma promoção não suportada.
- **Implementar `liquidity_status` já com o percentil 10 do Stage G3
  como threshold de produção**: rejeitada — transformaria uma escolha
  exploratória em contrato de publicação sem decisão específica, e o
  percentil amostral tem um defeito estrutural adicional (não é estável
  entre vintages — o mesmo mês histórico poderia mudar de classificação
  conforme novos meses são adicionados à amostra, mesmo com `total_kg`
  inalterado).
- **Deixar o threshold "pendente de decisão futura" (posição intermediária
  do Stage G4B) em vez de fechar a decisão**: rejeitada no Stage G4C — a
  evidência já reunida (correlação fraca, zero outliers indefensáveis) é
  suficiente para uma decisão definitiva de "sem threshold, só
  disclosure", não apenas para adiar. Manter em aberto indefinidamente
  sem nova evidência não teria propósito.
- **Aplicar suavização (legacy `VOLUME_MINIMO_T`) ao V2 bottom-up**:
  rejeitada — fora de escopo desta stage por instrução explícita, e o
  Stage G3 já mostrou que os grandes movimentos são majoritariamente
  explicáveis economicamente, não ruído a suprimir.
- **Renomear `calcular_serie_ipia_hrc_v2` para refletir "Corporate
  Benchmark" no próprio identificador Python**: rejeitada nesta stage —
  quebraria referências existentes sem necessidade; a mudança de nome
  público é só na camada de apresentação/documentação, não no código.

## Consequências

- IPIA-HRC deixa de estar bloqueado por `docs/METODOLOGIA.md` §15 na
  janela de publicação real (2019-02+) — mas **não** está
  automaticamente pronto para wiring de CLI/PDF (decisão separada, fora
  de escopo).
- `liquidity_status` (ou campo equivalente) **não existe e não está
  planejado** — a decisão (Stage G4C) é definitiva: NO THRESHOLD /
  DISCLOSURE ONLY, não um item pendente. `total_kg` permanece publicado
  como está; o disclosure textual (`docs/METODOLOGIA.md` §11.1) é o
  mecanismo completo de comunicação da limitação, não um substituto
  temporário.
- Nenhuma vintage existente foi alterada; a vintage `20260827T150423Z`
  permanece imutável e byte-idêntica.
- Nenhuma mudança em `VERSAO_METODOLOGIA` foi necessária — nada do que
  foi decidido/implementado altera o cálculo econômico (reconciliação de
  blockers, naming e a decisão de baixa liquidez são todas documentação/
  disclosure, nunca código econômico).
- Com os itens 1-10 fechados, o checklist de release readiness (memo do
  Stage G4 §12) fica completo — estado **READY FOR PUBLICATION WIRING**
  quanto às decisões de metodologia/publicação. O wiring de CLI/PDF em
  si permanece uma decisão de implementação separada, fora de escopo
  deste ADR.
- `docs/decisions/ipia_hrc_v2_publication_readiness.md` permanece como o
  registro da análise; este ADR é a decisão formal derivada dele.
