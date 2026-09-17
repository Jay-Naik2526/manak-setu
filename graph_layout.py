"""Compute the co-citation graph's layout once, on the server.

The browser used to do this: 110 animation frames, two physics passes each, over
319 mutually repelling nodes, repainting thousands of SVG elements every frame.
That is a quarter of a million DOM attribute writes to produce a picture that
never changes — the graph is rebuilt only when `rebuild_graph.py` runs, so the
layout is a property of the data, not of the session.

Computing it here makes the page's job trivial: read coordinates, draw once.
It also makes the picture *stable*. The old layout depended on how many frames
the browser happened to complete before the user navigated away, so the same
graph looked different on every visit and screenshots never matched.

The layout is spectral — the eigenvectors of the graph Laplacian — because a
force model collapses on a graph this dense. It is deterministic, so the same
edges always produce the same picture.

    python graph_layout.py            # write data/graph_layout.json
    python graph_layout.py --stats    # report spread without writing
"""

import argparse
import json
import sqlite3

import numpy as np

DB = "manak_setu.db"
OUT = "data/graph_layout.json"

# The canvas the client draws into, and the margin nodes may not cross. Both
# match the constants in app.js; a node outside these bounds is invisible.
WIDTH, HEIGHT, PAD = 1040, 660, 26

SEED = 7
# Passes of the overlap-separation step, and how hard it pushes.
#
# These were tuned for 319 nodes. At 1,858 the same settings left the median
# node 11 px from its nearest neighbour, which is less than two node radii —
# the picture read as a smear rather than a set of points. Raising the
# neighbourhood these three values define lifts that to 15.9 px.
#
# Pushing harder than this makes it worse, not better, which is why the numbers
# stop here: at close=1.30 the median gap falls back to 15.1 and the count of
# pairs closer than 4 px rises from 22 to 336, because strong repulsion packs a
# dense rim against the frame. Measured, not guessed — `--stats` prints both.
SEPARATION_STEPS = 120
SEPARATION_RADIUS = 0.90     # multiples of k, the ideal node spacing
SEPARATION_PUSH = 0.08


def _edges(conn) -> list[tuple[str, str, float]]:
    return [
        (r[0], r[1], float(r[2] or 0))
        for r in conn.execute(
            'SELECT "Source IS", "Target IS", "Confidence" FROM co_citation'
        )
    ]


