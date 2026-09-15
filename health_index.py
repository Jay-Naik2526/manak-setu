"""Procurement Standards Health Index — how healthy are the standards government
buyers are actually citing?

Every other measurement in this project asks whether the system is right. This
one asks something the system is uniquely placed to answer and nobody else can:
across real published government bids, how often does a tender cite a standard
BIS has already withdrawn or superseded, and which dead standards are still in
circulation?

That is not a retrieval metric. It is a procurement-policy measurement, and it
falls out of two things we already hold: a corpus of real tender documents with
their literal citations, and BIS's own status for each standard. Joining them
gives the Department of Consumer Affairs a demand signal it does not otherwise
have — which standards the procurement system leans on, and which of those are
overdue for revision.

Every figure carries its denominator. The corpus is a sample of Indian public
procurement, not a census, and the output says so: these are counts over the
documents we collected, never an estimate of the national rate.

    python health_index.py            # print the report
    python health_index.py --write    # also write data/health_index.json
"""

import argparse
import collections
import datetime
import json
import re
import sqlite3

DB = "manak_setu.db"
OUT = "data/health_index.json"
TOP_N = 15

# GeM bid numbers carry the year they were floated: GEM/2025/B/6183459.
YEAR_RE = re.compile(r"\b(20\d{2})\b")


def base_of(citation: str) -> str:
    return re.sub(r"\s+", " ", str(citation).split("(")[0].split(":")[0]).strip().upper()


def _register(conn) -> dict[str, dict]:
    """Status, title and successor by IS base number."""
    out: dict[str, dict] = {}
    for base, number, title, status, replaced, review, overdue in conn.execute(
        'SELECT "IS Base", "IS Number", "Full Title", "Status", "Replaced By", '
        '"Review Due", "Overdue" FROM standards'
    ):
        key = str(base).strip().upper()
        # First writer wins, and Current beats a dead edition of the same base:
        # a tender citing "IS 1554" without a part should not be called dead
        # because one part of it was withdrawn.
        if key not in out or (status == "Current" and out[key]["status"] != "Current"):
            out[key] = {
                "is_number": number, "title": title, "status": status,
                "replaced_by": replaced, "review_due": review, "overdue": overdue,
            }
    return out


def _year_of(tender_id: str) -> str:
    m = YEAR_RE.search(str(tender_id))
    return m.group(1) if m else "unknown"


def build() -> dict:
    conn = sqlite3.connect(DB)
    try:
        reg = _register(conn)
        rows = conn.execute(
            'SELECT "Tender ID", "Product Family", "IS Numbers Cited" '
            'FROM tenders WHERE "Usability" = ?', ("Usable",)
        ).fetchall()
        total_documents = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
    finally:
        conn.close()

    dead_by_doc = collections.Counter()      # is_number -> documents citing it
    demand = collections.Counter()           # is_number -> documents citing it
    by_year = collections.defaultdict(lambda: [0, 0])     # year -> [docs, docs with a dead citation]
    by_family = collections.defaultdict(lambda: [0, 0])
    unresolved_docs = 0
    documents_with_dead = 0
    citations_total = 0

    for tender_id, family, cited in rows:
        citations = [c.strip() for c in str(cited or "").split(";") if c.strip()]
        citations_total += len(citations)
        year = _year_of(tender_id)
        fam = str(family or "Unclassified")
        by_year[year][0] += 1
        by_family[fam][0] += 1

        has_dead, has_unresolved = False, False
        seen_bases = set()
        for c in citations:
            base = base_of(c)
            if base in seen_bases:
                continue
            seen_bases.add(base)
            hit = reg.get(base)
            if not hit:
                has_unresolved = True
                continue
            demand[hit["is_number"]] += 1
            if hit["status"] in ("Withdrawn", "Superseded"):
                has_dead = True
                dead_by_doc[hit["is_number"]] += 1
        if has_dead:
            documents_with_dead += 1
            by_year[year][1] += 1
            by_family[fam][1] += 1
        if has_unresolved:
            unresolved_docs += 1

    usable = len(rows)

    def rank(counter, limit=TOP_N):
        out = []
        for number, docs in counter.most_common(limit):
            hit = reg.get(base_of(number), {})
            out.append({
                "is_number": number,
                "title": hit.get("title"),
                "status": hit.get("status"),
                "replaced_by": (hit.get("replaced_by") or "UNKNOWN"),
                "review_due": hit.get("review_due") or "",
                "overdue": hit.get("overdue") or "",
                "documents": docs,
                "of": usable,
            })
        return out

    return {
        "generated": datetime.date.today().isoformat(),
        "corpus": {
            "documents_collected": total_documents,
            "documents_measured": usable,
            "citations_read": citations_total,
            "note": (
                "Counts over the tender documents in this corpus whose text could be "
                "read (Usability='Usable'). A sample of Indian public procurement, "
                "not a census — these are not national rates."
            ),
        },
        "headline": {
            "documents_with_a_dead_citation": documents_with_dead,
            "of_documents": usable,
            "documents_citing_a_standard_not_in_the_register": unresolved_docs,
            "distinct_dead_standards_in_circulation": len(dead_by_doc),
        },
        "by_year": [
            {"year": y, "documents": n, "with_dead_citation": d}
            for y, (n, d) in sorted(by_year.items())
        ],
        "by_family": [
            {"family": f, "documents": n, "with_dead_citation": d}
            for f, (n, d) in sorted(by_family.items(), key=lambda kv: -kv[1][1])
            if n
        ][:TOP_N],
        "dead_standards_still_cited": rank(dead_by_doc),
        "most_cited_standards": rank(demand),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    d = build()

    c, h = d["corpus"], d["headline"]
    print(f"Procurement Standards Health Index · {d['generated']}")
    print(f"\ncorpus: {c['documents_measured']} machine-readable documents "
          f"of {c['documents_collected']} collected · {c['citations_read']} citations read")
    print(f"\ndocuments citing a withdrawn or superseded standard: "
          f"{h['documents_with_a_dead_citation']} of {h['of_documents']}")
    print(f"distinct dead standards still in circulation        : "
          f"{h['distinct_dead_standards_in_circulation']}")
    print(f"documents citing a standard not in the register     : "
          f"{h['documents_citing_a_standard_not_in_the_register']} of {h['of_documents']}")

    if d["dead_standards_still_cited"]:
        print("\ndead standards still being cited:")
        for r in d["dead_standards_still_cited"][:8]:
            print(f"  {r['documents']:>3} of {r['of']:<4} {r['is_number']:<24} "
                  f"{r['status']:<11} {str(r['title'])[:44]}")

    if d["most_cited_standards"]:
        print("\nmost-cited standards (the demand signal for revision priority):")
        for r in d["most_cited_standards"][:8]:
            flag = " · REVIEW OVERDUE" if str(r["overdue"]).lower() == "yes" else ""
            print(f"  {r['documents']:>3} of {r['of']:<4} {r['is_number']:<24} "
                  f"{str(r['title'])[:40]}{flag}")

    if args.write:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
