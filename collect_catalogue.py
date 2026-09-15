"""Harvest the BIS catalogue broadly, rather than one cited number at a time.

`collect_missing_standards.py` answers "is this specific IS number in the
catalogue?" — it was built to close gaps the tender corpus exposed. That leaves
the register at whatever size the gaps happened to require: 2,087 rows against a
catalogue of roughly 22,000.

The same endpoint answers a different question just as well. `searchKnowStandards`
takes any search text and returns up to 500 records, so sweeping a large
vocabulary and taking the union covers the catalogue without ever asking for a
standard by name. Ten common words returned 3,696 distinct standards; the
vocabulary here is every substantial word the register's own titles already use,
which is the vocabulary BIS writes its titles in.

Two fields the gap-filling collector discarded are kept, because both are
published and both are useful:

  * `standardNameInHindi` — BIS's own Hindi title. Indexing it gives Hindi
    retrieval with no translation service in the loop.
  * `validUpto` — the date BIS set for the edition's review. Not an amendment,
    and never presented as one.

Writes data/standards_collected_catalogue.csv. Merging is a separate reviewed
step: merge_collected.py --collected data/standards_collected_catalogue.csv.

    python collect_catalogue.py --dry-run          # vocabulary and a sample
    python collect_catalogue.py                    # full sweep, resumable
"""

import argparse
import collections
import json
import os
import re
import sqlite3
import time

import pandas as pd

import collect_missing_standards as bis

OUT = "data/standards_collected_catalogue.csv"
PROGRESS = "data/standards_collected_catalogue.progress.jsonl"
DB = "manak_setu.db"

# The portal returns at most this many records for one search. A query that hits
# the cap is certainly truncated, so it is refined rather than trusted.
PAGE_CAP = 500
MIN_WORD = 4
STOPWORDS = {
    "and", "for", "the", "with", "from", "part", "section", "specification",
    "specifications", "requirements", "general", "method", "methods", "test",
    "tests", "other", "used", "type", "types", "first", "second", "third",
    "revision", "amendment", "code", "practice", "glossary", "terms", "its",
    "their", "this", "that", "such", "shall", "into", "upto", "including",
}
# Refinements appended to a capped query, chosen because they partition BIS
# titles rather than because they mean anything in particular.
REFINERS = ["specification", "method", "part", "test", "code", "safety",
            "requirements", "system", "material", "equipment", "industrial",
            "general", "quality", "design", "electrical", "steel", "water"]


def vocabulary() -> list[str]:
    """Search terms, drawn from what BIS already writes in its own titles."""
    conn = sqlite3.connect(DB)
    try:
        titles = [r[0] or "" for r in conn.execute('SELECT "Full Title" FROM standards')]
        families = {r[0] or "" for r in conn.execute('SELECT DISTINCT "Product Family" FROM standards')}
        products = [r[0] or "" for r in conn.execute('SELECT "Product Description" FROM certification_rules')]
    finally:
        conn.close()

    counts = collections.Counter()
    for text in titles + products:
        for word in re.findall(r"[A-Za-z]{%d,}" % MIN_WORD, str(text).lower()):
            if word not in STOPWORDS:
                counts[word] += 1

    words = [w for w, _ in counts.most_common()]
    # Department aliases ("CED", "ETD") and full names are their own good queries.
    for fam in families:
        for piece in re.split(r"[—\-,]", str(fam)):
            piece = piece.strip()
            if len(piece) >= 3 and piece.lower() not in ("n/a", "nan"):
                words.append(piece)
    # Bare designations reach standards whose titles use none of our vocabulary.
    words += [f"IS {d}" for d in range(1, 10)] + ["IS/IEC", "IS/ISO", "ISO", "IEC"]

    seen, out = set(), []
    for w in words:
        k = w.lower()
        if k not in seen:
            seen.add(k)
            out.append(w)
    return out


def row_of(record: dict, departments: dict[int, str]) -> dict:
    """One catalogue record in the register's shape. Nothing is inferred: every
    field is either copied from the response or left for the merge to fill."""
    status = "Withdrawn" if record.get("withdrawStatus") else bis.STATUS_MAP.get(
        record.get("isStatus"), "Current"
    )
    number = (record.get("standardNumber") or "").strip()
    review = (record.get("validUpto") or "")[:10]
    return {
        "IS Number": number,
        "Full Title": (record.get("standardName") or "").strip(),
        "Title (Hindi)": (record.get("standardNameInHindi") or "").strip(),
        "Year": (record.get("publishedOn") or "")[:4],
        "Status": status,
        "Replaced By": "UNKNOWN",
        "Supersedes": "UNKNOWN",
        "Product Family": departments.get(record.get("departmentId"), "Unassigned department"),
        "Priority": "Collected",
        "Source Link": "https://standards.bis.gov.in/website/know-your-standards",
        "IS Base": bis.base_of(number),
        "Review Due": review,
        "Collected From": "BIS searchKnowStandards (catalogue sweep)",
        "Department Id": record.get("departmentId"),
        "Committee Id": record.get("committeeId"),
    }


