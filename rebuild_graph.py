"""Rebuild the co-citation graph from tender_dataset.csv.

The existing graph was computed over the 134 `Usability = Usable` tenders only.
The project specification computes it over every tender that contains citations
(161 documents), which is why the spec quotes ~3,718 edges and the shipped file
holds 376. Same source data, wider base.

Nothing here is generated: every edge is a count of two IS numbers appearing in
the same real tender document. Writes a new file and leaves the original alone.
"""

import itertools
from collections import Counter

import pandas as pd

SRC = "data/tender_dataset.csv"
OUT = "data/co_citation_graph_full.csv"

# Specification thresholds (section 5.3).
MIN_CO_CITATIONS = 5
MIN_CONFIDENCE = 0.40
MIN_SOURCE_TENDERS = 8


def citation_sets(df: pd.DataFrame) -> list[set[str]]:
    sets = []
    for value in df["IS Numbers Cited"].dropna():
        cited = {c.strip() for c in str(value).split(";") if c.strip()}
        if cited:
            sets.append(cited)
    return sets


def main():
    tenders = pd.read_csv(SRC, encoding="utf-8-sig")
    sets = citation_sets(tenders)
    print(f"{len(tenders)} tender rows · {len(sets)} contain citations")

    source_count: Counter = Counter()
    pair_count: Counter = Counter()
    for cited in sets:
        for is_number in cited:
            source_count[is_number] += 1
        for a, b in itertools.permutations(sorted(cited), 2):
            pair_count[(a, b)] += 1

    total = len(sets)
    rows = []
    for (source, target), co in pair_count.items():
        src_n = source_count[source]
        if co < MIN_CO_CITATIONS or src_n < MIN_SOURCE_TENDERS:
            continue
        confidence = co / src_n
        if confidence < MIN_CONFIDENCE:
            continue
        tgt_n = source_count[target]
        # lift > 1 means the pair co-occurs more than independent citation implies
        lift = (co / total) / ((src_n / total) * (tgt_n / total)) if tgt_n else 0.0
        rows.append(
            {
                "Source IS": source,
                "Target IS": target,
                "Tenders Citing Source": src_n,
                "Tenders Citing Target": tgt_n,
                "Co-citation Count": co,
                "Confidence": round(confidence, 3),
                "Lift": round(lift, 3),
                "Evidence Statement": (
                    f"Cited alongside {source} in {co} of {src_n} comparable tenders"
                ),
            }
        )

    out = pd.DataFrame(rows).sort_values(
        ["Confidence", "Co-citation Count"], ascending=False
    )
    out.to_csv(OUT, index=False)

    nodes = set(out["Source IS"]) | set(out["Target IS"])
    print(f"\nthresholds: {MIN_CO_CITATIONS}+ co-citations, "
          f"{MIN_CONFIDENCE:.0%}+ confidence, source cited in {MIN_SOURCE_TENDERS}+ tenders")
    print(f"wrote {OUT}")
    print(f"  edges {len(out)}   nodes {len(nodes)}")
    print(f"  (previous file: 376 edges, 74 nodes)")
    print("\nstrongest relationships:")
    for _, r in out.head(8).iterrows():
        print(f"  {r['Source IS']:<22} -> {r['Target IS']:<22} "
              f"{r['Co-citation Count']:>3} of {r['Tenders Citing Source']:<3} "
              f"({r['Confidence']:.3f})")


if __name__ == "__main__":
    main()
