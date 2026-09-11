# MANAK-SETU — Complete Project Briefing Pack
### Team The RAGnarok · Smart India Hackathon 2026 · Problem Statement SIH26108

---

## HOW TO USE THIS FILE

**If you are a team member:** upload this file to any AI assistant (ChatGPT, Gemini, Claude), then send one message containing only your first name. The AI will take it from there and guide you step by step.

**If you are the AI assistant reading this:** your instructions are in Section 0 directly below. Read the entire document before responding to anything.

---

# SECTION 0 — INSTRUCTIONS FOR THE AI ASSISTANT

You are acting as a project guide for a member of a student hackathon team building a software project called MANAK-SETU. This document contains the complete project context, the team structure, every decision already locked, and a detailed task guide for each role.

## Your behaviour

**1. Wait for the user to give their name.**
The team members are: **Jay, Pari, Jash, Sommya, Jiya, Sharva.** If they give a name not on this list, ask which of these six they are working with and assist accordingly.

**2. Once you know who they are**, greet them briefly, tell them in two sentences what they own, then guide them through their **first task only**. Do not dump their entire task list on them at once — it causes paralysis. Walk them through one step, confirm it is done, then move to the next.

**3. Adapt to their technical level.**
Jay and Pari are technical and can handle code, architecture, and detail. Jash, Sommya, Jiya, and Sharva are not primarily coders — explain things in plain language, never assume knowledge of programming or of Indian Standards, and never use a technical term without explaining it in the same sentence.

**4. If the user is Jay or Pari**, remember they are a working pair on the core build, not two people on separate tracks. Whenever you help either of them with something that touches the other's area — database schema, API shape, confidence threshold, module boundaries — remind them to agree it with the other person before building, and help them write the interface down clearly so both sides build against the same contract. If one proposes a change that would break the other's work, flag it.

**5. Be a working partner, not a lecturer.**
If they paste raw text and ask you to extract standard numbers, just do it cleanly. If they are stuck, unstick them. If they ask "is this row correct?", check it against the rules in this document and answer honestly, including when the answer is no.

**6. Enforce the data integrity rules in Section 7 strictly. This is the most important thing you do.**
If a team member asks you to tell them which Indian Standards apply to a product, or what a standard's status or year is, from your own knowledge — **refuse**. Explain why: you will produce plausible-looking IS numbers that do not exist, and that will corrupt the dataset the entire project depends on. Redirect them to look it up on the official source and paste you the text instead. Be firm about this even if they push back or say it would be faster.

**7. Never invent project facts.**
If they ask something this document does not answer, say so plainly and tell them to ask Jay, rather than guessing on the project's behalf.

**8. Never tell a data collector to wait for anything technical.**
Jash, Sommya and Jiya work in Google Sheets, which are completely independent of the database, the code, and any software setup. If their sheet exists with example rows in it, they start immediately. If they ask whether they should wait for the database, the answer is a clear **no** — the two tracks run in parallel and never block each other. Sharva likewise starts immediately. The only sequencing rule that matters is not building the website before there is data to display in it, and that applies to Jay alone.

**9. Keep them oriented.**
If they seem lost or demotivated, remind them where their work fits and what it feeds into. Section 2 explains this for every role.

**10. Be concrete about edge cases.**
Data collection throws up messy real-world situations constantly — scanned documents, ambiguous wording, standards written in unusual formats. Section 6 covers the common ones. If something is not covered there, tell them to record what the source literally says, note it in the Flag column, and move on rather than guessing.

---

# SECTION 1 — THE PROJECT IN PLAIN LANGUAGE

## The problem

When a government department wants to buy something — electrical cables, LED lights, pipes — it writes a **tender document**. Inside that document is a technical specification naming the **Indian Standard** numbers the supplier must meet. An Indian Standard (written as "IS 694" or similar) is a rulebook published by the Bureau of Indian Standards (BIS) defining what a product must be made of, how it must perform, and how it must be tested.

There are more than 23,000 Indian Standards. The person writing the tender is an administrator, not an engineer. Four things therefore go wrong constantly:

1. **Wrong standard cited** — scopes overlap, and two standards can look equally relevant from the title alone.
2. **Outdated version cited** — standards get revised. A 1990 edition may have been replaced in 2010, but the officer copies last year's tender, which copied the year before's, and a dead standard number survives for decades.
3. **Incomplete set cited** — a product standard normally points to other standards (called **normative references**). A cable standard will point to a separate standard for the conductor and another for test methods. Cite only the headline standard, and a supplier can legally deliver something that passes the letter of the tender but fails in practice.
4. **Mandatory certification missed** — some products legally cannot be sold in India without BIS certification. If the tender does not demand it, non-compliant goods enter the supply chain.

The consequence is not academic: ambiguous specifications produce **procurement disputes**. The supplier delivers, the department rejects, payment stalls, arbitration follows, and public infrastructure waits.

## Our solution

**MANAK-SETU** takes a plain description of what is being purchased and returns the complete, current, correct set of Indian Standards for it — the governing standard, every connected standard, the current version, and any mandatory certification. It can also read an existing tender document and report what is wrong with it.

*Manak* means standard. *Setu* means bridge.

## Our core method — read this carefully, it is the heart of the project

The full text of Indian Standards is **sold** by BIS. We cannot legally download, scrape, or redistribute it, and we will not pretend otherwise.

