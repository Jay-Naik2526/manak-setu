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
| Better UI — animations, layout, something new | **H** (full specification), with A and E |
| Very optimised and smooth, everywhere | **S** — the list endpoints are 10.2 MB and 3.4 MB; the fix is server-side |
| Bhashini, integrated end to end | **L** — the client is built here; the two credentials are yours to paste |

Phase order by leverage: **A → S → H → L → B → C → D → E → F → G**. A and S make
it fast, H makes it memorable, L is the flow the user asked for by name. B–E are
independent of each other and can be done in any order if credits run short.
F and G are stretch: last, and only with the measurement.

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

## Phase L — Bhashini, integrated end to end  (~2 h; needs the user's two credentials to verify live)

**State:** `multilingual.py` has no Bhashini code — a comment says it "should be"
the provider (lines 26–28) and nothing more. The translation chain today is:
BIS Hindi titles → MyMemory → Google, with IS numbers and units masked by
`_protect()` before any provider sees the text. Bhashini goes **first** in that
chain when configured, and the rest is unchanged as fallback.

**What Bhashini is, precisely.** The Government of India's ULCA platform
(bhashini.gov.in) exposes translation through a two-step pipeline API. Step one
asks the platform which service handles a language pair and returns a callback
URL and an inference key; step two calls that URL with the text. The executing
model must **verify the endpoint and field names against the current
documentation at bhashini.gov.in / ulcacontrib before shipping** — they have
changed before — but the shape below is what the platform has published:

1. `POST https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline`
   headers `userID: <ULCA_USER_ID>`, `ulcaApiKey: <ULCA_API_KEY>`; body
   `{"pipelineTasks":[{"taskType":"translation","config":{"language":{"sourceLanguage":"hi","targetLanguage":"en"}}}],"pipelineRequestConfig":{"pipelineId":"64392f96daac500b55c543cd"}}`
   → read `pipelineInferenceAPIEndPoint.callbackUrl`,
   `pipelineInferenceAPIEndPoint.inferenceApiKey.{name,value}` and
   `pipelineResponseConfig[0].config[0].serviceId`.
2. `POST <callbackUrl>` with header `<inferenceApiKey.name>: <value>`; body
   `{"pipelineTasks":[{"taskType":"translation","config":{"language":{"sourceLanguage":"hi","targetLanguage":"en"},"serviceId":"<serviceId>"}}],"inputData":{"input":[{"source":"<masked text>"}]}}`
   → `pipelineResponse[0].output[0].target`.

**L1 — the client, in `multilingual.py`.** `_via_bhashini(text, source, target="en")`:
reads `ULCA_USER_ID` and `ULCA_API_KEY`; returns `None` immediately if either
is absent; caches the step-one config **per language pair for the process
lifetime** (it is stable and step one is the slow call); 12 s timeouts; any
HTTP error, timeout or unexpected shape returns `None` and logs one line, so
the chain falls through exactly as today. Language codes are ISO 639-1
(`hi mr bn ta te kn ml gu pa or ur as`) — the same ones `detect_script` and the
switcher already use. `MANAK_TRANSLATE_PROVIDER=bhashini` puts it first;
unset, the chain is unchanged. The response's `provider` field says which
provider actually answered, and the interface's language note reads
"translated by Bhashini" **only** when it did — never as a label on the
switcher.

**L2 — `python multilingual.py --doctor`.** One command that prints, for the
current environment: whether the two ULCA variables are set, whether step one
returns a callback for hi→en, whether step two translates a fixed sentence,
and the same for MyMemory and Google — each line PASS/FAIL with the reason.
This is the answer to "I have a problem integrating it": the user runs one
command and sees which step fails.

**L3 — the interface in twelve languages, translated by the Government's own
service.** `translate_ui.py --provider bhashini` regenerates the ten
machine-translated locale files (`frontend/locales.js`) through Bhashini's
batch input (`inputData.input` accepts a list), with the same `.mono` /
`.std-title` / IS-number exclusions. Keep the old files; write the new ones
only after a spot check of ten strings in two languages, and record in the
commit which provider produced each locale. Hindi and English stay
hand-checked.

