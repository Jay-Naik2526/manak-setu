"""Merge GeM tender rows collected by collect_gem_tenders.py into the corpus.

Additive only, and a dry run unless told otherwise. A document already in the
corpus — same source link or same tender id — is left exactly as it is. Every
added row keeps its source link, so any citation in the graph can be traced
back to the public document it was read from.

Two columns travel with the new rows that the original corpus did not have:
"Item Category", the bid's own product line as GeM prints it, which gives the
tender a real name instead of one derived from a filename; and "GeM Bid Id".
Existing rows simply carry them empty.

After a merge with --write, the derived tables are stale until rebuilt:

    python rebuild_graph.py --min-co 1 --min-confidence 0.05 --min-source 1
    python rebuild_backlog.py        # cited-but-not-held standards
    python load_db.py                # reload manak_setu.db

    python merge_gem_tenders.py            # report what would change
    python merge_gem_tenders.py --write    # do it
"""

import argparse
import collections
import json

import pandas as pd

MASTER = "data/tender_dataset.csv"
COLLECTED = "data/tender_collected_gem.csv"

MASTER_COLUMNS = [
    "Tender ID", "Product Family", "IS Numbers Cited", "Foreign Standards Cited",
    "Count", "Outdated Citations", "Any Outdated", "Document Type", "Usability",
    "Source Link", "Unmatched Citations",
]
EXTRA_COLUMNS = ["Item Category", "GeM Bid Id",
                 # Who was buying, read from the saved bid form. The original
                 # 220-row set has no bid form, so these stay empty there and
                 # every buyer figure carries "of N GeM documents".
                 "Ministry", "Department", "Organisation", "Office",
                 # Whether the document's own text demands certified material.
                 "Demands Standard Mark"]


# Columns the collector owns — the ones re-read from the saved bid form and its
# attachments. A refresh rewrites only these, and only on rows that came from
# GeM, so anything curated by hand elsewhere in the master is untouched.
COLLECTOR_OWNED = [
    "IS Numbers Cited", "Foreign Standards Cited", "Count", "Product Family",
    "Outdated Citations", "Any Outdated", "Unmatched Citations", "Usability",
    "Document Type", "Item Category",
    "Ministry", "Department", "Organisation", "Office",
    "Demands Standard Mark",
]


