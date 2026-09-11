"""Collect each standard's BIS review date.

BIS does not publish numbered amendments through the catalogue endpoint this
system reads — that was checked, and the response has no amendment field at all.
What it does publish is `validUpto`: the date the standard is due for review.

That is not the same thing as an amendment, and it is not presented as one. But
it answers a question an officer actually has — "is this edition still current,
or is it overdue for revision?" — and a date in the past is a real signal that a
citation should be confirmed before publication.

Writes data/review_dates.csv. Merge into the register with --apply.

    python collect_review_dates.py --limit 50      # sample first
    python collect_review_dates.py                 # whole register
    python collect_review_dates.py --apply
"""

import argparse
import datetime
import sqlite3
import time

import pandas as pd

import collect_missing_standards as bis

OUT = "data/review_dates.csv"
MASTER = "data/standards_master_extended.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--apply", action="store_true", help="write into the register")
    args = ap.parse_args()

    conn = sqlite3.connect("manak_setu.db")
    try:
        rows = conn.execute(
            'SELECT "IS Number", "IS Base" FROM standards ORDER BY "IS Number"'
        ).fetchall()
    finally:
        conn.close()
    rows = rows[: args.limit] if args.limit else rows
    print(f"{len(rows)} standards to check  (~{len(rows) * 0.75 / 60:.0f} min)")

    out, missed = [], 0
    today = datetime.date.today().isoformat()
    for i, (is_number, is_base) in enumerate(rows, 1):
        try:
            hit = bis.pick(bis.fetch(is_base or is_number), is_number)
        except Exception:                                    # noqa: BLE001
            missed += 1
            time.sleep(bis.DELAY_SECONDS)
            continue
        if hit:
            valid = (hit.get("validUpto") or "")[:10]
            if valid:
                out.append({
                    "IS Number": is_number,
                    "Review Due": valid,
                    "Overdue": "Yes" if valid < today else "No",
                    "Collected": today,
                })
        else:
            missed += 1
        if i % 100 == 0:
            print(f"  {i}/{len(rows)} · {len(out)} dates · {missed} no match")
        time.sleep(bis.DELAY_SECONDS)

    df = pd.DataFrame(out)
    df.to_csv(OUT, index=False)
    overdue = int((df["Overdue"] == "Yes").sum()) if len(df) else 0
    print(f"\ncollected {len(df)} review dates · {missed} without a match")
    print(f"overdue for review today: {overdue}")
    print(f"wrote {OUT}")

    if not args.apply or df.empty:
        return
    master = pd.read_csv(MASTER, encoding="utf-8-sig")
    merged = master.merge(df[["IS Number", "Review Due", "Overdue"]], on="IS Number", how="left")
    merged.to_csv(MASTER, index=False)
    print(f"merged into {MASTER} — {merged['Review Due'].notna().sum()} rows now carry a review date")


if __name__ == "__main__":
    main()
