# MANAK-SETU — Night 2 plan: performance, assurance, ministry value

Self-contained, like `FINAL-PLAN.md`. A model executing this needs nothing from
the chat that produced it. Read **State**, obey **Hard rules**, then work the
phases in the order given — each has implementation notes, commands and an
acceptance check. Report every number with its denominator; report failures as
failures; never present a stretch phase as done if it was not measured.

Repo: https://github.com/Jay-Naik2526/manak-setu · Live: https://manak-setu-h8b0.onrender.com
Local run: `backend_venv/bin/uvicorn main:app --port 8000` (serves API + frontend).

---

## Hard rules (unchanged, non-negotiable)

1. **Never fabricate or infer an IS number, title, year, status, supersession,
   certification rule, ministry name or buyer name.** Every value traces to a
   BIS page or a real tender document. `found: false` is correct behaviour.
2. **CSVs in `data/` change only through a `collect_*.py` → `merge_*.py --write`
   step.** Additive; never overwrite existing rows.
3. **Every statistic is computed fresh with its denominator.** No "100%". No
   percentage over a positive class smaller than ~30.
4. **BIS sells standard text.** Titles, numbers, families, status, review dates,
   public tender citations only. Never fetch or store standard text.
5. **Guards live in code, not prompts.** Anything an LLM writes is checked by
   regex against retrieved rows before it reaches the screen.
6. Palette stays petrol `#08303F` + amber `#C25A0D`.
7. Git author `Jay-Naik2526 <171161084+Jay-Naik2526@users.noreply.github.com>`,
   **no Co-Authored-By trailer**, push to `origin main` after each phase passes.
8. No loops, agents or background jobs the user did not ask for.
9. **One matcher, one extractor.** Any function that resolves an IS number
   imports `engine._is_base` / `engine._is_digits` / `engine.extract_citations`.
   Three separate bugs last night came from a second copy drifting.

---

## State (17 Sep 2026, commit `530fa2a`)

| Asset | Now |
|---|---|
| Register | 27,687 standards · 20,115 Current · 277 Superseded · 7,295 Withdrawn · 1,949 with BIS Hindi title |
| Tender corpus | 4,917 documents · 1,172 machine-readable · 6,085 citations |
| Coverage | 1,964 of 1,991 cited standards held (98.6%) · backlog 27 |
| Co-citation graph | 4,916 edges over 319 standards (`/graph` payload 916 KB — **the lag**) |
| Evaluation set | 621 pairs from BIS certification notifications, 14+ families |
| Retrieval (hybrid + cross-encoder) | Recall@1 464/621 (75%) · Recall@10 525/621 (85%) · abstain 39/621 |
| Health index | 422 of 1,172 documents cite a withdrawn/superseded standard · 354 distinct |
| Adversarial suite | 28/28 |
| Deploy | Render free: everything serves except `/recommend` (OOM, 745 MB needed vs 512) |

Saved locally (gitignored, ~19 GB): every fetched bid form and attachment under
`data/tenders/gem/` as `<bid>-bid.pdf` and `<bid>-<n>.pdf`. Phases B and F read
these; nothing is re-downloaded.

Known from last night, not yet acted on: without the cross-encoder, fused-rank
scoring reached 59/71 vs 56/71 at rank 1 on the old set. Phase D measures this
properly on 621 queries.

---

## The six asks, mapped