But **published government tenders are completely public**, and every tender names the standards it requires.

So: if we collect two hundred real tenders and record which standards each one cites, patterns emerge. If forty separate cable tenders all name the same two standards together, those two standards clearly belong together — and we learned that without ever reading the copyrighted standard text.

**We learn the relationships between standards from how real procurement documents actually use them.** This is legal, defensible, and almost certainly unique to us. It is also our answer to the hardest question we will be asked: *"where did your data come from?"*

Every person collecting data on this team is building that dataset. That is why the data work is not background work — it is the product.

---

# SECTION 2 — WHY EACH PERSON'S WORK MATTERS

Use this to keep people oriented when they lose sight of the point.

| Person | What they produce | What it becomes |
|---|---|---|
| Jash | Standards Master List | The catalogue the system searches, and the version data that lets us flag dead citations |
| Sommya | Tender Dataset | The evidence we learn standard-relationships from — the most valuable dataset on the project |
| Jiya | Certification Rules | The compliance layer that tells an officer "this product legally requires BIS certification" |
| Sharva | Demo, deck, QA, docs | The difference between a working product and a product that presents well — plus independent verification that our data is trustworthy |
| Jay & Pari | The software itself | The engine that turns all of the above into an answer in seconds |

Nothing works without the data. The data is worthless without the engine. The engine is worthless if the demo fails on stage.

---

# SECTION 3 — PROJECT METHODOLOGY

We follow **Design Thinking** for deciding *what* to build and **the Software Engineering lifecycle** for actually building it. Both run together; they are not alternatives.

## Design Thinking phases

**1. Empathise — understanding the user.**
Our primary user is a **procurement officer inside a government department or PSU who is writing a tender specification**. Not suppliers, not regulators — they benefit from the outcome, but we do not design for them.

We have no direct access to a real procurement officer. Rather than pretend otherwise, we treat our beliefs about their behaviour as **assumptions to be validated against real tenders**, which are public and which we are collecting anyway. Tenders are evidence of behaviour even when we cannot interview the people who wrote them.

*Key assumption being tested:* officers copy last year's tender and edit it rather than starting fresh. Sommya's data collection includes a column that tests this directly (Section 6, Sheet 2).

**2. Define — stating the problem precisely.**
> A procurement officer with no engineering background must name the correct, current, and complete set of Indian Standards in a tender specification, drawn from a catalogue of over 23,000 standards that continuously change, with no existing tool that understands what they are trying to buy.

**3. Ideate — generating and filtering options.**
Complete and locked. Section 4 defines what is in scope; Section 5 defines what we are deliberately not building.

**4. Prototype — building the thinnest thing that works end to end.**
Defined in Section 4 as the MVP. We build the narrowest complete path first, then widen it. We never build three half-features.

**5. Test — measuring honestly.**
Our measurement methodology is unusual and important. It is fully specified in Section 8. Read it before making any accuracy claim anywhere — in the deck, in the demo, or to a judge.

## Software Engineering lifecycle

| Stage | What it means here |
|---|---|
| Requirements | Section 4 (scope) and Section 5 (non-goals) are the requirements baseline. Nothing gets built that is not in Section 4. |
| Design | Data model, module boundaries, and the architecture in Section 9. Owned jointly by Jay and Pari. |
| Implementation | Build order in Section 10. Data collection and software build run in parallel. |
| Testing | Golden benchmark and the three-part measurement in Section 8, plus Sharva's independent data spot-checks. |
| Deployment | Working demo running locally with seeded data and no external network dependency on the demo path. |
| Maintenance | Out of scope for the hackathon itself, but the ingestion pipeline design shows we have thought about it — judges ask this. |

**Governance rules everyone follows:**
- Scope is frozen at Section 4. Anything new goes on a "later" list, not into the build.
- Every data row must have a working source link (Section 7).
- Any claim on a slide must be something the demo can actually do.
- If a feature is cut, it comes off the presentation the same day.

---

# SECTION 4 — SCOPE: WHAT WE ARE BUILDING

## Product families in scope

We cover **four product families thoroughly**, rather than 23,000 standards shallowly:

1. Electrical cables and wiring
2. LED lighting
3. Pipes (PVC and GI)
4. Safety equipment (helmets, gloves, protective gear)

*Chosen because a large number of public tenders exist for them, their standards are clearly defined, and several fall under mandatory certification rules so we can demonstrate that feature.*

**These are provisional until Sharva's scope validation confirms them (Section 12).** Collection begins immediately on families 1 and 2, which are the most certain. Families 3 and 4 begin once validation confirms they have enough tenders, or are swapped for a better family if they do not. This way nobody waits, and nobody wastes effort on a family we might drop.

A system provably correct about cables beats one vaguely plausible about everything. Judges test depth, not breadth — they pick one product and probe it.

## MVP — what must work for the demo

- **Forward path:** officer types or pastes a product requirement → system returns ranked applicable standards, each shown with the supporting evidence for why it matched
- **Connected standards:** results include related standards, each with a plain-language reason for inclusion
- **Version intelligence:** superseded citations flagged, current edition surfaced
- **Certification intelligence:** mandatory BIS / CRS / QCO / Hallmarking obligations attached automatically
- **Confidence gate:** when unsure, the system says so instead of guessing (behaviour specified in Section 11)
- **Tender Diff:** upload an existing tender document → receive an audit reporting outdated citations, missing connected standards, and missed mandatory certification
- **File upload:** PDF and DOCX both working
- **Clause output:** a ready-to-paste tender specification clause generated from the result

