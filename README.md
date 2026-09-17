# MANAK-SETU

SIH PS 26108. Given a product spec or a list of IS numbers cited in a tender, it
returns the correct current standard, whether any cited standard is
outdated/withdrawn, mandatory BIS certification requirements, and commonly
co-cited related standards.

The CSVs in `./data/` are the only source of truth. Nothing is generated,
inferred, or synthesised — if a lookup finds nothing, it returns `found: false`
(or a "Low - route to BIS office" confidence) instead of guessing. The semantic
matcher ranks the 27,687 real standards by embedding similarity; it is structurally
incapable of emitting an IS number that is not in the master list.

## How to run

```bash
python3 -m venv backend_venv
source backend_venv/bin/activate
pip install -r requirements.txt

python load_db.py          # builds manak_setu.db from the CSVs
python build_embeddings.py # builds standards_embeddings.npy (run once)

uvicorn main:app --reload
```

FastAPI serves `frontend/` itself, so open <http://127.0.0.1:8000>. The header
reads "connected · 5 tables" when the database loaded.

### Growing the tender corpus

The tender rows come from public procurement documents, and the largest
scriptable source is GeM. Every bid has a public bid document at
`bidplus.gem.gov.in/showbidDocument/<id>`, and that document links to the
buyer's specification attachments — which is where the IS numbers are written.
`collect_gem_tenders.py` samples bid ids across 2024–2026, follows those links,
and records only citations literally present in the attachments:

```bash
python collect_gem_tenders.py --sample 2000 --seed 3   # resumable; ~1 bid/s
python merge_gem_tenders.py                            # dry run: what would change
python merge_gem_tenders.py --write                    # additive merge
python rebuild_graph.py && python rebuild_backlog.py && python load_db.py
```

Service bids are skipped (they carry scopes of work, not specifications), bids
whose attachments are scans are kept as `Not extractable`, and each row's
`Product Family` is the majority family of its citations *as resolved in the
register* — never guessed from the document's wording. The fetched PDFs stay
under `data/tenders/` and are not committed; the repo carries citations and
source links, not copies of public documents.

To run the correctness checks:

```bash
python test_engine.py   # eyeball engine.py functions against real IS numbers
python benchmark.py     # dead-citation detector vs. tender ground truth
```

## Frontend

`frontend/` is a dependency-free app (`index.html` / `styles.css` / `app.js`) —
no build step, no framework. Ten pages:

| Page | What it does |
|---|---|
| **Dashboard** | Live corpus aggregates — status donut, coverage meter, decade histogram, family/degree/gap bars. Recomputed from SQLite on every load. |
| **Analyze Tender** | Drag-drop a tender PDF (parsed server-side by pdfplumber), paste spec text, or enter IS numbers. One-click presets load real corpus examples. Severity-sorted findings. |
| **Tender Corpus** | Browse and filter all 4,917 real tenders; click any row to run a live compliance check on its actual citations. |
| **Knowledge Graph** | Canvas graph of all 1,858 co-cited standards, each drawn with its 12 best-evidenced relationships out of 35,806 pairs held; laid out server-side. Family filter, confidence threshold, node drill-down with real evidence statements. |
| **Standards** | All 27,687 rows, searchable/filterable, with a detail drawer (record + certification + co-citations). |
| **Certifications** | All 737 rules across ISI Mark Scheme I, CRS, QCO and Hallmarking. |
| **Coverage & Gaps** | The 99.0% coverage figure with its exact denominator, and the 20-row remaining collection backlog. |
| **Benchmark** | Runs the golden benchmark live and shows the confusion matrix, with an explicit warning against quoting a bare accuracy percentage. |

