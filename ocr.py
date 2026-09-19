"""Reading the scans.

3,454 of the tender documents in this corpus are scanned PDFs: a photograph of
a page with no text layer. pdfplumber returns nothing for them, so the corpus
calls them Not extractable and every coverage figure is computed over the rest.
The specification is still there, printed on the page — the document that
prompted this says "As IS:694/2010" twelve times in a procurement table.

macOS Vision does the recognition. It ships with the operating system, so this
adds no model download, no API key and no network call, and no page ever leaves
the machine.

Two rules, both of them the project's own.

OCR proposes, the register disposes. A recognised IS number is a model's guess
about digits, and inventing digits is the one thing this project must never do.
So a citation recovered from a scan is kept only when it resolves against the
register. "IS 6941" read off a page that says "IS 694" is a reading error until
something else proves otherwise, and it is dropped rather than written into the
backlog, where it would become a standard BIS is supposed to hold and does not.

And a scan that has been read keeps its own class. Every figure on this console
carries its denominator, and a document whose citations were recognised is a
weaker piece of evidence than one whose citations were read from a text layer.
The corpus says which it is rather than quietly merging them.
"""
from __future__ import annotations

import os

MAX_PAGES = 12          # a tender's standards live in its specification tables
SCALE = 2.0             # 144 dpi against a 72 pt page box
MAX_PIXELS = 40_000_000  # a malformed MediaBox should not ask for 4 GB


def _quartz():
    import Quartz
    from Foundation import NSURL
    return Quartz, NSURL


def page_images(path: str, max_pages: int = MAX_PAGES, scale: float = SCALE):
    """Rasterise the first pages of a PDF, one CGImage at a time."""
    Quartz, NSURL = _quartz()
    doc = Quartz.CGPDFDocumentCreateWithURL(NSURL.fileURLWithPath_(path))
    if doc is None:
        return
    for i in range(1, min(Quartz.CGPDFDocumentGetNumberOfPages(doc), max_pages) + 1):
        page = Quartz.CGPDFDocumentGetPage(doc, i)
        if page is None:
            continue
        box = Quartz.CGPDFPageGetBoxRect(page, Quartz.kCGPDFMediaBox)
        w, h = int(box.size.width * scale), int(box.size.height * scale)
        if w < 8 or h < 8 or w * h > MAX_PIXELS:
            continue
        ctx = Quartz.CGBitmapContextCreate(
            None, w, h, 8, 0, Quartz.CGColorSpaceCreateDeviceRGB(),
            Quartz.kCGImageAlphaNoneSkipLast,
        )
        if ctx is None:
            continue
        # A scan drawn onto a transparent context comes out as black on black.
        Quartz.CGContextSetRGBFillColor(ctx, 1, 1, 1, 1)
        Quartz.CGContextFillRect(ctx, Quartz.CGRectMake(0, 0, w, h))
        Quartz.CGContextScaleCTM(ctx, scale, scale)
        Quartz.CGContextTranslateCTM(ctx, -box.origin.x, -box.origin.y)
        Quartz.CGContextDrawPDFPage(ctx, page)
        image = Quartz.CGBitmapContextCreateImage(ctx)
        if image is not None:
            yield image


def ocr_image(image) -> str:
    import Vision
    lines: list[str] = []

    def collect(request, _error):
        for observation in request.results() or []:
            candidates = observation.topCandidates_(1)
            if candidates and len(candidates):
                lines.append(candidates[0].string())

    request = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(collect)
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    # Language correction rewrites "IS 8130" towards dictionary words. The text
    # this reads is designations and dimensions, not prose.
    request.setUsesLanguageCorrection_(False)
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, None)
    handler.performRequests_error_([request], None)
    return "\n".join(lines)


def ocr_pdf(path: str, max_pages: int = MAX_PAGES, scale: float = SCALE) -> tuple[str, int]:
    """Recognised text, and how many pages it came from."""
    pages = 0
    out = []
    for image in page_images(path, max_pages, scale):
        out.append(ocr_image(image))
        pages += 1
    return "\n".join(out), pages


def register_bases(conn) -> set[str]:
    """Every base designation the register actually holds."""
    return {r[0] for r in conn.execute('SELECT "IS Base" FROM standards') if r[0]}


def citations_from_scan(text: str, held: set[str]) -> tuple[list[str], list[str]]:
    """Citations recognised in a scan, split into the ones the register can
    confirm and the ones it cannot.

    The second list is not a backlog. A designation nobody holds, recognised
    from a photograph of a page, is far more likely to be a misread digit than
    a standard BIS forgot to publish — and the coverage backlog is a claim
    about BIS, not about our optical character recognition. It is counted and
    reported, never promoted.
    """
    from engine import _is_base, extract_citations

    kept, dropped = [], []
    for citation in extract_citations(text):
        (kept if _is_base(citation) in held else dropped).append(citation)
    return kept, dropped


def available() -> bool:
    """Whether this machine can do the recognition at all."""
    if os.uname().sysname != "Darwin":
        return False
    try:
        import Quartz  # noqa: F401
        import Vision  # noqa: F401
    except ImportError:
        return False
    return True