## The demo moment

**Tender Diff is the screen a judge must remember.** Upload a real government tender, and seconds later: *"3 outdated citations · 2 missing connected standards · 1 missed mandatory certification."*

Every other MVP feature exists to make that moment possible and credible. When prioritising anything, ask: *does this protect the Tender Diff moment?*

---

# SECTION 5 — NON-GOALS (WHAT WE ARE DELIBERATELY NOT BUILDING)

Stating these explicitly prevents scope creep and answers judge questions cleanly.

- **Not covering all 23,000 standards.** Four families, done properly.
- **Not reproducing standard text.** It is copyrighted and sold. We work from metadata, titles, scopes, and public tender citations only.
- **Not replacing BIS or GeM.** We connect existing systems — that is what *Setu* means.
- **Not auto-deciding.** The officer always decides; the system advises with evidence and logs the decision.
- **Not building a mobile app.** Web only.
- **Not building user accounts, payments, or admin panels.**
- **Not building the browser extension for MVP.** It appears in the architecture as the intended integration path and we can describe it, but it is not built for this demo.
- **Not building multilingual input for MVP.** English only. Multilingual is in the architecture and on the roadmap, not in the build.
- **Not letting the language model choose standards.** Retrieval and the relationship graph decide; the model only phrases output. This is an architectural rule, not a preference.

> **Note for anyone presenting:** if a slide or answer mentions the browser extension or multilingual support, say clearly that it is designed and on the roadmap, not built. Claiming a feature the demo cannot show is the fastest way to lose a judge's trust.

---

# SECTION 6 — DATA COLLECTION SPECIFICATIONS

Three shared Google Sheets. Fixed columns. **Jay creates all three sheets and fills ten worked example rows in each before anyone starts.** If your sheet does not have example rows yet, message Jay — do not start guessing the format.

**Rules that apply to all three sheets:**
- Match the example rows exactly. Never add, rename, reorder, or delete columns.
- One row per record. Never merge two records into one row.
- Every row needs a working source link.
- If something is unclear, still enter the row and add a short note in the **Flag** column at the far right — do not guess, and do not silently skip it.
- **"Have it checked" means: message Jay with a link to your sheet, and wait for his reply before continuing.**

---

## SHEET 1 — Standards Master List · Owner: JASH

**Source:** standards.bis.gov.in, plus BIS catalogues on bis.gov.in
**Target:** 400–500 rows across the product families in scope

| Column | What goes in it |
|---|---|
| IS Number | Written exactly as `IS 694` — always "IS", one space, then the number. Convert other formats to this. |
| Full Title | The complete official title, copied and pasted exactly. Do not shorten or reword. |
| Year | The four-digit year of the edition, e.g. `2010`. Numbers only. |
| Status | Exactly one of: `Current`, `Superseded`, `Withdrawn` |
| Replaced By | If Superseded, the IS number that replaced it, in `IS ####` format. Otherwise leave as `—` |
| Product Family | Exactly one of the four families, spelled exactly as in Section 4 |
| Source Link | The URL of the page you read it from |
| Flag | Leave blank normally. Short note here if anything was unclear. |

**Why the Replaced By column matters more than it looks:** this is what lets our system catch tenders citing dead standards, which is one of our headline demo features. A blank or guessed value here directly breaks that feature.

### Detailed method

1. Open Sheet 1 and read all ten example rows before touching anything. Note the exact formatting of the IS number and the exact spelling of the status values.
2. Go to `standards.bis.gov.in`.
3. Start with **electrical cables and wiring**. Search using plain product words — "cable", "conductor", "wire", "insulation". Do not search for standard numbers; you are trying to discover them.
4. Open the first search result.
5. Copy the **IS number**. If it appears as `IS:694`, `IS-694`, or `IS 694:2010`, normalise it to `IS 694` in the IS Number column and put the year in the Year column separately.
6. Copy the **full title** exactly by selecting and pasting — do not retype it, because retyping introduces errors.
7. Record the **year** of the edition shown.
8. Record the **status**. If the page says the standard has been superseded, revised, or replaced, set status to `Superseded`. If it says withdrawn, use `Withdrawn`. If it shows as active or current, use `Current`.
9. If status is `Superseded`, find and record the **replacing IS number**. If the page does not say which standard replaced it, write `Unknown` and put a note in the Flag column. **Do not guess, and do not ask AI to guess.**
10. Set the **Product Family**.
11. Copy the **URL** from the address bar into Source Link. Check that it actually reopens the record — some search pages produce URLs that lead back to a blank search.
12. Move to the next result.
13. **After your first ten rows, stop.** Message Jay with a link to the sheet and wait for confirmation before continuing. One correction now prevents re-doing a hundred rows later.
14. Once confirmed, continue through cables, then LED lighting, then the remaining families once Sharva's validation confirms them.

### Situations you will hit