def done_queries() -> set[str]:
    if not os.path.exists(PROGRESS):
        return set()
    with open(PROGRESS, encoding="utf-8") as fh:
        return {json.loads(line)["query"] for line in fh if line.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="only the first N queries")
    args = ap.parse_args()

    words = vocabulary()
    if args.limit:
        words = words[: args.limit]
    print(f"vocabulary: {len(words)} search terms")
    print(f"sample: {', '.join(words[:14])}")
    if args.dry_run:
        print(f"\nestimated wall time: {len(words) * bis.DELAY_SECONDS / 60:.0f} min")
        return

    departments = bis.departments()
    print(f"departments: {len(departments)}")

    # Resume: records already collected, keyed by standardId equivalent.
    records: dict[str, dict] = {}
    if os.path.exists(OUT):
        for row in pd.read_csv(OUT, encoding="utf-8-sig").to_dict("records"):
            records[str(row["IS Number"])] = row
    skip = done_queries()
    todo = [w for w in words if w not in skip]
    print(f"{len(todo)} queries to run ({len(skip)} already done) · "
          f"{len(records)} records held · ~{len(todo) * bis.DELAY_SECONDS / 60:.0f} min\n")

    capped, failed = [], 0
    for i, word in enumerate(todo, 1):
        try:
            data = bis.fetch(word)
        except Exception as exc:                             # noqa: BLE001
            failed += 1
            print(f"  [{i}/{len(todo)}] {word:<24} ! {type(exc).__name__}")
            time.sleep(bis.DELAY_SECONDS * 2)
            continue

        before = len(records)
        for record in data:
            number = (record.get("standardNumber") or "").strip()
            if number and number not in records:
                records[number] = row_of(record, departments)
        added = len(records) - before
        if len(data) >= PAGE_CAP:
            capped.append(word)
        with open(PROGRESS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"query": word, "returned": len(data), "added": added}) + "\n")
        if i % 25 == 0 or added:
            print(f"  [{i}/{len(todo)}] {word:<24} {len(data):>4} returned  "
                  f"+{added:<4} total {len(records)}")
        if i % 100 == 0:
            pd.DataFrame(list(records.values())).to_csv(OUT, index=False)
        time.sleep(bis.DELAY_SECONDS)

    # A capped query was truncated at 500, so the rest of its matches were never
    # seen. Re-asking it with a refining word reaches a different slice.
    if capped:
        print(f"\n{len(capped)} queries hit the {PAGE_CAP} cap — refining")
        for word in capped:
            for refiner in REFINERS:
                query = f"{word} {refiner}"
                if query in skip:
                    continue
                try:
                    data = bis.fetch(query)
                except Exception:                            # noqa: BLE001
                    time.sleep(bis.DELAY_SECONDS * 2)
                    continue
                before = len(records)
                for record in data:
                    number = (record.get("standardNumber") or "").strip()
                    if number and number not in records:
                        records[number] = row_of(record, departments)
                with open(PROGRESS, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"query": query, "returned": len(data),
                                         "added": len(records) - before}) + "\n")
                time.sleep(bis.DELAY_SECONDS)
            print(f"  {word:<24} total {len(records)}")

    df = pd.DataFrame(list(records.values()))
    df.to_csv(OUT, index=False)
    hindi = int((df["Title (Hindi)"].fillna("").astype(str).str.strip() != "").sum())
    review = int((df["Review Due"].fillna("").astype(str).str.strip() != "").sum())
    print(f"\n{len(df)} distinct standards collected")
    print(f"  with a Hindi title : {hindi} ({hindi / len(df) * 100:.1f}%)")
    print(f"  with a review date : {review} ({review / len(df) * 100:.1f}%)")
    print("  by status          : " + ", ".join(
        f"{k} {v}" for k, v in df["Status"].value_counts().items()))
    print(f"  queries that failed: {failed}")
    print(f"\nwrote {OUT}")
    print("merge with: python merge_collected.py --collected "
          f"{OUT} --write")


if __name__ == "__main__":
    main()
