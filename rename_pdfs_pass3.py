"""Third pass: match PDF stems that look like citation keys to bib ids."""
import re
from pathlib import Path
from difflib import SequenceMatcher
from update_data import update
import codecs

PDF_DIR = Path("src/data/papers_pdf")
BIB = Path("bib/references.bib")


def compact(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    text = codecs.open(BIB, "r", "utf-8-sig").read()
    ids = re.findall(r"@\w+\s*\{\s*([^,\s]+)", text)
    id_set = set(ids)
    by_compact = {}
    for i in ids:
        by_compact.setdefault(compact(i), []).append(i)

    pdfs = sorted(p for p in PDF_DIR.iterdir() if p.suffix.lower() == ".pdf")
    renamed = []
    still = []
    deleted_dups = []

    for p in pdfs:
        stem = p.stem
        if stem in id_set:
            continue
        if any(i.replace(":", "_") == stem for i in id_set):
            continue

        # delete obvious duplicate of afzal
        if "Visual Analytics Based Decision Making" in stem or stem.startswith(
            "A Visual Analytics Based Decision Making"
        ):
            if (PDF_DIR / "afzal_visual_2020.pdf").exists():
                print(f"DELETE duplicate: {p.name}")
                p.unlink()
                deleted_dups.append(p.name)
                continue

        c = compact(stem)
        # exact compact match
        if c in by_compact and len(by_compact[c]) == 1:
            bib_id = by_compact[c][0]
            target = PDF_DIR / f"{bib_id.replace(':', '_')}.pdf"
            if target.exists() and target.resolve() != p.resolve():
                print(f"DUP keep both? {p.name} vs {target.name} -> delete extra")
                p.unlink()
                deleted_dups.append(p.name)
                continue
            print(f"COMPACT {p.name} -> {target.name}")
            p.rename(target)
            renamed.append(target.name)
            continue

        # fuzzy id match
        ranked = sorted(
            ((SequenceMatcher(None, c, compact(i)).ratio(), i) for i in ids),
            reverse=True,
        )
        best_score, best_id = ranked[0]
        second = ranked[1][0] if len(ranked) > 1 else 0
        if best_score >= 0.88 and best_score - second >= 0.03:
            target = PDF_DIR / f"{best_id.replace(':', '_')}.pdf"
            if target.exists() and target.resolve() != p.resolve():
                print(f"DUP {p.name} ~= {target.name} (score={best_score:.3f}) -> delete extra")
                p.unlink()
                deleted_dups.append(p.name)
                continue
            print(f"FUZZY-ID({best_score:.3f}) {p.name} -> {target.name}")
            p.rename(target)
            renamed.append(target.name)
        else:
            still.append((p.name, ranked[:3]))

    print(f"\nRenamed: {len(renamed)}  deleted dups: {len(deleted_dups)}  still: {len(still)}")
    if still:
        print("\nStill unmatched (first 40):")
        for name, ranked in still[:40]:
            print(f"  {name}")
            for sc, i in ranked:
                print(f"     {sc:.3f}  {i}")

    update()
    pdfs_now = list(PDF_DIR.glob("*.pdf"))
    matched = sum(
        1
        for p in pdfs_now
        if p.stem in id_set or any(i.replace(":", "_") == p.stem for i in id_set)
    )
    print(f"\nTotal PDFs: {len(pdfs_now)}  matching: {matched}  non-matching: {len(pdfs_now)-matched}")


if __name__ == "__main__":
    main()