- **The same standard appears in several parts** (Part 1, Part 2, and so on). Record each part as its own row, keeping the part number in the title.
- **You cannot tell whether it is current.** Set status to `Current`, write `status uncertain` in the Flag column, and move on.
- **The title runs very long.** Keep it in full. Length is not a problem; truncation is.
- **A standard seems to belong to two families.** Pick the closest one and note the other in the Flag column.

**Ask your AI to:** clean text you have pasted into the correct column format, normalise IS number formatting, check a batch of rows for duplicates or inconsistent status spellings, explain an unfamiliar technical term in a title.
**Never ask your AI to:** tell you which standards exist, what their status is, what year an edition is, or what replaced a superseded standard.

---

## SHEET 2 — Tender Dataset · Owner: SOMMYA

**Source:** eprocure.gov.in (CPPP), and gem.gov.in
**Target:** 200 tenders

| Column | What goes in it |
|---|---|
| Tender ID | The tender reference number as shown on the portal |
| Product Family | Exactly one of the four families |
| IS Numbers Cited | Every standard mentioned, normalised to `IS ####` and separated by semicolons: `IS 694; IS 8130; IS 10810` |
| Number of Standards Cited | How many, as a plain number. Lets us spot rows where extraction went wrong. |
| Contains Outdated Citation? | `Yes` / `No` / `Not checked` |
| Document Type | `Text PDF` / `Scanned PDF` / `Other` |
| Source Link | The URL of the tender |
| Flag | Blank normally; short note if anything was unclear |

**This is the most valuable sheet in the project.** It is the raw material the relationship engine is built from, and the evidence behind every accuracy claim we make on stage.

**The "Contains Outdated Citation?" column is a research finding, not admin.** It tests our assumption that officers copy old tenders forward. If a meaningful share of real tenders cite dead standards, that is direct evidence — and a strong line on stage: *"we checked 200 real tenders and X% cite at least one superseded standard."* No other team will have that number.

### Detailed method

1. Open Sheet 2 and study all ten example rows before starting.
2. Go to `eprocure.gov.in` and use the tender search.
3. Search for **electrical cables** first, using plain words like "supply of cables" or "LT cable".
4. Open a tender and download its main tender document or technical specification file.
5. Record the **Tender ID** and the **URL**.
6. Open the document and try to select some text with your mouse.
   - **If text selects normally**, it is a `Text PDF`. Continue to step 7.
   - **If nothing selects**, it is a `Scanned PDF` — an image of a document. Set Document Type to `Scanned PDF`, write `scanned, not extracted` in the Flag column, and move to the next tender. **Do not spend time typing these out by hand.** They are common on eprocure and are not worth the time.
7. Search the document for standard references. **Searching only for `IS ` will miss many of them.** Run all of these searches:
   - `IS ` (with a space)
   - `IS:` (with a colon)
   - `IS-` (with a hyphen)
   - `Indian Standard`
   - `BIS`
   - `conform` — often introduces a citation, as in "shall conform to..."
8. Collect every standard number you find anywhere in the document, including in tables, footnotes, and annexures.
9. Normalise each to `IS ####` format. If the document writes `IS:694-2010`, record it as `IS 694`. Drop the year — Sheet 1 handles years.
10. Enter them all in one cell, separated by a semicolon and a space.
11. Count them and put the number in **Number of Standards Cited**.
12. Fill **Contains Outdated Citation?** by checking each cited standard against Jash's Sheet 1. If any has status `Superseded` or `Withdrawn`, mark `Yes`. If all are `Current`, mark `No`. If Sheet 1 does not cover some of them yet, mark `Not checked` and move on. **Never guess this.**
13. **After your first ten tenders, stop.** Message Jay with the sheet link and wait for confirmation.
14. Once confirmed, continue toward 200, working family by family.

### Situations you will hit

- **A tender cites no standards at all.** Record it anyway with an empty IS Numbers cell and `0` in the count. This is a real finding — it means the tender is under-specified.
- **A tender cites an international standard** (ISO, IEC, BS). Do not put it in the IS Numbers column. Note it in the Flag column instead.
- **The tender document is enormous.** You only need the technical specification section. Use the search terms in step 7 rather than reading the whole thing.
- **The same standard is mentioned many times.** Record it once.
- **You are unsure which family a tender belongs to.** Pick the closest and note it in the Flag column.

**Ask your AI to:** extract IS numbers from tender text you paste in, using the exact prompt in Section 7; normalise a messy list into the right format; count the entries; check a batch for duplicates.
**Never ask your AI to:** suggest which standards a tender should have cited, or fill in the outdated-citation column from its own knowledge.

**Accuracy beats speed.** 150 carefully done tenders beat 250 careless ones. A wrong row here corrupts the relationship engine directly.

---

## SHEET 3 — Certification Rules · Owner: JIYA

**Source:** the BIS "Products under Compulsory Certification" list on bis.gov.in, and QCO gazette notifications
**Target:** full coverage of the product families in scope

| Column | What goes in it |
|---|---|
| Product Family | Exactly one of the four families |
| Product Description | What the notification specifically covers, copied from the source |
| IS Number | The standard it is tied to, in `IS ####` format |
| Certification Mandatory? | `Yes` / `No` |
| Scheme | Exactly one of: `QCO`, `BIS Product Certification`, `CRS`, `Hallmarking`, `None` |
| Notification Reference | The name, number or date of the order or notification, if shown |
| Source Link | The URL of the notification or list page |
| Flag | Blank normally; short note if anything was unclear |

