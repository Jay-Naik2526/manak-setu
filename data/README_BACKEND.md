# MANAK-SETU — FINAL Backend Data Pack

All numbers here are real, verified against original source links. No fabricated rows. Build against these files only.

## Files
- `standards_master.csv` — 405 rows. Cols: `IS Number, IS Base, Is IS Standard, Full Title, Year, Status(Current/Superseded/Withdrawn), Replaced By, Supersedes, Product Family, Priority, Source Link, Flag`
- `tender_dataset.csv` — 220 rows. Cols include `Usability` (`Usable`=134, `Multi-scope`=27, `Not extractable`=47, `Extraction failed`=12), `Any Outdated` (`Yes`/`No`/`Not checked`), `Unmatched Citations`
- `certification_rules.csv` — 77 in-scope rows (Electrical cables 31, Safety equipment 43, Pipes 3, LED 0 — see gap below)
- `co_citation_graph.csv` — 376 edges / 74 nodes (medium threshold: min 5 tenders citing source, min 3 co-citations, min confidence 0.25). Cols: `Source IS, Target IS, Tenders Citing Source, Tenders Citing Target, Co-citation Count, Confidence, Lift, Evidence Statement`. All derived from the 134 usable tenders — no fabricated standards involved.
- `coverage_gap_backlog.csv` — 404 IS numbers cited in tenders but absent from Standards Master, ranked by frequency. Feed the top ~50 to retrieval as "known unknowns" / low-confidence fallback candidates.
- `MANAK-SETU_FINAL.xlsx` — all five as sheets.

## Build against this directly
- **Retrieval / search index**: `standards_master.csv`, filter `Product Family` to your 4 in-scope families.
- **Relationship engine**: `co_citation_graph.csv` as-is. Join on `Source IS`/`Target IS`.
- **Version/dead-citation check**: join tender's cited IS → `standards_master.csv` on `IS Number` then `IS Base`. If `Status` in (Superseded, Withdrawn) → flag, surface `Replaced By` (may be `UNKNOWN`).
- **Certification check**: join cited/typed product family → `certification_rules.csv` on `IS Number`/`IS Base`.
- **Confidence gate**: if cited IS not in `standards_master.csv` → not-found path (Section 11 behaviour: show low-confidence nearest candidates + route to human), never silently drop.

## Honest gaps — say these on stage, don't hide them
1. **Coverage: 84/488 (17%) of tender-cited standards are in the master list.** 404-row backlog file is prioritized by demand — top rows are highest value if anyone has 30 more min to collect.
2. **Supersession data thin: 10 Superseded + 9 Withdrawn out of 405.** Real, not fabricated, but sparse — demo the "dead citation" feature using one of these known IS numbers, don't rely on random tender upload to trigger it.
3. **Outdated-citation stat: 4 of 62 fully-matchable usable tenders (6.5%)** cite a dead standard. Use "62 tenders where every citation was verifiable," not "200 tenders" — smaller number, defensible number.
4. **LED lighting has 0 certification rows.** Certification Intelligence demo must use cables or safety equipment, not LED, until Jiya adds real CRS rows.
5. Multi-scope (27) and unextractable (47+12) tenders excluded from graph/stats by design — not lost, just not double-counted.

## What NOT to do
Don't run any more "auto-fill gaps" pipelines on this data. Every gap listed above is real and correct; filling it requires an actual BIS page or tender, not a script.
