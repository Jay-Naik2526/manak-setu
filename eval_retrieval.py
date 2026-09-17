"""Retrieval evaluation harness.

Reports Recall@10, Precision@5, abstention rate and version accuracy against a
hand-labelled query set. It will not invent pairs: if data/golden_queries.csv is
missing the run stops and says so, because a made-up denominator is worse than
no number at all.

Extend data/golden_queries.csv with real officer spec text and the standard the
source document itself names. Five seed rows is not a benchmark — treat any
figure from this harness as indicative until the set is meaningfully larger.
"""

import datetime as _dt
import json
import os
import sys

import pandas as pd

import retrieval

GOLDEN = "data/golden_queries.csv"
RECALL_AT = 10
PRECISION_AT = 5


def _base(is_number: str) -> str:
    """Canonical form for comparison: number only, no part, year or footnote.

    Labels taken from Quality Control Orders are written as BIS writes them —
    "IS 1554(Part 1) : 1988", "IS 5557: 2004", "IS 8828 *". Splitting on "(" alone
    left the year and the asterisk attached, so correct hits were scored as
    misses and the reported recall was lower than the truth."""
    import re as _re

    text = str(is_number).split("(")[0]
    text = _re.sub(r"[:\s]*(?:19|20)\d{2}\s*$", "", text)
    return _re.sub(r"[^0-9a-z ]", "", text.lower()).strip()


