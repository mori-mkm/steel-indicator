# IPIA-HRC V2 — Publication Readiness Decision Memo (Stage G4)

**Status:** DECISION MEMO — presents evidence, options and a recommendation. **Not an ADR.** Nothing here is accepted methodology until the user decides. No code, threshold, formula, or CLI/PDF wiring was changed to produce this document.

**Inputs:** `docs/METODOLOGIA.md` (full, esp. §9.5, §12.9-§12.12, §15, §26), `docs/validation/ipia_hrc_v2_final_validation.md` (Stage G3), `docs/adr/0008` through `0012`, `docs/research/comex_live_validation.md`, `docs/research/hrc_ncm_history.md`, `docs/research/hrc_import_policy_history.md`, `docs/research/hrc_domestic_price_sources.md`.

---

## 1. Blocker inventory

`docs/METODOLOGIA.md` §15 lists exactly four blockers for "IPIA V2" (stated generically, not HRC-specific). Reclassified against actual later work and against the *actual proposed publication window* (EXPERIMENTAL 2019-02+, PUBLICATION_GRADE 2022-04+ — never earlier, since domestic data doesn't exist before 2019-01):

| # | Blocker (§15) | Classification | Why |
|---|---|---|---|
| 15.1 | Comex `/general` POST validated live | **A. ALREADY RESOLVED** | `docs/research/comex_live_validation.md` (Stage E2): FACT, endpoint/payload/response schema confirmed live, `success:true`, schema matches production adapter exactly. |
| 15.2 | Historical freight/insurance/CIF coverage | **B. CAN BE CLOSED WITH EXISTING EVIDENCE** (for the actual publication window) | Same doc: `metricFreight`/`metricInsurance` FACT-confirmed USABLE from 1997-01 for the HRC basket — the entire 2019-02+ publication window sits inside this confirmed range with large margin. Not closed for vergalhão (irrelevant here) or for 1997-2019 (irrelevant — not published). |
| 15.3 | NCM validity by historical period | **B. CAN BE CLOSED WITH EXISTING EVIDENCE** (for the actual publication window) | `docs/research/hrc_ncm_history.md` (Stage E3): FACT-level (two official MDIC/Camex correlation tables, 2012↔2017 and 2017↔2022) shows **zero** changes to chapter 72 / position 7208 — i.e., FULLY COMPARABLE with documentary evidence for 2012-present, which entirely covers the 2019-02+ publication window. The only open gap (1997-2012, INFERENCE-only) falls **outside** the window ever proposed for official publication. |
| 15.4 | Aço Brasil structured Excel validated | **C. DISCLOSURE-ONLY LIMITATION, NOT APPLICABLE TO THIS PRODUCT TODAY** | Aço Brasil feeds only the *legacy* import-penetration-rate metric (`taxa_penetracao_importacao_planos_mensal`, used by the legacy PDF page), which is **not part of IPIA-HRC V2's core formula** (`domestic PIA-based / PPI bottom-up × 100` — no Aço Brasil dependency anywhere in the V2 pipeline). It only becomes a real blocker again if/when a future report reintroduces an import-penetration chart alongside V2. |

**Conclusion:** none of the four §15 blockers, as originally written, survive unmodified once checked against later work and against the window actually proposed for publication. Recommend updating §15 (pending user approval — not done in this batch) to either mark all four closed-for-HRC-2019+, or narrow their scope explicitly to what remains open (vergalhão, pre-2019 backfill, Aço Brasil-dependent supplementary metrics).

---

## 2. Evidence matrix

| Blocker | Original reason | Current evidence | Status today | Recommended action |
|---|---|---|---|---|
| 15.1 Comex POST | Never executed live | `docs/research/comex_live_validation.md` §1 — FACT | **CLOSED** | Update §15.1 to closed; keep the research doc as the evidence citation |
| 15.2 Freight/insurance history | Coverage start unknown | `docs/research/comex_live_validation.md` §3, §11 ("PARTIALLY CLOSED" in that doc, but the open part — vergalhão, 1997-2019 — never enters IPIA-HRC V2's publication window) | **CLOSED for HRC 2019+** | Update §15.2 with the scope qualifier (closed for HRC's actual publication window; open for vergalhão and pre-2019) |
| 15.3 NCM validity | Extinct-code risk | `docs/research/hrc_ncm_history.md` §4, §8, §12 ("PARTIALLY CLOSED" there, same reasoning: the 1997-2012 gap is INFERENCE-only but falls outside 2019+) | **CLOSED for HRC 2019+** | Same treatment as 15.2 |
| 15.4 Aço Brasil Excel | Never inspected | No research doc exists; but §5.4 grep of the V2 pipeline (`preco_domestico_hrc_pia_v2`, `agregar_ipia_hrc_multi_ncm_mensal`, `calcular_ipia_hrc_v2_pia`) confirms zero Aço Brasil dependency | **NOT APPLICABLE to V2 core** | Reclassify as a supplementary-metric blocker, not a core-index blocker; revisit only if the penetration-rate chart is added to the V2 report |
| Low-liquidity treatment | Not previously a named blocker; surfaced by Stage G3 | `docs/validation/ipia_hrc_v2_final_validation.md` §12: corr(total_kg, ΔIPIA)=-0.189; 5/8 low-volume months overlap extreme-IPIA months; 0 of those flagged as "suspicious" (all classified A/B) | **D. REQUIRES USER DECISION** | See §3 below — this memo's main open item |
| Domestic double-proxy | §12.5/§12.10 methodology already discloses this | `docs/validation/...md` §4, §7, §9: Denton annual constraint exact (0.00000000% error, 5/5 years); corporate-benchmark gap stable (-11.66%±1.49pp, corr 0.85, trend flat) | **C. DISCLOSURE-ONLY** (see §4) | Publish with explicit proxy disclosure; not a blocker |

---

## 3. Low-liquidity months

**Evidence recap (Stage G3, §12):** 8 low-volume months (≤6.69M kg, 10th percentile): 2019-03, 2019-06, 2019-09, 2020-12, 2021-05, 2021-08, 2022-06, 2022-08. 5 of these (2019-03, 2019-09, 2021-05, 2021-08, 2022-08) also appear among the 20 most extreme IPIA values. Correlation between volume and |ΔIPIA| ≈ -0.19 (weak-to-moderate, expected direction, not dominant). **Every** individual outlier investigated in Stage G3 (§6, §16) was classified A (economically explainable) or B (data/coverage effect) — **zero** were classified D (suspicious). Notably, 2021-05 (the series' all-time maximum, IPIA=154.13) sits inside the well-documented, independently-corroborated 2021 global steel super-cycle (§16 episode 3) — i.e., the low-volume/extreme-value overlap has an external, non-methodological explanation in at least this case.

### Option A — Do not alter the index; only flag/disclose low-liquidity months
- **Benefit:** zero methodology risk, zero recalculation, fully transparent, respects the finding that movements are largely economically explainable.
- **Risk:** a genuinely noisy month (if one exists) stays in the published series unflagged in any structural way beyond a footnote/column.
- **Methodological impact:** none — pure disclosure.
- **Interpretability impact:** low — a flag column (already have `total_kg`, `policy_coverage` published) lets downstream users filter themselves.
- **Risk of hiding real signal:** none (nothing is hidden or altered).
- **Recalculation needed:** none.
- **Compatibility with current publication_status:** trivial — a `liquidity_flag` boolean/enum column is orthogonal to `PUBLICATION_GRADE`/`EXPERIMENTAL`/`PROVISIONAL`/`UNKNOWN`, exactly like `domestic_is_proxy` already is.

### Option B — Quality/liquidity flag column, preserve raw index value
- Same as A, formalized as a named field (e.g. `low_liquidity_flag`, threshold TBD) in the published/analytical schema, possibly with the underlying `total_kg`/percentile already shown.
- **Benefit:** more structured than a footnote; auditable threshold; still zero economic alteration.
- **Risk:** choosing a threshold is itself a small methodological decision (needs Level 2/3 sign-off) — but a much smaller one than smoothing.
- **Methodological impact:** minimal (one new disclosure field, no formula change).
- **Interpretability impact:** positive — clearer than a prose footnote.
- **Risk of hiding signal:** none.
- **Recalculation:** none — purely additive metadata.
- **Compatibility:** trivial, same as A.

### Option C — Apply legacy-style smoothing to low-liquidity months (V2 bottom-up)
- **Benefit:** could reduce apparent noise in thin months.
- **Risk:** **HIGH.** Stage G3 found the large movements were *predominantly economically explainable* (2021 super-cycle, 2022 AFRMM cut, FOB mix shifts) — smoothing risks suppressing real signal to make the series "look nicer," which CLAUDE.md explicitly forbids ("Não redesenhar a metodologia sem evidência... Stage G3 mostrou que os grandes movimentos foram em geral economicamente explicáveis"). The legacy smoothing (ADR 0005) was designed for a different import-cost engine (single combined CIF, fixed params) — porting it to the bottom-up multi-NCM V2 engine is a **new methodological decision**, not a reuse of an existing one, and was never evaluated against V2's actual coverage/uncertainty machinery (which already does something conceptually related — the EXPERIMENTAL uncertainty-range gate — via a different, already-approved mechanism).
- **Methodological impact:** material — changes published values.
- **Interpretability impact:** could reduce transparency (smoothed ≠ observed).
- **Risk of hiding real signal:** **material**, per the finding above.
- **Recalculation:** yes, full historical re-run + version bump.
- **Compatibility:** would need new provenance/status semantics (smoothed months would need their own ESTIMADO-style label, distinct from the four existing statuses).

### Option D — Convert low-volume months to UNKNOWN below a volume threshold
- **Benefit:** conservative, removes any month below a hard liquidity floor from the published series entirely.
- **Risk:** **material.** This would throw away real, already-approved-quality data (all 8 low-volume months pass the EXPERIMENTAL/PUBLICATION_GRADE coverage/uncertainty rules on their own terms) purely because of volume, a criterion never in the approved publication rules (§9.5.2/ADR 0009 use coverage/uncertainty, not volume). It duplicates/conflicts with the coverage-based UNKNOWN mechanism already in place, and would silently shrink the OFFICIAL window (already short — 48 months) without new evidence that a volume threshold is the right instrument.
- **Methodological impact:** material — introduces a brand-new eligibility axis (volume) alongside coverage/uncertainty, requiring a Level 3 decision on the threshold itself.
- **Interpretability impact:** negative for users who want the full observed history; positive for users who distrust thin months.
- **Risk of hiding real signal:** the highest of the four options — actively deletes data classified as A/B (not D) by Stage G3.
- **Recalculation:** yes.
- **Compatibility:** requires extending the status-decision logic (`agregar_ipia_hrc_multi_ncm_mensal`) with a new gate — new code, new tests, new ADR.

### RECOMMENDATION: **Option B** (structured liquidity flag, index value unaltered), with Option A as the minimum-viable fallback if a full schema change is deemed premature.

Justification: Stage G3's own evidence argues against C/D (real signal, not noise, in most flagged months) and CLAUDE.md explicitly warns against silently building suppression logic. B gives future consumers of the data (including a possible future Level 3 evaluation with more history) the structured information to decide for themselves, at essentially zero methodological risk. **This is a recommendation, not an implementation — the exact threshold and field name still require explicit approval before any code change.**

> **FINAL DECISION (Stage G4C, ADR 0013):** the user did not adopt Option B as written. The Stage G4B audit found that no field/threshold implied by Option B (or any option requiring a concrete cutoff) had methodological approval — the G3 `quantile(0.10)` was exploratory-only, sample-relative, and unrelated to the legacy `VOLUME_MINIMO_T`. Rather than defer indefinitely, the final decision closed the question as **NO THRESHOLD / DISCLOSURE ONLY** — closest in spirit to Option A, but explicit that no structured field (not even a flag) will exist until a future decision is grounded in new, specific evidence. `total_kg` remains published as observable information; the mandatory disclosure text (`docs/METODOLOGIA.md` §11.1) communicates the limitation instead of a schema field. This entry is preserved as the historical record of the options actually evaluated — see ADR 0013 for the accepted decision.

---

## 4. Domestic double-proxy risk assessment

**Two stacked approximations, both already disclosed in code/docs:** (1) PIA-Produto 2422.2020 is HRC-specific but mixes domestic+export destination (`PROXY_REASON_DESTINATION_MIX`, ADR 0010); (2) IPP 242-Siderurgia (the monthly movement indicator) is sector-wide, not HRC-specific (`PROXY_REASON_PRODUCT_AGGREGATION`, §12.9/ADR 0010).

**Does this block publication, or is it publishable as explicit methodology/proxy?**

Evidence weighing toward "publishable as proxy" (Stage G3):
- Denton annual constraint reproduces the PIA anchor **exactly** (0.00000000% error, all 5 benchmarked years) — the *annual* level is not an approximation, only the *within-year monthly path* is (via the IPP movement).
- Corporate-benchmark comparison (independent, non-PIA source): gap stable at -11.66% (±1.49pp), correlation 0.85, trend flat (-0.09pp/month) — evidence of **consistent bias, not instability or drift**. A biased-but-stable proxy is far more defensible for publication (with disclosure) than a noisy/drifting one.
- PROVISIONAL trajectory (chained purely off IPP, no annual anchor available yet) remains economically coherent (§14 of the validation doc — smaller-than-typical transition jump, lower volatility than official, consistent direction with import side).
- No evidence of artificial drift anywhere in the series (Denton boundary analysis, §9 of the validation doc, explicitly rules this out).

Evidence weighing toward caution:
- Two proxies stacked is objectively weaker than one — the true "HRC-domestic-only, destination-separated" price does not exist yet as a source.
- The corporate benchmark itself is *also* a proxy (segment-wide, not HRC-specific) — the 0.85 correlation is reassuring but is a comparison between two imperfect measures, not a ground-truth check.

### Classification: **YELLOW**

Not RED: no evidence of a broken, unstable, or drifting proxy — the evidence base (exact Denton constraint, stable/correlated corporate gap, economically coherent provisional) is unusually strong for a proxy-based domestic series. Not GREEN: it remains two layers of approximation, both already disclosed, neither yet supersedable by a better source (per the hierarchy in §12.8 of METODOLOGIA — "uma fonte superior pode substituir a V1 mediante spec/ADR").

**Recommendation:** publishable, with mandatory explicit disclosure (see §11) — this is a disclosure question, not a blocker. Do not treat "two proxies" as automatically disqualifying; the evidence shows the *combination* behaves in a defensible, stable, economically coherent way.

---

## 5. Experimental history decision (2019-02 → 2022-03)

Already-approved rule: EXPERIMENTAL requires `coverage ≥ 60%` AND `uncertainty_range_pct ≤ 2%` (ADR 0009, §9.5.2). Stage G3 confirmed **0 violations across all 27 EXPERIMENTAL months**, empirically, from the frozen vintage.

- **Option A (appear in the official historical series as EXPERIMENTAL):** consistent with the rule already having concrete, tested, empirically-verified thresholds — EXPERIMENTAL is not a vague hedge, it is a defined, checked quality tier.
- **Option B (research-only, not public product):** would discard 27 months (more than half of today's total OFFICIAL history) despite passing every already-approved quality gate — no new evidence from G3 supports this; would need its own justification, which isn't present.
- **Option C (different styling/footnote):** already implicitly true — `publication_status` is a first-class field, distinguishable in any chart/table by definition; no additional decision needed beyond confirming this display convention downstream.
- **Option D:** no other treatment was surfaced by the evidence as worth considering.

**RECOMMENDATION: A, styled per C.** Publish EXPERIMENTAL history as part of the official OFFICIAL series, visually distinguished (already the convention in the Stage G3/E11 charts — different marker/color, footnote explaining the coverage/uncertainty gate). The label itself already carries the disclosure; no separate quarantine is justified by the evidence.

---

## 6. PUBLICATION_GRADE window confirmation (2022-04 → 2023-12)

Stage G3: 21 months, 100.0000% policy coverage on every single one (0 violations), exact identity reconstruction (0.000000% error on sampled months), exact Denton annual constraint. No remaining technical reason not to treat this as the publication-grade historical core.

**No blocker found.** This window is the strongest evidence base in the entire series (fully known trade policy, exact reconstruction, exact Denton) and should be the anchor of any "core historical series" framing in publication material.

---

## 7. Provisional publication decision (2024-01 → current)

Considerations already established: vintage/revision persistence exists (Stage G2, ADR 0012); PROVISIONAL is never frozen and is fully revisable; Stage G3 found **no** artificial step at the 2023-12→2024-01 boundary (jump smaller than the typical ordinary monthly move); current value in the analyzed vintage is 126.74 (2026-06).

- **Option A (shown with the series, visually distinct, labeled PROVISIONAL):** leverages the already-built vintage infrastructure and the G3 finding of a smooth transition — nothing technical prevents it.
- **Option B (separate panel):** also viable, more conservative visually, but the underlying data support (no discontinuity) doesn't require this level of separation.
- **Option C (only the latest current value):** discards the useful trend information (2024-2026 trajectory) that G3 showed to be economically coherent, without evidence justifying the loss.
- **Option D (do not publish provisional):** discards the most policy-relevant number (the *current* reading) for a project whose stated mission includes tracking present conditions — not supported by any G3 finding.

**RECOMMENDATION: A** (shown with the series, visually distinct — dashed line/different marker, exactly the convention already used in the Stage G3/E11 charts — clearly labeled PROVISIONAL, with the current-value wording contract from §8 attached to the latest point specifically). The revision mechanism (vintage/`revised` column) already gives a technically sound way to communicate "this may change" without hiding the number.

---

## 8. Current value wording contract

Goal: never present a PROVISIONAL number as definitive.

**PT-BR:**
> IPIA-HRC V2 Provisório — [Mês/Ano]: [valor]
> Sujeito a revisão quando a próxima PIA-Produto anual for divulgada pelo IBGE. Não é o valor oficial/definitivo do período — ver metodologia.

**EN:**
> IPIA-HRC V2 Provisional — [Month/Year]: [value]
> Subject to revision upon release of the next IBGE PIA-Produto annual benchmark. Not the official/final value for the period — see methodology.

Applied to the current analyzed vintage: *"IPIA-HRC V2 Provisório — Jun/2026: 126,74. Sujeito a revisão..."* / *"IPIA-HRC V2 Provisional — Jun/2026: 126.74. Subject to revision..."*

**Not adopted automatically** — proposed wording only, per instructions.

---

## 9. Series naming

| Element | Proposed name | Rationale |
|---|---|---|
| Index (product) | **IPIA-HRC** (full: *Índice de Paridade de Importação do Aço — Bobina a Quente*) | Matches existing METODOLOGIA/ADR nomenclature; "V2" is an internal/engineering version marker, not a public-facing product distinction once V2 becomes the only published path |
| Official series | **IPIA-HRC Official** | Matches the already-implemented `official.csv`/`separar_ipia_hrc_v2_oficial_provisional` split — no new concept, just the public name for it |
| Provisional extension | **IPIA-HRC Provisional** | Same reasoning, matches `provisional.csv` |
| Old corporate-anchor path | **IPIA-HRC Corporate Benchmark (internal)** — explicitly NOT "IPIA-HRC" alone, NEVER without a qualifier | Must never look like the official series (see §10) |

**Recommendation:** drop the "V2" suffix from public-facing material once this becomes the sole published path (it remains useful internally as a stage/code marker, e.g. in function names) — "V2" implies "V1 also exists publicly," which would confuse readers, since the legacy monolith path was never published either.

---

## 10. Legacy path recommendation (`calcular_serie_ipia_hrc_v2` + corporate domestic)

Options were: (A) keep publicly available as benchmark/debug, (B) keep internal/deprecated, (C) remove after migration, (D) rename explicitly as benchmark-corporate.

**RECOMMENDATION: B + D combined — keep internal, deprecated, and rename to make the "corporate benchmark, not official" status explicit in code and any future docs** (e.g. rename the function's public framing — not necessarily the Python identifier itself, which is a separate, smaller decision — to something like "corporate benchmark path" in all user-facing references). Do **not** remove it (C) — it is the independent validation source used throughout Stage G3/ADR 0010/0011 and remains valuable as an ongoing sanity check even after V2-PIA becomes official; removing it would remove the only independent cross-check the project has for the domestic side. Do **not** make it publicly presented as a real product option (A) — it must never be mistaken for the official series (§9's naming constraint exists specifically to prevent this).

No implementation performed — this is a recommendation for a future Level 2 batch (renaming/deprecation marking) once the naming decision in §9 is formally accepted.

---

## 11. Mandatory publication disclosures

### SHORT DISCLOSURE (chart/dashboard footnote)

**PT-BR:** *"IPIA-HRC (V2): preço doméstico baseado em PIA-Produto (IBGE) + IPP-Siderurgia, ambos proxies declarados; import parity calculado por NCM/país/mês. Histórico 2019-02–2022-03 é EXPERIMENTAL; 2022-04–2023-12 é PUBLICATION_GRADE; período corrente é PROVISÓRIO e sujeito a revisão. Não é benchmark comercial oficial."*

**EN:** *"IPIA-HRC (V2): domestic price based on IBGE PIA-Produto + IPP-Siderurgia (both declared proxies); import parity computed by NCM/country/month. 2019-02–2022-03 history is EXPERIMENTAL; 2022-04–2023-12 is PUBLICATION_GRADE; the current period is PROVISIONAL and subject to revision. Not an official commercial benchmark."*

### FULL DISCLOSURE (report/methodology appendix)

Must cover, each with a one-paragraph explanation sourced from the documents already produced (drafted here, not yet formatted for publication):

1. **PIA annual benchmark** — IBGE PIA-Produto 2422.2020, annual, mixes domestic+export destination (proxy, `DESTINATION_MIX`).
2. **IPP monthly movement** — IBGE IPP 242-Siderurgia, sector-wide, not HRC-specific (proxy, `PRODUCT_AGGREGATION`).
3. **Domestic proxy status** — both of the above stacked; Denton preserves the annual anchor exactly, monthly path is estimated.
4. **Proportional Denton** — method, citation (IMF QNA Manual ch. 6), the documented boundary-revision property (a new PIA year can slightly revise nearby prior months **only in the unfrozen, non-official flow** — the vintage mechanism freezes published OFFICIAL months regardless).
5. **Historical trade-policy quality** — EXPERIMENTAL (2019-02–2022-03): coverage≥60%/uncertainty≤2%, empirically 0 violations. PUBLICATION_GRADE (2022-04+): 100% policy-resolved volume, empirically 0 violations.
6. **EXPERIMENTAL history** — included in official series, explicit quality tier, not a footnote-only caveat.
7. **PROVISIONAL current period** — shown, distinct styling, never called definitive, wording per §8.
8. **Revision policy** — append-only immutable vintages (ADR 0012); OFFICIAL frozen once published; PROVISIONAL revisable; revision comparison (`revised` field) is public/auditable.
9. **Low-liquidity limitation** — disclosed per the decision in §3 (flag, not alteration).
10. **Independent/not-official benchmark disclaimer** — this is a research/analytical index, not a licensed commercial price index; corporate-anchor comparison is a validation tool, never a calibration target.

---

## 12. Release criteria checklist

```
[ ] §15 blockers reconciled with this memo's evidence (user sign-off on the reclassification)
[ ] Low-liquidity policy approved (Option A vs. B, incl. exact field/threshold if B)
[ ] Domestic double-proxy disclosure text approved
[ ] EXPERIMENTAL display policy approved (styling convention confirmed)
[ ] PUBLICATION_GRADE window explicitly confirmed as the historical anchor
[ ] PROVISIONAL display policy approved (styling + wording contract from §8)
[ ] Current-value wording (PT-BR/EN) approved
[ ] Series naming approved (§9)
[ ] Legacy corporate path migration plan approved (§10)
[ ] Short + full disclosure text approved
[ ] docs/METODOLOGIA.md §15 updated to reflect closed/reclassified blockers (only after the above are accepted)
[ ] New ADR created for any decision that changes a previously-documented default (naming, legacy path status) — per project rules
```

No hypothetical/open-ended items added — this list is exhaustive of what this memo surfaced, not a speculative superset.

---

## 13. Final recommendation

**FACT:** Stage G3 found no methodology defect. All four §15 blockers, checked against the actual proposed publication window, are either closed or not applicable. The one open technical question (low-liquidity treatment) has a low-risk, non-methodology-changing recommended path (Option B). The domestic double-proxy is YELLOW, not RED, with strong stability/exactness evidence. No status-boundary artifacts were found.

**EVIDENCE:** §§1-11 above, all traceable to `docs/validation/ipia_hrc_v2_final_validation.md` (Stage G3), `docs/research/*` (Stages E2/E3), and ADRs 0008-0012.

**OPTIONS:**
- **OPTION 1 — Proceed to publication wiring unchanged, with disclosure.** Justification: no economic/methodological defect was found; every open item is a disclosure or naming/process decision, not a code change. This is the option the evidence most directly supports.
- **OPTION 2 — Proceed after a small methodological change.** Only applicable if the user prefers Option C or D for low-liquidity (§3) over this memo's Option B recommendation — in that case, the change would be: adding a volume-based eligibility gate (Option D) or a smoothing rule (Option C) to `agregar_ipia_hrc_multi_ncm_mensal`, requiring a new threshold decision, new tests, a version bump, and historical re-run. **Not recommended by this memo** — flagged only because the user may weigh the risk differently.
- **OPTION 3 — Do not publish yet.** Not supported by the evidence gathered — no defect serious enough to block was found in three independent validation passes (Stage G3 script + two code reviews).

**RECOMMENDATION: OPTION 1**, contingent on the user explicitly accepting the items in the §12 checklist (this memo does not self-approve anything).

If the user instead prefers a methodological change for low-liquidity treatment (moving to Option 2), the exact change would be: introduce a volume-based (or smoothing-based) rule inside `agregar_ipia_hrc_multi_ncm_mensal`'s status-decision logic, parallel to but independent of the existing coverage/uncertainty gates, with its own threshold, its own tests, its own ADR, and a `VERSAO_METODOLOGIA` bump (per `.claude/rules/methodology.md`'s coverage-threshold/smoothing rule) — **not implemented in this batch**.
