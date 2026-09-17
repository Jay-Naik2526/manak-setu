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
| Multilingual input (partly) | Translation providers refuse shared datacentre IPs. Hindi queries for standards BIS has named in Hindi now work without translation — 1,949 of 27,687 carry one — but most do not, so a Hindi query for a cable standard still fails on camera. |
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
**On screen:** the caption is generated from the database at run time, so it
states whatever the corpus currently holds — at the time of writing, 27,687
Indian Standards, 4,917 real government tenders, 35,806 co-citation pairs and
737 certification rules.

> Every figure is recomputed from the database on load — nothing on this page is
> typed in.

**Narration idea:** Open on scale and on provenance. These are real BIS records
and real published tenders, and the numbers are read from the database at load
time rather than written into the page.

### Step 2 — Overview · 9s
**On screen:** "And what it does not" — also generated live. Currently: 99.0% of
the standards real tenders cite are in the register, 1,966 of 1,986.

> It was 17% when we started. We collected the rest from the BIS catalogue
> rather than inventing them, and the remainder stay on the front page as a
> declared gap.

**Narration idea:** This is the honesty slide. The system publishes its own gap on
its front page. Emphasise the denominator — "1,966 of 1,986", not a round claim.
Seven of the gaps closed this week were never missing standards at all: the
citation pattern had been truncating "IS:2016-1967" into "IS 201619" when a PDF
lost the separator. Worth saying if asked how the gap shrinks.

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
> Generated live; currently 1,858 standards and 35,806 related pairs, each pair
> a count of two standards appearing in the same published tender. The picture
> draws each standard's twelve best-evidenced relationships — 13,602 lines — and
> says so on screen. Colour is BIS department. The clusters are procurement
> practice, not a layout choice.

**Narration idea — the legal insight.** BIS sells standard text, so relationships
cannot be mined from it. Tenders are public. Every edge is two standards cited
together by a real procurement officer. The clusters are how government actually
buys.

### Step 7 — Benchmark · 11s
**On screen:** "Measured, and stated carefully"
> Counts, not percentages. Retrieval ranks the right standard first on 492 of
> 621 BIS-labelled queries and within the top ten on 608, measured against all
> 27,687 standards. The dead-citation benchmark agrees with the flag stored at
> collection on 290 of 293 documents — and the three disagreements are standards
> BIS withdrew after collection, so the system is right and the stored flag is
> old.

**Narration idea — close here.** Every number has a denominator. And the strongest
thing on this screen is the pipeline table: six retrievers measured on the same
621 queries, and the one we ship is not the most accurate — it is the only one
that can still decline. Drop the cross-encoder and 30 honest abstentions become
30 confident wrong answers. Ending on measured restraint is stronger than ending
on a boast.

---

## 4. The numbers — all verified

Quote these exactly. Every one was computed fresh from the current data on
17 September 2026, and every one is reproducible with the command beside it.

**Data** — `curl -s localhost:8000/stats | python3 -m json.tool`
- **27,687 standards** in the register, harvested from the BIS catalogue
  (grown from 405, then 2,087)
- **4,917 tender documents**, **1,172 machine-readable**, 6,083 citations read
- **1,858 standards** in the co-citation graph, **35,806 related pairs**
  (65,872 stored rows — the table keeps a row per direction because confidence
  is directional; say *pairs*)
- 737 certification rules — ISI Mark Scheme I, CRS Scheme II, QCO, Hallmarking
- **1,966 of 1,986** standards cited by real tenders are in the register
  (**99.0%**); the remaining 20 are listed as a declared collection gap
- 1,949 standards carry BIS's own Hindi title (7.0%)
- Register last re-checked against the BIS portal on **17 Sep 2026** (120
  standards, 0 amendments found)

**Retrieval — 621 BIS-labelled queries against all 27,687 standards**

