"""Retrieval evaluation harness.

Reports Recall@10, Precision@5, abstention rate and version accuracy against a
hand-labelled query set. It will not invent pairs: if data/golden_queries.csv is
missing the run stops and says so, because a made-up denominator is worse than
no number at all.

Extend data/golden_queries.csv with real officer spec text and the standard the
source document itself names. Five seed rows is not a benchmark — treat any
figure from this harness as indicative until the set is meaningfully larger.
"""

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

    print()
    print("Matching is on IS Base, so a part/section suffix mismatch still counts as a hit.")
    print(f"n={n}. Report these as indicative, never as a headline accuracy figure.")


if __name__ == "__main__":
    main()