def refresh(master, new, write: bool, provided: set[str] | None = None) -> int:
    """Carry corrections on rows the master already holds.

    The merge is additive on purpose: the rule is that nothing overwrites a row
    that is already in data/. But a re-extraction exists precisely to correct
    rows already collected — when the citation pattern was found to be reading
    "IS 201619" out of "IS:2016-1967", leaving that in the master would mean
    knowingly keeping a fabricated designation rather than the one the document
    prints.

    So a refresh is allowed, and it is explicit, narrow and reported: opt-in
    with --refresh, matched on the GeM bid id, limited to COLLECTOR_OWNED
    columns, and every changed field is counted before anything is written.
    """
    key = "GeM Bid Id"
    if key not in master.columns or key not in new.columns:
        print("no GeM Bid Id column on both sides — nothing to refresh")
        return 0
    # Only the columns the collected file actually carried. main() pads `new`
    # with every EXTRA_COLUMN so the additive path has a uniform frame, and a
    # refresh that trusted `src.columns` therefore read those pads as data: a
    # dry run of the OCR collection offered to blank Item Category, Ministry,
    # Department, Organisation, Office and Demands Standard Mark on all 3,659
    # rows it touched, because the OCR collector does not read the bid form and
    # never claimed to. A collector corrects what it derived. Silence is not a
    # value.
    owned = [c for c in COLLECTOR_OWNED if provided is None or c in provided]
    skipped = [c for c in COLLECTOR_OWNED if c not in owned]
    if skipped:
        print(f"refresh  : {len(skipped)} collector column(s) absent from the "
              f"collected file and left alone — {', '.join(skipped)}")
    src = new.dropna(subset=[key]).drop_duplicates(subset=[key]).set_index(key)
    fields = collections.Counter()
    rows = set()
    for i, bid in master[key].items():
        if pd.isna(bid) or bid not in src.index:
            continue
        for col in owned:
            if col not in src.columns:
                continue
            before, after = master.at[i, col], src.at[bid, col]
            if str(before) == str(after) or (pd.isna(before) and pd.isna(after)):
                continue
            fields[col] += 1
            rows.add(i)
            if write:
                master.at[i, col] = after
    print(f"\nrefresh  : {len(rows)} existing rows differ from the re-read collection")
    for col, n in fields.most_common():
        print(f"  {n:>5}  {col}")
    if not write and rows:
        print("  (dry run — add --write to apply)")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--refresh", action="store_true",
                    help="also carry corrections onto rows the master already "
                         "holds, for the columns the collector owns")
    ap.add_argument("--collected", default=COLLECTED)
    args = ap.parse_args()

    master = pd.read_csv(MASTER, encoding="utf-8-sig")
    new = pd.read_csv(args.collected, encoding="utf-8-sig")
    # What the collector actually wrote, before the padding below.
    provided = set(new.columns)
    # A collector that only corrects rows the master already holds carries no
    # new source links — collect_tender_ocr.py re-reads attachments that were
    # downloaded from links already recorded. The additive path below still
    # runs and still adds nothing, because every one of those tender ids is
    # already in the master.
    if "Source Link" not in new.columns:
        new["Source Link"] = ""
    # Pad both frames so the additive path has a uniform shape. `provided`
    # above is what decides whether a column is data or padding, so this can
    # safely fill in anything a partial collector left out.
    for col in MASTER_COLUMNS + EXTRA_COLUMNS:
        if col not in master.columns:
            master[col] = ""
        if col not in new.columns:
            new[col] = ""

    have_links = set(master["Source Link"].dropna().astype(str))
    have_ids = set(master["Tender ID"].dropna().astype(str))
    keep = new[~new["Source Link"].astype(str).isin(have_links)
               & ~new["Tender ID"].astype(str).isin(have_ids)]
    keep = keep.drop_duplicates(subset=["Tender ID"]).drop_duplicates(subset=["Source Link"])

    usable_before = int((master["Usability"] == "Usable").sum())
    usable_added = int((keep["Usability"] == "Usable").sum())
    print(f"corpus now      : {len(master)} documents, {usable_before} usable")
    print(f"collected       : {len(new)} rows, {len(keep)} new")
    print(f"after merge     : {len(master) + len(keep)} documents, "
          f"{usable_before + usable_added} usable")
    print("new rows by family:")
    for fam, n in keep["Product Family"].value_counts().head(12).items():
        print(f"  {n:>4}  {fam}")

    touched = refresh(master, new, args.write, provided) if args.refresh else 0

    if not args.write:
        print("\ndry run — nothing written. Re-run with --write to merge.")
        return

    merged = pd.concat([master, keep[MASTER_COLUMNS + EXTRA_COLUMNS]], ignore_index=True)
    merged.to_csv(MASTER, index=False)
    print(f"\nwrote {MASTER}: {len(merged)} documents"
          + (f" ({touched} existing rows refreshed)" if touched else ""))
    # Order matters and used to be wrong here: rebuild_backlog reads the
    # database, not the CSV, so running it before load_db recomputes the
    # backlog against the register as it was before this merge — which is how
    # a backlog listing eight citations no longer in the corpus survived a
    # full rebuild. load_db runs first, and again at the end to pick up the
    # files the rebuilds wrote.
    # rebuild_graph.py's built-in defaults are stricter than the thresholds this
    # corpus was actually built at. Running it bare rebuilt the graph at
    # min-co 2 / min-confidence 0.2 and cut it from 1,858 nodes to 635 — a
    # silent two-thirds loss in a file nobody reads, discovered only because the
    # layout printed its node count. The chain carries the thresholds, read from
    # data/graph_meta.json so this line cannot drift from the graph on disk.
    meta = {}
    try:
        with open("data/graph_meta.json", encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        pass
    flags = ""
    if meta:
        flags = (f" --min-co {meta.get('min_co_citations', 1)}"
                 f" --min-confidence {meta.get('min_confidence', 0.05)}"
                 f" --min-source {meta.get('min_source_tenders', 1)}")
    print(f"now run: python load_db.py --allow-shrink && python rebuild_graph.py{flags} "
          "&& python rebuild_backlog.py && python load_db.py --allow-shrink "
          "&& python graph_layout.py && python health_index.py --write")


if __name__ == "__main__":
    main()
