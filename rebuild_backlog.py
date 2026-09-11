"""Recompute the collection backlog against the current register.

The shipped coverage_gap_backlog.csv was derived when the register held 405
standards. We have since collected 146 more from the BIS catalogue, so a
backlog listing gaps we have since filled overstates the problem — and this
project's whole claim is that its numbers are recomputed, not carried forward.

Nothing is invented here. The backlog is exactly the set of IS numbers that
real tenders cite and the register does not hold, ranked by how many tenders
want them. Writes a new file; the original is left alone.
"""

import re
import sqlite3

import pandas as pd

DB_PATH = "manak_setu.db"
OUT = "data/coverage_gap_backlog_current.csv"


def base(is_number: str) -> str:
    return re.sub(r"\s+", " ", str(is_number).split("(")[0].split(":")[0]).strip()


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            'SELECT "IS Numbers Cited" FROM tenders WHERE "Usability" = ?', ("Usable",)
        ).fetchall()
        held_exact = {r[0] for r in conn.execute('SELECT "IS Number" FROM standards')}
        held_base = {r[0] for r in conn.execute('SELECT "IS Base" FROM standards')}
        held_digits = {r[0] for r in conn.execute('SELECT "IS Digits" FROM standards') if r[0]}
    finally:
        conn.close()

    demand: dict[str, int] = {}
    for (value,) in rows:
        cited = {c.strip() for c in str(value or "").split(";") if c.strip()}
        for is_number in cited:
            demand[is_number] = demand.get(is_number, 0) + 1

    digits = lambda s: re.sub(r"[^0-9]", "", base(s))
    missing = {
        k: v for k, v in demand.items()
        if k not in held_exact and base(k) not in held_base and digits(k) not in held_digits
    }
    out = pd.DataFrame(
        sorted(({"Tenders Citing": v, "IS Number": k} for k, v in missing.items()),
               key=lambda r: (-r["Tenders Citing"], r["IS Number"]))
    )
    out.to_csv(OUT, index=False)

    total = len(demand)
    print(f"usable tenders          {len(rows)}")
    print(f"distinct IS cited       {total}")
    print(f"held in register        {total - len(missing)}  ({100 * (total - len(missing)) / total:.1f}%)")
    print(f"still to collect        {len(missing)}")
    print(f"\nwrote {OUT}")
    print("\nmost-wanted gaps:")
    for _, r in out.head(8).iterrows():
        print(f"  {r['IS Number']:<24} cited by {r['Tenders Citing']} tenders")


if __name__ == "__main__":
    main()
