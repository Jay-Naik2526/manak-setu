"""Do government buyers copy their specifications — and their dead citations?

The health index says 422 machine-readable documents cite a standard BIS has
withdrawn. It cannot say *why*, and the answer changes what the Department of
Consumer Affairs would do about it. If 422 buyers each made an independent
mistake, the remedy is 422 conversations. If most of them pasted the same
specification from the same template, one circular aimed at that template fixes
them all.

So this measures text reuse directly. Each document's specification text is cut
into 5-word shingles, reduced to a 128-permutation MinHash signature, and
banded into an LSH index; pairs that collide in any band are compared exactly
and kept when their Jaccard similarity reaches the threshold. Clusters are the
connected components of that graph.

MinHash rather than exact comparison because 1,172 documents is 686,000 pairs,
and rather than a new dependency because it is forty lines of numpy.

Every figure is a count over the documents whose text could be read. A cluster
is evidence that two documents share wording — not proof that one was copied
from the other, and the output says so.

    python tender_lineage.py            # report
    python tender_lineage.py --write    # also write data/tender_lineage.json
"""

import argparse
import collections
import datetime
import glob
import json
import os
import re
import sqlite3

import numpy as np

DB = "manak_setu.db"
PDF_DIR = os.path.join("data", "tenders", "gem")
OUT = "data/tender_lineage.json"

SHINGLE = 5
PERMS = 128
BANDS = 32               # 32 bands of 4 rows: catches pairs from about 0.6 up
ROWS = PERMS // BANDS
JACCARD_MIN = 0.80
MIN_SHINGLES = 40        # below this a document is too short to compare
PRIME = (1 << 61) - 1
SEED = 17

_WORD = re.compile(r"[a-z0-9]+")


def shingles(text: str) -> set[int]:
    """5-word shingles, hashed. Words only, lowercased: a specification copied
    with different spacing or capitalisation is still the same specification."""
    words = _WORD.findall(text.lower())
    if len(words) < SHINGLE:
        return set()
    return {
        hash(" ".join(words[i:i + SHINGLE])) & 0xFFFFFFFF
        for i in range(len(words) - SHINGLE + 1)
    }