def compute(edges: list[tuple[str, str, float]]) -> dict[str, list[float]]:
    """Spectral layout, then a short repulsion pass to separate overlaps.

    A force layout was tried first and collapsed twice: 90% of the register in a
    forty-pixel band, then a fifteen-pixel one. That is not a tuning failure, it
    is what spring models do to a dense graph. This one averages 31 edges per
    node and its core is nearly complete, so every node is pulled toward every
    other and the equilibrium really is a ball.

    Spectral layout does not have that failure mode. The eigenvectors of the
    graph Laplacian place a node according to the *structure* of its
    connections rather than the sum of forces on it, so groups that are more
    connected internally than externally separate — and they separate because
    of the co-citation evidence, not because anything here grouped them.
    Product family is never consulted; that the clusters come out looking like
    BIS departments is a finding, not an arrangement.

    The second and third eigenvectors of the normalised Laplacian are the
    coordinates (the first is constant and carries no information).
    """
    ids = sorted({e[0] for e in edges} | {e[1] for e in edges})
    if not ids:
        return {}
    index = {node: i for i, node in enumerate(ids)}
    n = len(ids)
    if n < 3:
        return {node: [WIDTH / 2, HEIGHT / 2] for node in ids}

    # Weighted adjacency. Co-citation count is the evidence — how many real
    # tenders cited the pair together — so it is what decides closeness.
    adj = np.zeros((n, n))
    for a, b, weight in edges:
        i, j = index[a], index[b]
        adj[i, j] = adj[j, i] = max(adj[i, j], weight)

    degree = adj.sum(axis=1)
    inv_sqrt = 1.0 / np.sqrt(np.maximum(degree, 1e-9))
    laplacian = np.eye(n) - (adj * inv_sqrt[:, None]) * inv_sqrt[None, :]
    values, vectors = np.linalg.eigh(laplacian)
    order = np.argsort(values)
    pos = np.stack([vectors[:, order[1]], vectors[:, order[2]]], axis=1)
    pos = pos * inv_sqrt[:, None]               # undo the normalisation's skew

    # Spectral coordinates are extremely uneven — a few structurally distinct
    # nodes sit far out while the core bunches. Ranking each axis and spreading
    # by rank keeps the *ordering* the eigenvectors found while giving every
    # node room, which is what makes the picture readable.
    for axis in (0, 1):
        ranks = np.empty(n)
        ranks[np.argsort(pos[:, axis])] = np.arange(n)
        pos[:, axis] = ranks / max(n - 1, 1) - 0.5

    rng = np.random.default_rng(SEED)
    pos += rng.normal(0, 0.006, pos.shape)      # break exact ties deterministically
    pos *= np.array([WIDTH - 2 * PAD, HEIGHT - 2 * PAD])

    # Short repulsion-only pass: rank-spreading guarantees room on each axis
    # separately but two nodes can still land on the same point. No attraction
    # here — the eigenvectors already decided who belongs near whom, and adding
    # springs back would reintroduce the collapse.
    k = np.sqrt(float(WIDTH * HEIGHT) / n)
    for step in range(SEPARATION_STEPS):
        delta = pos[:, None, :] - pos[None, :, :]
        dist = np.sqrt((delta ** 2).sum(-1))
        np.fill_diagonal(dist, np.inf)
        close = dist < k * SEPARATION_RADIUS
        if not close.any():
            break
        push = np.where(close[..., None], delta / np.maximum(dist, 1e-6)[..., None], 0.0)
        pos += push.sum(axis=1) * (k * SEPARATION_PUSH)

    lo, hi = pos.min(axis=0), pos.max(axis=0)
    span = np.maximum(hi - lo, 1e-6)
    pos = (pos - lo) / span
    pos[:, 0] = pos[:, 0] * (WIDTH - 2 * PAD) + PAD
    pos[:, 1] = pos[:, 1] * (HEIGHT - 2 * PAD) + PAD

    return {node: [round(float(pos[i, 0]), 1), round(float(pos[i, 1]), 1)]
            for node, i in index.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true", help="report without writing")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    try:
        edges = _edges(conn)
    finally:
        conn.close()
    layout = compute(edges)
    if not layout:
        raise SystemExit("co_citation is empty — run rebuild_graph.py first")

    xs = sorted(p[0] for p in layout.values())
    ys = sorted(p[1] for p in layout.values())

    def q(a, frac):
        return a[min(len(a) - 1, int(len(a) * frac))]

    print(f"{len(layout)} nodes from {len(edges)} edges")
    print(f"  x {xs[0]:6.1f} … {xs[-1]:6.1f}   (canvas 0 … {WIDTH})")
    print(f"  y {ys[0]:6.1f} … {ys[-1]:6.1f}   (canvas 0 … {HEIGHT})")
    # The range alone hides a collapse: a ball of nodes with two outliers spans
    # the whole canvas and still draws as a dot. The middle half is the number
    # that says whether the picture is readable.
    xiqr, yiqr = q(xs, 0.75) - q(xs, 0.25), q(ys, 0.75) - q(ys, 0.25)
    print(f"  middle half of nodes spans {xiqr:.0f} x {yiqr:.0f} px "
          f"({xiqr / WIDTH:.0%} x {yiqr / HEIGHT:.0%} of the canvas)")
    if xiqr < WIDTH * 0.15 or yiqr < HEIGHT * 0.15:
        print("  WARNING: the layout has collapsed — most nodes overlap")
    outside = sum(1 for p in layout.values()
                  if not (PAD <= p[0] <= WIDTH - PAD and PAD <= p[1] <= HEIGHT - PAD))
    print(f"  outside the frame: {outside}")

    # How far the typical node sits from its nearest neighbour. The IQR says the
    # cloud fills the frame; this says whether the points inside it are
    # distinguishable, which is the thing that actually reads as crowded.
    pts = np.array(list(layout.values()))
    gaps = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(gaps, np.inf)
    nearest = gaps.min(axis=1)
    print(f"  nearest neighbour: median {np.median(nearest):.1f} px · "
          f"{int((nearest < 4).sum())} pairs closer than 4 px")

    if args.stats:
        print("\n--stats — nothing written")
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(layout, fh, separators=(",", ":"), sort_keys=True)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
