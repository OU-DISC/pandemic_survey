"""Match and rename PDFs in papers_pdf to BibTeX ids."""
import re
import codecs
import unicodedata
import shutil
from pathlib import Path
from difflib import SequenceMatcher
from update_data import update

PDF_DIR = Path("src/data/papers_pdf")
BIB = Path("bib/references.bib")
AUTO_THRESHOLD = 0.72  # rename automatically if best score >= this and clearly ahead


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
    for e in parts:
        if not e.strip():
            continue
        m = re.match(r"@\w+\s*\{\s*([^,\s]+)", e)
        if not m:
            continue
        eid = m.group(1)
        ids.add(eid)
        author = extract_field(e, "author")
        first_author = ""
        if author:
            a0 = author.split(" and ")[0].strip()
            first_author = (
                a0.split(",")[0].strip().lower()
                if "," in a0
                else a0.split()[-1].strip().lower()
            )
        entries.append(
            {
                "id": eid,
                "title": norm(extract_field(e, "title")),
                "doi": extract_field(e, "doi").lower().strip(),
                "author": first_author,
                "year": extract_field(e, "year").strip(),
            }
        )
    return entries, ids


def score_match(stem, ent):
    stem_n = norm(stem.replace("_", " ").replace("-", " "))
    score = SequenceMatcher(None, stem_n, ent["title"]).ratio()
    fn = stem.lower()
    if ent["author"] and ent["author"] in fn:
        score += 0.15
    if ent["year"] and ent["year"] in fn:
        score += 0.1
    compact_stem = re.sub(r"[^a-z0-9]", "", stem.lower())
    compact_id = re.sub(r"[^a-z0-9]", "", ent["id"].lower())
    if compact_stem and (compact_stem == compact_id or compact_stem in compact_id or compact_id in compact_stem):
        score += 0.25
    # author_year style filenames
    if ent["author"] and ent["year"]:
        if fn.startswith(ent["author"]) and ent["year"] in fn:
            score += 0.2
    return score


def safe_pdf_name(bib_id: str) -> str:
    # Windows forbids : * ? etc. Replace colon with underscore for filesystem.
    return bib_id.replace(":", "_") + ".pdf"


def main():
    entries, ids = load_entries()
    # Also map filesystem-safe ids back to real ids
    fs_to_id = {i.replace(":", "_"): i for i in ids}

    pdfs = sorted(p for p in PDF_DIR.iterdir() if p.suffix.lower() == ".pdf")
    exact = []
    to_fix = []
    ambiguous = []
    no_match = []

    for p in pdfs:
        stem = p.stem
        if stem in ids or stem in fs_to_id:
            # if file uses underscore form of colon-id, and real id has colon,
            # SurVis looks for id.pdf with colon which can't exist on Windows —
            # keep underscore form; ensure bib id uses underscore if needed.
            exact.append(p.name)
            continue

        ranked = sorted(
            ((score_match(stem, ent), ent) for ent in entries),
            key=lambda x: x[0],
            reverse=True,
        )
        best_score, best = ranked[0]
        second = ranked[1][0] if len(ranked) > 1 else 0

        if best_score >= AUTO_THRESHOLD and best_score - second >= 0.05:
            to_fix.append((p, best["id"], best_score, best["title"]))
        elif best_score >= 0.55:
            ambiguous.append((p, ranked[:3]))
        else:
            no_match.append((p, ranked[:3]))

    print(f"PDFs: {len(pdfs)}")
    print(f"Already matching: {len(exact)}")
    print(f"Auto-rename: {len(to_fix)}")
    print(f"Ambiguous (need review): {len(ambiguous)}")
    print(f"No good match: {len(no_match)}")

    renamed = []
    skipped = []
    for p, bib_id, score, title in to_fix:
        target_name = safe_pdf_name(bib_id)
        target = PDF_DIR / target_name
        # If bib id has colon, SurVis expects id.pdf with colon — on Windows we
        # must use underscore and preferably align bib key. Prefer renaming file
        # to filesystem-safe form of exact bib id.
        if ":" in bib_id:
            # Use underscore version matching how SurVis/Windows can store it;
            # also check if underscore id exists in bib already.
            underscore_id = bib_id.replace(":", "_")
            if underscore_id in ids:
                target = PDF_DIR / f"{underscore_id}.pdf"
                bib_id = underscore_id
            else:
                target = PDF_DIR / f"{underscore_id}.pdf"
                bib_id = underscore_id  # file name only; warn below

        if target.exists() and target.resolve() != p.resolve():
            skipped.append((p.name, target.name, "target exists"))
            continue
        print(f"RENAME {p.name}")
        print(f"    -> {target.name}  (score={score:.3f})")
        print(f"       {title[:70]}")
        p.rename(target)
        renamed.append((p.name, target.name))

    if ambiguous:
        print("\n=== AMBIGUOUS (not renamed) ===")
        for p, ranked in ambiguous:
            print(f"\n{p.name}")
            for score, ent in ranked:
                print(f"  {score:.3f}  {ent['id']}  | {ent['title'][:65]}")

    if no_match:
        print("\n=== NO GOOD MATCH (not renamed) ===")
        for p, ranked in no_match:
            print(f"\n{p.name}")
            for score, ent in ranked:
                print(f"  {score:.3f}  {ent['id']}  | {ent['title'][:65]}")

    if skipped:
        print("\n=== SKIPPED ===")
        for a, b, why in skipped:
            print(f"  {a} -> {b}: {why}")

    print(f"\nRenamed: {len(renamed)}")
    update()
    print(open("src/data/generated/available_pdf.js", encoding="utf-8").read())


if __name__ == "__main__":
    main()
