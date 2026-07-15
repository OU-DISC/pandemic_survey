"""Second pass: rename remaining PDFs by title match to BibTeX ids."""
import re
import codecs
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from update_data import update

PDF_DIR = Path("src/data/papers_pdf")
BIB = Path("bib/references.bib")


def extract_field(entry, field):
    m = re.search(rf"{field}\s*=\s*\{{", entry, re.I)
    if not m:
        return ""
    start = m.end()
    depth = 1
    i = start
    while i < len(entry) and depth:
        if entry[i] == "{":
            depth += 1
        elif entry[i] == "}":
            depth -= 1
        i += 1
    return entry[start : i - 1]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[{}\\]", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_entries():
    text = codecs.open(BIB, "r", "utf-8-sig").read()
    parts = re.split(r"(?=@\w+\s*\{)", text)[1:]
    entries = []
    ids = set()
    by_title = {}
    for e in parts:
        if not e.strip():
            continue
        m = re.match(r"@\w+\s*\{\s*([^,\s]+)", e)
        if not m:
            continue
        eid = m.group(1)
        ids.add(eid)
        title = norm(extract_field(e, "title"))
        entries.append({"id": eid, "title": title})
        if title:
            by_title.setdefault(title, []).append(eid)
    return entries, ids, by_title


def filename_as_title(stem):
    s = stem.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return norm(s)


def main():
    entries, ids, by_title = load_entries()
    pdfs = sorted(p for p in PDF_DIR.iterdir() if p.suffix.lower() == ".pdf")

    renamed = []
    still = []
    duplicates = []

    for p in pdfs:
        stem = p.stem
        if stem in ids or stem.replace("_", ":") in ids:
            continue
        # already filesystem-safe form of an id with colon
        if any(i.replace(":", "_") == stem for i in ids):
            continue

        ft = filename_as_title(stem)

        # exact title match
        if ft in by_title and len(by_title[ft]) == 1:
            bib_id = by_title[ft][0]
            target = PDF_DIR / f"{bib_id.replace(':', '_')}.pdf"
            if target.exists() and target.resolve() != p.resolve():
                duplicates.append((p.name, target.name))
                continue
            print(f"EXACT  {p.name[:70]}")
            print(f"    -> {target.name}")
            p.rename(target)
            renamed.append(target.name)
            continue

        # fuzzy title
        ranked = sorted(
            (
                (SequenceMatcher(None, ft, ent["title"]).ratio(), ent)
                for ent in entries
            ),
            key=lambda x: x[0],
            reverse=True,
        )
        best_score, best = ranked[0]
        second = ranked[1][0] if len(ranked) > 1 else 0
        # also: filename title contained in bib title or vice versa
        contain = best["title"] in ft or ft in best["title"]
        if (best_score >= 0.85 and best_score - second >= 0.03) or (
            contain and best_score >= 0.7
        ):
            bib_id = best["id"]
            target = PDF_DIR / f"{bib_id.replace(':', '_')}.pdf"
            if target.exists() and target.resolve() != p.resolve():
                duplicates.append((p.name, target.name))
                continue
            print(f"FUZZY({best_score:.3f}) {p.name[:70]}")
            print(f"    -> {target.name}")
            print(f"       {best['title'][:70]}")
            p.rename(target)
            renamed.append(target.name)
        else:
            still.append((p, ranked[:3]))

    print(f"\nRenamed this pass: {len(renamed)}")
    print(f"Still unmatched: {len(still)}")
    print(f"Duplicates (kept original): {len(duplicates)}")

    if still:
        print("\n=== STILL UNMATCHED ===")
        for p, ranked in still:
            print(f"\n{p.name}")
            for score, ent in ranked:
                print(f"  {score:.3f}  {ent['id']}")

    if duplicates:
        print("\n=== DUPLICATES (PDF for this id already exists) ===")
        for a, b in duplicates:
            print(f"  {a[:60]}  already have {b}")

    update()
    pdfs_now = [p.stem for p in PDF_DIR.glob("*.pdf")]
    matched = sum(1 for s in pdfs_now if s in ids or any(i.replace(":", "_") == s for i in ids))
    print(f"\nTotal PDFs: {len(pdfs_now)}  matching ids: {matched}  non-matching: {len(pdfs_now)-matched}")


if __name__ == "__main__":
    main()
