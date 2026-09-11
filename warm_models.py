"""Download the transformer weights during the build, not on the first query.

Both encoders are fetched lazily the first time retrieval runs. On a free-tier
host that puts a ~120 MB download inside the first user request, which either
times out or makes the first officer to open the site wait a minute for an
answer that normally takes under a second. Pulling them here moves that cost
into the build, where nobody is watching.

Only the cross-encoder is conditional: MANAK_LIGHT=1 skips it at runtime, so
there is no point spending build time or disk on it.
"""

import os

from sentence_transformers import CrossEncoder, SentenceTransformer

import retrieval

print(f"warming {retrieval.BI_ENCODER}")
SentenceTransformer(retrieval.BI_ENCODER)

if os.getenv("MANAK_LIGHT") == "1":
    print("MANAK_LIGHT=1 — skipping the cross-encoder, it is not loaded at runtime")
else:
    print(f"warming {retrieval.CROSS_ENCODER}")
    CrossEncoder(retrieval.CROSS_ENCODER)

print("model cache warm")