Also: dark mode, ⌘K command palette, and a print stylesheet (⎙ exports the
current analysis as a report).

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/analyze` | Spec match + dead-citation + certification + related, for a list of IS numbers |
| `POST` | `/extract` | Upload a PDF → pdfplumber text + literal IS-citation extraction |
| `POST` | `/extract-text` | Same extraction over pasted text |
| `GET` | `/stats` | Live corpus aggregates with explicit denominators |
| `GET` | `/graph` | Co-citation nodes + edges, enriched with title/status/family |
| `GET` | `/standards` · `/standard?is_number=` | All standards · one standard with cert + related |
| `GET` | `/certifications` · `/tenders` · `/backlog` | Full tables |
| `GET` | `/benchmark` | Re-runs the golden benchmark, returns the confusion matrix |
| `GET` | `/health` | Row counts per table, and when BIS was last checked |
| `POST` | `/report` | The audit as a standalone printable compliance report |

## `POST /analyze`

Request:

```json
{
  "spec_text": "steel reinforcement bars for construction",
  "cited_is_numbers": ["IS 5831", "IS 999999"]
}
```

`spec_text` is optional (skip it to only check cited IS numbers). `cited_is_numbers`
is optional (skip it to only run the spec match).

Response:

```json
{
  "matched_standards": {
    "matches": [
      {"is_number": "IS 9537 (Part 2)", "score": 0.3814},
      {"is_number": "IS 1653", "score": 0.3752},
      {"is_number": "IS 3837", "score": 0.3225},
      {"is_number": "IS 3480", "score": 0.3157},
      {"is_number": "IS 10606", "score": 0.3154}
    ],
    "confidence": "Low - route to BIS office",
    "message": "No confident match found for this spec. Top candidates are shown for reference only — route to a BIS office for manual verification."
  },
  "dead_citations": {
    "IS 5831": {"found": true, "dead": false, "status": "Current"},
    "IS 999999": {"found": false}
  },
  "certifications": {
    "IS 5831": {"found": false},
    "IS 999999": {"found": false}
  },
  "related": {
    "IS 5831": [
      {"target_is": "IS 8130", "confidence": 0.95, "lift": 5.786, "evidence_statement": "Cited alongside IS 5831 in 19 of 20 comparable tenders"},
      ...
    ],
    "IS 999999": []
  }
}
```

Confidence bands for `matched_standards`: `score >= 0.65` → `High`,
`score >= 0.40` → `Medium`, else `Low - route to BIS office` (this example spec
text was deliberately generic to show the low-confidence path — real construction
specs like "PVC insulated cable" score High, e.g. matching `IS 5831` at 0.77).

`GET /health` returns row counts per table, e.g.:

```json
{"status": "ok", "row_counts": {"standards": 27687, "tenders": 4917, "co_citation": 65872, "certification_rules": 737, "coverage_gap_backlog": 20}}
```

## Known Data Gaps

These are real, disclosed limitations of the current dataset — not implementation
bugs. Do not try to "fix" them by adding synthetic rows to the CSVs.

- **Standards coverage**: 27,687 standards in `standards_master_extended.csv`,
  collected from the BIS catalogue's own public search endpoint by
  `collect_catalogue.py` (34,884 records swept, 29,939 new). Of the 4,917 tender
  rows, **1,172 are `Usability = Usable`** — the rest are service bids, scans, or
  specifications naming no standard, and are excluded from every coverage and
  accuracy statistic. Those 1,172 usable tenders cite **1,986 distinct IS
  numbers**, of which **1,966 (99.0%)** are present in the register. The figure
  was 84 (17%) at the start of the project and 483 of 488 (99.0%) against the
  old 2,087-row register; it fell to 891 of 1,237 (72.0%) when the corpus grew,
  the catalogue harvest closed it again to 1,964 of 1,991 (98.6%), and fixing
  the citation pattern that was reading "IS 201619" out of "IS:2016-1967"
  removed eight fabricated gaps and added five real citations. The remaining **20** correctly
  return `found: false` and are the rows in `coverage_gap_backlog_current.csv`.
  That gap is closed by collection, never by writing synthetic rows into the
  CSVs.
- **Deployment memory**: the full pipeline needs more than the 512 MB a free
  host provides — measured at 745 MB with 27,687 standards, torch and both
  encoders. `sentence_transformers` is imported lazily, so every endpoint that
  does not embed anything serves at 135 MB; `/recommend` and the audit path do
  not fit. `MANAK_LEXICAL=1` runs BM25, the filters and the gate in 188 MB with
  no torch at all, and ranks well (61/71 at rank 1 on the golden set against the
  hybrid's 56/71) — but it is **not** a supported fallback, because BM25 is
  unbounded and its scores scale with query length, so no threshold separates a
  real match from a coincidence across queries of different shapes. The
  confidence gate needs the dense retriever's bounded similarity.
- **Hindi titles**: 1,949 of 27,687 standards (7.0%) carry the Hindi title BIS
  publishes for them, collected by `collect_catalogue.py` from the same
  catalogue endpoint as the English one. Those are indexed directly, so a Hindi
  query can be matched without a translation service — which matters because
  the free translation providers refuse the shared datacentre addresses a hosted
  deployment sits behind. Coverage is narrow and skewed to recently published
  standards, so this path complements translation rather than replacing it.
  Where BIS has not named a standard in Hindi, nothing is invented and the query
  falls back to translation.
- **Confidence calibration**: `eval_retrieval.py` writes `data/calibration.json`
  — for each score band, how often the top answer was the expected standard.
  The honest reading is that **the score is concentrated, not calibrated**:
  569 of the 621 queries (92%) score between 0.9 and 1.0, and within that band
  the answer is right **453 of 569 times (80%)**. The remaining bands hold one
  to nineteen queries each, which is far too few to quote, so the interface
  shows a calibration line only for a band with at least 30 queries and says
  nothing for the rest. Expected calibration error is 0.161.
  The cause is the cross-encoder's sigmoid saturating — the score behaves more
  like a decision than a probability. It is still the right input to the gate,
  which compares it against fixed thresholds, but it should not be presented as
  "the system is 97% sure".
- **Evaluation set**: 621 query/standard pairs in `golden_queries.csv`, built by
  `build_golden.py` from BIS's own certification notifications — the
  notification names a product in its own words and states the standard it
  applies to, so the label comes from a legal instrument rather than from
  hand review. It was 71 pairs and electrical-only while it was built from the
  77 Quality Control Orders; the catalogue sweep added the Scheme I list, and
  with it 146 steel, 20 agro-textile, 18 fastener, 17 aluminium and 12 cement
  queries.
  Current scores against all 27,687 standards: **Recall@1 464/621 (75%)**,
  **Recall@10 525/621 (85%)**, abstention 39/621 (6%), of which 14 had no
  correct answer available. `eval_retrieval.py` breaks rank-1 down by product
  family, because one figure over a set this uneven hides which domains it was
  measured on — fasteners score 94%, cement 83%, steel 78%, hand tools 50%.
  Two limits remain: the queries are notification text rather than an officer's
  own phrasing, and families BIS does not certify are still unmeasured.
- **Certification gaps**: `certification_rules_all.csv` has 737 rows across four schemes — BIS Product Certification (ISI Mark, Scheme I) 628, Quality Control Orders 77, CRS (Scheme II) 30, Hallmarking 2. Some
  product families — e.g. LED lighting — currently have **zero** certification
  rows. `check_certification` correctly returns `found: false` for these;
  there is no certification data to report, not missing logic.
- **Supersession coverage**: of 27,687 standards, 20,115 are `Current`, 277 are
  `Superseded`, and 7,295 are `Withdrawn`. `pipeline.py --only versions` verified
  all 549 reachable pre-harvest rows against the BIS portal and found **99
  amendments** — 52 status changes (43 of them standards recorded as Current that
  BIS has since withdrawn or superseded, 40 of those withdrawn outright) and 47
  edition-year corrections. All 99 were applied and are stamped in `Provenance`.
  Only a small number of standards carry a recorded successor; the rest have
  `Replaced By = "UNKNOWN"` (no recorded successor), and `check_dead_citation`
  surfaces that value as-is rather than inventing a replacement.
- **Citation extraction**: citations are read literally from document text, and
  the pattern has been narrowed twice against real documents. It no longer reads
  the English word "is" followed by a number ("purchase preference is 20%"), nor
  a table row number after the boilerplate "as per relevant IS", nor a match
  inside a longer word such as THIS or BASIS. Re-extracting the collected
  corpus from the saved attachments removed 3,341 citations the earlier pattern
  had invented. Anything the pattern still reads is present verbatim in the
  document.

## Checks

[![checks](https://github.com/Jay-Naik2526/manak-setu/actions/workflows/checks.yml/badge.svg)](https://github.com/Jay-Naik2526/manak-setu/actions/workflows/checks.yml)

Every push runs three gates, none of which are unit tests — because none of
this project's real bugs were the kind a unit test catches. Each one was two
places holding the same fact and drifting apart.

| Gate | What it refuses |
|---|---|
| `consistency_check.py` | The backlog disagreeing with the coverage figure; a graph node that resolves to nothing and is declared nowhere; a citation that is neither held nor logged as a gap; a stored citation the designation pattern refuses; a golden-set label naming a readable standard the register lacks; `/stats` row counts that do not match `COUNT(*)`. |
| `qa_adversarial.py` | 28 cases that must fail safely — a corrupt PDF, a scanned page with no text layer, an override with no rationale, a phantom citation with no graph support, a peer lookup with nothing comparable. |
| `eval_retrieval.py --min-recall` | Retrieval getting worse than a level already demonstrated. A floor, not a target: tuning toward a number is how an evaluation set gets gamed. Run locally — it needs both encoders and does not fit a free runner's budget. |

`consistency_check.py --quick` skips the re-extraction pass, which re-reads
saved tender attachments and diffs them against the stored citations. Run it
without `--quick` locally, where the PDFs are.
