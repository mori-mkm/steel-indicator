# Steel Indicator

A reproducible, auditable platform for Brazilian steel sector indices — built around versioned methodology, immutable data vintages and explicit provenance.

## What it does

Steel Indicator turns public trade, price and industrial-production data into sector indices for the Brazilian steel market. The first index shipped end-to-end is **IPIA-HRC** — the Import Parity Index for Hot-Rolled Coil. Every published number can be traced back to the source observation, the historical policy parameter, the methodology version and the exact data vintage that produced it.

## Why it exists

Brazil has no public, product-specific, reproducible index comparing the cost of importing steel to the price charged domestically. Company disclosures, trade data and industrial statistics exist separately, each with its own gaps, revisions and proxies. This project assembles them into one auditable pipeline instead of a one-off spreadsheet: every transformation — interpolation, proxy substitution, temporal chaining — is labeled, versioned and testable, never silently applied.

## IPIA-HRC

```text
IPIA-HRC = Domestic Price (R$/t) / Import Parity Price (R$/t) × 100
```

| IPIA-HRC | Reading |
|---|---|
| **> 100** | Domestic price is above import parity — importing would have been cheaper. |
| **= 100** | Domestic price and import parity coincide. |
| **< 100** | Domestic price is below import parity — the local producer has a competitive cushion. |

## Current methodology

Full detail lives in [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md). Summary of the currently published (V2) path:

**Import side** — realized Comex Stat trade data, month × NCM × country of origin:
- 13 NCMs of non-alloy hot-rolled coil, width ≥ 600 mm;
- historical import tariff (II) and AFRMM by validity period, never today's rate applied retroactively;
- antidumping/quota windows resolved per NCM and date;
- BCB SGS exchange rate (date-bounded retrieval, never `/ultimos/N`);
- observed freight and insurance where available, CIF build-up;
- port/logistics costs and importer margin to a landed cost per tonne (PPI).

**Domestic side** — PIA-Produto (IBGE/SIDRA, table 7752, category 2422.2020) as the annual benchmark, distributed to a monthly series by the movement of IPP 242-Siderurgia via **Proportional Denton** (first-differences, constrained so the annual mean matches the PIA level). Declared PROXY on two independent grounds: PIA mixes domestic-market and export destinations (`DESTINATION_MIX`), and IPP 242 is a sector-wide index, not HRC-specific (`PRODUCT_AGGREGATION`). A Usiminas+CSN corporate-disclosure anchor (the V1 approach) remains as an independent validation benchmark, never used to calibrate the PIA-based series.

**Low liquidity** — no volume threshold. `total_kg` is published as observed; nothing is smoothed, interpolated or excluded based on import volume. A disclosure statement covers the limitation instead (`docs/METODOLOGIA.md` §11.1) — see [ADR 0013](docs/adr/0013-ipia-hrc-publication-contract.md) for why a threshold was considered and rejected.

## Publication contract

Every published month carries a `publication_status`:

| Status | Meaning |
|---|---|
| **PUBLICATION_GRADE** | Full historical trade-policy coverage validated for the month. |
| **EXPERIMENTAL** | Published, but with known/quantified trade-policy coverage gaps. |
| **PROVISIONAL** | Current extension beyond the last confirmed PIA-Produto benchmark year — revisable when IBGE publishes the next annual PIA. |
| **UNKNOWN** | Not publishable for that month — never appears in official or provisional output, and is never interpolated to fill the gap. |

Public series names: **IPIA-HRC Official** (PUBLICATION_GRADE + EXPERIMENTAL history), **IPIA-HRC Provisional** (current extension), and **IPIA-HRC Corporate Benchmark** (the Usiminas+CSN anchor) — internal/deprecated, never presented as equivalent to the official series.

## Current validated coverage

Coverage windows and the current value change with every publication run — treat any specific number below as a **validated vintage example**, not a live figure:

```text
vintage 20260827T202855Z
OFFICIAL:     2019-02 → 2023-12  (27 EXPERIMENTAL + 21 PUBLICATION_GRADE)
PROVISIONAL:  2024-01 → 2026-06  (latest: 126.74)
```