def main():
    import argparse

    ap = argparse.ArgumentParser()
    # A floor, not a target. CI should fail when retrieval gets worse than a
    # level we have already shown it can hold — it should never encourage
    # tuning toward a number, which is how an evaluation set gets gamed.
    ap.add_argument("--min-recall", type=float, default=None,
                    help=f"exit non-zero if Recall@{RECALL_AT} falls below this "
                         "fraction (e.g. 0.80). Omit to report only.")
    args = ap.parse_args()

    if not os.path.exists(GOLDEN):
        print(f"No golden set at {GOLDEN}.")
        print("Create it with columns: query,expected_is,source — then re-run.")
        sys.exit(1)

    df = pd.read_csv(GOLDEN, encoding="utf-8-sig")
    n = len(df)
    print(f"Golden set: {n} labelled quer{'y' if n == 1 else 'ies'} from {GOLDEN}\n")

    hits_at_k = 0
    prec_total = 0.0
    abstained = 0
    abstain_rows = []
    rows = []

    for _, row in df.iterrows():
        q, expected = str(row["query"]), str(row["expected_is"])
        res = retrieval.recommend(q)
        cands = res["candidates"]
        ranked = [c["is_number"] for c in cands]

        exact = expected in ranked
        loose = _base(expected) in [_base(c) for c in ranked]
        rank = next(
            (i + 1 for i, c in enumerate(ranked) if _base(c) == _base(expected)), None
        )

        if loose:
            hits_at_k += 1
        top5 = [_base(c) for c in ranked[:PRECISION_AT]]
        prec_total += top5.count(_base(expected)) / max(1, len(top5))

        if res["decision"] == "abstain":
            abstained += 1
            abstain_rows.append((q[:58], res["reason"], loose))

        rows.append(
            {
                "expected": expected,
                "rank": rank,
                "exact": exact,
                "decision": res["decision"],
                "top": ranked[0] if ranked else "—",
                "top_score": cands[0]["score"] if cands else 0.0,
            }
        )

    # Recall@1 is the question an officer actually asks: is the first answer the
    # right one? Recall@10 says the right answer was somewhere in the list, which
    # matters for the ranking but not for someone reading the top result.
    hits_at_1 = sum(1 for r in rows if r["rank"] == 1)
    print(f"Recall@1     : {hits_at_1}/{n}  ({hits_at_1 / n:.0%})   "
          f"— expected standard ranked first")

    # A single figure over a set this uneven hides which domains it was measured
    # on. The register covers many families; the evaluation set covers the ones
    # BIS names in a certification notification, and unevenly.
    if "family" in df.columns:
        by_family: dict[str, list[int]] = {}
        for row, (_, g) in zip(rows, df.iterrows()):
            fam = str(g.get("family") or "").strip()
            fam = (fam if fam and fam.lower() != "nan" else "QCO seed rows")[:44]
            by_family.setdefault(fam, []).append(1 if row["rank"] == 1 else 0)
        print("\n  rank-1 by product family (families with 8 or more queries):")
        for fam, hits in sorted(by_family.items(), key=lambda kv: -len(kv[1])):
            if len(hits) >= 8:
                print(f"    {sum(hits):>4}/{len(hits):<4} ({sum(hits)/len(hits):>4.0%})  {fam}")
    print(f"Recall@{RECALL_AT}    : {hits_at_k}/{n}  ({hits_at_k / n:.0%})   "
          f"— expected standard present in the reranked candidates")
    print(f"Precision@{PRECISION_AT}  : {prec_total / n:.3f}")
    print(f"Abstention  : {abstained}/{n}  ({abstained / n:.0%})")
    if abstain_rows:
        correct = sum(1 for _, _, found in abstain_rows if not found)
        print(f"              {correct} of {len(abstain_rows)} abstentions had no correct "
              f"answer available (a correct abstention)")
    print()

    print(f"{'expected':<26}{'rank':>5}{'top hit':>26}{'score':>8}  decision")
    print("-" * 76)
    for r in rows:
        print(f"{r['expected']:<26}{str(r['rank'] or '—'):>5}{r['top']:>26}"
              f"{r['top_score']:>8.3f}  {r['decision']}")

    # Calibration: does a score of 0.9 mean the same thing as a score of 0.5?
    # A confidence number is only worth showing if it predicts something, and
    # the honest way to say so is with the count it was measured on.
    buckets: dict[str, list[int]] = {}
    for r in rows:
        score = float(r["top_score"] or 0)
        lo = min(int(score * 10) / 10, 0.9)
        buckets.setdefault(f"{lo:.1f}", []).append(1 if r["rank"] == 1 else 0)

    print("\ncalibration — how often the top answer is right, by the score it was given:")
    calibration = []
    ece_num = 0.0
    for key in sorted(buckets):
        hits = buckets[key]
        lo = float(key)
        accuracy = sum(hits) / len(hits)
        midpoint = lo + 0.05
        ece_num += len(hits) * abs(accuracy - midpoint)
        calibration.append({"from": round(lo, 2), "to": round(lo + 0.1, 2),
                            "queries": len(hits), "correct": sum(hits),
                            "accuracy": round(accuracy, 3)})
        bar = "#" * round(accuracy * 24)
        print(f"  {lo:.1f}-{lo + 0.1:.1f}  {sum(hits):>4}/{len(hits):<4} "
              f"({accuracy:>5.0%})  {bar}")
    ece = ece_num / max(n, 1)
    print(f"  expected calibration error: {ece:.3f}  "
          f"(mean gap between a bucket's score and how often it was right)")

    rank1 = sum(1 for r in rows if r["rank"] == 1)
    with open("data/calibration.json", "w", encoding="utf-8") as fh:
        json.dump({"generated": _dt.date.today().isoformat(), "queries": n,
                   "rank_1": rank1, "recall_at": RECALL_AT, "recall_hits": hits_at_k,
                   "abstained": abstained,
                   "buckets": calibration, "expected_calibration_error": round(ece, 4),
                   "note": ("Measured on the golden set: for each query, the score the top "
                            "candidate received and whether it was the expected standard. "
                            "A bucket's accuracy is over the queries that landed in it.")},
                  fh, indent=1)
    print("  wrote data/calibration.json")

    print()
    print("Matching is on IS Base, so a part/section suffix mismatch still counts as a hit.")
    print(f"n={n}. Report these as indicative, never as a headline accuracy figure.")

    if args.min_recall is not None:
        actual = hits_at_k / n if n else 0.0
        held = actual >= args.min_recall
        print(f"\nfloor: Recall@{RECALL_AT} {actual:.3f} against a floor of "
              f"{args.min_recall:.3f} — {'held' if held else 'BREACHED'}")
        if not held:
            sys.exit(1)


if __name__ == "__main__":
    main()
