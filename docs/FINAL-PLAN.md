# MANAK-SETU — Final plan for the 500 → 5 stage

Self-contained. A model executing this needs nothing from the chat that produced
it. Read **State**, obey **Hard rules**, then work **Phases** in order — each has
commands and an acceptance check. Report honestly at every checkpoint: numbers
with denominators, failures as failures.

Repo: https://github.com/Jay-Naik2526/manak-setu · Live: https://manak-setu-h8b0.onrender.com
Local run: `backend_venv/bin/uvicorn main:app --port 8000` (serves API + frontend).

---

## Hard rules (from CLAUDE.md — non-negotiable)

1. **Never fabricate or infer an IS number, title, year, status, supersession or
   certification rule.** Every row in `data/*.csv` traces to a BIS page or a real
   tender document. A lookup that finds nothing returns `found: false` — that is
   correct behaviour, not a bug.
2. **Never modify the CSVs in `data/` except through an explicit collection step**
   (a `collect_*.py` script writing a `*_collected*.csv`, then a `merge_*.py`
   with `--write`). Merges are additive; existing rows are never overwritten.
3. **Every statistic is computed fresh and stated with its denominator.** Never
   "100% coverage", never "100% accuracy", never a percentage over a positive
   class smaller than ~30.
4. **BIS sells the text of standards.** Index titles, numbers, families,
   status, review dates, and public tender citations only. Never fetch or store
   standard text.
5. **Guards live in code, not prompts.** Any LLM output is validated by regex
   against the retrieved set before it reaches the screen.
6. Do not change the colour palette (petrol `#08303F`, amber `#C25A0D`).
7. Git: author `Jay-Naik2526 <171161084+Jay-Naik2526@users.noreply.github.com>`,
   **no Co-Authored-By trailer**, push to `origin main` after each phase passes.
8. Do not create loops, agents or background jobs the user did not ask for.

---

## State (16 Sep 2026)

| Asset | Now |
|---|---|
| Standards register (`data/standards_master_extended.csv`) | 2,087 rows: 1,595 Current · 95 Superseded · 397 Withdrawn |
| Tender corpus (`data/tender_dataset.csv`) | 220 documents, 134 Usable |
| Co-citation graph | 3,336 edges / 193 nodes (usable tenders only) |
| Certification rules | 737 (Scheme I 628 · QCO 77 · CRS 30 · Hallmarking 2) |
| Retrieval eval (`eval_retrieval.py`, 71 golden queries) | Recall@1 58/71 (82%) · Recall@10 65/71 (92%) · abstain 3/71 |
| Dead-citation benchmark (`benchmark.py`) | 4/4 caught, 0 FP over 20 clean (n=24) |
| Adversarial suite (`qa_adversarial.py`) | 23/23 |
| Deploy | Render free (512 MB), full mode, no Ollama, translation provider refuses the datacentre IP |

### Standing target: 1,000 usable tender documents

The user asked for a corpus of **1,000 `Usability = Usable` documents**. The
corpus held 134 before collection started. Measured yield is **2.5% Usable per
bid id tried**, so ~35,000 more ids are needed. The collector is the way to get
there and it runs detached; keep it alive across the whole plan.