| Ask | Phase |
|---|---|
| The graph fully lags but must be shown | **A** |
| Alternative RAG pipelines (mentor) | **D** |
| How to be sure it never gives an incorrect answer | **C** (+ D's baseline) |
| USPs that reach top 5 | **B, C, D, E, F** — each is a claim no other team can make |
| Value to the Ministry of Consumer Affairs, Food & Public Distribution | **B**, **E** |
| Better UI | **A, E, H** |

Phase order by leverage: **A → B → C → D → E → H → F → G**. A is mandatory. B–E
are independent of each other after A and can be done in any order if credits
run short. F and G are stretch: do them last and only with the measurement.

---

## Phase A — The graph must not lag  (~2 h)

**Cause, measured:** the Graph view fetches all 4,916 edges (916 KB), creates
one SVG `<line>` per edge and one `<g>` per node, then runs `settle()` — 110
frames × 2 physics passes over 319 mutually-repelling nodes, repainting
thousands of DOM elements per frame. The hero graph on the Overview already
samples (56 nodes / 190 edges) and is fine; leave it alone.

**Fix — three parts, all required:**

1. **Compute the layout once, on the server.** New `graph_layout.py`: load
   `co_citation` from the DB, run a deterministic force layout in NumPy (319
   nodes — an O(n²) settle of 300 iterations is milliseconds), scale to
   1040×660 with the same 26 px walls the client uses, round coordinates to 1
   decimal, write `data/graph_layout.json` `{is_number: [x, y]}`. Seeded
   (`np.random.default_rng(7)`) so the picture is the same on every rebuild.
   `engine.full_graph()` merges `x, y` into each node. Run it at the end of
   `rebuild_graph.py` so it can never go stale.
2. **Send less.** `/graph` accepts `min_count` (default 5 — already the build
   threshold, so this is a no-op until raised) and `edge_limit` (default 1500,
   by co-citation count desc). Drop fields the client never reads from the
   edge objects; keep `source, target, count, confidence`. Node objects keep
   `id, title, status, product_family, degree, x, y`. Target: default payload
   **≤ 250 KB**. A "Show all 4,916 edges" toggle refetches with
   `edge_limit=0`.
3. **Draw with Canvas 2D, not SVG.** Replace the SVG build in `drawGraph()`:
   one `<canvas>` sized to the container × `devicePixelRatio`; edges drawn as
   three `Path2D` objects bucketed by confidence (<0.5, 0.5–0.8, ≥0.8) so the
   whole edge set is three `stroke()` calls; nodes as arcs coloured by family;
   labels only for the top 40 by degree plus the hovered/selected node. Pan and
   zoom through a single transform matrix; redraw only on interaction. Hit
   testing on mousemove: nearest node by squared distance over 319 nodes (a
   loop, no library). Keep the family filter, confidence slider, legend, node
   drill-down (`pickNode`) and the drawer exactly as they behave now. Delete
   `settle()`, `SETTLE_FRAMES`, `SETTLE_STEPS`, `EDGE_EVERY` and the drag
   physics; dragging a node just moves it and redraws.
   `prefers-reduced-motion` needs no special case any more — nothing animates.

**Acceptance:** `/graph` default response ≤ 250 KB (state the bytes); Graph
view first paint under 300 ms on a laptop (measure with
`performance.now()` around `drawGraph`, print it to the console once); panning
holds 60 fps in the DevTools performance panel; no console errors in light and
dark themes; the same standard selected before and after the change opens the
same drawer content; `qa_adversarial.py` still 28/28. Commit the layout JSON.

---

## Phase B — The ministry lens (Department of Consumer Affairs' USP)  (~3 h)

BIS sits under the Department of Consumer Affairs. What the department cannot
see today is **which parts of government are procuring against dead or
uncertified standards**. Every GeM bid form names its buyer — sampled 40 of 40
carry `Ministry/State Name`, `Department Name`, `Organisation Name`,
`Office Name` — and the forms are saved locally.

**B1 — extract the buyer, honestly.** In `collect_gem_tenders.py`, generalise
`extract_category()` into `field_after_label(lines, label)` and use it for the
four labels above; add columns `Ministry`, `Department`, `Organisation` to the
row. Add `--rederive` coverage for these fields (it already re-reads saved bid
forms). Values are stored **exactly as printed**, whitespace-collapsed; no
normalisation to codes, no guessing when the label is absent (leave empty).
Then `merge_gem_tenders.py` carries the three columns (add to `EXTRA_COLUMNS`),
`load_db.py` reloads. Original 220 rows have no bid form: columns stay empty
and every ministry figure states "of N GeM documents".

**B2 — the QCO enforcement gap.** DoCA's core mandate is consumer protection,
and the sharpest procurement failure in that mandate is buying a product that
legally requires the ISI mark without asking for it. `audit._statutory_omission`
already detects this per document. Compute it per row at extraction time and
store `Demands Standard Mark` (Yes/No/Not applicable) using the same
`MARK_CLAIM` pattern `llm.py` uses (import it; do not copy it), over the
attachment text. Aggregate in `health_index.py`:
*"X of Y documents that cite a product under compulsory certification never
demand the Standard Mark."* List the top product categories where this
happens. This is the single most DoCA-relevant number in the project.

**B3 — health index by buyer.** Extend `health_index.py` output with
`by_ministry` and `by_department`: documents, share with a dead citation,
share with a QCO omission, top dead standard — only for buyers with ≥ 10
documents, and always with the count beside the share. Serve on
`/health-index`. Add a **Ministry** section to the Overview health card
(table: buyer · documents · dead-citation share · QCO-omission share).

**B4 — the Food & Public Distribution and Legal Metrology lenses.** Both are
DoCA's own portfolio. Do **not** invent mappings. Derive two register filters
from titles only: `weighing|measuring instrument|balance|weights` (Legal
Metrology) and `food grain|foodgrain|jute bag|gunny|sack|storage of grain|
warehouse` (PDS/FCI). Add them as two entries in the Product Family filter
labelled "Legal Metrology (title match)" and "Food-grain storage & packaging
(title match)", and report how many register rows and how many corpus citations
each lens captures. If a lens captures fewer than 10 corpus citations, say so
on screen rather than dressing it up.

**Acceptance:** `SELECT COUNT(*) FROM tenders WHERE Ministry <> ''` reported
against the GeM row count; the QCO-omission figure printed with both numbers;
`by_ministry` only lists buyers with ≥ 10 documents; a spot check of five
extracted ministry strings against their bid PDFs (print both); 28/28.

---

## Phase C — Correctness assurance you can show a judge  (~3 h)

The question "how do you know it is not wrong?" has to be answered with
mechanisms, not adjectives. Build the four that are missing.

**C1 — `consistency_check.py`.** One script that asserts the invariants the
project's honesty rests on, and exits non-zero on any failure:
- backlog row count == `coverage.unmatched`
- every graph node resolves in the register; every edge endpoint is a node
- every citation in a Usable row either resolves or appears in the backlog
- no citation in the corpus matches the retired patterns (`\bis \d`, a
  generic-phrase prefix, `THIS|BASIS|AXIS` boundaries) — re-extract 50 random
  saved attachments and diff against stored citations; zero differences
- no IS number in `golden_queries.csv` is absent from the register
- `/health.row_counts` equals live `SELECT COUNT(*)` per table
Print each check with its numbers. This is the mechanical version of "two
numbers for one fact is the failure this project exists to avoid".

**C2 — calibration.** `eval_retrieval.py --calibration` buckets the 621 queries
by the top candidate's score (0.4–0.5 … 0.9–1.0) and reports empirical rank-1
accuracy per bucket plus expected calibration error. Write
`data/calibration.json`; render on the Benchmark screen as a bar per bucket
with the count on each bar. The honest claim this enables: *"when the system
says 0.9, it is right N of M times"* — with the actual N and M.

**C3 — provenance and freshness on every standard.** The drawer for a standard
shows: `Provenance` (already stored), the collection date, `Review Due`, and a
**"Verify on BIS"** button. The button must open the BIS catalogue with that
number as the search — establish the working URL form in a browser first
(`standards.bis.gov.in/website/know-your-standards` with the number prefilled,
or the search page if no deep link exists) and do not ship a guessed link.
`/health` gains `register_snapshot_date` (max collection date in the register)
and the sources footer shows "verified against the BIS catalogue as of <date>".

**C4 — CI that refuses a dishonest push.** `.github/workflows/checks.yml`:
install (CPU torch wheel index), `load_db.py --allow-shrink`, start uvicorn,
run `qa_adversarial.py` (fail on any failure), `consistency_check.py` (fail on
any failure), and `eval_retrieval.py` with a **floor** — Recall@10 ≥ 0.80 on
the 621 set — that fails the build if retrieval regresses. A floor, not a
target: the README says which. Add the workflow badge to the README.

**The judge answer this phase produces** (put it in the demo brief): the system
is structurally unable to emit an IS number outside the register; a gate
declines rather than guesses; six code guards check anything an LLM writes; an
invariant checker and 28 adversarial cases run on every push; the confidence
score is calibrated and the curve is on screen; every standard carries its BIS
provenance and a one-click verification link; and the officer's decisions are
logged so disagreements are visible.

**Acceptance:** `consistency_check.py` passes locally and prints its numbers;
calibration bars render with counts; the Verify link opens BIS and shows the
right standard for three numbers you try; the workflow is green on GitHub.

---

## Phase D — Alternative RAG pipelines, measured (the mentor's ask)  (~3 h, LLM parts need Ollama)

"Alternative RAG pipelines" is an invitation to show engineering judgement,
not to bolt on another chatbot. Build a **pipeline registry** and a
**leaderboard**, and let the numbers argue.

**D1 — registry.** In `retrieval.py`, `PIPELINES` with a shared interface
`run(query) -> candidates`:
- `hybrid_ce` — today's default: dense ∥ BM25 → RRF → cross-encoder → gate
- `hybrid_rrf` — the same without the cross-encoder (last night's finding)
- `dense` — MiniLM only
- `bm25` — lexical only (no gate; document why: unbounded scores)
- `graph_expand` — `hybrid_ce`, then add co-citation neighbours of the top 3
  as candidates before the gate (GraphRAG in the honest sense: retrieval
  expanded by the corpus, not by a model)
- `llm_only` — ask the local model to name the governing standard with **no**
  retrieval. This is the baseline that shows why the rest exists. Only runs
  when Ollama is up; otherwise recorded as "not measured", never faked.
`recommend()` takes `pipeline=` (default `hybrid_ce`); `/recommend` accepts it
as an optional field; nothing in the UI changes yet.

**D2 — `eval_pipelines.py`.** Runs every pipeline over the 621 set and writes
`data/pipeline_leaderboard.json`: Recall@1, Recall@10, abstention, mean
latency, peak RSS, and — for `llm_only` — **fabrication rate**: the share of
answers whose IS number does not exist in the register at all. Retrieval
pipelines have a fabrication rate of exactly zero by construction; say so in
the table with the reason.

**D3 — show it.** `/pipelines` serves the JSON; the Benchmark screen gains a
**Pipelines** table. If `hybrid_rrf` beats `hybrid_ce` at rank 1 on 621
queries *and* its calibration (C2) is as good, switch the default and record
the decision in the commit with both tables. If it does not, keep the
cross-encoder and record that too. Either outcome is a story.

**D4 — grounded "Ask the register" (optional, local only).** `POST /ask
{question}`: retrieve the top standards, certification rules and co-citations
for the question with the existing retrieval, hand **only those rows** to the
model, and require every IS number in the reply to appear in them
(`subset_guard`, unchanged). On failure return the rows themselves with a
note. A small panel on the Draft screen, shown only when `/llm` reports
available. It is a stretch because the hosted deployment has no model.

**Acceptance:** leaderboard JSON with all denominators; the table renders; the
`llm_only` row shows a measured fabrication rate or "not measured"; the
default-pipeline decision is written down with the numbers that made it.

---

## Phase E — The officer's deliverable: a compliance report  (~2 h)

An officer cannot attach a web page to a file noting. Give them a document.

`GET /report?text=…` (and a **"Export compliance report"** button on the Audit
screen that POSTs the current text): server-rendered HTML, print-ready, with —
the tender's citations and each one's status and BIS provenance; the
suggested edits (replace / add / clause / unresolved, with any did-you-mean and
its evidence); certification obligations with the Gazette reference; the
register snapshot date; and a footer stating that the report lists what the
register holds and does not certify the tender. Reuse `audit_tender()` and the
existing print stylesheet; no new dependencies. Same palette.

**Acceptance:** the report for the "outdated" preset opens, prints to one or
two A4 pages, and every IS number on it resolves in the register or is marked
unresolved.

---

## Phase H — UI, in the order a judge notices  (~2 h)

1. Graph (Phase A) — the thing that visibly lags today.
2. Loading skeletons on Graph and Standards; never a blank white area.
3. **"How this was decided"** — under every recommendation, three plain
   sentences generated from the trace: which retriever found it, which filter
   demoted the runner-up and why, and what the gate compared. The data is
   already in the response; this is wording.
4. Ministry section on the health card (B3); Pipelines table and calibration
   bars on Benchmark (C2, D3); Verify-on-BIS in the drawer (C3); Export button
   on Audit (E).
5. Keyboard: `/` focuses search, `Esc` closes drawer and palette, arrow keys
   move through result rows. Check focus rings in both themes.
6. Empty states say what to do next, not "no data".
7. Re-run the Run-demo end to end; keep it under 100 s; captions are live.

---

## Phase F — Template propagation (stretch, measurement-first)  (~3 h)

Dead citations are not random: they are copied from the last tender. Measure
it. For each GeM document with saved attachments, shingle the attachment text
(5-word shingles), MinHash with 128 permutations (implement it in ~40 lines;
no new dependency), LSH-cluster at Jaccard ≥ 0.8. For each dead standard in
the health index, report how many of its citing documents fall into shared
clusters: *"IS 8112 (withdrawn) is cited in 15 documents; 11 of them share
≥ 80 % identical specification text — one template, copied."* Write
`data/tender_lineage.json`; add a line to the health index card. If the
clusters are weak (few documents share text), report that and do not ship the
card. This is root-cause evidence for the ministry — a circular aimed at one
template fixes many tenders.

---

## Phase G — Drop torch from serving (stretch, gated on measurement)  (~2 h)

`/recommend` needs 745 MB; the free host has 512. The 466 MB is torch. Export
both encoders to ONNX (`pip install "optimum[onnxruntime]" onnxruntime`) and
load them with `SentenceTransformer(..., backend="onnx")` /
`CrossEncoder(..., backend="onnx")`. Measure peak RSS the same way as last
night and the 621-query recall. Ship **only if** RSS < 450 MB with the full
register and Recall@1/@10 are unchanged; otherwise record the numbers and stop.
Do not lower the register to fit.

---

## Phase P — Presentation text (user's side; this supplies it)

Numbers, with the commands that produce them, go in
`docs/MANAK-SETU-demo-brief.md` after each phase. New USP bullets, in the order
to say them:

- **For the Department of Consumer Affairs:** across N machine-readable
  government tender documents, X cite a standard BIS has withdrawn, and Y that
  buy a product under compulsory certification never demand the ISI mark —
  broken down by buying ministry. A measurement no other team can make.
- **It cannot invent a standard.** Every answer is a row from the BIS
  catalogue; an LLM-only baseline measured on the same 621 questions fabricates
  Z% of the time (or: "not measured", if Ollama was unavailable — never a
  guess).
- **It knows when to say no**, and its confidence is calibrated: when it says
  0.9 it is right N of M times.
- **Six retrieval pipelines measured against each other** on 621 BIS-labelled
  queries; the one shipped won on the numbers, and the table is on screen.
- **Every standard is one click from BIS**, stamped with when it was verified.
- **Officers get a document**, not a web page: a printable compliance report
  with provenance.

Keep the 11 kV → IS 7098 (Part 2) opener. Fix the idea PPT's 405 / 226 / 3,718.

---

## Order of execution and credit economy

A first — it is the only thing a judge will visibly see failing. Then B, C, D,
E in any order; they are independent. H interleaves. F and G last, and only
with measurement. Push after each phase. If credits run short, a finished
A + B + C is worth more than a half-finished everything: the graph works, the
ministry has its number, and the correctness story is mechanical.
