"""Generate PNG thumbnails from matched PDFs for SurVis papers_img."""
import re
import codecs
from pathlib import Path
import fitz  # PyMuPDF
from update_data import update

PDF_DIR = Path("src/data/papers_pdf")
IMG_DIR = Path("src/data/papers_img")
BIB = Path("bib/references.bib")
MAX_WIDTH = 300  # SurVis-friendly thumbnail width


def main():
    ids = set(
        re.findall(
            r"@\w+\s*\{\s*([^,\s]+)",
            codecs.open(BIB, "r", "utf-8-sig").read(),
        )
    )
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    created = skipped = failed = unmatched_pdf = 0

    for pdf in pdfs:
        stem = pdf.stem
        # only thumbnails for PDFs that match a bib id
        if stem not in ids and not any(i.replace(":", "_") == stem for i in ids):
            unmatched_pdf += 1
            continue

        out = IMG_DIR / f"{stem}.png"
        if out.exists():
            skipped += 1
            continue

        try:
            doc = fitz.open(pdf)
            if doc.page_count < 1:
                doc.close()
                failed += 1
                continue
            page = doc.load_page(0)
            # scale so width ~= MAX_WIDTH
            zoom = MAX_WIDTH / page.rect.width
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pix.save(str(out))
            doc.close()
            created += 1
            if created % 25 == 0:
                print(f"  ... {created} thumbnails")
        except Exception as e:
            failed += 1
            msg = f"FAIL {pdf.name}: {e}"
            print(msg.encode("ascii", "replace").decode("ascii"))

    update()
    imgs = list(IMG_DIR.glob("*.png"))
    matched_img = sum(
        1
        for p in imgs
        if p.stem in ids or any(i.replace(":", "_") == p.stem for i in ids)
    )
    print(f"Created: {created}")
    print(f"Skipped (already exist): {skipped}")
    print(f"Failed: {failed}")
    print(f"PDFs without bib match (ignored): {unmatched_pdf}")
    print(f"Total PNGs: {len(imgs)}  matching bib: {matched_img}")


if __name__ == "__main__":
    main()
