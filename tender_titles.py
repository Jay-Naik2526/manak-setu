"""Readable names for tender documents.

The corpus identifies each tender by the filename it was downloaded as, which is
what a procurement portal happens to serve: "1722334397.pdf",
"Execution_Electrical_Civil_Works_Ground_", "bo5iuhy.pdf". Those are honest but
unreadable, and a screen full of them looks like a directory listing rather than
a corpus of public documents.

This derives a display name *from the filename only*. It is formatting, not
authorship:

  * extension, epoch prefixes and UUIDs are stripped — they identify the
    download, not the document
  * snake_case, kebab-case and camelCase are split into words
  * procurement abbreviations that appear in these filenames are expanded
    (NIT, NIQ, LT, HT, Vol) — each one standard in Indian tendering
  * the result is title-cased, with acronyms left uppercase

Where the filename carries no words at all — a bare number, a UUID, a random
string — nothing is invented. The document is shown as "Untitled tender" with
its identifier, because the alternative is to make up a subject for a real
government document, and a plausible invented title is worse than an ugly true
one. The original identifier is always kept and is what links to the source.
"""

import re

# Abbreviations as they appear in these filenames. Each is standard usage in
# Indian public procurement; none is a guess about what the tender is for.
ABBREVIATIONS = {
    "nit": "Notice Inviting Tender",
    "niq": "Notice Inviting Quotation",
    "nib": "Notice Inviting Bid",
    "eoi": "Expression of Interest",
    "rfp": "Request for Proposal",
    "boq": "Bill of Quantities",
    "loa": "Letter of Award",
    "lt": "LT",
    "ht": "HT",
    "pvc": "PVC",
    "gi": "GI",
    "led": "LED",
    "rcc": "RCC",
    "hdpe": "HDPE",
    "xlpe": "XLPE",
    "vol": "Volume",
    "sec": "Section",
    "doc": "Document",
    "tenderdoc": "Tender Document",
    "spec": "Specification",
    "tech": "Technical",
    "addendum": "Addendum",
    "corrigendum": "Corrigendum",
}

ALWAYS_UPPER = {"LT", "HT", "PVC", "GI", "LED", "RCC", "HDPE", "XLPE", "IS", "BIS",
                "II", "III", "IV", "VI", "VII", "VIII", "IX"}

SMALL_WORDS = {"and", "for", "of", "the", "to", "in", "with", "under", "on", "at"}

# Procurement vocabulary that will not appear in a BIS standard title but is
# ordinary tender language.
PROCUREMENT_WORDS = {
    "tender", "tenders", "document", "documents", "notice", "inviting", "quotation",
    "bid", "bids", "bidding", "enquiry", "volume", "part", "section", "annexure",
    "schedule", "compliance", "technical", "specification", "specifications",
    "execution", "works", "work", "supply", "supplies", "revised", "revision",
    "addendum", "corrigendum", "amendment", "draft", "final", "general",
    "conditions", "contract", "scope", "estimate", "quantities", "civil",
    "electrical", "mechanical", "ground", "floor", "package", "division",
    "department", "board", "corporation", "council", "municipal", "authority",
    "project", "phase", "zone", "circle", "unit", "open", "limited", "global",
}

_VOCAB: set[str] | None = None


def vocabulary(db_path: str = "manak_setu.db") -> set[str]:
    """Words BIS itself uses, read from the register.

    Heuristics cannot separate "Iuhy" from a real word — both are alphabetic and
    both have vowels. A dictionary can, and there is a good one already in the
    database: 2,087 standard titles, their product families, and the certification
    product descriptions. A filename fragment is treated as a word only if BIS
    writes it somewhere, or it is ordinary tender vocabulary."""
    global _VOCAB
    if _VOCAB is not None:
        return _VOCAB
    words = set(PROCUREMENT_WORDS)
    try:
        import sqlite3

        conn = sqlite3.connect(db_path)
        try:
            for query in ('SELECT "Full Title" FROM standards',
                          'SELECT DISTINCT "Product Family" FROM standards',
                          'SELECT "Product Description" FROM certification_rules'):
                for (value,) in conn.execute(query):
                    words.update(re.findall(r"[a-z]{3,}", str(value or "").lower()))
        finally:
            conn.close()
    except Exception:                                    # noqa: BLE001
        pass                                             # vocabulary stays minimal
    _VOCAB = words
    return _VOCAB


UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{6,12}\b", re.I)
EPOCH_RE = re.compile(r"\b1[0-9]{9}\b")                 # download timestamps
TIMESTAMP_RE = re.compile(r"\b20\d{2}[_-]\d{2}[_-]\d{2}([_-]\d{2}){0,3}\b")
EXT_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip|pd)$", re.I)