Two different figures, and the difference matters if a judge asks. The
leaderboard measures the **retriever**: raw candidates, before the voltage,
material, role and status filters and before the confidence gate. `Coverage`
measures the **product**: what an officer is actually shown. The retriever
finds the right standard more often than the product shows it, which is the
filters doing their job.

`python eval_pipelines.py --write` — retriever only:
- Rank 1: **492/621 (79.2%)**
- Recall@10: **608/621 (97.9%)**
- Abstains on **38/621**
- 122 ms a query

**Confidence is concentrated, not calibrated — say this honestly.**
569 of the 621 queries score between 0.9 and 1.0, and in that band the top
answer is right **453 of 569 times (80%)**. Expected calibration error 0.161.
The other bands hold too few queries to quote, so the interface shows a
calibration line only for a band with at least 30 queries. Never say "the
system is 97% sure".

**Six retrieval pipelines, measured against each other** — on the Benchmark
screen. The headline is not which won:

| Pipeline | Rank 1 | Recall@10 | Abstains | ms |
|---|---|---|---|---|
| hybrid_ce (shipped) | 492/621 | 608/621 | 38/621 | 122 |
| hybrid_rrf | 485/621 | 608/621 | **1/621** | 69 |
| dense (MiniLM only) | 485/621 | 607/621 | no gate | 32 |
| bm25 | 468/621 | 596/621 | no gate | 65 |
| graph_expand | 492/621 | 591/621 | 38/621 | 94 |
| llm_only | not measured — no local model | — | — | — |

**The cross-encoder does not earn its place on accuracy.** Its rank-1 lead over
the same pipeline without it is 7 queries in 621 and does not survive a paired
McNemar test (p=0.296), at nearly double the latency. It keeps its place
because it is the only configuration where the gate can still decline: on the
38 queries it abstains on, `hybrid_rrf` answers 37 confidently and is **wrong
on 30**. Dropping it would trade 30 honest abstentions for 30 confident wrong
answers. In 34 of those 38 the correct standard was in the candidate list
anyway — which is what the abstention is for.

`graph_expand` is a **negative result and we report it as one**: identical at
rank 1, recall@10 falls from 608 to 591 because co-citation neighbours displace
correct answers down the list. The graph is evidence about procurement, not a
retrieval aid.

**Dead-citation detection** — `python benchmark.py`
- Agrees with the flag stored at collection on **290 of 293** documents
- The 3 disagreements are **newly dead**: BIS withdrew those standards after
  the documents were collected. The system is right and the stored flag is old.
- Say it as agreement, never as accuracy: both sides now read the same
  register, so this measures drift, not correctness.

**Procurement Standards Health Index — the measurement only this corpus makes**
`python health_index.py`
- **422 of 1,172** machine-readable government tender documents cite a standard
  BIS has already withdrawn or superseded
- **354** distinct dead standards still in circulation
- Most-cited dead standards: IS 14246 and IS 303 (33 documents each),
  IS 8112 and IS 325 (28 each)

**Who is buying — read from the saved GeM bid forms**
Buyer named on **1,036 of 1,172** measured documents (the pre-GeM set has no
bid form and is excluded rather than counted as unknown). Ministries with at
least 10 documents:
- Ministry of Defence — **124 of 268** cite a dead standard; most often IS 303,
  in 32 documents
- Heavy Industries & Public Enterprises — 55 of 166
- Power — 34 of 101 · Petroleum & Natural Gas — 33 of 116
- Chemicals & Fertilizers — 23 of 41

**The QCO enforcement gap — the single most Consumer-Affairs-relevant number**
- **47 of the 104** documents that cite a product under compulsory BIS
  certification, and whose text could be read, **demand the Standard Mark
  nowhere at all**. As written, uncertified goods meet those specifications.
- 161 documents cite such a product in all; 57 had no readable attachment and
  are excluded rather than assumed compliant.
- Concentrated in Electrotechnical (19), Civil Engineering (11) and electrical
  cables (7).
