"""Load the CSV sources into SQLite.

Row counts are checked against the previous load rather than against numbers
typed into this file. Hardcoded expectations were wrong the moment the register
grew, and an assert that fires on legitimate growth teaches you to delete the
assert. What actually matters is: nothing is empty, and a large unexplained drop
stops the load before it replaces good data with bad.
"""

import argparse
import json
import os
import sqlite3

import pandas as pd

DB_PATH = "manak_setu.db"
STATE = "data/load_state.json"

# A drop larger than this against the previous load is treated as a mistake —
# a truncated download or a bad merge — not as an intentional change.
MAX_SHRINK = 0.20

TABLES = {
    "standards": "data/standards_master_extended.csv",
    "tenders": "data/tender_dataset.csv",
    "co_citation": "data/co_citation_graph_full.csv",
    # The original 77 QCO rows plus the 628 products under compulsory ISI-mark
    # certification collected from bis.gov.in (collect_certification.py). The
    # original file is unchanged and still the first authority on its own rows.
    "certification_rules": "data/certification_rules_all.csv",
    "coverage_gap_backlog": "data/coverage_gap_backlog_current.csv",
}


def _create_indexes(conn) -> None:
    """Index the columns every lookup actually uses.

    There were none. `to_sql(..., if_exists="replace")` drops the table and
    rebuilds it on each load, taking any index with it, so nothing survived.
    /peers averaged 330 ms because resolving each citation of each matched bid
    was a full scan of 27,687 rows."""
    indexes = [
        ("standards", "IS Number"), ("standards", "IS Base"), ("standards", "IS Digits"),
        ("standards", "Status"), ("standards", "Product Family"),
        ("tenders", "Tender ID"), ("tenders", "Usability"), ("tenders", "Product Family"),
        ("certification_rules", "IS Number"), ("certification_rules", "IS Base"),
        ("certification_rules", "Scheme"),
        ("co_citation", "Source IS"), ("co_citation", "Target IS"),
        ("coverage_gap_backlog", "IS Number"),
    ]
    made = 0
    for table, column in indexes:
        columns = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            continue
        name = f"ix_{table}_{column.lower().replace(' ', '_')}"
        conn.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {table}("{column}")')
        made += 1
    conn.execute("ANALYZE")
    conn.commit()
    print(f"\nindexed {made} columns")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-shrink", action="store_true",
                    help="permit a table to shrink beyond the guard — use when the "
                         "drop is the intended result of a merge or a recompute")
    args = ap.parse_args()

    previous = {}
    if os.path.exists(STATE):
        with open(STATE) as fh:
            previous = json.load(fh)

    frames, counts = {}, {}
    for table, csv_path in TABLES.items():
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if df.empty:
            raise SystemExit(f"{csv_path} is empty — refusing to load {table}")
        before = previous.get(table)
        if before and len(df) < before * (1 - MAX_SHRINK) and not args.allow_shrink:
            raise SystemExit(
                f"{table}: {len(df)} rows, down from {before} — more than "
                f"{MAX_SHRINK:.0%} smaller. Refusing to load. Restore the source, or "
                f"re-run with --allow-shrink if the drop is intended."
            )
        if table == "standards":
            # BIS publishes adopted IEC texts as "IS/IEC 60947" while tenders cite
            # them "IS 60947". The number is the identity; the prefix is not. This
            # column is what makes the two resolve to the same standard.
            df["IS Digits"] = (
                df["IS Number"].astype(str)
                .str.split("(").str[0].str.split(":").str[0]
                .str.replace(r"[^0-9]", "", regex=True)
            )
        frames[table], counts[table] = df, len(df)

    conn = sqlite3.connect(DB_PATH)
    try:
        for table, df in frames.items():
            df.to_sql(table, conn, if_exists="replace", index=False)
            before = previous.get(table)
            delta = "" if before is None else f"  ({len(df) - before:+d})"
            print(f"{table:<22} {len(df):>6} rows{delta}   {TABLES[table]}")
        _create_indexes(conn)
    finally:
        conn.close()

    with open(STATE, "w") as fh:
        json.dump(counts, fh, indent=1)
    print(f"\nloaded into {DB_PATH}; counts recorded in {STATE}")


if __name__ == "__main__":
    main()
