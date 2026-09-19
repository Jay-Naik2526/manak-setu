"""Read the scans that pdfplumber could not.

3,454 documents in this corpus are scanned PDFs — a photograph of a page with
no text layer — and 264 more are text PDFs whose text layer is empty. They were
collected, stored and then set aside as Not extractable, which is honest but
incomplete: the specification is printed on the page, and the page is on disk.

This reads them with macOS Vision (see ocr.py for why that and not a service),
extracts citations with the same `engine.extract_citations` every other path in
this project uses, and keeps only the designations the register can confirm.

    python collect_tender_ocr.py --limit 40      # pilot, writes nothing new
    python collect_tender_ocr.py                 # the whole backlog of scans
    python merge_gem_tenders.py --refresh \
        --collected data/tender_collected_ocr.csv --write

It is resumable: rows already in the output file are skipped, so an interrupted
run continues where it stopped.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import sqlite3
import sys
import time

import pandas as pd

import ocr

OUT = "data/tender_collected_ocr.csv"
PDF_DIR = "data/tenders/gem"
DB = "manak_setu.db"

# "Foreign Standards Cited" and "Document Type" are deliberately absent. This collector does not
# look for ISO or IEC designations, and the merge only rewrites columns the
# collected file actually carries — so leaving it out means the master keeps
# whatever it already holds, rather than having this run assert "none found"
# about a question it never asked.
COLUMNS = [
    "Tender ID", "GeM Bid Id", "Product Family", "IS Numbers Cited",
    "Count", "Outdated Citations", "Any Outdated",
    "Unmatched Citations", "Usability",
    "OCR Pages", "OCR Characters", "OCR Dropped",
]

# Its own class, deliberately. Every figure on the console carries its
# denominator, and a citation a model recognised from a photograph is weaker
# evidence than one read from a text layer. Nothing that filters on "Usable"
# picks these up by accident; the screens that should count them name them.
OCR_USABILITY = "Read by OCR"

# Below this, recognition returned a page number and a smudge. Calling that
# "read" would put a document in the readable population on the strength of
# twelve characters, and every denominator on the console would quietly absorb
# it. Measured against the pilot: a real specification page yields thousands.
MIN_OCR_CHARS = 200


# One listing of the attachment directory, indexed by bid.
#
# This was a glob per document. 3,659 documents against a directory holding
# 28,792 files is 105 million path comparisons before a single page is read,
# and the run sat at 100% CPU in the parent process with no worker ever
# starting. The directory is read once.
_INDEX: dict[int, list[str]] | None = None


def _index() -> dict[int, list[str]]:
    global _INDEX
    if _INDEX is None:
        _INDEX = {}
        for name in sorted(os.listdir(PDF_DIR)):
            if not name.endswith(".pdf") or name.endswith("-bid.pdf"):
                continue
            head = name.split("-", 1)[0]
            if head.isdigit():
                _INDEX.setdefault(int(head), []).append(os.path.join(PDF_DIR, name))
    return _INDEX


def _paths(bid: float) -> list[str]:
    return _index().get(int(bid), [])


def _work(job):
    """One document, in a worker process. Returns a plain dict — CGImages and
    Vision handlers never cross the process boundary."""
    tender_id, bid = job
    text, pages, chars = "", 0, 0
    for path in _paths(bid):
        try:
            got, n = ocr.ocr_pdf(path)
        except Exception:                                    # noqa: BLE001
            continue
        text += "\n" + got
        pages += n
    chars = len(text.strip())
    return {"Tender ID": tender_id, "GeM Bid Id": bid,
            "text": text, "OCR Pages": pages, "OCR Characters": chars}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="stop after N documents")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) // 2))
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    if not ocr.available():
        print("macOS Vision is not available on this machine — nothing to do.")
        return 1

    conn = sqlite3.connect(DB)
    held = ocr.register_bases(conn)
    rows = conn.execute(
        'SELECT "Tender ID", "GeM Bid Id" FROM tenders '
        'WHERE "Usability" != ? AND "GeM Bid Id" IS NOT NULL '
        'ORDER BY "Tender ID"', ("Usable",)
    ).fetchall()
    conn.close()

    done: set[str] = set()
    if os.path.exists(args.out):
        done = set(pd.read_csv(args.out, encoding="utf-8-sig")["Tender ID"].astype(str))

    jobs = [(t, b) for t, b in rows if str(t) not in done and _paths(b)]
    if args.limit:
        jobs = jobs[: args.limit]
    print(f"{len(rows)} documents not extractable · {len(done)} already read · "
          f"{len(jobs)} to read · {args.workers} workers", flush=True)
    if not jobs:
        return 0

    # One classifier. The GeM collector already derives family, outdated and
    # unmatched from the register; importing it is the rule, and writing a
    # second copy here is how the two-numbers-for-one-fact bugs start.
    from collect_gem_tenders import classify, register

    reg, _ = register()
    out: list[dict] = []
    started = time.time()
    ctx = mp.get_context("spawn")           # Vision and fork() do not mix
    with ctx.Pool(args.workers) as pool:
        for i, got in enumerate(pool.imap_unordered(_work, jobs, chunksize=1), 1):
            kept, dropped = ocr.citations_from_scan(got.pop("text"), held)
            family, outdated, unmatched = classify(kept, reg)
            out.append({
                **got,
                "Product Family": family,
                "IS Numbers Cited": "; ".join(kept),
                "Count": len(kept),
                "Outdated Citations": "; ".join(outdated),
                # The same meaning it has everywhere else: what the register
                # said when this row was written. `unmatched` is empty by
                # construction — a designation the register cannot confirm was
                # dropped before it got here, so OCR can never put a standard
                # into the coverage backlog.
                "Any Outdated": ("Yes" if outdated else "No") if kept else "Not checked",
                "Unmatched Citations": "; ".join(unmatched),
                # Document Type is not written either. The corpus already
                # records whether each of these is a Scanned PDF, a Text PDF
                # with an empty layer, or Other, and that was determined by
                # looking at the file. This run only establishes that Vision
                # could read it, which is a different question.
                # The class describes how the text was obtained, not whether it
                # happened to cite anything — which is exactly what this column
                # has always meant. A scan that was read and cites nothing is
                # directly comparable to a text PDF that cites nothing; a scan
                # that could not be read at all is not, and keeps its old class.
                "Usability": (OCR_USABILITY if got["OCR Characters"] >= MIN_OCR_CHARS
                              else "Not extractable"),
                "OCR Dropped": "; ".join(dropped),
            })
            if i % 25 == 0 or i == len(jobs):
                pd.DataFrame(out, columns=COLUMNS).to_csv(
                    args.out, index=False, mode="a" if done else "w",
                    header=not done, encoding="utf-8-sig")
                done |= {str(r["Tender ID"]) for r in out}
                out = []
                rate = i / (time.time() - started)
                print(f"  {i}/{len(jobs)} · {rate:.1f} docs/s · "
                      f"{(len(jobs) - i) / max(rate, 1e-6) / 60:.0f} min left", flush=True)

    read = pd.read_csv(args.out, encoding="utf-8-sig")
    recovered = int((read["Count"] > 0).sum())
    print(f"\n{len(read)} scans read · {recovered} yielded a citation the register confirms · "
          f"{int(read['Count'].sum())} citations kept · "
          f"{sum(len(str(d).split(';')) for d in read['OCR Dropped'].fillna('') if str(d).strip())} dropped as unconfirmable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
