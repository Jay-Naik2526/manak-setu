"""Collect real tender specifications from GeM, the Government e-Marketplace.

Every bid published on GeM has a public bid document at

    https://bidplus.gem.gov.in/showbidDocument/<bid id>

The bid form itself rarely cites a standard — it is a bilingual cover sheet.
But it carries link annotations to its attachments: the buyer's specification
documents, technical-compliance sheets and BOQs, hosted on gem.gov.in. Those are
where the IS numbers are written. So the collector reads the bid PDF for its
links, fetches the attachments that are PDFs, and extracts the citations that
are literally present in them. Nothing is inferred.

Bid ids are sequential integers, so the corpus can be sampled honestly across
time rather than cherry-picked around products we already know. A bid with no
specification attachments (most service bids) is skipped and counted; a bid
whose attachments are scans is kept as "Not extractable" so it is never
mistaken for a tender that cites nothing.

Writes data/tender_collected_gem.csv in the same schema as tender_dataset.csv.
Merging into the corpus is a separate, reviewed step: merge_gem_tenders.py.
The PDFs are kept under data/tenders/gem/ for re-extraction and are not
committed — they are public documents, but the repo carries citations and
source links, not copies.

    python collect_gem_tenders.py --sample 80                 # yield probe
    python collect_gem_tenders.py --sample 1500 --seed 3      # a real sweep
    python collect_gem_tenders.py --ids 6713228 9569038       # specific bids
"""

import argparse
import collections
import concurrent.futures
import io
import json
import os
import random
import re
import sqlite3
import time
import urllib.error
import urllib.request

import pandas as pd
from pypdf import PdfReader

from engine import extract_document

BID_URL = "https://bidplus.gem.gov.in/showbidDocument/{}"
OUT = "data/tender_collected_gem.csv"
PDF_DIR = "data/tenders/gem"
PROGRESS = "data/tender_collected_gem.progress.jsonl"
DB = "manak_setu.db"

# Observed live range: ids below ~6.7M are 2023 and earlier; ids above ~9.75M
# do not exist yet. Sampling across this span spreads the corpus over 2024-2026.
ID_LOW, ID_HIGH = 6_700_000, 9_750_000

DELAY_SECONDS = 0.5
WORKERS = int(os.getenv("MANAK_GEM_WORKERS", "4"))   # concurrent bids; each still pauses between its own requests
TIMEOUT = 45
MAX_ATTACHMENTS = 8
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36 "
                    "(MANAK-SETU SIH26108 research prototype)"}

# Attachment routes that carry documents. Catalogue pages, SLA forms, PVC
# certificates and the bid's own download stub are not specifications.
ATTACHMENT_RE = re.compile(
    r"https://(?:mkp|bidplus)\.gem\.gov\.in/"
    r"(?:catalog_data/catalog_support_document/|bidding/bid/documentdownload/|resources/upload_nas/)"
    r"\S+", re.I,
)
BID_NUMBER_RE = re.compile(r"\bGEM/20\d\d/B/\d{6,8}\b")
CATEGORY_RE = re.compile(r"Item Category\s*/\s*(.{0,220}?)(?:\s+(?:Consignee|Bid |Total Quantity|Minimum Average|OEM|MSE|Estimated|Evaluation|Item\s|Quantity)|\n{2,}|$)", re.S)
# The bid form is bilingual and its Hindi font leaves glyph ids in the text
# layer: "Item Category/मद (cid:18)(cid:18) testing weather proof PVC…". Those,
# and the Devanagari itself, are stripped so only the English line remains.
CID_RE = re.compile(r"\(cid:\d+\)|[\u0900-\u097F]+")
# Service bids carry scopes of work, not product specifications; their
# attachments were read and never cited a standard. The category names the kind.
SERVICE_RE = re.compile(r"\b(service|services|hiring|manpower|consultanc|outsourc|AMC|annual maintenance|"
                        r"repair|housekeeping|security guard|catering|transport|custom bid for services|"
                        r"leasing|rental|printing|training|survey|audit)\b", re.I)
