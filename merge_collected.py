"""Merge collected BIS catalogue rows into the standards register.

Additive only. A standard already in the register is left exactly as it is —
collection fills gaps, it never overwrites a row that is already there. Where the
two disagree, that is an amendment, and amendments belong to `pipeline.py --apply`
where they are reported before anything is written.

Every added row carries its provenance: the endpoint it came from and the date,
so "where did this row come from" is answerable per row rather than per file.

    python merge_collected.py                      # dry run: report only
    python merge_collected.py --write              # merge and write
"""

import argparse
import datetime
import os
import re

import pandas as pd

MASTER = "data/standards_master_extended.csv"
COLLECTED = "data/standards_collected_all.csv"

MASTER_COLUMNS = [
    "IS Number", "Full Title", "Year", "Status", "Replaced By", "Supersedes",
    "Product Family", "Priority", "Source Link", "IS Base", "Is IS Standard",
    "Flag", "Provenance",
]


def base_of(is_number: str) -> str:
    return re.sub(r"\s+", " ", str(is_number).split("(")[0].split(":")[0]).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="actually write the merged file")
    ap.add_argument("--collected", default=COLLECTED)
    args = ap.parse_args()

    if not os.path.exists(args.collected):
        raise SystemExit(f"{args.collected} not found — run collect_missing_standards.py --all")

    master = pd.read_csv(MASTER, encoding="utf-8-sig")
    fresh = pd.read_csv(args.collected, encoding="utf-8-sig")
    print(f"register   {len(master):>5} rows")
    print(f"collected  {len(fresh):>5} rows")

    held = set(master["IS Number"].astype(str)) | set(master["IS Base"].astype(str))
    fresh = fresh.drop_duplicates(subset=["IS Number"], keep="first")

    is_new = ~(
        fresh["IS Number"].astype(str).isin(held)
        | fresh["IS Number"].astype(str).map(base_of).isin(held)
    )
    additions = fresh[is_new].copy()
    already = len(fresh) - len(additions)

    # The portal returns the full designation, "IS 1000:2021". The register keeps
    # the number and the edition year in separate columns, so split rather than
    # merge two shapes into one table — otherwise half the register reads
    # "IS 4985" and half reads "IS 4985:2000" and nothing lines up on screen.
    designation = additions["IS Number"].astype(str)
    year_in_number = designation.str.extract(r":\s*((?:19|20)\d{2})")[0]
    additions["IS Number"] = designation.str.replace(r"\s*:\s*(?:19|20)\d{2}\s*$", "",
                                                     regex=True).str.strip()

    # Where publishedOn and the designation disagree, the designation wins: it is
    # what a tender actually cites. The disagreements are counted, not hidden.
    stated = pd.to_numeric(additions["Year"], errors="coerce")
    from_number = pd.to_numeric(year_in_number, errors="coerce")
    disagreed = int(((stated.notna()) & (from_number.notna()) & (stated != from_number)).sum())
    recovered = int((stated.isna() & from_number.notna()).sum())
    additions["Year"] = from_number.fillna(stated)

    today = datetime.date.today().isoformat()
    additions["IS Base"] = additions["IS Number"].astype(str).map(base_of)
    additions["Is IS Standard"] = "Yes"
    additions["Flag"] = ""
    additions["Provenance"] = f"BIS searchKnowStandards, collected {today}"
    for col in MASTER_COLUMNS:
        if col not in additions.columns:
            additions[col] = ""
    additions = additions[MASTER_COLUMNS]

    merged = pd.concat([master, additions], ignore_index=True)
    merged = merged.drop_duplicates(subset=["IS Number"], keep="first")

    print(f"\nyear recovered from designation   {recovered}")
    print(f"designation/publishedOn disagreed {disagreed} (designation kept)")
    print(f"\nalready held, skipped   {already}")
    print(f"new rows to add         {len(additions)}")
    print(f"register after merge    {len(merged)}")

    if len(additions):
        print("\nsample of what would be added:")
        for _, r in additions.head(6).iterrows():
            print(f"  {str(r['IS Number']):<24} {str(r['Full Title'])[:58]}")
        fams = additions["Product Family"].value_counts()
        print("\nby department:")
        for fam, n in fams.head(10).items():
            print(f"  {n:>4}  {fam}")

    if not args.write:
        print("\ndry run — nothing written. Re-run with --write to merge.")
        return

    merged.to_csv(MASTER, index=False)
    print(f"\nwrote {MASTER} — {len(merged)} rows")
    print("next: rebuild_backlog.py, load_db.py, build_embeddings.py "
          "(pipeline.py does all three)")


if __name__ == "__main__":
    main()