This sheet feeds the **Certification Intelligence** feature — the part of our system that tells an officer a product legally requires certification. It is one of the features we demonstrate directly.

### Detailed method

1. Open Sheet 3 and study all ten example rows.
2. Go to `bis.gov.in` and find the **Products under Compulsory Certification** list.
3. Work through it looking only for entries matching our product families.
4. For each relevant entry, record the product description **exactly as written** in the source. Do not paraphrase — the precise wording is what determines whether a product is covered.
5. Record the IS number the entry ties to.
6. Set **Certification Mandatory?** to `Yes` if the entry appears on a compulsory list.
7. Set **Scheme** to whichever the source states. If the source does not say clearly, enter your best reading and add a note in the Flag column.
8. Record the **notification reference** if one is shown.
9. Copy the URL.
10. **After your first ten rows, stop.** Message Jay with the sheet link and wait for confirmation.
11. Once confirmed, continue, then move on to QCO gazette notifications for the same families.

### Situations you will hit

- **The notification is long and legalistic.** Ask your AI to summarise it so you can find the relevant section — then read that section yourself before recording anything.
- **You cannot tell whether our product is covered.** Record what the document literally says in Product Description, write `coverage unclear` in the Flag column, and move on. Do not interpret.
- **One notification covers many products.** Record one row per product.
- **A product appears covered but no IS number is given.** Record it with `Unknown` in the IS Number column and flag it.

**This sheet needs the most careful reading of the three.** It involves judging what a legal notification actually covers, which is interpretation rather than transcription. Go slowly. When in doubt, record the literal text and flag it.

**Ask your AI to:** summarise a long notification so you can locate the relevant part, explain legal or technical terminology, check your rows for consistent spelling of scheme names.
**Never ask your AI to:** decide whether a product requires certification, or which scheme applies.

---

# SECTION 7 — RULES FOR USING AI ON THIS PROJECT

Everyone on this team will use AI. That is expected and fine. But it must be used as a **text-processing tool**, never as a **source of facts**.

## Good uses

- **Extracting standard numbers from a document you have already opened.** Paste the text and ask:
  > *"List every Indian Standard number mentioned in this text. Output only the IS numbers, one per line. Do not include any that are not present in the text."*
- Reformatting messy pasted text into the sheet's column structure
- Normalising IS number formats (`IS:694-2010` → `IS 694`)
- Checking a finished batch of rows for duplicates, typos, or inconsistent spelling
- Explaining what a technical or legal term means
- Summarising a long gazette notification so you can find the relevant section faster

## Never do these

- **Asking AI which standards apply to a product.** It will invent IS numbers that do not exist and they will look completely real.
- Filling in a year, status, replacement, or certification requirement you did not read from an actual source
- Generating example rows "to save time"
- Asking AI to guess a Replaced By value
- Asking AI whether a tender should have cited something

## THE RULE

> **If you cannot paste a working source link for a row, the row does not go in the sheet. No exceptions.**

A missing row costs us nothing. A wrong row costs us the accuracy number our entire pitch depends on — and if a judge checks one fabricated IS number and finds it does not exist, the project's credibility collapses in front of them.

---

# SECTION 8 — HOW WE MEASURE ACCURACY

This is the most important methodological decision on the project. Anyone making a claim about accuracy — in the deck, in the demo, or to a judge — must understand this section.

## The problem with the obvious approach

We cannot simply score ourselves against what real tenders cited, because **real tenders contain the exact errors we claim to fix.** Scoring against them would penalise us for being right. But "what an expert should have cited" is unavailable to us, because we have no expert.

## Our three-part answer

**Part A — Citation Recovery.**
Given only the tender's product description, do we retrieve the standards it actually cited? Honest, mechanical, requires no expertise. This is our headline number. It measures: *does our system understand what is being bought?*

**Part B — Version Correctness.**
For every standard cited across the collected tenders, is our status and replacement data correct? This is verified by **re-checking a random sample directly against the BIS source pages** — not against Sheet 1, since Sheet 1 is the thing being tested. Sharva's spot-checks produce this number. Expect it to be high, because this is checkable fact rather than judgement.

**Part C — Enrichment.** *Reported separately, never mixed into the accuracy figure.*
How many additional connected standards do we surface beyond what the tender cited? Framed as: *"across 200 tenders we surfaced an average of N additional connected standards per tender, of which M were manually verified as genuinely applicable."*

## The golden benchmark

Jash and Sommya jointly take **30 tenders** from Sheet 2 and record, for each, what the correct complete answer should be.

How to build it:
1. Pick 30 tenders that are text PDFs with at least three standards cited.
2. For each, write down the product description in plain words, as an officer would state the requirement.
3. List the standards the tender actually cited.
4. Add any standard that Sheet 1 shows as the current replacement for a cited-but-superseded standard.
5. Keep this in a separate tab so it never mixes with the raw collection sheet.

To check the instructions are unambiguous, **both do the same 10 tenders independently first and compare.** Where they disagree, tighten the definition before continuing with the remaining 20.

## What to say on stage

> *"We don't measure against what officers wrote, because what they wrote is the problem. We measure three things: whether we understand the requirement, whether our version data is correct, and what we add beyond the human baseline."*

Every competing team will claim their solution is accurate. We will report measured numbers against real government tenders and explain our methodology. Judges notice the difference immediately.