def _split_words(text: str) -> list[str]:
    text = re.sub(r"[_\-.]+", " ", text)
    # camelCase and ALLCAPSWord boundaries
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", text)
    return [w for w in re.split(r"\s+", text) if w]


def _cased(word: str, first: bool) -> str:
    upper = word.upper()
    if upper in ALWAYS_UPPER:
        return upper
    low = word.lower()
    if low in SMALL_WORDS and not first:
        return low
    return word[:1].upper() + word[1:].lower() if word.isalpha() else word


def display_title(identifier: str, product_family: str | None = None) -> dict:
    """A readable name, plus whether it actually says anything."""
    raw = str(identifier or "").strip()
    if not raw:
        return {"title": "Untitled tender", "derived": False, "identifier": raw}

    text = EXT_RE.sub("", raw)
    text = UUID_RE.sub(" ", text)
    text = TIMESTAMP_RE.sub(" ", text)
    text = EPOCH_RE.sub(" ", text)

    words = _split_words(text)

    # Keep only tokens that are actually words. Download filenames are full of
    # hex fragments and random prefixes — "bo5iuhy", "1tlVzErH", "acf8a4cdeab" —
    # and letting those through produced titles like "Bill of Iuhy", which reads
    # as though the system invented a subject. A token survives if it is a known
    # abbreviation, or a pronounceable word, or a number that belongs to the
    # word before it (Volume 3, Part 2).
    ORDINAL_OWNERS = {"volume", "part", "section", "vol", "sec", "no"}
    vocab = vocabulary()
    kept: list[str] = []
    for i, w in enumerate(words):
        low = w.lower()
        if low in ABBREVIATIONS:
            kept.append(ABBREVIATIONS[low])
            continue
        if w.isdigit():
            prev = kept[-1].lower() if kept else ""
            if prev in ORDINAL_OWNERS and len(w) <= 3:
                kept.append(w)
            continue
        if not w.isalpha():
            continue                      # mixed letters and digits: an identifier
        if len(w) < 3:
            continue
        if low not in vocab:
            continue                      # not a word BIS or a tender would use
        kept.append(w)
    expanded = kept

    # A name needs at least one real word; "bo5iuhy" is not one.
    meaningful = [w for w in expanded if re.search(r"[A-Za-z]{3,}", w)]
    if not meaningful:
        short = raw[:26] + ("…" if len(raw) > 26 else "")
        family = (product_family or "").strip()
        label = "Untitled tender"
        if family and family.lower() not in ("n/a", "unclassified", "nan"):
            label = f"Untitled {family[0].lower() + family[1:]} tender"
        return {"title": label, "derived": False, "identifier": short}

    # A title should not open or close on a conjunction: "pqr_and_technical_spec"
    # left "And Technical Specification" once the identifier fragment was dropped.
    while expanded and expanded[0].lower() in SMALL_WORDS:
        expanded.pop(0)
    while expanded and expanded[-1].lower() in SMALL_WORDS:
        expanded.pop()
    if not expanded:
        family = (product_family or "").strip()
        label = "Untitled tender"
        if family and family.lower() not in ("n/a", "unclassified", "nan"):
            label = f"Untitled {family[0].lower() + family[1:]} tender"
        return {"title": label, "derived": False, "identifier": raw[:26]}

    parts = " ".join(expanded).split()
    title = " ".join(_cased(w, i == 0) for i, w in enumerate(parts))
    title = re.sub(r"\s{2,}", " ", title).strip(" -–—,")
    # Documents whose whole name is generic gain nothing from it on its own.
    if title.lower() in ("tender document", "document", "tender", "volume",
                         "addendum", "corrigendum", "technical specification",
                         "notice inviting tender", "specification"):
        family = (product_family or "").strip()
        if family and family.lower() not in ("n/a", "unclassified", "nan"):
            title = f"{title} — {family}"
    return {"title": title[:90], "derived": True, "identifier": raw}


if __name__ == "__main__":
    import sqlite3

    conn = sqlite3.connect("manak_setu.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT "Tender ID", "Product Family" FROM tenders').fetchall()
    derived = 0
    for r in rows:
        d = display_title(r["Tender ID"], r["Product Family"])
        derived += d["derived"]
        if rows.index(r) < 22:
            flag = "  " if d["derived"] else "··"
            print(f" {flag} {d['title'][:56]:<58} {r['Tender ID'][:34]}")
    print(f"\n{derived} of {len(rows)} filenames carry a readable name; "
          f"{len(rows) - derived} are shown as untitled rather than invented")
