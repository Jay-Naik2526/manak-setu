# MANAK-SETU — Prototype Video Brief

**SIH 2026 · PS 26108 · Department of Consumer Affairs (BIS) · Team The RAGnarok**

Everything needed to write and record the prototype video. The demo runs itself —
click **Run demo** in the toolbar and narrate over it.

Live: https://manak-setu-h8b0.onrender.com
Code: https://github.com/Jay-Naik2526/manak-setu

---

## 1. Before you record — read this first

**Record against the hosted link**, not a local machine. Two features do not work
there and must not appear in the video:

| Feature | Why it is absent |
|---|---|
| Multilingual input | The translation provider refuses shared datacentre IPs. The page says so honestly, but that is not a good look on camera. |
| LLM-drafted clauses | A 7B model does not fit a free 512 MB host. Clauses come from the deterministic template, and the interface states this. |

The Hindi step has already been removed from Run demo for exactly this reason.
Both features are real and can be shown live to the panel on a laptop — they are
simply not filmable from the hosted instance.

**Warm the page before recording.** Open the link, let it fully load, then start
Run demo. The free tier sleeps, and a cold start is slow.

---

## 2. What the project is

A procurement officer writing a government tender has to cite Indian Standards.
They do it from memory, or by copying an older tender. Three things go wrong:

1. They cite a standard **BIS has since withdrawn or superseded** — the tender
   becomes legally challengeable.
2. They cite the **wrong part** of a multi-part standard. IS 7098 Part 1 covers
   cables up to 1100 V; Part 2 covers 3.3–33 kV. Citing Part 1 for an 11 kV cable
   is a real and common error.
3. They **omit a mandatory certification** — some products legally require an ISI
   mark under a Quality Control Order, and leaving it out permits
   non-compliant goods.

MANAK-SETU works in both directions:

- **Forward** — paste a specification, get the governing standard, related
  standards, mandatory certification, and a draft clause.
- **Backward** — paste or upload an existing tender, get a list of edits: which
  citations are dead and what replaces them.

The audit only **suggests**. There is no approval workflow. The officer edits
their own tender, and the tender remains the record.

### The constraint that shaped everything

**BIS sells the full text of Indian Standards.** It cannot legally be downloaded,
scraped or redistributed. So the system never reads standard text. It retrieves
over public catalogue metadata — number, title, product family, status — and over
the citations found in public tender documents.

Say this out loud in the video. It is the single strongest signal that the team
understood the domain rather than just the technology.

---

## 3. The seven demo steps — what is on screen and what to say

Total automated hold time is **70 seconds**. Narration should track it closely.

### Step 1 — Overview · 9s
**On screen:** "What the console holds"
> 2,087 Indian Standards, 220 real government tenders, 3,336 co-citation edges,
> 737 certification rules. Every figure is recomputed from the database on load —
> nothing on this page is typed in.

**Narration idea:** Open on scale and on provenance. These are real BIS records
and real published tenders, and the numbers are read from the database at load
time rather than written into the page.

### Step 2 — Overview · 9s
**On screen:** "And what it does not"
> 99% of the standards real tenders cite are in the register — 483 of 488. It was
> 17% when we started. We collected the rest from the BIS catalogue rather than
> inventing them, and the last 5 stay on the front page as a declared gap.

**Narration idea:** This is the honesty slide. The system publishes its own gap on
its front page. Emphasise "483 of 488" — a stated denominator, not a round claim.

### Step 3 — Draft clause · 10s
**On screen:** "A specification, and the standard that governs it"
> Retrieval reads the voltage and the material out of the text, so 1.1 kV resolves
> to Part 1 and not Part 2. The filters are shown above the answer: nothing is
> reordered invisibly.

**Narration idea — this is the money shot.** A keyword search returns IS 7098 and
stops. This reads the voltage out of the sentence and picks the correct *part*.
Part 1 versus Part 2 is the difference between a valid tender and a challengeable
one.

### Step 4 — Audit · 11s
**On screen:** "A published tender, audited"
> A real procurement document with the 17 IS numbers its text actually cites. The
> report is a list of edits: replace IS 434 (Part 1) with IS 9968 — a stored
> supersession, not a model guess.

**Narration idea:** The reverse direction. A real government document, its real
citations, and a concrete replacement drawn from the BIS register — not generated.

### Step 5 — Audit · 10s
**On screen:** "The clause nobody wrote"
> These items carry mandatory BIS certification and the tender never asks for the
> Standard Mark. The console drafts the missing clause with the Gazette order that
> makes it binding, ready to paste.

**Narration idea:** Not just an error found — an omission found, with the legal
instrument that makes it binding, and wording ready to paste.

### Step 6 — Graph · 10s
**On screen:** "Where 'related' comes from"
> 193 standards joined by 3,336 edges, each edge a count of two standards
> appearing in the same published tender. Colour is BIS department. The clusters
> are procurement practice, not a layout choice.

**Narration idea — the legal insight.** BIS sells standard text, so relationships
cannot be mined from it. Tenders are public. Every edge is two standards cited
together by a real procurement officer. The clusters are how government actually
buys.