**L4 — deployment.** The two credentials go in Render's Environment tab (the
user does this — they are secrets and never enter `render.yaml` or the repo).
Then the hosted site translates through Bhashini, which does not refuse the
datacentre IP the free providers refuse — so the Hindi demo step can return to
the walkthrough **if and only if** it is verified working on the live link.

**Registration, for the user (the model cannot do this):** bhashini.gov.in →
register on ULCA → profile → generate `userID` and `ulcaApiKey`; set them as
`ULCA_USER_ID` and `ULCA_API_KEY` locally (`export …`) and in Render; run
`--doctor`.

**Acceptance:** with the variables unset, every existing test passes and the
behaviour is byte-for-byte what it was; with them set, `--doctor` shows PASS on
both steps, `औद्योगिक सुरक्षा हेलमेट` returns IS 2925 with `provider: bhashini` in
the response and the note on screen; the golden 71 Hindi-path check from the
README is re-run and its number recorded. No claim of Bhashini anywhere on
screen or in the brief until that acceptance has been seen.

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

## Phase S — Very optimised and smooth, measured  (~3 h, right after A)

**Cause, measured (17 Sep):** `/standards` serves **10,244,760 bytes** and
`/tenders` **3,429,003 bytes**, uncompressed; `/certifications` 952 KB; `/graph`
916 KB at 1.16 s. The Standards, Tenders and Certification views each fetch the
*entire* table on first open (`api('/standards')` at app.js:1259, `/tenders` at
:767 and :1161, `/certifications` at :1336) and then cap the *display* at 250
rows — so the browser downloads and parses ten megabytes to show 250 lines. The
register grew thirteenfold and the list endpoints never changed. This is the
invisible lag; the graph was the visible one.

**S1 — list endpoints become searchable and paged.** `/standards`, `/tenders`,
`/certifications` accept `q`, `family`, `status`, `limit` (default 100, max
500), `offset`, and return `{total, rows}` with a **lean projection** — only the
columns the table shows (Standards: number, title, year, status, family, review
due; Tenders: id, title, family, count, any outdated, usability; Certs: number,
description, scheme, notification). Search is `LIKE` over number and title with
the same `_is_digits` normalisation the resolver uses, so "IS:694" and "694"
find the same rows. Detail stays on `/standard?is_number=`. CSV export moves to
`/standards.csv` etc., streamed with `StreamingResponse`, so the button still
exports everything without the view ever holding everything.

**S2 — the views switch to server search.** Standards, Tenders and
Certifications: a 200 ms debounced search box, family/status selects that
requery, a "Load 100 more" control (or windowed infinite scroll — the simpler
one that stays smooth), and the table renders only the rows it has. Initial
transfer per view **≤ 100 KB** (state the bytes). Sorting by a column requeries
with `sort=`; never sorts a partial page client-side and calls it sorted.

**S3 — SQLite indexes.** In `load_db.py` after the load: indexes on
`standards("IS Base")`, `standards("IS Digits")`, `standards("Status")`,
`standards("Product Family")`, `tenders("Usability")`, `tenders("Ministry")`,
`co_citation("Source IS")`, `co_citation("Target IS")`. Measure `/audit-text`,
`/peers` and `/standard` p95 over 20 calls before and after and write both
numbers in the commit.

**S4 — caching.** Versioned static assets (`app.js?v=`, `styles.css?v=`) get
`Cache-Control: public, max-age=31536000, immutable`; `index.html` gets
`no-cache`; API responses carry an `ETag` (hash of body) so unchanged `/stats`
and `/health-index` return 304. `/stats`, `/health-index` and `/graph` are
cached in memory for 120 s and invalidated by `load_db.py` (write a marker
file it bumps). Gzip is already on; check `Content-Encoding: gzip` appears on
every JSON response over 1 KB.