Run `python src/indices_setoriais.py --ipia-latest` for the coverage and value of the vintage actually persisted in your checkout.

## Vintage / reproducibility

Every `--ipia` run persists an **immutable, append-only vintage** under `data/processed/vintages/ipia_hrc_v2/<vintage_id>/`, where `vintage_id` is a UTC timestamp (e.g. `20260827T202855Z`). A vintage's manifest records:

- `reference_period` — the month a given observation actually describes;
- `vintage_id` / `created_at_utc` — when this publication was produced;
- `previous_vintage_id` — chains vintages so revision history is traceable;
- `methodology_version` — the `VERSAO_METODOLOGIA` that produced this vintage;
- per-source fetch timestamps (Comex, BCB, IBGE) — what each source looked like when collected;
- SHA-256 hashes of every persisted CSV.

Earlier vintages are never overwritten or mutated; a later run only appends a new one. `--ipia-latest` and `--pdf-ipia` always read the most recent vintage with no network access and never create a new one.

## Architecture

```text
steel-indicator/
├── README.md
├── CLAUDE.md
├── requirements.txt
├── pytest.ini
├── src/
│   ├── indices_setoriais.py       # calculation engine, CLI, embedded selftest
│   ├── steel_indicator/           # extracted package (in-progress migration)
│   │   ├── domain/                # generic index engine, provenance
│   │   ├── data/                  # data contracts
│   │   ├── sources/                # Comex adapter
│   │   ├── parameters/            # historical trade-policy resolution (II/AFRMM/antidumping)
│   │   └── storage/                # vintage store, manifest
│   └── reporting/                 # presentation layer (PDF), consumes calculated results only
├── scripts/                        # one-off production/research runners (see docs/LEGACY notes below)
├── tests/
│   ├── characterization/           # freezes legacy behavior
│   ├── unit/                       # deterministic, no network
│   └── integration/                # reserved for live-source contract tests (currently empty)
├── docs/                           # methodology, ADRs, architecture, data sources, validation
├── data/
│   ├── curated/                    # versioned curated inputs (company-disclosure anchor)
│   ├── raw/                        # gitignored
│   └── processed/                  # gitignored — CSV outputs + vintage store
├── references/                     # original research, evidence only
└── .claude/                        # project rules and agent definitions
```

`src/indices_setoriais.py` is still the orchestration/compatibility surface for the whole engine (CLI, calculation, embedded `selftest()`); `src/steel_indicator/` is the target package structure being extracted from it incrementally (see [`docs/architecture.md`](docs/architecture.md)). Reporting never recollects data or recomputes economics — it consumes the same result objects the CLI/CSV outputs use.

## Data sources

| Data | Source |
|---|---|
| Brazilian steel imports (value, weight, freight, insurance, origin) | Comex Stat / MDIC (`/general` POST) |
| Exchange rate | Banco Central do Brasil — SGS |
| Domestic price benchmark (PIA-Produto) | IBGE / SIDRA table 7752 |
| Monthly chaining index (IPP 242-Siderurgia) | IBGE / SIDRA |
| Corporate validation anchor | Usiminas and CSN public quarterly disclosures |

Full source registry, verification states and collection rules: [`docs/data-sources.md`](docs/data-sources.md).

## How to install