### Step 7 — Benchmark · 11s
**On screen:** "Measured, and stated carefully"
> All 4 known dead-citation documents caught, 0 false positives across 20 sampled
> clean ones. Retrieval scores 92% Recall@10 on 71 queries labelled by BIS Quality
> Control Orders. The positive class here is 4 — too small for an accuracy claim,
> so we never make one.

**Narration idea — close here.** Every number has a denominator. Four positives is
too small a sample for a percentage, so the system reports counts. Ending on
measured restraint is stronger than ending on a boast.

---

## 4. The numbers — all verified

Quote these exactly. Every one was computed fresh from the current data.

**Data**
- 2,087 standards in the register (grown from 405)
- 220 tender documents, 134 machine-readable
- 3,336 co-citation edges across 193 standards
- 737 certification rules — ISI Mark Scheme I, CRS Scheme II, Hallmarking
- **483 of 488** standards cited by real tenders are in the register (99.0%)

**Retrieval — 71 labelled queries**
- Recall@1: **58/71 (82%)** — the top answer was correct
- Recall@10: **65/71 (92%)**
- Abstention: 3/71 (4%)

**Dead-citation detection — n=24**
- 4 of 4 known outdated-citation documents caught
- 0 false positives across 20 clean documents

**Robustness:** 23 of 23 adversarial tests pass.

### Never say
- "100% coverage" or "100% accuracy" — neither is true.
- Any accuracy percentage derived from the 4-document positive class.
- That the system reads the text of Indian Standards. It does not.

---

## 5. Terminology, in plain words

**Recall@1 — 82%.** Out of 71 test questions with a known correct answer, the very
first standard shown was the right one 58 times. This is the number that matters
most to an officer, because they read the top result.

**Recall@10 — 92%.** The correct standard was somewhere in the top ten 65 times.
This measures the search; Recall@1 measures the experience.

**False positive — 0 of 20.** The system flagged a clean tender as having a dead
citation. It never did this in testing.

**Abstention — 4%.** How often the system declines to answer. Not a failure: it is
the system refusing to guess.

**Certification (ISI mark / QCO).** For some products, Indian law requires the BIS
Standard Mark. The legal instrument is a Quality Control Order published in the
Gazette. A tender for such a product that does not demand the mark permits
non-compliant goods. The system carries 737 of these rules and drafts the missing
clause with its Gazette reference.

**Superseded vs withdrawn.** Superseded means BIS replaced it with a newer
standard — there is a specific replacement. Withdrawn means BIS pulled it with no
successor. Both make a citation invalid; only one has an automatic fix.

---

## 6. How it works, for the technical questions

**Two searches run at once.** One compares meaning using sentence embeddings
(MiniLM); one matches exact words (BM25). Meaning catches "potable water" against
"drinking water supplies"; exact matching catches "XLPE" and "IS 7098".

**Their rankings are fused, not their scores.** Reciprocal Rank Fusion combines
positions, because a cosine similarity and a BM25 score are not comparable
numbers — but "3rd" and "5th" are.

**The top 10 are reranked by a cross-encoder**, which reads the query and the
title together rather than comparing two pre-computed vectors. More accurate,
slower — which is why it only sees ten candidates and not 2,087.

**Four filters then enforce voltage, material, document role and status**, applied
as one combined sort so no filter can silently undo another.

**A confidence gate decides whether to answer at all.** Pure `if` statements, no
model: below a score threshold, or too close to the runner-up, or two parts of one
standard split only by a voltage the spec never stated — the system abstains and
routes to a BIS officer.

**The language model never retrieves and never decides.** It is handed facts that
were already retrieved and asked only to phrase them. Six guards then check its
output *in code*: every IS number and edition year must appear in the retrieved
set, certification claims are checked in both directions, and invented legal
language is blocked. If any guard fails, a deterministic template is used and the
interface says so.

**Stack:** FastAPI, SQLite, NumPy, sentence-transformers, rank_bm25, pdfplumber.
Vanilla HTML/CSS/JS — no framework, no build step. Ollama running qwen2.5 locally
and optionally, so no data leaves the machine.

---

## 7. The strongest lines to use

> The system never reads the standards themselves. BIS sells that text. We index
> public catalogue metadata and the citations in public tenders.

> Eleven kilovolts resolves to IS 7098 Part 2, not Part 1. That distinction is the
> difference between a valid tender and a challengeable one.

> Every edge in this graph is two standards cited together in a real published
> tender. The clusters are procurement practice, not a layout choice.

> A wrong citation makes a tender legally challengeable. So when the system is not
> confident, it returns nothing and routes to a BIS officer rather than guessing.

> Four positive cases is too small a sample for a percentage, so we report counts.

---

## 8. Honest limitations — say these if asked

They strengthen the case rather than weaken it.

- **The test set is electrical-heavy.** It is largely derived from Quality Control
  Orders, so measured accuracy is strongest on cables, meters and footwear, and
  thinnest on civil and pipes.
- **BIS does not publish amendment data** through any endpoint we could find — and
  we recovered the full request contract for the one that appeared to offer it. It
  returns empty for every standard. So the system shows BIS *review dates* and
  labels them as review dates, never as amendments.
- **Verification found 99 real errors in our own register**, including 40
  standards marked Current that BIS has withdrawn. Finding those is the system
  working.
- **Ten of twelve interface languages are machine-translated and unreviewed.**
  Hindi and English are checked.