---

# SECTION 9 — TECHNICAL ARCHITECTURE

*Primarily for Jay and Pari. Everyone else: read it once so you can answer a judge who asks you directly.*

The system is **two pipelines sharing one knowledge core.**

## Runtime query path (per request)

| Layer | Contains | In MVP? |
|---|---|---|
| Integration | REST API · web dashboard · *(browser extension — designed, not built)* | Partly |
| Orchestration | Query routing · session handling · *(language normalisation — designed, not built)* | Partly |
| Intelligence | Hybrid retrieval (semantic + keyword) → reranking → confidence gate → LLM for phrasing only | Yes |
| Knowledge Core | Standards relationship graph · vector index · version ledger · certification rule engine | Yes |
| Output | Ranked standards with evidence · Tender Diff report · paste-ready clause · audit log | Yes |

## Ingestion pipeline (continuous background)

Harvest → Extract → Link References → Track Versions → Map Certification → feeds the shared Knowledge Core

For the hackathon this is represented by our manual collection process plus the import loaders. The automated version is designed and described, not built.

## The architectural rule that must never be broken

> **Retrieval and the graph decide. The model only phrases the output.**

The language model never selects a standard. Every recommendation must trace back to a retrieved record with a score and visible supporting evidence. This is what makes the system auditable and hallucination-resistant, and it is our prepared answer when a judge asks how we prevent the AI making things up.

## Stack

**Core (needed for MVP):**
- Frontend: Next.js · TypeScript · Tailwind CSS
- Backend: FastAPI (Python) · REST
- Intelligence: sentence-transformer embeddings · BM25 keyword search · cross-encoder reranker
- Data: PostgreSQL + pgvector
- Documents: PyMuPDF (PDF) · python-docx (DOCX)

**Additional (in the full architecture, optional for MVP):**
- Cytoscape.js for the graph view
- Self-hosted open-weight model via Ollama for the phrasing layer
- Redis cache, Celery for async document jobs
- Docker and Docker Compose
- OCR fallback for scanned documents

*Self-hosting the model rather than calling a paid API is deliberate: it supports the data-sovereignty argument for a government tool and removes a per-query cost that scales badly at national volume. Team hardware supports this comfortably.*

**Note on hardware:** this project runs fine on an ordinary laptop. Embeddings are computed once over a few hundred standards, and retrieval takes milliseconds. Low resource requirements are a feature for public-sector software, not a limitation — say so if asked.

**Are we training a model?** No. We use pre-trained embedding and reranking models as-is, compute relationships by counting co-citations in real tenders, and apply fixed rules for version and certification logic. Nothing is trained. This is deliberate: a trained model cannot explain why it chose a standard, and it goes stale the moment BIS publishes an amendment.

---

# SECTION 10 — BUILD ORDER

**Data collection and software build run on completely separate tracks. They do not block each other.**

Data collectors work in Google Sheets. Sheets are independent of the database. **Nobody collecting data ever waits for any software to exist.**

## Track 1 — Data collection

**Only prerequisite:** the three sheets exist with ten example rows filled in. Jay creates these. Once they exist:

- Jash, Sommya and Jiya start collecting straight away, all three in parallel, beginning with cables and LED lighting
- Sharva starts scope validation straight away — this is the earliest task on the project
- No database, no code, no setup required

## Track 2 — Software build (in parallel)

1. Repository structure and module boundaries agreed
2. Database schema designed
3. Retrieval prototyped against a CSV export of whatever data exists so far — no database needed to start
4. Database and validated import path built, so sheets can be loaded properly as they grow
5. Relationship engine built once Sheet 2 has enough tenders for co-citation patterns to be meaningful
6. Version and certification logic wired in from Sheets 1 and 3
7. Golden benchmark created; system measured against it
8. Website built — forward path first, then Tender Diff
9. Demo, deck, backup video and documentation finalised and rehearsed

## What genuinely depends on what

| Task | Waits for |
|---|---|
| Data collection (Jash, Sommya, Jiya) | Sheets with example rows. Nothing else. |
| Scope validation (Sharva) | Nothing. Start now. |
| Retrieval prototype (Jay) | A handful of rows in Sheet 1 — a CSV export is fine |
| Database and import path (Pari) | Nothing. Start now. |
| Relationship engine | Enough tenders in Sheet 2 for patterns to be meaningful |
| Website | A working engine underneath it |

**The one real bottleneck on the whole project is the example rows.** Until those exist, three people cannot start. Everything else can proceed in parallel.

The only sequencing rule that genuinely matters: **do not build the website before there is data to show in it.** A polished interface over an empty database demos worse than a plain one over real data.

---

# SECTION 11 — LOCKED BEHAVIOUR DECISIONS

**When the system is not confident:** never show a blank screen. Show three things — the nearest candidates explicitly labelled *"low confidence — not recommended for citation"*, a plain statement of why (*"no standard in our corpus closely matches this description"*), and a route onward (nearest BIS office or the relevant sectional committee).

*Reasoning: a blank result looks broken; a confident wrong answer is dangerous; a clearly labelled uncertain answer with a human route is what a real compliance tool does. We will demonstrate this deliberately by asking the system something it cannot answer.*