**S5 — the client.** `content-visibility: auto` with `contain-intrinsic-size`
on cards below the fold; `<link rel="preload">` for the two font files with
`font-display: swap`; `passive: true` on scroll and wheel listeners; the i18n
DOM walk runs inside `requestIdleCallback`; no `innerHTML` rebuild of a table on
keystroke — render on the debounced result only. Split `app.js` by view using
native `<script type="module">` and dynamic `import()` per view **only if** the
measured parse time of the single file exceeds 40 ms on a mid-range laptop;
otherwise leave it, and say which.

**S6 — warm start where memory allows.** `MANAK_WARM=1` loads the retrieval
state in a background thread at startup so the first query is not the slow
one. Off by default; never set on the 512 MB host.

**Budget and acceptance (paste the numbers into the commit):**
- Lighthouse Performance **≥ 90** on Overview, Draft, Audit, Graph, Standards
  — mobile and desktop; CLS < 0.05 everywhere.
- Standards view opens in **< 400 ms** with **< 100 KB** transferred; `/graph`
  ≤ 250 KB (Phase A); no request on any first screen larger than 250 KB.
- No long task > 50 ms while typing in any search box (DevTools performance).
- `/audit-text` p95 < 300 ms and `/peers` p95 < 400 ms locally after S3.
- Nothing in any response body changes meaning; `qa_adversarial.py` 28/28
  after each sub-phase (its list-endpoint checks may need `limit=` — update
  them, do not weaken them).

---

## Phase H — The interface: evidence made visible  (~6 h, second in the order)

**Thesis.** Every other team's UI will look like an AI product: gradients, glow,
a chat box. Ours should look like an instrument — and every piece of motion
must *show where an answer came from*. The system's honesty is the brand, so
the animations are the retrieval trace, the filters, the gate and the
provenance becoming visible in sequence. Nothing decorative. Nothing that
implies work the system did not do (no "thinking" spinner that outlasts the
real latency, no shimmering "AI" badges).

**Constraints.** Palette unchanged (petrol `--pet-*`, amber `--amber`,
semantic `--ok/--bad/--info`, family colours `--k1…--k8`). Vanilla HTML/CSS/JS,
no framework, no build step. Fonts stay Merriweather (display) and JetBrains
Mono (numbers); add **Inter Tight** or **IBM Plex Sans** from Google Fonts for
UI text only if the system stack looks weak after H1 — one face, one weight
range, nothing else. Everything respects the existing
`@media (prefers-reduced-motion: reduce)` block (styles.css:741): motion
becomes instant state, never a missing state.

### H0 — Motion tokens (write these first, in `styles.css`)

```css
:root{
  --t-fast:120ms; --t-base:200ms; --t-slow:320ms; --t-reveal:600ms;
  --ease-out:cubic-bezier(.2,.7,.2,1); --ease-in-out:cubic-bezier(.65,0,.35,1);
  --stagger:40ms; --rise:8px;
}
```
Rules, enforced by review: animate **transform and opacity only**; enter
animations run **once** (IntersectionObserver, `{threshold:.2}`, unobserve
after firing) — never on every scroll; no motion on any table longer than 60
rows; `will-change` only on the element currently animating; anything with
more than ~200 elements is drawn on Canvas, not the DOM. Reuse the existing
`rise`, `pop`, `fadeUp`, `tin`, `pin` keyframes; retime them to the tokens.

### H1 — Layout: instrument, not dashboard

- **Left rail navigation** (72 px, icons with labels on hover/expand; expands
  to 220 px on ≥1440 px screens) replacing the top tab strip; the top bar
  becomes a slim status line: connection dot, register snapshot date
  (`/health.register_snapshot_date`, Phase C3), ⌘K, theme, role. The rail's
  active item carries a 3 px amber bar — the only amber in the chrome.
