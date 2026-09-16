"""Build an evaluation set from pairings BIS itself published.

A golden set needs a query and the standard that governs it, and the pairing has
to come from someone other than the system being tested. Labelling them myself
would be marking my own homework: the reasoning that picks the answer would
write the answer key.

The certification rules give exactly that pairing for free. Each Quality Control
Order names a product in its own words and states the IS number it applies to —

    "AC static watt-hour meters, class 1 & 2"            -> IS 13779
    "Residual current operated circuit breakers ..."     -> IS 12640 (Part 1)

The description is written by the notification, not copied from the standard's
title, so retrieving the right standard from it is a real test rather than a
lookup of the title against itself. And the pairing is a legal instrument, which
is a stronger authority than anything I could assert.

Two honest limits, recorded in the file itself:

  * QCO coverage is electrical, electronics and a few consumer goods. This set
    does not represent pipes, cement or civil standards, so a score from it is
    not a score for the whole corpus.
  * The five hand-written seed rows include two self-retrieval controls, where
    the query is the standard's own title. Those measure that the index works,
    not that retrieval is good. They are kept and marked.

    python build_golden.py            # write data/golden_queries.csv
    python build_golden.py --dry-run
"""

import argparse
import re
import sqlite3

import pandas as pd

# The full certification register, not just the original 77 Quality Control
# Order rows. The catalogue sweep added the Scheme I list — 156 steel and iron
# products, 19 fasteners, 17 aluminium, 16 cement, 20 geotextiles — which is
# precisely the non-electrical ground the QCO-only set could not cover. Same
# method, same authority: BIS names the product in its own words and states the
# standard it applies to.
RULES = "data/certification_rules_all.csv"
OUT = "data/golden_queries.csv"
DB = "manak_setu.db"

# Descriptions shorter than this are too generic to test retrieval ("Cement").
MIN_QUERY_CHARS = 22


def clean(text: str) -> str:
    """QCO text arrives with hard line breaks and inconsistent dashes."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"\s*-\s*Part\s*", " Part ", t, flags=re.I).strip(" -,")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rules = pd.read_csv(RULES, encoding="utf-8-sig")
    conn = sqlite3.connect(DB)
    try:
        held = {r[0] for r in conn.execute('SELECT "IS Number" FROM standards')}
        held |= {r[0] for r in conn.execute('SELECT "IS Base" FROM standards')}
        titles = {r[0]: (r[1] or "") for r in conn.execute(
            'SELECT "IS Number", "Full Title" FROM standards')}
    finally:
        conn.close()

    rows, skipped = [], {"short": 0, "not_held": 0, "same_as_title": 0}
    seen = set()
    for _, r in rules.iterrows():
        is_number = str(r["IS Number"]).strip()
        query = clean(r["Product Description"])
        if len(query) < MIN_QUERY_CHARS:
            skipped["short"] += 1
            continue
        if is_number not in held and str(r.get("IS Base", "")).strip() not in held:
            skipped["not_held"] += 1
            continue
        # If the notification simply repeats the title, it is a self-retrieval
        # control rather than a test, and this set already has two of those.
        title = titles.get(is_number, "")
        if title and query.lower()[:40] == title.lower()[:40]:
            skipped["same_as_title"] += 1
            continue
        if query.lower() in seen:
            continue
        seen.add(query.lower())
        rows.append({
            "query": query,
            "expected_is": is_number,
            "source": (f"{clean(r.get('Scheme')) or 'BIS certification'} product "
                       f"description, {clean(r.get('Notification Reference'))[:52] or 'certification_rules_all.csv'}"),
            "family": clean(r.get("BIS Product Category"))[:48],
        })

    existing = pd.read_csv(OUT, encoding="utf-8-sig") if OUT else None
    combined = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    combined = combined.drop_duplicates(subset=["query"], keep="first")

    print(f"certification rules      {len(rules)}")
    print(f"  too short             {skipped['short']}")
    print(f"  standard not held     {skipped['not_held']}")
    print(f"  description = title   {skipped['same_as_title']}")
    print(f"usable new pairs        {len(rows)}")
    print(f"existing seed rows      {0 if existing is None else len(existing)}")
    print(f"golden set total        {len(combined)}")
    print("\nsample:")
    for _, r in pd.DataFrame(rows).head(5).iterrows():
        print(f"  {r['expected_is']:<22} {r['query'][:64]}")

    if args.dry_run:
        print("\ndry run — nothing written")
        return
    combined.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}")
    print("These labels come from BIS notifications, not from hand review. They are "
          "stronger than a guess and weaker than an officer's judgement — the set is "
          "also electrical-heavy, so treat the score as indicative for that domain.")


if __name__ == "__main__":
    main()