```bash
git clone https://github.com/mori-mkm/steel-indicator.git
cd steel-indicator
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

```bash
pip install -r requirements.txt
```

Direct dependencies: pandas, NumPy, Requests, Matplotlib, pdfplumber, xlrd (see `requirements.txt` for why each is needed).

## Usage

| Command | Network | Creates vintage | Output |
|---|---|---|---|
| `--selftest` | no | no | math/provenance self-checks, exit code |
| `--check-sources` | yes | no | live probe of the public APIs used |
| `--ipia` | yes | **yes** | publishes IPIA-HRC: fetches sources, calculates, persists a new vintage, writes `data/processed/ipia_hrc_v2_official.csv` + `ipia_hrc_v2_provisional.csv` |
| `--ipia-latest` | no | no | prints the latest persisted vintage's summary |
| `--pdf-ipia` | no | no (PDF only) | 4-page IPIA-HRC PDF built from the latest persisted vintage |

`--ipia-latest` and `--pdf-ipia` fail with an explicit message (never a silent fallback) if no vintage has been published yet. `--ano-ini`/`--ano-fim` do not apply to the IPIA-HRC commands — the publication window is fixed by the approved contract ([ADR 0013](docs/adr/0013-ipia-hrc-publication-contract.md)).

## Testing

```bash
python -m pytest tests/ -v
python src/indices_setoriais.py --selftest
```

330 automated tests (characterization + unit), plus the embedded engine self-check. No unit or characterization test makes a live network call or writes to `data/processed/`.

## Reporting

```bash
python src/indices_setoriais.py --pdf-ipia
```

generates a 4-page `data/processed/ipia_relatorio.pdf` entirely from the latest published vintage — never re-fetches or recalculates:

1. **IPIA-HRC** — executive view: current provisional value (or, if none exists yet, the last confirmed historical value, explicitly labeled as historical, never as current), last-12-months trend, and vintage metadata.
2. **Paridade de Importação** — import-parity cost series and quality indicators.
3. **Dinâmica Histórica** — full history by `publication_status`; months without a publishable value render as a real gap, never interpolated or implied adjacent.
4. **Metodologia, Qualidade e Publicação** — status legend, domestic-proxy disclosure, low-liquidity disclosure, corporate-benchmark validation note, vintage metadata.

A separate legacy report path (`gerar_relatorio_ipia`, cost-decomposition + country-of-origin breakdown) still exists in `src/reporting/report_builder.py` but is no longer reachable from `--pdf-ipia`.

## Methodology governance

- [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md) — official methodology, all products.
- [`docs/adr/`](docs/adr/) — 13 accepted Architecture Decision Records, including the domestic-price anchor ([0001](docs/adr/0001-ancora-preco-domestico-usiminas-csn-ponderado.md)), the PIA-Produto benchmark ([0010](docs/adr/0010-pia-produto-hrc-benchmark-anual-proportional-denton.md)), the official/provisional split ([0011](docs/adr/0011-ipia-hrc-v2-status-provisional-e-series-oficial-provisional.md)), append-only vintages ([0012](docs/adr/0012-ipia-hrc-v2-vintages-append-only.md)), and the publication contract ([0013](docs/adr/0013-ipia-hrc-publication-contract.md)).
- [`docs/validation/`](docs/validation/) and [`docs/decisions/`](docs/decisions/) — the evidence and readiness analysis behind the V2 publication decision.
- [`docs/data-sources.md`](docs/data-sources.md) — source-by-source verification status and collection rules.
- [`docs/architecture.md`](docs/architecture.md) — target software architecture and current migration state.

## Project roadmap

**DONE:**
- IPIA-HRC (import-side + PIA-based domestic side, publication contract, vintages, CLI, 4-page report).

**NEXT:**
- IPIA-Rebar — same shared engine, own NCM basket and domestic-price source (not yet implemented);
- ICCS — sector credit-conditions index (pillar/weight specification exists in `docs/METODOLOGIA.md`; collectors not yet implemented);
- ICS — synthetic sector-conditions index (not yet started).

## Limitations

- the domestic price is a declared **proxy** (PIA mixes export destinations; IPP 242 is sector-wide, not HRC-specific) — not an observed HRC-specific price;
- publication-grade history is short (21 months, 2022-04–2023-12); the rest of the published history is either EXPERIMENTAL or PROVISIONAL;
- the current extension (PROVISIONAL) is revisable whenever IBGE releases the next annual PIA-Produto benchmark;
- no volume-based smoothing is applied to low-liquidity months — a disclosure statement covers the limitation instead of a threshold;
- this is independent research, not a licensed price-reporting agency index; it should not be used as the sole basis for a commercial or contractual decision.

## Disclaimer

Steel Indicator is an independent data-engineering and methodology project. It is not affiliated with, endorsed by, or sourced under license from Comex Stat/MDIC, Banco Central do Brasil, IBGE, Usiminas or CSN. All source data is public; all transformations are documented and auditable in `docs/`.

## Author

**Matheus Mori**

Statistics, Data Science, Machine Learning and decision-oriented analytics products.

GitHub: [github.com/mori-mkm](https://github.com/mori-mkm)