def signature(shingle_set: set[int], a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """One MinHash signature: the smallest value of each hash permutation."""
    values = np.fromiter(shingle_set, dtype=np.int64, count=len(shingle_set))
    # (a*x + b) mod prime, for all 128 permutations at once.
    hashed = (np.outer(a, values) + b[:, None]) % PRIME
    return hashed.min(axis=1)


def cluster(signatures: dict[str, np.ndarray], sets: dict[str, set[int]],
            threshold: float = JACCARD_MIN) -> list[list[str]]:
    """LSH candidates, verified exactly, then connected components."""
    buckets: dict[tuple, list[str]] = collections.defaultdict(list)
    for doc, sig in signatures.items():
        for band in range(BANDS):
            key = (band, tuple(sig[band * ROWS:(band + 1) * ROWS].tolist()))
            buckets[key].append(doc)

    # A band collision is a candidate, not a match. Every candidate pair is
    # checked against the real Jaccard before it is believed.
    parent = {doc: doc for doc in signatures}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    checked: set[tuple] = set()
    for members in buckets.values():
        if len(members) < 2 or len(members) > 200:
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pair = (members[i], members[j]) if members[i] < members[j] else (members[j], members[i])
                if pair in checked:
                    continue
                checked.add(pair)
                a, b = sets[pair[0]], sets[pair[1]]
                inter = len(a & b)
                if inter and inter / len(a | b) >= threshold:
                    union(*pair)

    groups: dict[str, list[str]] = collections.defaultdict(list)
    for doc in signatures:
        groups[find(doc)].append(doc)
    return [sorted(g) for g in groups.values() if len(g) > 1]


def read_documents(limit: int = 0) -> tuple[dict[str, set[int]], dict[str, dict]]:
    import pdfplumber

    from engine import MAX_PAGES

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            'SELECT "Tender ID", "GeM Bid Id", "IS Numbers Cited", "Ministry" '
            'FROM tenders WHERE "Usability" = ?', ("Usable",)
        ).fetchall()
    finally:
        conn.close()

    sets: dict[str, set[int]] = {}
    meta: dict[str, dict] = {}
    read = 0
    for r in rows:
        bid = r["GeM Bid Id"]
        if bid is None or str(bid).lower() == "nan":
            continue
        paths = [p for p in sorted(glob.glob(os.path.join(PDF_DIR, f"{int(float(bid))}-*.pdf")))
                 if not p.endswith("-bid.pdf")]
        if not paths:
            continue
        text = ""
        for path in paths:
            try:
                with pdfplumber.open(path) as pdf:
                    text += "\n".join((pg.extract_text() or "") for pg in pdf.pages[:MAX_PAGES])
            except Exception:                                # noqa: BLE001
                continue
        s = shingles(text)
        read += 1
        if read % 150 == 0:
            print(f"  {read} documents read", flush=True)
        if len(s) < MIN_SHINGLES:
            continue
        key = str(r["Tender ID"])
        sets[key] = s
        meta[key] = {
            "cited": [c.strip() for c in str(r["IS Numbers Cited"] or "").split(";") if c.strip()],
            "ministry": str(r["Ministry"] or ""),
        }
        if limit and len(sets) >= limit:
            break
    print(f"read {read} documents; {len(sets)} long enough to compare")
    return sets, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    sets, meta = read_documents(args.limit)
    if len(sets) < 2:
        raise SystemExit("not enough readable documents to compare")

    rng = np.random.default_rng(SEED)
    a = rng.integers(1, PRIME, size=PERMS, dtype=np.int64)
    b = rng.integers(0, PRIME, size=PERMS, dtype=np.int64)
    signatures = {doc: signature(s, a, b) for doc, s in sets.items()}

    # Reading the documents is the expensive part, so every threshold worth
    # asking about is answered from the same read. 0.8 is near-identical
    # documents; 0.5 is documents that share half their wording, which is what
    # a shared section inside otherwise different tenders looks like.
    print(f"\ntext reuse across {len(sets)} documents:")
    sweep = []
    for t in (0.8, 0.65, 0.5, 0.35):
        gs = cluster(signatures, sets, t)
        covered = len({d for g in gs for d in g})
        sweep.append({"jaccard": t, "clusters": len(gs), "documents_in_a_cluster": covered})
        print(f"  Jaccard >= {t:.2f}   {len(gs):>3} clusters   "
              f"{covered:>4} of {len(sets)} documents ({covered / len(sets):.1%})")

    groups = cluster(signatures, sets, JACCARD_MIN)
    in_cluster = {doc for g in groups for doc in g}

    # Which dead standards travel with a template.
    conn = sqlite3.connect(DB)
    try:
        dead = {str(r[0]).strip().upper() for r in conn.execute(
            'SELECT "IS Base" FROM standards WHERE "Status" IN ("Withdrawn","Superseded")') if r[0]}
        current = {str(r[0]).strip().upper() for r in conn.execute(
            'SELECT "IS Base" FROM standards WHERE "Status" = "Current"') if r[0]}
    finally:
        conn.close()
    dead -= current

    base = lambda c: re.sub(r"\s+", " ", str(c).split("(")[0].split(":")[0]).strip().upper()
    where = {doc: i for i, g in enumerate(groups) for doc in g}
    by_standard: dict[str, dict] = {}
    for doc, m in meta.items():
        for c in {base(x) for x in m["cited"]}:
            if c not in dead:
                continue
            e = by_standard.setdefault(c, {"documents": 0, "in_clusters": collections.Counter()})
            e["documents"] += 1
            if doc in where:
                e["in_clusters"][where[doc]] += 1

    findings = []
    for number, e in by_standard.items():
        if not e["in_clusters"]:
            continue
        biggest, shared = e["in_clusters"].most_common(1)[0]
        if shared < 2:
            continue
        findings.append({
            "is_number": number, "documents": e["documents"],
            "sharing_one_template": shared,
            "cluster_size": len(groups[biggest]),
        })
    findings.sort(key=lambda f: (-f["sharing_one_template"], -f["documents"]))

    print("\ndead standards that travel with a shared specification:")
    if not findings:
        print("  none — the documents citing dead standards do not share text")
    for f in findings[:10]:
        print(f"  {f['is_number']:<16} cited in {f['documents']:>3} documents · "
              f"{f['sharing_one_template']} of them share one specification")

    payload = {
        "generated": datetime.date.today().isoformat(),
        "documents_compared": len(sets),
        "clusters": len(groups),
        "documents_in_a_cluster": len(in_cluster),
        "jaccard_threshold": JACCARD_MIN,
        "threshold_sweep": sweep,
        "shingle_words": SHINGLE,
        "findings": findings[:20],
        "note": (
            "Shared wording between two tender documents, measured on 5-word "
            "shingles with a 128-permutation MinHash and verified exactly at "
            f"Jaccard >= {JACCARD_MIN}. A cluster is evidence that documents share "
            "specification text, not proof that one was copied from another, and "
            "counts are over the documents whose text could be read."
        ),
    }
    if args.write:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