- **Only the absence is reported.** "No mark language anywhere" is
  unambiguous; a long tender mentioning BIS somewhere is no proof the certified
  item is covered. If asked, that distinction is the strongest answer, not the
  weakest point.

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
slower — which is why it only sees ten candidates and not 27,687.

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

**The six USP lines, in the order to say them.** These are the claims no other
team can make, because each needs the tender corpus and the BIS register joined
together.

> **For the Department of Consumer Affairs.** Across 1,172 machine-readable
> government tender documents, 422 cite a standard BIS has already withdrawn —
> and 47 of the 104 that buy a product under compulsory certification never
> demand the ISI mark at all. As written, uncertified goods meet those
> specifications. We can break both down by buying ministry: Defence, 124 of 268.

> **It cannot invent a standard.** Every answer is a row from the BIS catalogue —
> the matcher is structurally incapable of returning a number the register does
> not hold. The leaderboard counts answers outside the register for every
> pipeline: zero, by construction, not by care.

> **It knows when to say no, and we measured what that is worth.** On the 38
> queries where it declines, the faster pipeline without the cross-encoder
> answers 37 confidently and is wrong on 30. We ship the slower one for that
> reason alone.

> **Six retrieval pipelines measured against each other** on 621 BIS-labelled
> queries, with the table on screen — including a negative result we kept.

> **Every standard is one click from BIS**, and the footer states the date the
> register was last re-checked against the portal.

> **Officers get a document, not a web page** — a printable compliance report
> with the provenance of every line, which says in its own footer that it is not
> a certification of the tender.

**If a judge asks "what did you get wrong?"** — this is a good answer, not a bad
one. The citation pattern was truncating "IS:2016-1967" into "IS 201619" when a
PDF lost the separator, and seven of the twenty-seven gaps in our coverage
backlog were that, not missing standards. An invariant checker we wrote found
it. That is the difference between a system that is careful and a system that
says it is.

---

## 8. Honest limitations — say these if asked

They strengthen the case rather than weaken it.

- **The test set is uneven across families.** It comes from BIS's own
  certification notifications, so the label is a legal instrument rather than
  our opinion — but coverage follows what BIS certifies. Rank-1 by family:
  fasteners 94%, cement 83%, steel 78%, hand tools 50%. Families BIS does not
  certify are unmeasured. Say the breakdown, not one figure.
- **BIS does not publish amendment data** through any endpoint we could find — and
  we recovered the full request contract for the one that appeared to offer it. It
  returns empty for every standard. So the system shows BIS *review dates* and
  labels them as review dates, never as amendments.
- **Verification found 99 real errors in our own register**, including 40
  standards marked Current that BIS has withdrawn. Finding those is the system
  working.
- **Ten of twelve interface languages are machine-translated and unreviewed.**
  Hindi and English are checked.
- **We tested whether dead citations are copied between tenders, and they are
  not.** MinHash over 1,036 documents: even at a loose 0.35 similarity, four
  fifths share text with nothing, and no dead standard has more than 3 of its
  citing documents in one cluster. We do not ship a finding the measurement
  does not support. It sharpens the pitch rather than weakening it — if these
  were copied, a circular would fix them; because they are independent choices,
  the fix has to happen where the clause is written, which is this system.
- **Confidence is concentrated, not calibrated.** 569 of 621 queries score
  between 0.9 and 1.0, and in that band the answer is right 453 times — 80%,
  not 97%. The score behaves like a decision, not a probability. It is still
  the right input to the gate, which compares it against fixed thresholds, and
  the interface refuses to show a calibration line for any band with fewer than
  30 queries.
- **The dead-citation benchmark is not an independent accuracy test any more.**
  Both sides consult the same register, so it measures agreement and drift. An
  independent test needs someone reading twenty tenders and marking the dead
  citations by hand — that work has not been done, and we say so rather than
  presenting agreement as accuracy.
- **`/recommend` does not fit the free host.** The full pipeline needs 745 MB
  against 512 available; the demo runs locally for that reason. Measured, not
  estimated, and we did not shrink the register to fit.