FOREIGN_RE = re.compile(r"\b(?:IEC|ISO|ASTM|BS\s?EN|BS|DIN|EN|IEEE|ANSI)\s*[:\-]?\s*\d{2,6}(?:[-\s]?\d+)?\b")


def fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def attachment_links(pdf_bytes: bytes) -> list[str]:
    """URLs the bid document links to. These live in annotations, not text."""
    links: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception:                                    # noqa: BLE001
        return links
    for page in reader.pages:
        for annot in page.get("/Annots") or []:
            try:
                action = annot.get_object().get("/A") or {}
                uri = str(action.get("/URI") or "")
            except Exception:                            # noqa: BLE001
                continue
            if ATTACHMENT_RE.match(uri) and uri not in links:
                links.append(uri)
    return links[:MAX_ATTACHMENTS]


def register() -> tuple[dict[str, dict], dict[str, str]]:
    """Status and family by IS base number, for Outdated / Unmatched columns."""
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute('SELECT "IS Base", "Status", "Product Family" FROM standards').fetchall()
    finally:
        conn.close()
    by_base = {}
    for base, status, family in rows:
        by_base.setdefault(str(base).strip().upper(), {"status": status, "family": family})
    return by_base, {}


def base_of(citation: str) -> str:
    return re.sub(r"\s+", " ", citation.split("(")[0].split(":")[0]).strip().upper()


def classify(citations: list[str], reg: dict[str, dict]) -> tuple[str, list[str], list[str]]:
    """Family by majority of resolved citations; outdated and unmatched lists.
    Derived from the register, never guessed from the document's wording."""
    families = collections.Counter()
    outdated, unmatched = [], []
    for c in citations:
        hit = reg.get(base_of(c))
        if not hit:
            unmatched.append(c)
            continue
        if hit["family"]:
            families[hit["family"]] += 1
        if hit["status"] in ("Withdrawn", "Superseded"):
            outdated.append(f"{c} ({hit['status']})")
    family = families.most_common(1)[0][0] if families else "Unclassified"
    return family, outdated, unmatched


def collect_bid(bid: int, reg: dict[str, dict]) -> dict | None:
    """One bid → one row, or None with a reason in the progress log."""
    pdf = fetch(BID_URL.format(bid))
    if not pdf or not pdf.startswith(b"%PDF-"):
        return {"bid": bid, "outcome": "no bid document"}
    links = attachment_links(pdf)
    if not links:
        return {"bid": bid, "outcome": "no specification attachments"}

    bid_text = extract_document(pdf, f"{bid}.pdf").get("text", "")
    number = (BID_NUMBER_RE.search(bid_text) or [None])[0] if BID_NUMBER_RE.search(bid_text) else f"GEM-bid-{bid}"
    category = ""
    m = CATEGORY_RE.search(CID_RE.sub(" ", bid_text))
    if m:
        category = re.sub(r"\s+", " ", m.group(1))
        # The line runs on into the bid's quantity block and GeM's "Custom" tag.
        category = re.split(r"\s*,?\s*\bCustom\b|\s*Total\s+\d", category, maxsplit=1)[0]
        category = category.strip(" :/-,")[:120]
    if category and SERVICE_RE.search(category):
        return {"bid": bid, "outcome": "service bid", "category": category}

    citations: list[str] = []
    foreign: list[str] = []
    scanned_docs, text_docs, source = 0, 0, ""
    os.makedirs(PDF_DIR, exist_ok=True)
    for i, url in enumerate(links):
        time.sleep(DELAY_SECONDS)
        doc = fetch(url)
        if not doc or not doc.startswith(b"%PDF-"):
            continue
        try:
            r = extract_document(doc, os.path.basename(url))
        except Exception:                                # noqa: BLE001
            continue
        with open(os.path.join(PDF_DIR, f"{bid}-{i}.pdf"), "wb") as fh:
            fh.write(doc)
        if r.get("scanned"):
            scanned_docs += 1
            continue
        text_docs += 1
        found = r.get("citations") or []
        if found and not source:
            source = url
        for c in found:
            if c not in citations:
                citations.append(c)
        for f in FOREIGN_RE.findall(r.get("text", "")):
            f = re.sub(r"\s+", " ", f).strip()
            if f not in foreign:
                foreign.append(f)

    if not text_docs and not scanned_docs:
        return {"bid": bid, "outcome": "attachments not fetchable"}
    if not citations:
        if scanned_docs and not text_docs:
            usability, doc_type = "Not extractable", "Scanned PDF"
        else:
            return {"bid": bid, "outcome": "specification cites no IS", "category": category}
    else:
        usability, doc_type = "Usable", "Text PDF"

    family, outdated, unmatched = classify(citations, reg)
    return {
        "bid": bid,
        "outcome": usability,
        "row": {
            "Tender ID": number,
            "Product Family": family,
            "IS Numbers Cited": "; ".join(citations),
            "Foreign Standards Cited": "; ".join(foreign[:12]),
            "Count": len(citations),
            "Outdated Citations": "; ".join(outdated),
            "Any Outdated": ("Yes" if outdated else "No") if citations else "Not checked",
            "Document Type": doc_type,
            "Usability": usability,
            "Source Link": source or links[0],
            "Unmatched Citations": "; ".join(unmatched),
            "Item Category": category,
            "GeM Bid Id": bid,
            "Attachments Read": text_docs + scanned_docs,
        },
    }