**When showing a connected standard**, always explain why it is included, honestly and from the data: *"cited alongside IS 694 in 38 of 42 comparable tenders."* This is more defensible than an AI-generated justification, and it makes our method a visible strength rather than a hidden implementation detail.

**The officer always decides.** The system advises with evidence; the officer accepts or overrides, and the decision is logged. This answers the accountability question before a judge raises it.

---

# SECTION 12 — ROLE-SPECIFIC TASK GUIDES

*AI assistant: once the user identifies themselves, work through the relevant guide below, one step at a time.*

---

## JAY — Core build (paired with Pari)

**Owns:** the three sheets and their example rows, search engine, relationship engine, frontend, overall technical direction

**How this role works:** the core build is a two-person pair. You and Pari work on the same codebase, in the same working sessions, in constant contact. Pari owns the database, data pipeline, rule engine and confidence gate; you own search, the relationship engine and the frontend. The two halves must fit together exactly, so interfaces are agreed jointly before either side builds against them.

**Sequence:**

1. **Create the three Google Sheets with ten worked example rows each, using the exact column structures in Section 6.** This is the highest-priority task on the entire project — three people cannot start until it exists. Do it before anything technical.
2. Share the sheets with Jash, Sommya, Jiya and Sharva, and send them this document.
3. Agree repository structure and module boundaries with Pari.
4. Prototype hybrid search against a CSV export of Sheet 1 — semantic embeddings over titles, plus keyword search for exact codes like "1.1 kV". Neither works alone: pure semantic search fails on codes, pure keyword search fails on paraphrase.
5. Review Sharva's scope validation and confirm or swap the remaining product families.
6. Build the relationship engine — compute co-citation strength from Sheet 2. If two standards appear together in a high proportion of comparable tenders, that is a strong edge.
7. Wire in version and certification logic from Sheets 1 and 3.
8. Build the frontend: forward path first, then the Tender Diff screen with disproportionate polish.
9. Measure continuously against the golden benchmark — check every significant change for whether it helped or hurt.

**Watch for:** the temptation to build UI before data exists. Resist it.

**Coordinate with Pari on:** schema changes, the confidence threshold (it depends on how your retrieval scores behave), API shapes between backend and frontend, and what the loaders should accept or reject.

---

## PARI — Core build (paired with Jay)

**Owns:** database, data pipeline, rule engine, confidence gate

**How this role works:** the core build is a two-person pair. You and Jay work on the same codebase, in the same working sessions, in constant contact — not on separate tracks merged later. You own the components below end to end; Jay owns search, the relationship engine and the frontend. The two halves must fit together exactly, so decisions are made jointly as you go. Before starting a component, agree its interface with Jay so both sides build against the same contract.

**Sequence:**

1. Agree repository structure and module boundaries with Jay before writing anything.
2. Design the PostgreSQL schema covering all three sheets, plus tables for the relationship graph and the audit log. Walk Jay through it before building, since his search and relationship work reads directly from it.
3. Build the loaders that import the sheets with validation — reject rows missing a source link, flag malformed IS numbers, catch duplicates, and reject status or scheme values that are not on the allowed list.
4. This does not block anyone, since the collectors work in Sheets independently — but have it ready before the sheets grow large enough that importing by hand becomes painful.
5. Build the certification rule engine — fixed deterministic rules from Sheet 3, no AI involved. It must be predictable and explainable.
6. Build the confidence gate — the threshold logic that decides when the system abstains, with the behaviour specified in Section 11. Agree the threshold with Jay, since it depends on how his retrieval scores behave.
7. Work alongside Jay on the search and relationship engines as they come together.

**Watch for:** your validation rules are the quality gate on all collected data. Being strict early saves re-work later.

**Coordinate with Jay on:** schema changes (they affect his queries), the confidence threshold, API shapes between backend and frontend, and anything that changes what the loaders accept or reject.

---

## JASH — Standards Master List

**You own Sheet 1.** Everything the system can search comes from your sheet.

**You are not waiting for anything technical.** Your work happens entirely in a Google Sheet. You do not need the database, any code, or any setup. If your sheet exists with example rows, start now. If it does not, message Jay.

**Your full method is in Section 6, Sheet 1.** Follow it step by step. Key points:

- Start with electrical cables, then LED lighting
- Normalise every IS number to `IS ####` format
- Copy titles by selecting and pasting, never by retyping
- The Status and Replaced By columns power a headline demo feature — never guess them
- **Stop after ten rows and have them checked by Jay before continuing**
- Target 400–500 rows
- Once your sheet is substantially underway, work with Sommya on the 30-tender golden benchmark (Section 8)

**Ask your AI to:** clean pasted text into row format, normalise IS number formatting, check batches for duplicates and inconsistent status spellings, explain unfamiliar technical terms.
**Never ask your AI to:** tell you which standards exist, their status, their year, or what replaced them.

---

## SOMMYA — Tender Dataset

**You own Sheet 2 — the most valuable dataset on the project.** The relationship engine is built entirely from your work.

**You are not waiting for anything technical.** Your work happens entirely in a Google Sheet, independent of the database or any code. If your sheet exists with example rows, start now. If it does not, message Jay.

**Your full method is in Section 6, Sheet 2.** Follow it step by step. Key points:

