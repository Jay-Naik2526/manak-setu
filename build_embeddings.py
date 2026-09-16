import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

CSV_PATH = "data/standards_master_extended.csv"
EMBEDDINGS_PATH = "standards_embeddings.npy"
IS_NUMBERS_PATH = "standards_embeddings_is_numbers.csv"
MODEL_NAME = "all-MiniLM-L6-v2"


def main():
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    texts = (df["Full Title"].fillna("") + " " + df["Product Family"].fillna("")).tolist()

    print(f"Loading model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Embedding {len(texts)} standards...")
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    # Stored at half precision. The vectors are L2-normalised so every component
    # is within [-1, 1], where float16 carries about three decimal digits — finer
    # than the gaps between ranked cosine scores, and half the file and half the
    # memory on a host that has 512 MB for everything.
    np.save(EMBEDDINGS_PATH, embeddings.astype(np.float16))
    df[["IS Number"]].to_csv(IS_NUMBERS_PATH, index=False)

    print(f"\nSaved embeddings: {EMBEDDINGS_PATH} shape={embeddings.shape}")
    print(f"Saved IS Number index: {IS_NUMBERS_PATH}")


if __name__ == "__main__":
    main()
