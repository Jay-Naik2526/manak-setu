# Hugging Face Space — CPU, free tier (2 vCPU, 16 GB RAM).
#
# Everything the console needs except the language model: retrieval, the graph,
# the audit, all twelve languages. Ollama is not installed here — a free CPU
# Space cannot host a 7B model — so clauses come from the deterministic template
# and the interface says so, which is the behaviour the guards were written for.

FROM python:3.12-slim

# HF Spaces runs containers as uid 1000; anything the app writes must be owned
# by that user, including the model cache.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1

WORKDIR /app

# CPU-only torch: the full wheel is 1.2 GB and there is no GPU on this tier.
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

COPY --chown=user . /app
USER user

# Bake the encoders into the image so the first request is not a 175 MB download.
RUN python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('all-MiniLM-L6-v2'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); \
print('encoders cached')"

# Rebuild the database from the CSVs at build time: the CSVs are the source of
# truth, and this keeps the image honest even if a stale .db were committed.
RUN python load_db.py --allow-shrink && python -c "\
import os; print('db rows ok' if os.path.getsize('manak_setu.db') > 100000 else 'DB TOO SMALL')"

EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