- Check first whether text selects in the PDF. If it does not, mark it `Scanned PDF`, flag it, and skip it — do not type them out by hand
- Search for `IS `, `IS:`, `IS-`, `Indian Standard`, `BIS`, and `conform` — searching only for `IS ` will miss many citations
- Record every standard found anywhere in the document, including tables and annexures
- Normalise to `IS ####` and drop years
- **Stop after ten tenders and have them checked by Jay before continuing**
- Target 200 tenders
- Once underway, work with Jash on the 30-tender golden benchmark (Section 8)

**Ask your AI to:** extract IS numbers from tender text you paste in, using the exact prompt in Section 7; normalise messy lists; count entries; check batches for duplicates.
**Never ask your AI to:** suggest which standards a tender should have cited, or fill the outdated-citation column from its own knowledge.

**Accuracy beats speed.** 150 careful tenders beat 250 careless ones.

---

## JIYA — Certification Rules

**You own Sheet 3.** This feeds our Certification Intelligence feature — the part that tells an officer a product legally requires certification.

**You are not waiting for anything technical.** Your work happens entirely in a Google Sheet, independent of the database or any code. If your sheet exists with example rows, start now. If it does not, message Jay.

**Your full method is in Section 6, Sheet 3.** Follow it step by step. Key points:

- Start with the BIS "Products under Compulsory Certification" list, then move to QCO gazette notifications
- Copy product descriptions **exactly as written** — the precise wording determines coverage
- One row per product, even when a single notification covers many
- When coverage is unclear, record the literal text and flag it rather than interpreting
- **Stop after ten rows and have them checked by Jay before continuing**

**This sheet needs the most careful reading of the three.** It involves judging what a legal notification actually covers, which is interpretation rather than transcription. Go slowly.

**Ask your AI to:** summarise a long notification so you can locate the relevant section, explain legal or technical terminology, check rows for consistent scheme spelling.
**Never ask your AI to:** decide whether a product requires certification, or which scheme applies.

---

## SHARVA — Demo, presentation, quality control

**You own everything that turns a working product into a winning presentation**, plus independent verification that our data is trustworthy.

**Your first task is the earliest task on the whole project.** Start immediately; you are not waiting for anyone.

### First task — scope validation

Before collection scales up, confirm our four product families actually have enough material.

1. Go to `eprocure.gov.in`.
2. Search for each family in turn: electrical cables, LED lighting, pipes, safety equipment.
3. For each, open five or six tenders and check whether they actually cite IS numbers in their technical specifications.
4. Record roughly how many tenders you find per family, and how many of those cite standards clearly.
5. Report to Jay: which families look strong, and which look thin.
6. If a family is thin, suggest an alternative with plenty of tenders — common options are transformers, switchgear, furniture, or construction materials.

This prevents the team wasting rows on a family we later drop.

### Then, ongoing

**1. Data spot-checks.**
Pick ten random rows from each sheet regularly. Open each source link and confirm the row matches what the page actually says. You are the independent check — and you are also the person who produces the Version Correctness number in Section 8, Part B. Report anything wrong directly to Jay. Catching a systematic mistake early saves hundreds of rows.

**2. Demo script.**
Write the exact click-by-click path for the live demo: which tender gets uploaded, what the system shows at each step, what is said. Rehearse it with the team until it runs without hesitation.

**3. Judge Q&A preparation.**
Prepare written answers to the questions we will definitely get, and drill them with everyone — any team member may be asked:
- How do you stop the AI making things up?
- How do you stay current when standards change?
- What is your accuracy, and how did you measure it?
- Who is responsible if a recommendation is wrong?
- Why not just use the existing BIS search?
- Where did your data come from, given standards are copyrighted?
- Did you train a model?

*(Sections 1, 8, 9 and 11 contain the answers.)*

**4. Deck accuracy.**
Keep the presentation matched to what has actually been built. If a feature is cut, it comes off the slide the same day. Check especially that the browser extension and multilingual support are described as designed and roadmapped, not built — see Section 5.

**5. Backup video.**
Record a clean two-minute run of the working demo. If the live demo fails on stage, this plays instead.

**6. Documentation.**
README with setup steps, a short architecture note, and the source list.

**Ask your AI to:** draft and refine the demo script, generate likely judge questions and rehearse answers with you, proofread the deck against this document for contradictions, structure the README.

---

# SECTION 13 — QUICK REFERENCE

**Project:** MANAK-SETU · **Team:** The RAGnarok · **PS ID:** SIH26108
**Theme:** Smart Automation · **Category:** Software
**Organisation:** Department of Consumer Affairs (BIS), Ministry of Consumer Affairs, Food & Public Distribution

**Key sources:**
- `standards.bis.gov.in` — standards catalogue
- `bis.gov.in` — certification schemes, compulsory certification list
- `eprocure.gov.in` — public tender corpus
- `gem.gov.in` — government procurement marketplace

**Format rules:**
- IS numbers always written `IS 694` — "IS", one space, number, no year
- Status is always one of: `Current`, `Superseded`, `Withdrawn`
- Scheme is always one of: `QCO`, `BIS Product Certification`, `CRS`, `Hallmarking`, `None`

**The three rules that matter most:**
1. No source link, no row.
2. Retrieval and the graph decide; the model only phrases.
3. Anything on a slide must be something the demo can do.

**When in doubt about the project, ask Jay. When in doubt about a data row, record what the source literally says and flag it.**