**Never fake this number.** If the collector cannot reach 1,000 in the time
available, report the real count with its denominator (e.g. "612 usable of
1,431 documents collected from 24,500 bid ids") and say plainly that the target
was not met. A smaller honest corpus beats a padded one, and padding it would
break hard rule 1.

Keep-alive check — run this at the start of every phase, and relaunch if dead:

```bash
pgrep -f collect_gem_tenders.py >/dev/null || \
  (MANAK_GEM_WORKERS=8 nohup backend_venv/bin/python collect_gem_tenders.py \
     --sample 60000 --seed 5 > /tmp/gem_collect.log 2>&1 &)
```

The collector is resumable and idempotent: it skips every id already in the
progress log, so relaunching never re-reads work and never duplicates a row.
`--sample 60000` draws from the same seeded range; already-tried ids are
filtered out, so the effective new work is what remains.

**The collector runs detached on the Mac** (started 16 Sep):
`collect_gem_tenders.py`, 8 workers. It resumes from
`data/tender_collected_gem.progress.jsonl`; rows accumulate in
`data/tender_collected_gem.csv`; PDFs under `data/tenders/gem/` (gitignored).
Observed outcome mix per bid id tried: 2.5% Usable · 5.5% Not extractable ·
~30% id does not exist · ~30% no spec attachment · ~12% service bid ·
~8% spec cites no IS. Check:

```bash
pgrep -f collect_gem_tenders.py && python3 -c "
import json,collections
L=[json.loads(l) for l in open('data/tender_collected_gem.progress.jsonl') if l.strip()]
c=collections.Counter(x['outcome'] for x in L); print(len(L),'tried', dict(c))"
```

If it is not running, relaunch with the keep-alive command above. Do not stop it
to run other phases — it uses a different host from the BIS catalogue API and the
two can run together.

Key files: `retrieval.py` (hybrid retrieval, filters, gate), `engine.py`
(lookups, stats, extraction), `audit.py` (tender audit + suggestions), `llm.py`
(Ollama + 6 guards), `multilingual.py`, `pipeline.py` (5 stages),
`collect_missing_standards.py` (BIS API client: `fetch()`, `pick()`,
`STATUS_MAP`, department map), `merge_collected.py`, `collect_gem_tenders.py`,
`merge_gem_tenders.py`, `rebuild_graph.py`, `rebuild_backlog.py`, `load_db.py`,
`build_embeddings.py`, `frontend/{index.html,app.js,i18n.js,styles.css}`.

---

## Why the current submission does not reach top 5, and what would

Everyone in this PS will submit "RAG + LLM + knowledge graph + multilingual".
Those are table stakes now. What no other team can have is **evidence from the
procurement system itself**, because no other team has (a) the whole BIS
catalogue and (b) thousands of real bid documents. Everything below turns those
two assets into claims a ministry evaluator cannot get anywhere else.

The four differentiators, in the order they should be built:

| # | Differentiator | Why nobody else has it |
|---|---|---|
| D1 | **Procurement Standards Health Index** — measured share of live government bids citing withdrawn/superseded standards, by product family and year, with the top dead standards still in circulation | Needs a real bid corpus. Turns the tool into a policy instrument for DoCA/BIS, not only an officer's assistant. |
| D2 | **Peer citations per item category** — "buyers of *this* GeM item category cited these standards, N times" | Needs GeM item categories + citations. Empirical, not model-inferred. |
| D3 | **Phantom-citation detector** — a cited IS number that does not exist in the catalogue is checked for a one-digit slip against standards that are co-cited with the rest of the document, and the officer is shown "did you mean IS 694 (co-cited with 3 of your other standards)?" as a *suggestion with evidence* | Needs the full catalogue (to know what exists) and the graph (to rank candidates). Catches the most common real error: a typo. |
| D4 | **Native Hindi retrieval over BIS's own Hindi titles** — no translation service in the loop | BIS's catalogue API returns `standardNameInHindi`. Legally clean, works on the hosted link where translation fails. |

Prerequisites: **P1 full catalogue harvest** (2,087 → most of ~22,000) and
**P2 tender merge** (220 → ~1,400 documents). Both are real collection from
official sources through the existing scripts.

---

## Phase 0 — Merge collected tenders (re-runnable; merge again as more arrive)

```bash
backend_venv/bin/python collect_gem_tenders.py --rederive      # titles from saved bid forms
backend_venv/bin/python merge_gem_tenders.py                    # dry run — read the numbers
backend_venv/bin/python merge_gem_tenders.py --write
backend_venv/bin/python rebuild_graph.py && backend_venv/bin/python rebuild_backlog.py
backend_venv/bin/python load_db.py
backend_venv/bin/python qa_adversarial.py                       # must stay 23/23
backend_venv/bin/python benchmark.py                            # positives will grow; report counts
```

Acceptance: `/stats` shows the new document and usable counts; the Tenders view
shows GeM rows with real titles; `git add data/tender_dataset.csv
data/co_citation_graph_full.csv data/coverage_gap_backlog_current.csv
data/tender_collected_gem.csv` and push. Record before/after in the commit body.

Note: the backlog (cited-but-not-held) will grow — that is P1's job, not a bug.

Merging is additive and repeatable. Run this phase again whenever the collector
has added a few hundred rows; each pass picks up only what is new. Re-run
Phase 3 (health index) and Phase 4 (peers) after any later merge so their
figures match the corpus.

---

## Phase 1 — P1: full BIS catalogue harvest  (~1.5 h, mostly unattended)

`searchKnowStandards` returns ≤500 records per query and accepts any word; ten
words already returned 3,696 unique standards. Sweep many words, union on
`standardId`.

Build `collect_catalogue.py` reusing `collect_missing_standards.fetch`,
`STATUS_MAP` and the department map:

1. Query words = every distinct alphabetic token (len ≥ 4) from the current
   register's titles + department names + numbers "IS 1".."IS 9", "IS/IEC",
   "ISO". Expect ~2,500 queries at 0.7 s → ~30 min. Log queries that hit 500 (cap)
   and re-query them with a second token appended.
2. Row schema = the one in `collect_missing_standards.py` (`IS Number`, `Full
   Title`, `Year` from `publishedOn[:4]`, `Status` via `withdrawStatus`/`isStatus`,
   `Replaced By`/`Supersedes` = `UNKNOWN`, `Product Family` = department name,
   `Priority` = `Collected`, `Source Link`, `IS Base`, `Collected From`,
   `Department Id`, `Committee Id`) **plus** `Title (Hindi)` from
   `standardNameInHindi` and `Review Due` from `validUpto[:10]`.
3. Write `data/standards_collected_catalogue.csv`; merge with
   `merge_collected.py --collected data/standards_collected_catalogue.csv --write`
   (additive; add `Title (Hindi)` to `MASTER_COLUMNS` there and in `load_db.py`).
4. `build_embeddings.py` (re-embeds ~15–20k titles, minutes on CPU), then
   `load_db.py`, then **re-run `eval_retrieval.py` and report the new Recall@1/@10
   honestly** — expect a drop from 82% because of more distractors. Then
   `rebuild_backlog.py` (backlog should shrink toward zero) and `qa_adversarial.py`.
5. Render: the build already runs `load_db.py`; commit the new `.npy` and
   `standards_embeddings_is_numbers.csv`. Check memory after deploy; if the
   service OOMs, set `MANAK_LIGHT=1` — do not shrink the register.

Acceptance: register ≥ 12,000 rows, every row with a Source Link and
provenance; eval numbers re-measured and written into README "Known Data Gaps";
`/health` and the site show the new counts (they read live).

---

## Phase 2 — D4: native Hindi retrieval  (~1 h, after P1)

In `retrieval._load()`, build a second BM25 index over `Title (Hindi)` where
present (tokeniser: split on whitespace/punctuation, keep Devanagari tokens).
In `recommend()`: if `detect_script(query) == "hi"` (Devanagari), **run the Hindi
BM25 before translation** and include its ranking in `_rrf()` alongside the
translated dense + BM25 rankings; if translation is unavailable, use the Hindi
ranking alone and set `reason` to `hindi_title_match` rather than
`translation_unavailable`. The cross-encoder still scores English blobs, so when
only Hindi ranking exists use the fused rank as the score (the `LIGHT_MODE`
path already does this). Report in `language.note` which path answered.

Acceptance: with the translation providers blocked (set `MYMEMORY=""` or point
`HOST` to a closed port in a test), the query `औद्योगिक सुरक्षा हेलमेट` still returns
IS 2925 when the register carries a Hindi title for it, and the UI note says the
match came from BIS's Hindi title. Measure: how many of the golden 71 have a
Hindi title, and Recall@10 over those via Hindi queries (write the number with
denominator into README). Restore the Hindi demo step **only if** it works on
Render.

---

## Phase 3 — D1: Procurement Standards Health Index  (~2 h, after Phase 0)

`health_index.py` → `data/health_index.json`, computed from `tender_dataset.csv`
(Usable rows only) joined to the register:

- share of usable documents citing ≥1 Withdrawn/Superseded standard — overall,
  by year (from `GEM/<year>/B/…` in Tender ID, else "unknown"), by Product Family
- top 15 dead standards by number of citing documents, each with its status and
  `Replaced By` if known
- top 15 most-cited standards overall (the demand signal), with `Review Due` /
  `Overdue` — this is BIS's revision-priority list
- explicit denominators in every figure

Expose `GET /health-index`; add an Overview card **"Procurement standards
health"** (status stripe + two small tables) and a slide-ready sentence
generated from the data, e.g. *"Of 552 machine-readable government bids
(2024–2026), 61 cite a standard BIS has withdrawn. The most common: IS 1554
(Part 1):1988 — 14 documents."* Never round to a headline percentage without
the count beside it.

Acceptance: endpoint returns denominators; card renders in both themes; the
sentence appears in `docs/MANAK-SETU-demo-brief.md` and the PPT text below.

---

## Phase 4 — D2: peer citations per item category  (~1.5 h, after Phase 0)

`GET /peers?text=<spec or category>`: BM25 over `Item Category` of GeM rows
(build in `engine.py` at first call; cache in module state); take the top 30
matching documents; count their cited IS numbers; return `[{is_number, title,
status, documents, of}]` sorted by count, plus `matched_documents`. In the
Draft screen, under the governing standard, render **"Other government buyers of
similar items cited"** with counts (e.g. "IS 7098 (Part 2) — 14 of 21 similar
bids"). Withdrawn ones get the status pill so the officer sees peers citing dead
standards too — that is a feature.

Acceptance: query "XLPE cable 11 kV" lists IS 7098 with a count; an unrelated
query ("photocopier paper") returns few or no peers rather than cables.

---

## Phase 5 — D3: phantom-citation detector  (~1.5 h, after P1)

In `audit._unresolved()` (citations not in the register): for each, generate
candidates from the register whose digit string is within Damerau-Levenshtein
distance 1 (one substitution, insertion, deletion or adjacent transposition)
of the cited digits. Rank candidates by co-citation strength with the
document's *other* resolved citations (`co_citation` table); keep only
candidates with ≥1 co-citation link or an exact Product Family match. Emit a
suggestion `{"cited": "IS 6994", "did_you_mean": "IS 694", "evidence": "co-cited
with IS 5831 and IS 8130 in 27 tenders"}` — a suggestion, never a replacement.
Show it in the audit report's "unresolved" block as *"Not in the BIS catalogue.
Possibly a slip for IS 694 — co-cited with 2 of this document's standards."*

Acceptance: a unit test in `qa_adversarial.py`: a text citing "IS 6994" with
"IS 5831; IS 8130" suggests IS 694 with evidence; a text citing "IS 99999"
alone yields no suggestion. Suite must remain all-pass.

---

## Phase 6 — evidence  (~1–2 h with the team)

- Extend `data/golden_queries.csv` with 30–50 civil/pipe/steel pairs taken from
  real tender clauses (`build_golden.py` shows the format; source column must
  name the document). Re-run `eval_retrieval.py`; write the numbers by family.
- Re-run `benchmark.py` on the bigger corpus; report counts.

---

## Phase 7 — presentation (user's side; the plan supplies the text)

Slide fixes: 405 → current register count; 226 → current document count; 3,718 →
current edge count; remove Redis and Docker logos (stack is FastAPI, Python,
SQLite, NumPy, Hugging Face, Ollama, HTML/CSS/JS); ingestion caption →
*"Re-runs on a schedule; flags editions past their BIS review date."*

New USP bullets (replace generic ones):
- *Procurement Standards Health Index — measured from N real government bids: X
  cite a withdrawn standard; top offenders listed.*
- *Peer citations — what other government buyers cited for the same item, with counts.*
- *Phantom-citation detection — a typo'd IS number is caught against the full
  catalogue and the document's own co-citations.*
- *Native Hindi retrieval over BIS's own Hindi titles — no translation service.*
- *Abstains rather than guesses; every IS number an LLM writes is checked in code.*

Keep the 11 kV → Part 2 example as the opener of the technical section.

---

## Order of execution and what runs unattended

1. Phase 1 harvest (unattended ~30 min) can start **now**, in parallel with the
   GeM sweep — different hosts. Then embeddings + eval.
2. Phase 0 merge when the sweep is done (or at ~6 h, merge what exists; the
   collector resumes later and a second merge is additive).
3. Phases 2, 3, 4, 5 are independent of each other; do 3 and 4 first (they use
   the tender merge), then 5, then 2.
4. Phase 6 needs teammates; Phase 7 is the user's.

Push after each phase. Final report: a table of every number on the slides with
the command that produced it.
