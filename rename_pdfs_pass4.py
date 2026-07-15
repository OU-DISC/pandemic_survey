"""Fourth pass: match PDFs by shared year + author tokens with bib ids."""
import re
from pathlib import Path
from update_data import update
import codecs

PDF_DIR = Path("src/data/papers_pdf")
BIB = Path("bib/references.bib")


def tokens(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def year_of(s):
    years = re.findall(r"(19|20)\d{2}", s)
    return years[-1] if years else None


def main():
    text = codecs.open(BIB, "r", "utf-8-sig").read()
    ids = re.findall(r"@\w+\s*\{\s*([^,\s]+)", text)
    id_set = set(ids)

    pdfs = sorted(p for p in PDF_DIR.iterdir() if p.suffix.lower() == ".pdf")
    renamed = []
    still = []

    for p in pdfs:
        stem = p.stem
        if stem in id_set or any(i.replace(":", "_") == stem for i in id_set):
            continue

        # Only try citation-key-like names (short, has year), not long titles
        if len(stem) > 60 or stem.count("_") > 6:
            still.append(p.name)
            continue

        py = year_of(stem)
        pt = tokens(stem)
        if not py:
            still.append(p.name)
            continue

        candidates = []
        for i in ids:
            if year_of(i) != py:
                continue
            it = tokens(i)
            # require meaningful overlap beyond year
            overlap = (pt & it) - {py, "covid", "19", "the", "and", "of", "a"}
            if len(overlap) >= 2 or (
                len(overlap) >= 1 and len(pt - {py}) <= 3 and len(it - {py}) <= 4
            ):
                # jaccard on non-year tokens
                a = pt - {py}
                b = it - {py}
                if not a or not b:
                    continue
                j = len(a & b) / len(a | b)
                candidates.append((j, len(overlap), i))

        candidates.sort(reverse=True)
        if not candidates:
            still.append(p.name)
            continue

        best_j, best_ov, best_id = candidates[0]
        second_j = candidates[1][0] if len(candidates) > 1 else 0
        if best_j >= 0.5 and best_j - second_j >= 0.05:
            target = PDF_DIR / f"{best_id.replace(':', '_')}.pdf"
            if target.exists() and target.resolve() != p.resolve():
                print(f"DUP {p.name} -> delete, have {target.name}")
                p.unlink()
                continue
            print(f"TOKEN({best_j:.2f}) {p.name} -> {target.name}")
            p.rename(target)
            renamed.append(target.name)
        else:
            still.append(p.name)
            if candidates:
                print(f"SKIP {p.name}")
                for j, ov, i in candidates[:3]:
                    print(f"   {j:.2f} ov={ov} {i}")

    print(f"\nRenamed: {len(renamed)}  still-ish: {len(still)}")
    update()
    pdfs_now = list(PDF_DIR.glob("*.pdf"))
    matched = sum(
        1
        for p in pdfs_now
        if p.stem in id_set or any(i.replace(":", "_") == p.stem for i in id_set)
    )
    print(f"Total: {len(pdfs_now)} matching: {matched} non-matching: {len(pdfs_now)-matched}")
    # list non-matching
    non = [
        p.name
        for p in pdfs_now
        if p.stem not in id_set and not any(i.replace(":", "_") == p.stem for i in id_set)
    ]
    print("\nNon-matching files:")
    for n in non:
        print(" ", n)


if __name__ == "__main__":
    main()