- **Content column** max 1280 px; cards lose their uniform border-and-shadow —
  spend `--sh-2` and `--r-3` only on the one card that is the answer
  (`#fw-gov`, the audit ledger, the health headline); supporting cards get a
  hairline `--line` and no shadow. Hierarchy comes from that difference.
- **Draft screen on ≥1200 px becomes two columns**: the query (spec text,
  presets, language) on the left and **sticky**; results on the right. The
  officer never scrolls away from what they typed.
- Type scale, set once: 34/26/20/16/14/12 with Merriweather at 900 for h1–h2
  only; UI text 14/1.5; numbers always `.mono` with `tabular-nums`. Uppercase
  eyebrows get `letter-spacing:.08em`.

### H2 — The signature moment: the retrieval-trace rail (Draft screen)

When `runForward()` receives a response, before the answer card appears,
render a horizontal **rail** at the top of `#fw-out`:

`Query → Dense (20) ∥ BM25 (20) → Fused (10) → Rerank → Filters → Gate → Answer`

Each node is a small pill; they light up left to right with a `--stagger`
delay (total ≈ 700 ms), and **every number on the rail is read from the
response**: `candidates[].dense_rank/bm25_rank` (how many came from each
retriever), the fused shortlist length, `voltage_filter/material_filter/
role_filter.applied` (a filter pill lights amber only if it demoted something,
and shows what: "voltage · 2 demoted"), and the gate's `decision` and `reason`.
If the decision is `abstain`, the rail ends at a **red stop** labelled with the
reason and the answer card is replaced by the existing abstention note — the
animation must make declining look deliberate, not like a failure. For the
Hindi-title path (`language.hindi_titles_searched`), the Dense/BM25 pills read
"BIS Hindi titles" so the rail never lies about which index answered.

Then the **answer card** enters (`pop`, `--t-slow`) and the runner-up
candidates slide into the trace table beneath with a 40 ms stagger; a
candidate demoted by a filter carries a small tag naming the filter. Clicking
any rail node scrolls to and highlights the corresponding rows.

### H3 — Confidence, drawn

Replace the score pill on `#fw-gov` with a **confidence arc** (inline SVG,
120 px): a 270° track with the two thresholds marked at 0.45 and 0.80 and
labelled "declines below / high above"; the needle sweeps from 0 to the score
over `--t-reveal` with `--ease-out`. Under it, one line from Phase C2's
calibration file: *"At this confidence the system was right N of M times"* —
with the real N and M for that bucket, or nothing if C2 has not run. The arc
colour is `--ok` above 0.80, `--amber` between, `--bad` below.

### H4 — Audit: the document x-ray

`runAudit()` today returns a list. Add the document itself: render the pasted
text in a reading pane and, as findings arrive, **underline each citation in
place** — `--ok` solid for Current, `--amber` for Superseded, `--bad` for
Withdrawn, dotted `--ink-3` for unresolved with a small "did you mean IS 694?"
chip from Phase D3's phantom detector. Underlines appear in reading order at
`--stagger` intervals; the findings **ledger** on the right builds row by row
in the same order, and its count-up uses the existing counter. Click an
underline → the ledger row highlights; click a row → the pane scrolls to the
citation. A slim summary bar above both: "17 citations · 3 withdrawn · 1
superseded · 2 unresolved" — from the response, never typed in.

### H5 — The health index as a picture

On `#ov-health` (and the Ministry section from B3): horizontal bars per
ministry, width = documents, fill = dead-citation share as a darker segment,
each bar grows from zero on enter (`transform: scaleX`, `--t-reveal`, staggered)
with the count printed at the end of the bar — never a bare percentage. The
"dead standards still cited" list gets a small inline bar per row. The year
row becomes a compact column chart with the same treatment. All CSS transforms
on ≤ 40 elements; no library.

### H6 — The graph: cinematic once, then still

