# MANAK-SETU

SIH PS 26108. Given a product spec or a list of IS numbers cited in a tender, it
returns the correct current standard, whether any cited standard is
outdated/withdrawn, mandatory BIS certification requirements, and commonly
co-cited related standards.

The CSVs in `./data/` are the only source of truth. Nothing is generated,
inferred, or synthesised — if a lookup finds nothing, it returns `found: false`
(or a "Low - route to BIS office" confidence) instead of guessing. The semantic
matcher ranks the 2,087 real standards by embedding similarity; it is structurally
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

Then serve the frontend (a separate origin keeps CORS honest):

```bash
cd frontend && python3 -m http.server 5500
```

Open <http://127.0.0.1:5500>. The sidebar status reads "backend online" when the
two are talking.

To run the correctness checks:

```bash
python test_engine.py   # eyeball engine.py functions against real IS numbers
python benchmark.py     # dead-citation detector vs. tender ground truth
```

## Frontend

`frontend/` is a dependency-free app (`index.html` / `styles.css` / `app.js`) —
no build step, no framework. Eight pages:

| Page | What it does |
|---|---|
| **Dashboard** | Live corpus aggregates — status donut, coverage meter, decade histogram, family/degree/gap bars. Recomputed from SQLite on every load. |
| **Analyze Tender** | Drag-drop a tender PDF (parsed server-side by pdfplumber), paste spec text, or enter IS numbers. One-click presets load real corpus examples. Severity-sorted findings. |
| **Tender Corpus** | Browse and filter all 220 real tenders; click any row to run a live compliance check on its actual citations. |
| **Knowledge Graph** | Animated force-directed graph of the 193 co-cited standards / 3,336 edges. Family filter, confidence threshold, node drill-down with real evidence statements. |
| **Standards** | All 2,087 rows, searchable/filterable, with a detail drawer (record + certification + co-citations). |
| **Certifications** | All 77 QCO/CRS rules. |
| **Coverage & Gaps** | The 99.0% coverage figure with its exact denominator, and the 5-row remaining collection backlog. |
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
| `GET` | `/health` | Row counts per table |

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
{"status": "ok", "row_counts": {"standards": 2087, "tenders": 220, "co_citation": 3336, "certification_rules": 737, "coverage_gap_backlog": 5}}
```

## Known Data Gaps

These are real, disclosed limitations of the current dataset — not implementation
bugs. Do not try to "fix" them by adding synthetic rows to the CSVs.

- **Standards coverage**: 2,087 standards in `standards_master_extended.csv`. Of the 220
  tender rows, only **134 are `Usability = Usable`** (the rest —
  `Not extractable` / `Multi-scope` / `Extraction failed` — are excluded from
  every coverage/accuracy stat). Those 134 usable tenders cite **488 distinct
  IS numbers**, of which **483 (99.0%)** are present in the register. The figure
  was 84 (17%) at the start of the project and 182 (37.3%) before the full
  harvest: `collect_missing_standards.py --all` collected 1,126 catalogue records
  from the BIS Standards Portal's own public search endpoint (1,181 targets, 55
  with no catalogue match).
  The remaining **5** correctly return `found: false` from
  `check_dead_citation` / `check_certification`, and are the 5 rows in
  `coverage_gap_backlog_current.csv` (`rebuild_backlog.py`). That gap is closed
  by collection, never by writing synthetic rows into the CSVs.
- **Review dates**: 1,844 of 2,087 standards carry BIS's own `validUpto`
  review date, collected by `collect_review_dates.py`. **121 are overdue** — the
  edition is past the date BIS set for its review, so the citation should be
  confirmed before publication. This is *not* an amendment number: BIS does not
  publish those through any endpoint this system could reach, and the interface
  says so rather than implying otherwise. The endpoints tried, and the contract
  recovered for one of them, are documented at the top of `stage_versions` in
  `pipeline.py`.
- **Certification gaps**: `certification_rules_all.csv` has 737 rows across four schemes — BIS Product Certification (ISI Mark, Scheme I) 628, Quality Control Orders 77, CRS (Scheme II) 30, Hallmarking 2. Some
  product families — e.g. LED lighting — currently have **zero** certification
  rows. `check_certification` correctly returns `found: false` for these;
  there is no certification data to report, not missing logic.
- **Supersession coverage**: of 2,087 standards, 1,595 are `Current`, 95 are
  `Superseded`, and 397 are `Withdrawn`. `pipeline.py --only versions` verified
  all 549 reachable pre-harvest rows against the BIS portal and found **99
  amendments** — 52 status changes (43 of them standards recorded as Current that BIS
  has since withdrawn or superseded, 40 of those withdrawn outright) and 47 edition-year corrections. All 99 were applied
  and are stamped in `Provenance`.
  Only **10** standards carry a recorded successor; the rest have
  `Replaced By = "UNKNOWN"`
  (no recorded successor); `check_dead_citation` surfaces that value as-is
  rather than inventing a replacement.
