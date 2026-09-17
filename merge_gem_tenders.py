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

    python rebuild_graph.py          # co-citation edges over usable tenders
    python rebuild_backlog.py        # cited-but-not-held standards
    python load_db.py                # reload manak_setu.db

    python merge_gem_tenders.py            # report what would change
    python merge_gem_tenders.py --write    # do it
"""

import argparse

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
                 "Ministry", "Department", "Organisation", "Office"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--collected", default=COLLECTED)
    args = ap.parse_args()

    master = pd.read_csv(MASTER, encoding="utf-8-sig")
    new = pd.read_csv(args.collected, encoding="utf-8-sig")
    for col in EXTRA_COLUMNS:
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

    if not args.write:
        print("\ndry run — nothing written. Re-run with --write to merge.")
        return

    merged = pd.concat([master, keep[MASTER_COLUMNS + EXTRA_COLUMNS]], ignore_index=True)
    merged.to_csv(MASTER, index=False)
    print(f"\nwrote {MASTER}: {len(merged)} documents")
    print("now run: python rebuild_graph.py && python rebuild_backlog.py && python load_db.py")


if __name__ == "__main__":
    main()