def done_ids() -> set[int]:
    if not os.path.exists(PROGRESS):
        return set()
    with open(PROGRESS, encoding="utf-8") as fh:
        return {json.loads(line)["bid"] for line in fh if line.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="how many bid ids to sample")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ids", type=int, nargs="*", help="specific bid ids")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    ids = list(args.ids or [])
    if args.sample:
        ids += rng.sample(range(ID_LOW, ID_HIGH), args.sample)
    skip = done_ids()
    ids = [i for i in ids if i not in skip]
    if not ids:
        raise SystemExit("nothing to do — every requested id is already in the progress log")

    reg, _ = register()
    rows = []
    if os.path.exists(OUT):
        rows = pd.read_csv(OUT, encoding="utf-8-sig").to_dict("records")
    outcomes = collections.Counter()
    print(f"{len(ids)} bids to read · {len(rows)} rows already collected · {len(skip)} ids already tried")

    def work(bid):
        try:
            return collect_bid(bid, reg) or {"bid": bid, "outcome": "error"}
        except Exception as exc:                          # noqa: BLE001
            return {"bid": bid, "outcome": f"error: {type(exc).__name__}"}

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS)
    for n, result in enumerate(pool.map(work, ids), 1):
        outcomes[result["outcome"]] += 1
        with open(PROGRESS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({k: v for k, v in result.items() if k != "row"}) + "\n")
        if "row" in result:
            rows.append(result["row"])
            pd.DataFrame(rows).to_csv(OUT, index=False)
            r = result["row"]
            print(f"  [{n}/{len(ids)}] {result['bid']}  {r['Usability']:<16} {r['Count']:>2} IS  "
                  f"{r['Product Family'][:28]:<30} {r['Item Category'][:40]}", flush=True)
        else:
            print(f"  [{n}/{len(ids)}] {result['bid']}  · {result['outcome']}", flush=True)
    pool.shutdown()

    print("\noutcomes:")
    for k, v in outcomes.most_common():
        print(f"  {v:>5}  {k}")
    usable = sum(1 for r in rows if r.get("Usability") == "Usable")
    print(f"\n{len(rows)} rows in {OUT} · {usable} usable · "
          f"{sum(int(r.get('Count') or 0) for r in rows)} citations in total")


if __name__ == "__main__":
    main()