On top of Phase A's Canvas renderer: nodes **fade in by family cluster**
(eight groups, 60 ms apart), edges reveal with a single `lineDashOffset` sweep
over `--t-reveal` — once — then the scene is static. Hover: the hovered
neighbourhood at full strength, everything else at 25 % alpha, tooltip shows
the real evidence sentence ("cited alongside IS 5831 in 46 of 51 comparable
tenders"). Click: the camera **eases** to the node (tween the transform matrix
over `--t-slow`) and opens the drawer. A **focus mode** toggle hides edges
below the confidence slider's value with a 200 ms fade. Reduced motion: no
entry sweep, no camera tween.

### H7 — Page and theme transitions

Use the **View Transitions API** in `go(v, entity)` when
`document.startViewTransition` exists: outgoing view fades 40 % and slides
−6 px, incoming rises 6 px, `--t-base`, `--ease-in-out`. The theme toggle
becomes a **radial wipe** from the toggle button (a `clip-path: circle()`
animation on `::view-transition-new(root)`, 400 ms) — the one flourish that
earns its place because it is instant to understand. Both feature-detected;
both disabled under reduced motion.

### H8 — Micro-interactions and states

- **Provenance ribbon** on every answer card: a hairline footer "BIS catalogue
  record · collected <date> · Verify ↗" (Phase C3). Ink-3, mono, 11.5 px. This
  is the honesty brand made visible on every screen.
- Status pills tick into place (`pop`, `--t-fast`); copy buttons morph to a
  check for 900 ms; toasts slide from bottom-right and stack.
- Skeletons keep the `sh` shimmer; under reduced motion they are flat.
- Empty states: a 48 px inline SVG in `--pet-400` line art and a sentence that
  names the next action ("Paste a specification or pick a preset").
- Error states name the cause and the fix, never "something went wrong".
- Keyboard: `/` focuses search, `Esc` closes drawer and palette, `↑↓` walk
  result rows, `Enter` opens the drawer; visible focus rings in both themes
  (`outline: 2px solid var(--amber); outline-offset: 2px`).
- Dark theme: audit every new element against `--surface-*` and `--ink-*`;
  canvas colours read tokens via `getComputedStyle` at draw time.

### H9 — Run demo, rebuilt as a film

Keep the seven steps and the sub-100 s budget. Add a **progress rail** at the
bottom (seven dots, the active one filled amber, elapsed time in mono); a
dimmed backdrop with a soft spotlight that **eases** between targets rather
than jumping; captions appear with a typewriter (35 ms/char, skipped under
reduced motion, and skippable with Space). The Draft step lets the trace rail
(H2) play in full — it is the demo's best 10 seconds.

### What not to build

No gradients or glow, no purple, no confetti, no particle backgrounds, no
parallax that costs a frame, no motion on the Standards table, no fake
progress bars, no sound. If an animation cannot say what data drives it, cut
it.

### Performance budget and acceptance

- Added JS ≤ 30 KB, added CSS ≤ 12 KB; no new runtime dependencies.
- Lighthouse Performance ≥ 90 and CLS < 0.05 on Overview, Draft, Audit, Graph
  (run it in Chrome, paste the four scores into the commit).
- 60 fps during the trace rail and the graph entry sweep (DevTools performance
  panel); first paint of the Graph view unchanged from Phase A.
- Reduced motion verified: toggle the OS setting and walk every screen — no
  missing content, no stuck states.
- Every animation in H2–H6 is listed in the commit with the response field
  that drives it. If one is decorative, remove it before committing.
- Run-demo end to end under 100 s, captions live, no console errors.
- `qa_adversarial.py` 28/28 after each sub-phase; nothing in the API changes.

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

A and S first — nothing else matters if the site stalls — then H, then L. Then
B, C, D, E in any order; they are independent. F and G last, and only with
measurement. Push after each phase. If credits run short, a finished
A + S + H + L is worth more than a half-finished everything: it is fast, it is
the one they remember, and Hindi works through the Government's own service.
